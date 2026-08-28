"""Independent offline smoke test for every public DP3 CLI gate."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
TREE = REPO_ROOT / "tree.yaml"
FIXTURES = PACKAGE_ROOT / "fixtures"


def _run(command: str, input_path: Path | None, output_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable, "-m", "dp3_tree", command]
    if command == "validate-tree":
        argv.extend(["--tree", str(TREE)])
    else:
        argv.extend(["--tree", str(TREE), "--input", str(input_path)])
    argv.extend(["--output", str(output_path), *extra])
    return subprocess.run(argv, cwd=PACKAGE_ROOT, text=True, capture_output=True, check=False)


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    with TemporaryDirectory(prefix="dp3-selftest-") as directory:
        out = Path(directory)

        tree_result = _run("validate-tree", None, out / "tree.json")
        _require(tree_result.returncode == 0, tree_result.stderr.strip())
        tree_report = _read(out / "tree.json")
        _require(tree_report["ok"] and tree_report["details"]["cell_count"] == 30, "tree gate did not verify 30 cells")
        print("validate-tree: ok (frozen schema, 30 active cells)")

        samples_result = _run("validate-samples", FIXTURES / "valid_samples.json", out / "samples.json")
        _require(samples_result.returncode == 0, samples_result.stderr.strip())
        _require(_read(out / "samples.json")["ok"], "valid samples were rejected")
        print("validate-samples: ok (FAB/OUT compatibility)")

        negative_samples = _read(FIXTURES / "negative_samples.json")
        for case in negative_samples:
            case_input = out / f"{case['fixture_id']}.json"
            case_output = out / f"{case['fixture_id']}.result.json"
            case_input.write_text(json.dumps(case["records"], ensure_ascii=False), encoding="utf-8")
            result = _run("validate-samples", case_input, case_output)
            _require(result.returncode == 1, f"negative sample {case['fixture_id']} unexpectedly passed")
        print(f"negative samples: ok ({len(negative_samples)} rejected)")

        map_result = _run("validate-map", FIXTURES / "valid_process_equipment_map.json", out / "map.json")
        _require(map_result.returncode == 0, map_result.stderr.strip())
        map_report = _read(out / "map.json")
        _require(map_report["ok"], "valid map was rejected")
        _require("P7" in map_report["details"]["unmapped_processes"], "unmapped process was not explicit")
        print("validate-map: ok (many-to-many, no fallback synthesis)")

        render_result = _run("render", FIXTURES / "valid_render_input.json", out / "render.json")
        _require(render_result.returncode == 0, render_result.stderr.strip())
        rendered = _read(out / "render.json")
        _require(len(rendered["cells"]) == 30, "render did not emit all 30 cells")
        _require(any(row["empty_space"] for row in rendered["cells"]), "render did not emit an explicit empty space")
        print("render: ok (30 cells, explicit empty spaces)")

    print("selftest: PASS (offline)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"selftest: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
