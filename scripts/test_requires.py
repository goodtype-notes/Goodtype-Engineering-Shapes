"""Pinned host requirement conformance and package feature coverage."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = json.loads((ROOT / "fixtures/addon-requires/manifests.json").read_text(encoding="utf-8"))
HOST_FEATURES = set(next(row for row in FIXTURES if row["name"] == "known")["manifest"]["requires"])


def outcome(manifest):
    features = manifest.get("requires", [])
    if (not isinstance(features, list) or len(features) > 16
            or any(not isinstance(f, str) or len(f) > 48
                   or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", f) for f in features)
            or len(set(features)) != len(features)):
        return "invalid"
    missing = sorted(set(features) - HOST_FEATURES)
    return "missing:" + ",".join(missing) if missing else "accepted"


def require_features(manifest, used):
    if outcome(manifest) != "accepted":
        raise ValueError("Unsupported host requirements: " + outcome(manifest))
    missing = used - set(manifest.get("requires", []))
    if missing:
        raise ValueError("Undeclared host features: " + ", ".join(sorted(missing)))


class RequirementTests(unittest.TestCase):
    def test_host_fixtures(self):
        for row in FIXTURES:
            with self.subTest(row=row["name"]):
                self.assertEqual(outcome(row["manifest"]), row["expected"])

    def test_package(self):
        manifest = json.loads((ROOT / "goodtype-addon.json").read_text(encoding="utf-8"))
        used = used_features(manifest)
        self.assertTrue(used, "Feature detection must inspect shipped payloads")
        require_features(manifest, used)
        for feature in used:
            with self.subTest(omitted=feature), self.assertRaisesRegex(ValueError, feature):
                require_features(dict(manifest, requires=[f for f in manifest["requires"] if f != feature]), used)
        with self.assertRaisesRegex(ValueError, "future-feature"):
            require_features(dict(manifest, requires=["future-feature"]), used)


def used_features(manifest):
    used = set()

    def visit(value):
        if isinstance(value, dict):
            if value.keys() & {"startCap", "endCap"}:
                used.add("end-caps")
            if "stretch" in value:
                used.add("group-stretch")
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for files in manifest["contents"].values():
        for file in files:
            visit(json.loads((ROOT / file).read_text(encoding="utf-8")))
    return used


if __name__ == "__main__":
    unittest.main()
