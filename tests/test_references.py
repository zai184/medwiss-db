"""parse_calculators: line format, empty group, malformed-line tolerance."""

from api.routers.references import parse_calculators

SAMPLE = """# comment

Kardiologie | EKG | QTc | https://x/calc/48 | qtc, ekg
Notfall | | Wells | https://x/calc/115 | wells
totally malformed
Kardiologie | Gefäße |  | https://x/calc/1 | x
"""


def test_parse_calculators(tmp_path):
    f = tmp_path / "calculators.txt"
    f.write_text(SAMPLE, encoding="utf-8")
    calcs = parse_calculators(f)
    assert len(calcs) == 2
    assert calcs[0].discipline == "Kardiologie"
    assert calcs[0].group == "EKG"
    assert calcs[0].keywords == ["qtc", "ekg"]
    assert calcs[1].group is None
