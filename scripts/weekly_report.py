"""Generate status from actual pytest JUnit output, including failed runs."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET

def generate_report(junit: Path, output: Path, state: Path) -> None:
    project = json.loads(state.read_text())
    lines = ["# Weekly project status", "",
             f"Generated: {datetime.now(timezone.utc).isoformat()}", "",
             f"Project phase: {project['phase']}", ""]
    if junit.exists():
        root = ET.parse(junit).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        totals = {key: sum(int(s.get(key, "0")) for s in suites)
                  for key in ("tests", "failures", "errors", "skipped")}
        passed = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
        status = "PASS" if totals["tests"] > 0 and totals["failures"] + totals["errors"] == 0 else "FAIL"
        lines += [f"Test status: {status}", f"Tests: {totals['tests']}; passed: {passed}; "
                  f"failures: {totals['failures']}; errors: {totals['errors']}; skipped: {totals['skipped']}"]
    else:
        lines += ["Test status: UNKNOWN — JUnit output missing; tests may not have run."]
    lines += ["", "Scientific status: synthetic analytic objective only; no validated simulations or measurements.",
              "", "Next tasks: see TASK_QUEUE.md and ROADMAP.md.", "",
              "This report reflects this workflow run; it does not summarize historical runs."]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, default=Path("artifacts/pytest.xml"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/weekly-status.md"))
    parser.add_argument("--state", type=Path, default=Path("PROJECT_STATE.json"))
    args = parser.parse_args()
    generate_report(args.junit, args.output, args.state)
