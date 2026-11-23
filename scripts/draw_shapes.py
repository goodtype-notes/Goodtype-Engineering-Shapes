"""Build the engineering artwork from editable point and curve definitions."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRINGS = {"en": {"name": "Engineering Shapes"}, "de": {"name": "Technische Symbole"}}
LIBRARIES = {}

def point(x, y):
    return dict(x=x, y=y)

def shape(x, y, kind, style=None, **geometry):
    return dict(type="shape", x=x, y=y, geometry=dict(kind=kind, **geometry), style=style or {})

def line(x, y, u, v):
    return shape(x, y, "line", start=point(0, 0), end=point(u-x, v-y))

def rect(x, y, w, h, r=0):
    return shape(x, y, "rectangle", widthPt=w, heightPt=h, cornerRadiusPt=r)

def ellipse(x, y, w, h=None, fill=None):
    return shape(x, y, "ellipse", {"fillColor": fill} if fill else None, widthPt=w, heightPt=h or w)

def paths(data):
    """Translate absolute M/L/C/Z drawing instructions into core-relative handles."""
    tokens = iter(re.findall(r"[MLCZ]|-?\d+(?:\.\d+)?", data))
    nodes = []
    result = []

    def read_point():
        return point(float(next(tokens)), float(next(tokens)))

    def relative(control, anchor):
        return point(control["x"]-anchor["x"], control["y"]-anchor["y"])

    def flush(closed=False):
        if len(nodes) == 2 and not closed and all(len(node) == 1 for node in nodes):
            result.append(line(*nodes[0]["point"].values(), *nodes[1]["point"].values()))
        elif nodes:
            # A cubic may already end at its first knot. Keep the incoming tangent.
            if closed and nodes[-1]["point"] == nodes[0]["point"]:
                last = nodes.pop()
                if "handleIn" in last:
                    nodes[0]["handleIn"] = last["handleIn"]
            result.append(shape(0, 0, "spline", nodes=list(nodes), closed=closed))
        nodes.clear()

    for command in tokens:
        if command == "M":
            flush()
            nodes.append(dict(point=read_point()))
        elif command == "L":
            nodes.append(dict(point=read_point()))
        elif command == "C":
            control1, control2, end = read_point(), read_point(), read_point()
            nodes[-1]["handleOut"] = relative(control1, nodes[-1]["point"])
            nodes.append(dict(point=end, handleIn=relative(control2, end)))
        elif command == "Z":
            flush(True)
        else:
            raise ValueError(f"Unexpected drawing instruction: {command}")
    flush()
    return result

def library(key, en, de):
    label = f"lib-{key}"
    STRINGS["en"][label], STRINGS["de"][label] = en, de
    result = dict(id=key, label=label, items=[])
    LIBRARIES[key] = result
    return result["items"]

def add(key, en, de, search_en, search_de, w, h, drawing="", *objects):
    search = key + "-search"
    STRINGS["en"].update({key: en, search: search_en})
    STRINGS["de"].update({key: de, search: search_de})
    items.append(dict(id=key, label=key, search=search, widthPt=w, heightPt=h,
                      objects=paths(drawing) + list(objects)))

items = library("circuits", "Circuits", "Schaltungen")
add("resistor", "Resistor", "Widerstand", "IEC ohm passive", "IEC Ohm Bauteil", 48, 24,
    "M0 12 L12 12 M36 12 L48 12", rect(12, 6, 24, 12))
add("capacitor", "Capacitor", "Kondensator", "capacitance plates", "Kapazität Platten", 48, 24,
    "M0 12 L20 12 M20 3 L20 21 M28 3 L28 21 M28 12 L48 12")
add("polarized-capacitor", "Polarized capacitor", "Gepolter Kondensator", "electrolytic capacitance positive", "Elko Elektrolytkondensator Pluspol", 48, 32,
    "M0 16 L20 16 M20 7 L20 25 M30 7 C25 11 25 21 30 25 M26.25 16 L48 16 M10 8 L16 8 M13 5 L13 11")
add("inductor", "Inductor", "Spule", "coil inductance choke", "Induktivität Wicklung Drossel", 48, 24,
    "M0 12 L8 12 C8 0 16 0 16 12 C16 0 24 0 24 12 C24 0 32 0 32 12 C32 0 40 0 40 12 L48 12")
diode = "M0 16 L16 16 M16 7 L32 16 L16 25 Z M32 16 L48 16"
add("diode", "Diode", "Diode", "rectifier anode cathode", "Gleichrichter Anode Kathode", 48, 32,
    diode + " M32 7 L32 25")
add("led", "LED", "Leuchtdiode", "light emitting diode", "LED Licht Halbleiter", 48, 36,
    "M0 24 L16 24 M16 15 L32 24 L16 33 Z M32 15 L32 33 M32 24 L48 24 "
    "M22 13 L31 4 M26 4 L31 4 L31 9 M32 14 L41 5 M36 5 L41 5 L41 10")
add("zener", "Zener diode", "Z-Diode", "zener regulator breakdown", "Zenerdiode Spannungsstabilisierung Durchbruch", 48, 32,
    diode + " M36 7 L32 7 L32 25 L28 25")
source = "M0 16 L12 16 M36 16 L48 16 "
add("dc-source", "DC voltage source", "Gleichspannungsquelle", "voltage supply DC plus minus", "Gleichspannung DC Plus Minus", 48, 32,
    source + "M15 16 L21 16 M18 13 L18 19 M27 16 L33 16", ellipse(12, 4, 24))
add("ac-source", "AC voltage source", "Wechselspannungsquelle", "sinusoidal voltage generator", "Wechselspannung Sinus Generator", 48, 32,
    source + "M16 16 C20 4 24 16 24 16 C24 16 28 28 32 16", ellipse(12, 4, 24))
add("current-source", "Current source", "Stromquelle", "current supply arrow", "Konstantstrom Stromversorgung Pfeil", 48, 32,
    source + "M16 16 L32 16 M27 12 L32 16 L27 20", ellipse(12, 4, 24))
add("battery", "Battery", "Batterie", "cell DC supply", "Zelle Gleichspannung Versorgung", 48, 24,
    "M0 12 L12 12 M12 3 L12 21 M19 7 L19 17 M26 3 L26 21 M33 7 L33 17 M33 12 L48 12")
add("ground", "Ground", "Masse", "GND earth reference", "GND Erdung Bezugspotenzial", 24, 24,
    "M12 0 L12 12 M2 12 L22 12 M6 16 L18 16 M9 20 L15 20")
add("open-switch", "Open switch", "Offener Schalter", "SPST disconnect contact", "Öffner Schaltkontakt Unterbrecher", 48, 24,
    "M0 16 L10 16 M14 15 L34 4 M38 16 L48 16", ellipse(10, 14, 4), ellipse(34, 14, 4))
add("push-button", "Push button", "Taster", "normally open momentary contact", "Schließer Drucktaster Tastkontakt", 48, 28,
    "M0 20 L10 20 M38 20 L48 20 M12 13 L36 13 M24 4 L24 13 M19 4 L29 4",
    ellipse(10, 18, 4), ellipse(34, 18, 4))
add("lamp", "Lamp", "Lampe", "bulb indicator light", "Glühlampe Leuchte Anzeige", 48, 32,
    source + "M16 8 L32 24 M32 8 L16 24", ellipse(12, 4, 24))
add("fuse", "Fuse", "Sicherung", "overcurrent protection cartridge", "Schmelzsicherung Überstrom Schutz", 48, 24,
    "M0 12 L48 12", rect(12, 6, 24, 12))
add("transformer", "Transformer", "Transformator", "coupled coils magnetic core", "Trafo Wicklungen Magnetkern", 56, 48,
    "M0 8 L12 8 C23 8 23 16 12 16 C23 16 23 24 12 24 C23 24 23 32 12 32 C23 32 23 40 12 40 L0 40 "
    "M56 8 L44 8 C33 8 33 16 44 16 C33 16 33 24 44 24 C33 24 33 32 44 32 C33 32 33 40 44 40 L56 40 "
    "M26 6 L26 42 M30 6 L30 42")
add("op-amp", "Operational amplifier", "Operationsverstärker", "op amp differential gain", "OPV OPAMP Differenzverstärker Verstärkung", 56, 48,
    "M0 12 L12 12 M0 36 L12 36 M12 3 L44 24 L12 45 Z M44 24 L56 24 "
    "M16 15 L22 15 M19 12 L19 18 M16 33 L22 33")
transistor = "M0 24 L17 24 M17 13 L17 35 M17 20 L32 12 L32 0 M17 28 L32 36 L32 48 "
add("npn", "NPN transistor", "NPN-Transistor", "BJT bipolar emitter collector base", "Bipolartransistor Emitter Kollektor Basis", 48, 48,
    transistor + "M24 27 L30 35 L20 34", ellipse(8, 6, 36))
add("pnp", "PNP transistor", "PNP-Transistor", "BJT bipolar emitter collector base", "Bipolartransistor Emitter Kollektor Basis", 48, 48,
    transistor + "M24 37 L19 29 L29 30", ellipse(8, 6, 36))
add("n-mosfet", "N-channel MOSFET", "N-Kanal-MOSFET", "NMOS enhancement field effect gate drain source", "NMOS Anreicherung Feldeffekttransistor Gate Drain Source", 48, 48,
    "M0 24 L14 24 M14 12 L14 36 M20 11 L20 18 M20 21 L20 27 M20 30 L20 37 "
    "M20 14 L32 14 L32 0 M20 34 L32 34 L32 48 M32 34 L32 24 L21 24 M25 21 L21 24 L25 27")
add("junction", "Junction dot", "Verbindungspunkt", "node connected wires", "Knoten Leiter Kreuzung", 24, 24,
    "M0 12 L24 12 M12 0 L12 24", ellipse(9, 9, 6, fill="#20242c"))
add("terminal", "Terminal", "Anschlussklemme", "open terminal pin connector", "Klemme Anschluss Pin", 32, 24,
    "M0 12 L22 12", ellipse(22, 7, 10))

items = library("logic", "Logic gates", "Logikgatter")
and_gate = "M12 4 L26 4 C50 4 50 36 26 36 L12 36 Z M0 12 L12 12 M0 28 L12 28 "
or_gate = "M11 4 C30 4 35 7 44 20 C35 33 30 36 11 36 C19 26 19 14 11 4 Z M0 12 L15.7 12 M0 28 L15.7 28 "
xor_line = "M5 4 C13 14 13 26 5 36 "
for key, en, de, se, sd, outline, bubble in [
    ("and", "AND", "UND", "conjunction logic", "Konjunktion Logik", and_gate, False),
    ("or", "OR", "ODER", "disjunction logic", "Disjunktion Logik", or_gate, False),
    ("nand", "NAND", "NICHT-UND", "negated conjunction", "negierte Konjunktion NAND", and_gate, True),
    ("nor", "NOR", "NICHT-ODER", "negated disjunction", "negierte Disjunktion NOR", or_gate, True),
    ("xor", "XOR", "Exklusiv-ODER", "exclusive or parity", "XOR Antivalenz Parität", or_gate + xor_line, False),
    ("xnor", "XNOR", "Äquivalenzgatter", "exclusive nor equivalence", "XNOR Gleichheit Exklusiv-NICHT-ODER", or_gate + xor_line, True),
]:
    if key in {"xor", "xnor"}:
        outline = outline.replace("L15.7 12", "L9.7 12").replace("L15.7 28", "L9.7 28")
    output = "M50 20 L60 20" if bubble else "M44 20 L60 20"
    add(key, en, de, se, sd, 60, 40, outline + output, *([ellipse(44, 17, 6)] if bubble else []))
for key, en, de, se, sd, bubble in [
    ("not", "NOT", "NICHT", "inverter negation", "Inverter Negation", True),
    ("buffer", "Buffer", "Puffer", "noninverting driver", "Treiber nichtinvertierend", False),
]:
    add(key, en, de, se, sd, 60, 40, "M0 20 L12 20 M12 5 L44 20 L12 35 Z "
        + ("M50 20 L60 20" if bubble else "M44 20 L60 20"),
        *([ellipse(44, 17, 6)] if bubble else []))
add("d-flip-flop", "D flip-flop", "D-Flipflop", "clocked latch register memory", "Taktregister Speicher Kippstufe", 60, 40,
    "M0 12 L12 12 M0 28 L12 28 M12 24 L18 28 L12 32 M48 12 L60 12 "
    "M19 8 L19 17 C29 17 29 8 19 8 M34 12 C34 6 42 6 42 12 C42 18 34 18 34 12 M39 14 L43 18",
    rect(12, 2, 36, 36))
add("multiplexer", "Multiplexer", "Multiplexer", "mux signal selector", "MUX Datenwähler Umschalter", 60, 48,
    "M0 12 L12 12 M0 20 L12 20 M0 28 L12 28 M0 36 L12 36 M12 3 L44 13 L44 35 L12 45 Z "
    "M44 24 L60 24 M28 40 L28 48 M22 30 L22 18 L28 26 L34 18 L34 30")

items = library("mechanics", "Mechanics", "Mechanik")
hatches = " ".join(f"M{x} {y} L{x-5} {y+6}" for x, y in [(12,32),(20,32),(28,32),(36,32)])
add("fixed-support", "Fixed support", "Einspannung", "clamped wall cantilever", "eingespannt Kragarm Wand", 48, 40,
    "M16 3 L16 37 M16 20 L48 20 " + " ".join(f"M16 {y} L8 {y+5}" for y in (5,11,17,23,29,35)))
add("pin-support", "Pin support", "Festlager", "pinned hinged bearing", "Gelenklager Gelenk Auflager", 48, 40,
    "M24 0 L24 10 M24 10 L10 32 L38 32 Z M7 32 L41 32 " + hatches)
add("roller-support", "Roller support", "Loslager", "rolling movable bearing", "Rollenlager verschiebliches Auflager", 48, 40,
    "M24 0 L24 8 M24 8 L10 25 L38 25 Z M7 32 L41 32 " + hatches,
    *[ellipse(x, 25, 7) for x in (12,20.5,29)])
add("force-arrow", "Force arrow", "Kraftpfeil", "load force vector", "Last Vektor Einzelkraft", 48, 24,
    "M0 12 L48 12 M39 7 L48 12 L39 17")
add("moment-arrow", "Moment arrow", "Momentenpfeil", "torque curved rotation", "Drehmoment Rotation Biegemoment", 44, 40,
    "M35 29 C44 14 32 4 22 4 C10 4 4 13 6 23 C8 31 14 36 22 36 M15 30 L22 36 L14 39")
add("distributed-load", "Distributed load", "Streckenlast", "uniform load beam", "Gleichlast Linienlast Balken", 56, 36,
    "M8 4 L48 4 M0 32 L56 32 " + " ".join(f"M{x} 4 L{x} 26 M{x-3} 22 L{x} 26 L{x+3} 22" for x in (8,18,28,38,48)))
add("spring", "Spring", "Feder", "linear stiffness elastic", "Schraubenfeder Steifigkeit elastisch", 56, 24,
    "M0 12 L10 12 L14 4 L20 20 L26 4 L32 20 L38 4 L44 20 L48 12 L56 12")
add("damper", "Damper", "Dämpfer", "dashpot viscous piston", "Dämpfung Kolben Stoßdämpfer", 56, 24,
    "M0 12 L24 12 M24 5 L24 19 M17 3 L39 3 L39 21 L17 21 M39 12 L56 12")
add("mass-block", "Mass block", "Masseblock", "lumped mass dynamics", "Masse Körper Dynamik", 48, 32,
    "M18 21 L18 12 M18 16 C19 11 24 11 24 16 L24 21 M24 16 C25 11 30 11 30 16 L30 21", rect(4, 4, 40, 24))
add("pulley", "Pulley", "Seilrolle", "sheave rope wheel", "Umlenkrolle Seil Flaschenzug", 48, 48,
    "M24 0 L24 8 M8 24 L8 48 M40 24 L40 48", ellipse(8, 8, 32), ellipse(21,21,6))
add("beam", "Beam", "Balken", "structural member bar", "Träger Stab Tragwerk", 56, 24, "", rect(0, 8, 56, 8))
add("axes", "Coordinate axes", "Koordinatenachsen", "Cartesian XY directions origin", "kartesisch XY Ursprung Richtungen", 48, 48,
    "M8 0 L8 40 L48 40 M4 7 L8 0 L12 7 M41 36 L48 40 L41 44 "
    "M16 5 L19 10 M22 5 L17 14 M36 29 L42 35 M42 29 L36 35")

items = library("flowchart", "Flowchart", "Flussdiagramm")
add("process", "Process", "Prozess", "action step operation", "Aktion Schritt Verarbeitung", 64, 40, "", rect(2,2,60,36))
add("decision", "Decision", "Entscheidung", "branch condition diamond", "Verzweigung Bedingung Raute", 64, 40,
    "M32 0 L64 20 L32 40 L0 20 Z")
add("terminator", "Start or end", "Start oder Ende", "terminator oval entry exit", "Terminator Anfang Abschluss", 64, 40, "", rect(2,4,60,32,16))
add("input-output", "Input or output", "Ein- oder Ausgabe", "data parallelogram", "Daten Parallelogramm Eingabe Ausgabe", 64, 40,
    "M13 2 L63 2 L51 38 L1 38 Z")
add("document", "Document", "Dokument", "report paper wavy edge", "Bericht Blatt Wellenkante", 64, 40,
    "M3 3 L61 3 L61 32 C42 21 25 44 3 34 Z")
add("connector", "Connector", "Konnektor", "continuation on page link", "Verbinder Fortsetzung Sprungmarke", 40, 40, "", ellipse(5,5,30))
add("flow-arrow", "Flow arrow", "Ablaufpfeil", "transition direction edge", "Übergang Richtung Verbindung", 48, 24,
    "M0 12 L48 12 M38 6 L48 12 L38 18")

items = library("lab", "Laboratory", "Labor")
add("beaker", "Beaker", "Becherglas", "graduated vessel glass liquid", "Messskala Glas Gefäß Flüssigkeit", 48, 56,
    "M12 8 L38 8 L33 14 L33 46 C33 49 31 50 28 50 L13 50 C10 50 8 48 8 45 L8 14 L4 8 L12 8 "
    "M33 22 L25 22 M33 30 L28 30 M33 38 L25 38")
add("erlenmeyer", "Erlenmeyer flask", "Erlenmeyerkolben", "conical flask chemistry", "Kegelflasche Kolben Chemie", 48, 56,
    "M16 5 L32 5 M19 5 L19 21 L7 45 C4 51 8 52 13 52 L35 52 C40 52 44 51 41 45 L29 21 L29 5 "
    "M12 36 L36 36")
add("round-bottom-flask", "Round-bottom flask", "Rundkolben", "boiling flask round glass", "Siedekolben Rundboden Glas", 48, 56,
    "M16 4 L32 4 M19 4 L19 19 C4 23 4 35 8 43 C11 50 18 53 24 53 C30 53 37 50 40 43 C44 35 44 23 29 19 L29 4")
add("test-tube", "Test tube", "Reagenzglas", "sample tube chemistry", "Probenröhrchen Versuch Chemie", 32, 56,
    "M5 5 L27 5 M8 5 L8 43 C8 55 24 55 24 43 L24 5 M8 33 L24 33")
add("burette", "Burette", "Bürette", "titration graduated stopcock", "Titration Maßskala Hahn", 32, 64,
    "M11 3 L21 3 M12 3 L12 42 L16 47 L20 42 L20 3 M20 10 L16 10 M20 16 L17 16 "
    "M20 22 L16 22 M20 28 L17 28 M20 34 L16 34 M8 49 L25 49 M25 46 L25 52 M16 51 L16 61",
    ellipse(14,47,4))
add("funnel", "Funnel", "Trichter", "filtration transfer cone", "Filtration Filter Umfüllen", 48, 48,
    "M4 6 L44 6 M6 6 L20 26 L20 44 L28 40 L28 26 L42 6 M11 13 L37 13")
add("bunsen-burner", "Bunsen burner", "Bunsenbrenner", "flame heat gas", "Flamme Hitze Gas Brenner", 48, 64,
    "M20 34 L28 34 L28 55 M20 55 L20 34 M28 48 L39 48 L39 53 L28 53 "
    "M24 29 C12 28 13 18 21 13 C24 10 25 6 24 2 C37 11 36 27 24 29 Z "
    "M24 28 C20 25 21 21 25 17 C28 21 29 24 27 26 C26 27 25 28 24 28 Z", rect(7,55,34,5,2))
add("thermometer", "Thermometer", "Thermometer", "temperature bulb scale", "Temperatur Messskala Wärme", 32, 60,
    "M10 43 L10 9 C10 2 20 2 20 9 L20 43 C29 49 24 58 15 58 C6 58 1 49 10 43 Z "
    "M15 48 L15 20 M20 15 L26 15 M20 22 L24 22 M20 29 L26 29 M20 36 L24 36",
    ellipse(12,47,6))

def write(path, value):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

paths_written = []
for key, data in LIBRARIES.items():
    path = f"content/shapes/{key}.json"
    write(path, data)
    paths_written.append(path)

write("goodtype-addon.json", dict(manifestVersion=1, id="engineering-shapes", version="0.1.0",
    apiVersion="goodtype-api 0.1", target="x86_64-pc-windows-msvc", transport="content",
    permissions=[], commands=[], settings=[], contents={"shapes": paths_written}, strings=STRINGS))
