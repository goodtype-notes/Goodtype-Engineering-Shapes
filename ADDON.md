# Engineering Shapes

Put standard technical symbols straight onto a Goodtype page. Pick a drawing from five libraries and connect it to your own wires, arrows or notes.

## Five libraries

- **Circuits** has 23 symbols, from an IEC resistor and supply sources to a transformer, transistors and a junction.
- **Logic gates** has 10 ANSI-style symbols including XOR, XNOR, a D flip-flop and a multiplexer.
- **Mechanics** has 13 symbols for supports, loads, moving parts, axes and dimension lines.
- **Flowchart** has 8 shapes for steps, decisions, data and connections, including a double arrow.
- **Laboratory** has 8 drawings of common glassware and instruments.

## Use in Goodtype

Install the pack from **Addons**, then open **Insert shape** on a page. Browse the libraries or search by name. Symbols follow your pen’s outline colour and weight when inserted. You can move or resize them as ordinary Goodtype objects.

When the Connectors addon is enabled, snap to component leads, flowchart edges and selected mechanical or laboratory attachment points.

Arrowheads in version 0.2.0 follow the ends of their lines or curves when you move the handles. The manifest declares `requires: ["end-caps", "group-stretch"]`.

Select a two-terminal symbol to stretch it from either port. Do not release this 0.2 package before a Goodtype host with P1 is published; released v0.3.x hosts reject `requires`.
