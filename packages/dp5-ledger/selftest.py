"""Independent CLI-only smoke test for the DP5 ledger contract."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
FIXTURES = PACKAGE_ROOT / "fixtures"
TREE = REPO_ROOT / "tree.yaml"


def _read(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _parent(payload, path: str):
    parts = path.split(".")
    current = payload
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current, parts[-1]


def _mutate(base, mutations):
    result = copy.deepcopy(base)
    for mutation in mutations:
        parent, final = _parent(result, mutation["path"])
        if mutation["op"] == "set":
            if isinstance(parent, list):
                parent[int(final)] = mutation["value"]
            else:
                parent[final] = mutation["value"]
        elif mutation["op"] == "delete":
            if isinstance(parent, list):
                del parent[int(final)]
            else:
                del parent[final]
        elif mutation["op"] == "append":
            (parent[int(final)] if isinstance(parent, list) else parent[final]).append(mutation["value"])
        else:
            raise RuntimeError(f"unknown fixture mutation {mutation['op']}")
    return result


def _run(input_path: Path, output_path: Path):
    return subprocess.run(
        [sys.executable, "-m", "dp5_ledger", "validate-ledger", "--tree", str(TREE), "--input", str(input_path), "--output", str(output_path)],
        cwd=PACKAGE_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    base = _read("valid_ledger.json")
    with TemporaryDirectory(prefix="dp5-selftest-") as directory:
        temp = Path(directory)
        valid_result = _run(FIXTURES / "valid_ledger.json", temp / "valid.json")
        valid_report = json.loads((temp / "valid.json").read_text(encoding="utf-8"))
        _require(valid_result.returncode == 0 and valid_report["ok"], valid_result.stderr or str(valid_report))
        print("valid ledger: ok (four record types, read-only tree contract)")

        rejected = 0
        for name in ("negative_points.json", "negative_metrics.json", "negative_edges.json", "negative_pairs.json"):
            for case in _read(name):
                input_path = temp / f"{case['fixture_id']}.json"
                output_path = temp / f"{case['fixture_id']}.report.json"
                input_path.write_text(json.dumps(_mutate(base, case["mutations"]), ensure_ascii=False), encoding="utf-8")
                result = _run(input_path, output_path)
                report = json.loads(output_path.read_text(encoding="utf-8"))
                _require(result.returncode == 1 and not report["ok"], f"{case['fixture_id']} unexpectedly passed")
                _require(any(case["expected_error"] in error for error in report["errors"]), str(report["errors"]))
                rejected += 1
        print(f"negative fixtures: ok ({rejected} rejected)")

        for nonfinite in ("invalid_nan.json", "invalid_inf.json"):
            result = _run(FIXTURES / nonfinite, temp / f"{nonfinite}.report.json")
            report = json.loads((temp / f"{nonfinite}.report.json").read_text(encoding="utf-8"))
            _require(result.returncode == 2 and not report["ok"], str(report))
        print("NaN/Inf input: ok (machine-readable schema rejection)")
    print("selftest: PASS (offline)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"selftest: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
