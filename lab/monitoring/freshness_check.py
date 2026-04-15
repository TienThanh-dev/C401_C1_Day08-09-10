"""
Kiểm tra freshness từ manifest pipeline (SLA đơn giản theo giờ).

Mở rộng (Distinction-b, Bonus +1): đo 2 ranh giới thay vì 1:
  - ingest_lag  : data age = khoảng từ `latest_exported_at` đến `run_timestamp`
                  → cho biết data đã "cũ" bao lâu khi pipeline nhận vào.
  - publish_lag : pipeline age = khoảng từ `run_timestamp` đến now
                  → cho biết index hiện tại đã "lỗi thời" bao lâu.

SLA áp lên `ingest_lag` (nguồn gốc dữ liệu); `publish_lag` là thông tin bổ sung.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


def parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def check_manifest_freshness(
    manifest_path: Path,
    *,
    sla_hours: float = 24.0,
    now: datetime | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Trả về ("PASS" | "WARN" | "FAIL", detail dict).

    Đo 2 boundary (Distinction-b):
      - ingest_lag  : latest_exported_at → run_timestamp  (data staleness)
      - publish_lag : run_timestamp → now                 (index staleness)

    SLA check áp trên ingest_lag (độ tươi của nguồn dữ liệu).
    """
    now = now or datetime.now(timezone.utc)

    if not manifest_path.is_file():
        return "FAIL", {"reason": "manifest_missing", "path": str(manifest_path)}

    data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Boundary 1: ingest_lag — data age (exported_at → run_timestamp)
    exported_ts = data.get("latest_exported_at") or ""
    run_ts = data.get("run_timestamp") or ""

    dt_exported = parse_iso(str(exported_ts)) if exported_ts else None
    dt_run = parse_iso(str(run_ts)) if run_ts else None

    ingest_lag_hours: float | None = None
    if dt_exported and dt_run:
        ingest_lag_hours = (dt_run - dt_exported).total_seconds() / 3600.0

    # Boundary 2: publish_lag — index age (run_timestamp → now)
    publish_lag_hours: float | None = None
    if dt_run:
        publish_lag_hours = (now - dt_run).total_seconds() / 3600.0

    # SLA check: dùng ingest_lag làm mốc chính; fallback run_timestamp nếu không có exported_at
    check_dt = dt_exported or dt_run
    if check_dt is None:
        return "WARN", {
            "reason": "no_timestamp_in_manifest",
            "manifest_run_id": data.get("run_id"),
        }

    age_hours = (now - check_dt).total_seconds() / 3600.0
    detail: Dict[str, Any] = {
        "sla_hours": sla_hours,
        "ingest_lag_hours": round(ingest_lag_hours, 3) if ingest_lag_hours is not None else None,
        "publish_lag_hours": round(publish_lag_hours, 3) if publish_lag_hours is not None else None,
        "latest_exported_at": exported_ts,
        "run_timestamp": run_ts,
        "age_hours_checked": round(age_hours, 3),
    }

    if age_hours <= sla_hours:
        return "PASS", detail
    return "FAIL", {**detail, "reason": "freshness_sla_exceeded"}
