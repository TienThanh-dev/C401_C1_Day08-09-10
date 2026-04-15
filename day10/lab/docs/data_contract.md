# Data contract — Lab Day 10

> Đồng bộ với `contracts/data_contract.yaml`.  
> Owner: C401 — C1 | SLA freshness: 24h

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|--------------------|----------------|
| `policy_refund_v4.txt` | CSV export (`policy_export_dirty.csv`) | Stale refund window "14 ngày" thay vì "7 ngày" | `refund_no_stale_14d_window` violations > 0 → halt |
| `sla_p1_2026.txt` | CSV export | Ngày format DD/MM/YYYY không parse được ISO | `invalid_effective_date_format` quarantine count tăng |
| `it_helpdesk_faq.txt` | CSV export | Duplicate chunk_text từ cùng nguồn | `duplicate_chunk_text` quarantine count tăng |
| `hr_leave_policy.txt` | CSV export | Bản cũ 2025 (10 ngày) lẫn với bản 2026 (12 ngày) | `stale_hr_policy_effective_date` quarantine count tăng |

**Failure modes bổ sung phát hiện qua pipeline:**

| Failure | Rule xử lý | Severity |
|---------|-----------|----------|
| `unknown_doc_id` | allowlist check | quarantine |
| `missing_chunk_text` | empty text check | quarantine |
| `missing_effective_date` | date parse | quarantine |
| `pydantic_validation_error` | Pydantic `CleanedRow` | quarantine |
| PII còn sót | E8 `no_pii_in_cleaned` | warn |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| `chunk_id` | string | Có | `{doc_id}_{seq}_{sha256[:16]}` — stable, unique |
| `doc_id` | string | Có | Một trong 4 giá trị trong `ALLOWED_DOC_IDS` |
| `chunk_text` | string (min 8 ký tự) | Có | Sau normalize_unicode + mask_pii |
| `effective_date` | date YYYY-MM-DD | Có | Chuẩn hoá từ ISO hoặc DD/MM/YYYY |
| `exported_at` | datetime | Không | Dùng tính `ingest_lag` trong freshness check |

**Validate bởi:** Pydantic `CleanedRow` model — fail → quarantine với `reason=pydantic_validation_error`.

---

## 3. Quy tắc quarantine vs drop

| Reason | Lưu tại | Ai xử lý |
|--------|---------|---------|
| `unknown_doc_id` | `artifacts/quarantine/*.csv` | Team lead review — xoá nếu không liên quan |
| `duplicate_chunk_text` | `artifacts/quarantine/*.csv` | Tự động — giữ bản đầu tiên |
| `stale_hr_policy_effective_date` | `artifacts/quarantine/*.csv` | Chờ HR team cung cấp bản effective_date mới |
| `missing_effective_date` | `artifacts/quarantine/*.csv` | Fix nguồn export → rerun pipeline |
| `pydantic_validation_error` | `artifacts/quarantine/*.csv` | Debug cleaning rule, kiểm tra schema |

Record quarantine **không bị xoá** — lưu để audit trail và reprocessing khi nguồn được fix.

---

## 4. Phiên bản & canonical

| Doc | Source of truth | Quy tắc version |
|-----|----------------|----------------|
| `policy_refund_v4` | `data/docs/policy_refund_v4.txt` | v4 — cửa sổ hoàn tiền 7 ngày làm việc |
| `hr_leave_policy` | `data/docs/hr_leave_policy.txt` | `effective_date ≥ HR_LEAVE_MIN_EFFECTIVE_DATE` (đọc từ `.env`) |
| `sla_p1_2026` | `data/docs/sla_p1_2026.txt` | 2026 — P1 SLA 15 phút phản hồi |
| `it_helpdesk_faq` | `data/docs/it_helpdesk_faq.txt` | FAQ hiện hành — 5 lần sai → khóa tài khoản |
