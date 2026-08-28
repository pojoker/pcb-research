"""Explicitly opt-in T1 endpoint reachability probes.

Probe records are transport observations only.  A successful HTTP response is
never converted into a bearing decision by this module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Callable, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


T1_PROBE_FIELDS = ("origin_source_id", "carrier_url")


@dataclass(frozen=True)
class ProbeRecord:
    origin_source_id: str
    carrier_url: str
    probed_at: str
    network_enabled: bool
    reachable: bool | None
    http_status: int | None
    error_type: str | None
    error_message: str | None
    bearing_decision: str = "待人工裁决"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


Fetcher = Callable[[str, float], int]


def _default_fetcher(url: str, timeout_seconds: float) -> int:
    request = Request(url, method="HEAD", headers={"User-Agent": "dp2-sources/0.1"})
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310: explicit user opt-in
        return int(response.status)


def probe_t1_sources(
    records: Iterable[Mapping[str, object]],
    *,
    enable_network: bool = False,
    timeout_seconds: float = 10.0,
    fetcher: Fetcher | None = None,
    today: date | None = None,
) -> list[ProbeRecord]:
    """Probe each supplied T1 candidate only when ``enable_network`` is true.

    ``fetcher`` exists for offline tests.  It receives ``(url, timeout)`` and
    returns an HTTP status, so tests never need a real network endpoint.
    """

    probe_date = (today or date.today()).isoformat()
    probe_fetcher = fetcher or _default_fetcher
    results: list[ProbeRecord] = []
    for record in records:
        source_id = str(record.get("origin_source_id", "")).strip()
        url = str(record.get("carrier_url", "")).strip()
        if not enable_network:
            results.append(
                ProbeRecord(
                    source_id, url, probe_date, False, None, None,
                    "network_disabled", "network probing requires --enable-network"
                )
            )
            continue
        try:
            http_status = probe_fetcher(url, timeout_seconds)
            results.append(
                ProbeRecord(
                    source_id, url, probe_date, True, 200 <= http_status < 400,
                    http_status, None, None
                )
            )
        except HTTPError as exc:
            results.append(
                ProbeRecord(source_id, url, probe_date, True, False, exc.code, "HTTPError", str(exc))
            )
        except URLError as exc:
            results.append(
                ProbeRecord(source_id, url, probe_date, True, False, None, "URLError", str(exc.reason))
            )
        except Exception as exc:  # retained as an auditable transport failure
            results.append(
                ProbeRecord(source_id, url, probe_date, True, False, None, type(exc).__name__, str(exc))
            )
    return results


def t1_probe_csv_header() -> tuple[str, ...]:
    """Return the exact ordered schema for the probe input CSV."""

    return T1_PROBE_FIELDS
