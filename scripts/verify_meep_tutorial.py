"""Compare an executed upstream script log with our actual taper run records."""
import argparse
import hashlib
import json
from pathlib import Path
import re

def compare(official_log: Path, sweep_json: Path, source_script: Path) -> dict[str, object]:
    rows = re.findall(r"^refl:, ([^,]+), ([^,]+), ([^\n]+)$", official_log.read_text(), flags=re.MULTILINE)
    reference = {float(length): (float(mode), float(flux)) for length, mode, flux in rows}
    runs = json.loads(sweep_json.read_text())["runs"]
    if not reference or len(reference) != len(rows):
        raise ValueError("Official log must contain unique reflection results")
    lengths = {float(r["parameters"]["taper_length_um"]) for r in runs}
    if lengths != set(reference) or len(runs) != len(reference):
        raise ValueError("Official and backend runs must cover identical lengths with one width")
    comparisons = []
    for run in runs:
        if run["data_kind"] != "fdtd_meep_2d_unvalidated" or run["configuration"]["resolution"] != 25:
            raise ValueError("Expected actual tutorial-resolution FDTD records")
        length = float(run["parameters"]["taper_length_um"])
        official_mode, official_flux = reference[length]
        mode_error = abs(run["powers"]["fundamental_reflection"] - official_mode)
        flux_error = abs(run["powers"]["reflected_flux_fraction"] - official_flux)
        comparisons.append({"taper_length_um": length, "official_reflection_mode": official_mode,
                            "official_reflection_flux": official_flux,
                            "backend_reflection_mode": run["powers"]["fundamental_reflection"],
                            "backend_reflection_flux": run["powers"]["reflected_flux_fraction"],
                            "mode_absolute_difference": mode_error, "flux_absolute_difference": flux_error,
                            "matches_printed_precision": mode_error <= 5.1e-9 and flux_error <= 5.1e-9})
    return {"comparison_kind": "executed_upstream_script_reproduction_not_independent_physical_validation",
            "scientifically_validated": False,
            "source_script_url": "https://raw.githubusercontent.com/NanoComp/meep/master/python/examples/mode-decomposition.py",
            "source_script_sha256": hashlib.sha256(source_script.read_bytes()).hexdigest(),
            "official_log_sha256": hashlib.sha256(official_log.read_bytes()).hexdigest(),
            "all_match_printed_precision": all(c["matches_printed_precision"] for c in comparisons),
            "comparisons": comparisons}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-log", type=Path, required=True)
    parser.add_argument("--sweep", type=Path, required=True)
    parser.add_argument("--source-script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.official_log, args.sweep, args.source_script)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    if not result["all_match_printed_precision"]:
        raise SystemExit("Tutorial comparison differs; inspect the actual differences")
