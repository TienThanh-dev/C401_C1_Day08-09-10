"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).

Mở rộng:
  Rule mới 1: mask_pii — ẩn email/SĐT (metric_impact: pii_masked_count)
  Rule mới 2: normalize_unicode — NFC + strip BOM/ZWSP (metric_impact: unicode_normalized_count)
  Rule mới 3: dynamic_hr_cutoff — đọc cutoff từ env (metric_impact: quarantine_records thay đổi)
  Pydantic CleanedRow — validate schema sau clean (Distinction-a, Bonus +2)
"""

from __future__ import annotations

import csv
import hashlib
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field, ValidationError

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")

# Rule mới 1: PII patterns (email + SĐT Việt Nam)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_PHONE_VN_RE = re.compile(r"\b0\d{9,10}\b")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


class CleanedRow(BaseModel):
    """Pydantic model — validate schema cleaned row (Distinction-a, Bonus +2)."""

    chunk_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    chunk_text: str = Field(min_length=8)
    effective_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    exported_at: str = ""


def _mask_pii(text: str) -> str:
    """
    Rule mới 1: Ẩn email và SĐT Việt Nam trong chunk_text.

    metric_impact: Trên inject chứa PII → chunk_text có marker [EMAIL_MASKED]
    hoặc [PHONE_MASKED], chứng minh rule hoạt động.
    """
    result = _EMAIL_RE.sub("[EMAIL_MASKED]", text)
    return _PHONE_VN_RE.sub("[PHONE_MASKED]", result)


def _normalize_unicode(text: str) -> str:
    """
    Rule mới 2: Chuẩn hóa Unicode NFC + loại BOM/zero-width space.

    metric_impact: Trên inject chứa BOM (\\ufeff) hoặc ZWSP (\\u200b)
    → text thay đổi hoặc trở thành rỗng → quarantine_records tăng.
    """
    cleaned = text.replace("\ufeff", "").replace("\u200b", "")
    return unicodedata.normalize("NFC", cleaned)


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline:
    1) Quarantine: doc_id không thuộc allowlist.
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: hr_leave_policy có effective_date < cutoff (đọc từ env).
    4) Quarantine: chunk_text rỗng sau normalize.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 '14 ngày làm việc' → 7 ngày.

    Mở rộng:
    7) normalize_unicode — NFC + strip BOM/ZWSP trước mọi xử lý text.
    8) mask_pii — ẩn email/SĐT sau khi fix refund.
    9) dynamic_hr_cutoff — cutoff HR đọc từ HR_LEAVE_MIN_EFFECTIVE_DATE env.
    10) Pydantic CleanedRow — validate schema trước khi đưa vào cleaned.
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    # Rule mới 3: đọc cutoff từ env thay vì hard-code (Distinction-d)
    hr_cutoff = os.environ.get("HR_LEAVE_MIN_EFFECTIVE_DATE", "2026-01-01")

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = _normalize_unicode(raw.get("chunk_text", ""))  # Rule mới 2
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        if doc_id == "hr_leave_policy" and eff_norm < hr_cutoff:  # Rule mới 3
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        key = _norm_text(text)
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        fixed_text = text
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        # Rule mới 1: ẩn PII (email, SĐT)
        fixed_text = _mask_pii(fixed_text)

        seq += 1
        row_data = {
            "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
            "doc_id": doc_id,
            "chunk_text": fixed_text,
            "effective_date": eff_norm,
            "exported_at": exported_at or "",
        }

        # Pydantic validate — Distinction-a: schema gate trước khi embed
        try:
            CleanedRow(**row_data)
        except ValidationError as e:
            quarantine.append({**raw, "reason": f"pydantic_validation_error: {e}"})
            continue

        cleaned.append(row_data)

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
