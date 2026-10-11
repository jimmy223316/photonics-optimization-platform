import importlib.util
from pathlib import Path
import json
import pytest

spec = importlib.util.spec_from_file_location("weekly_report", Path(__file__).parents[1] / "scripts/weekly_report.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

@pytest.mark.parametrize("xml, expected", [
    ('<testsuites><testsuite tests="3" failures="0" errors="0" skipped="1"/></testsuites>', "Test status: PASS"),
    ('<testsuite tests="2" failures="1" errors="0"/>', "Test status: FAIL"),
    ('<testsuites><testsuite tests="0"/></testsuites>', "Test status: FAIL"),
    (None, "Test status: UNKNOWN")])
def test_report_uses_observed_test_status(tmp_path, xml, expected):
    junit = tmp_path / "tests.xml"
    if xml is not None:
        junit.write_text(xml)
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"phase": "prototype"}))
    output = tmp_path / "report.md"
    module.generate_report(junit, output, state)
    assert expected in output.read_text()
    assert "no validated simulations" in output.read_text()
