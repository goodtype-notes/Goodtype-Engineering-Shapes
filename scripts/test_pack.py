"""Regression checks for strict validation and deterministic packaging."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from zipfile import ZipFile

from package import package
from validate import shape_object, validate, validate_stretch


class ValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        manifest, files = validate(report=False)
        self.manifest = copy.deepcopy(manifest)
        for name, path in files.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)

    def save(self, path, data):
        (self.root / path).write_text(json.dumps(data), encoding="utf-8")

    def test_manifest_rejects_privileges_and_locale_mismatch(self):
        mutations = [
            {"commands": [{"id": "run"}]},
            {"entrypoint": "program.exe"},
            {"strings": {"en": {"name": "Name", "extra": "Extra"}, "de": {"name": "Name"}}},
            {"contents": {"shapes": ["content/shapes/../example.json"]}},
            {"contents": {"shapes": ["content/shapes/nested/example.json"]}},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.save("goodtype-addon.json", self.manifest | mutation)
                with self.assertRaises(ValueError):
                    validate(self.root, report=False)

    def test_duplicate_keys(self):
        with (self.root / "goodtype-addon.json").open(encoding="utf-8") as stream:
            source = stream.read()
        (self.root / "goodtype-addon.json").write_text('{"id": "other",' + source[1:], encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            validate(self.root, report=False)

    def test_geometry_or_spacing_bounds(self):
        contents = self.manifest["contents"]
        if "shapes" in contents:
            path = contents["shapes"][0]
            data = json.loads((self.root / path).read_text(encoding="utf-8"))
            data["items"][0]["objects"][0]["geometry"]["end"]["x"] = 1000
        else:
            path = contents["templates"][0]
            data = json.loads((self.root / path).read_text(encoding="utf-8"))
            data["templates"][0]["template"]["elements"][0]["spacingPt"] = 72 / 25.4
        self.save(path, data)
        with self.assertRaisesRegex(ValueError, "Invalid number"):
            validate(self.root, report=False)

    def test_two_port_items_have_stretch_and_native_arrows_use_line_ports(self):
        declared = []
        native = {"flow-arrow", "double-arrow", "force-arrow"}
        for path in self.manifest["contents"]["shapes"]:
            items = json.loads((self.root / path).read_text(encoding="utf-8"))["items"]
            for item in items:
                if len(item.get("ports", [])) == 2:
                    validate_stretch(item)
                    declared.append(item["id"])
                if item["id"] in native:
                    native.remove(item["id"])
                    self.assertNotIn("ports", item)
                    self.assertNotIn("stretch", item)
                    self.assertEqual(item["objects"][0]["geometry"]["kind"], "line")
        self.assertEqual(len(declared), 21)
        self.assertFalse(native)

    def test_stretch_rejects_bad_axis_roles_sockets_and_floors(self):
        path = next(path for path in self.manifest["contents"]["shapes"] if path.endswith("circuits.json"))
        data = json.loads((self.root / path).read_text(encoding="utf-8"))
        item = next(item for item in data["items"] if item["id"] == "resistor")
        original = item["stretch"]
        for change in ({"axis": [1, 0]}, {"axis": [False, 1]}, {"roles": ["body"]},
                       {"mode": "span"}, {"leadFloors": [100, 4]}, {"virtualSockets": [12, 36]}):
            with self.subTest(change=change):
                item["stretch"] = original | change
                self.save(path, data)
                with self.assertRaises(ValueError):
                    validate(self.root, report=False)

    def test_item_ports_accept_stroke_allowance_and_reject_invalid_values(self):
        path = self.manifest["contents"]["shapes"][0]
        data = json.loads((self.root / path).read_text(encoding="utf-8"))
        item = data["items"][0]
        item.pop("stretch", None)
        item["ports"] = [{"x": -0.5, "y": 12}]
        self.save(path, data)
        validate(self.root, report=False)
        for ports in ([{"x": -0.51, "y": 12}], [{"x": "NaN", "y": 12}], item["ports"] * 33):
            with self.subTest(ports=ports):
                item["ports"] = ports
                self.save(path, data)
                with self.assertRaises(ValueError):
                    validate(self.root, report=False)

    def test_relative_handles_determine_curve_bounds(self):
        g = dict(kind="spline", closed=False, nodes=[
            {"point": {"x": 10, "y": 4}, "handleOut": {"x": 4, "y": -8}},
            {"point": {"x": 22, "y": 4}, "handleIn": {"x": -4, "y": -8}},
        ])
        obj = dict(type="shape", x=0, y=2, geometry=g, style={})
        # The controls extend above the item, while the curve is tangent to its edge.
        shape_object(obj, 24, 12)
        obj["y"] = 1
        with self.assertRaisesRegex(ValueError, "Invalid number"):
            shape_object(obj, 24, 12)


    def test_fill_follows_the_pen_or_a_fixed_colour(self):
        obj = dict(type="shape", x=0, y=0, geometry=dict(kind="ellipse", widthPt=6, heightPt=6), style={})
        for fill in ("pen", None, "#20242c"):
            shape_object(obj | {"style": {"fillColor": fill}}, 6, 6)
        with self.assertRaisesRegex(ValueError, "hex"):
            shape_object(obj | {"style": {"fillColor": "ink"}}, 6, 6)

    def test_labels_overhang_by_half_the_larger_dimension(self):
        label = dict(type="typst", x=-24, y=-24, source="$R$", layoutWidthPt=24, scale=1)
        shape_object(label, 48, 16)
        with self.assertRaisesRegex(ValueError, "Invalid number"):
            shape_object(label | {"x": -25}, 48, 16)

    def test_shape_caps_match_geometry_and_enum(self):
        point = lambda x, y: {"x": x, "y": y}
        nodes = [{"point": point(2, 2)}, {"point": point(10, 2)}, {"point": point(6, 10)}]
        geometries = [
            (dict(kind="line", start=point(2, 2), end=point(10, 2)), True),
            (dict(kind="spline", nodes=nodes, closed=False), True),
            (dict(kind="spline", nodes=nodes, closed=True), False),
            (dict(kind="ellipse", widthPt=10, heightPt=10), False),
            (dict(kind="rectangle", widthPt=10, heightPt=10, cornerRadiusPt=0), False),
        ]
        for geometry, supports_caps in geometries:
            for key in ("startCap", "endCap"):
                for cap in ("none", "arrow", "open", "dot", "bar", "triangle", None, []):
                    with self.subTest(geometry=geometry, key=key, cap=cap):
                        obj = dict(type="shape", x=0, y=0, geometry=geometry, style={key: cap})
                        if cap == "none" or (supports_caps and cap in ("arrow", "open", "dot", "bar")):
                            shape_object(obj, 12, 12)
                        else:
                            with self.assertRaisesRegex(ValueError, "[Cc]ap"):
                                shape_object(obj, 12, 12)

    def test_package_is_reproducible_and_extracted_content_validates(self):
        archive = package()
        expected = hashlib.sha256(archive.read_bytes()).hexdigest()
        package()
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), expected)
        self.assertEqual((archive.parent / "SHA256SUMS").read_text().split()[0], expected)
        with tempfile.TemporaryDirectory() as destination:
            with ZipFile(archive) as zipped:
                self.assertIsNone(zipped.testzip())
                self.assertTrue(all(name.startswith(archive.stem + "/") for name in zipped.namelist()))
                zipped.extractall(destination)
            validate(Path(destination) / archive.stem, report=False)
