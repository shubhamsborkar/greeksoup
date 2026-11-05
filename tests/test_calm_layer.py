"""The calm layer (web/assets/calm.css) may hide a table column only whole: a body cell it hides must
have its header cell hidden by the same rule, or every figure after it sits under the wrong heading
(Watch US, 5 November 2026: Price showed the day %, Mkt Cap fell off the right edge)."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CSS = os.path.join(HERE, "..", "web", "assets", "calm.css")


def _hiding_rules():
    css = re.sub(r"/\*.*?\*/", "", open(CSS, encoding="utf-8").read(), flags=re.S)
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if re.search(r"display\s*:\s*none", body):
            yield [s.strip() for s in sel.split(",")]


def test_no_table_cell_hidden_without_its_header():
    for sels in _hiding_rules():
        for s in sels:
            # a rule that can reach a whole cell: "table .x" or "td.x" removes a <td> carrying that class
            assert not re.match(r"^table\s+\.[\w-]+$", s), "%s hides body cells but not their header" % s
            m = re.match(r"^td(\.[\w-]+)$", s)
            if m:
                assert "th" + m.group(1) in sels, "%s is hidden without th%s" % (s, m.group(1))


def test_watch_header_cells_carry_the_column_class():
    html = open(os.path.join(HERE, "..", "web", "watch.html"), encoding="utf-8").read()
    assert '<th class="${k}"></th>' in html
