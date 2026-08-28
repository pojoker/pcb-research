"""Independent, offline smoke test for all four DP2 CLI gates.

Run from this package root with ``python3 selftest.py``.  The script invokes
the public module CLI in subprocesses, so it does not test private helpers or
silently bypass the input schemas.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


PACKAGE_ROOT = Path(__file__).resolve().parent


def _run(command: str, input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "dp2_sources", command, str(input_path), str(output_path)],
        cwd=PACKAGE_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    with TemporaryDirectory(prefix="dp2-selftest-") as directory:
        output_root = Path(directory)

        ledger_output = output_root / "ledger.json"
        ledger = _run(
            "validate-ledger",
            PACKAGE_ROOT / "fixtures" / "source_ledger_template.csv",
            ledger_output,
        )
        _require(ledger.returncode == 1, "validate-ledger should reject the intentionally incomplete fixture")
        ledger_result = _read_json(ledger_output)
        _require(len(ledger_result) == 1 and not ledger_result[0]["valid"], "validate-ledger result is unexpected")
        print("validate-ledger: ok (incomplete fixture rejected)")

        probe_output = output_root / "probe.json"
        probe = _run(
            "probe-t1",
            PACKAGE_ROOT / "fixtures" / "t1_probe_sources.csv",
            probe_output,
        )
        _require(probe.returncode == 0, f"probe-t1 failed: {probe.stderr.strip()}")
        probe_result = _read_json(probe_output)
        _require(len(probe_result) == 2, "probe-t1 did not process the complete fixture")
        _require(all(item["network_enabled"] is False for item in probe_result), "probe-t1 unexpectedly enabled network")
        _require(all(item["reachable"] is None for item in probe_result), "probe-t1 turned disabled probes into reachability")
        _require(
            all(item["bearing_decision"] == "待人工裁决" for item in probe_result),
            "probe-t1 upgraded transport state to T1 bearing",
        )
        print("probe-t1: ok (offline and pending human bearing decision)")

        freeze_output = output_root / "8534.json"
        freeze = _run(
            "check-8534",
            PACKAGE_ROOT / "fixtures" / "8534_freeze_template.csv",
            freeze_output,
        )
        _require(freeze.returncode == 1, "check-8534 should reject the unfrozen fixture")
        freeze_result = _read_json(freeze_output)
        _require(freeze_result["status"] == "待核-口径未冻结", "check-8534 incorrectly froze its fixture")
        print("check-8534: ok (unfrozen fixture remains pending)")

        echoes_output = output_root / "echoes.json"
        echoes = _run(
            "detect-echoes",
            PACKAGE_ROOT / "fixtures" / "prismark_three_layers.json",
            echoes_output,
        )
        _require(echoes.returncode == 0, f"detect-echoes failed: {echoes.stderr.strip()}")
        echoes_result = _read_json(echoes_output)
        _require(len(echoes_result) == 1, "detect-echoes did not reproduce its known fixture cluster")
        _require(echoes_result[0]["counted_source_count"] == 1, "detect-echoes counted repost layers as independent sources")
        print("detect-echoes: ok (three repost layers count as one source)")

    print("selftest: PASS (offline)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"selftest: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
