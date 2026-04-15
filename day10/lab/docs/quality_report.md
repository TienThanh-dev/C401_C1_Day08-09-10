# Quality Report — Lab Day 10

**Nhóm:** C401 — C1  
**run_id (clean):** `clean-run`  
**run_id (inject):** `inject-bad`  
**Ngày:** 2026-04-15

---

## 1. Pipeline statistics

| Metric | clean-run | inject-bad |
|--------|-----------|------------|
| `raw_records` | 10 | 10 |
| `cleaned_records` | 6 | 10 |
| `quarantine_records` | 4 | 0 |
| `embed_upsert count` | 6 | 10 |
| Expectations halt? | Không | Không (`--skip-validate`) |

> **inject-bad** dùng flag `--no-refund-fix --skip-validate`: bỏ qua fix "14→7 ngày" và bỏ qua toàn bộ expectation gate → mọi row (kể cả stale, duplicate, sai policy) đều lọt vào ChromaDB.

---

## 2. Before / After retrieval — bảng chứng cứ

| question_id | Scenario | `contains_expected` | `hits_forbidden` | `top1_doc_id` | Nhận xét |
|-------------|----------|---------------------|------------------|---------------|---------|
| `q_refund_window` | **clean-run** (PASS) | yes | **no** | policy_refund_v4 | Trả đúng "7 ngày làm việc" |
| `q_refund_window` | **inject-bad** (FAIL) | yes | **yes** | policy_refund_v4 | Trả "14 ngày làm việc" — chunk stale lọt embed |
| `q_p1_sla` | clean-run | yes | no | sla_p1_2026 | Đúng: 15 phút P1 |
| `q_p1_sla` | inject-bad | yes | no | sla_p1_2026 | Không bị ảnh hưởng |
| `q_lockout` | clean-run | yes | no | it_helpdesk_faq | Đúng: 5 lần sai |
| `q_lockout` | inject-bad | yes | no | it_helpdesk_faq | Không bị ảnh hưởng |
| `q_leave_version` | clean-run | yes | no | hr_leave_policy | **top1_doc_matches=yes** — 12 ngày 2026 |
| `q_leave_version` | inject-bad | yes | no | hr_leave_policy | top1 vẫn đúng (bản cũ không override do embed nhiều version) |

---

## 3. Giải thích kết quả (interpret)

### 3.1. q_refund_window — câu hỏi chứng minh rõ nhất

**Kịch bản inject:** `--no-refund-fix` → không fix "14 ngày làm việc" → chunk stale được embed vào `day10_kb`.

**Tác động:** `hits_forbidden=yes` — retrieval trả về đoạn "14 ngày làm việc" (stale policy-v3), mâu thuẫn với policy hiện hành "7 ngày làm việc".

**Sau khi fix (clean-run):** `hits_forbidden=no` — pipeline loại chunk stale, embed đúng "7 ngày làm việc" → agent trả lời đúng.

**Khoảng cách chứng minh được:** `hits_forbidden: yes → no` khi bật cleaning rule.

### 3.2. q_leave_version — Merit evidence

**clean-run:** `contains_expected=yes`, `top1_doc_matches=yes` — pipeline loại chunk HR cũ (2025-01-01, "10 ngày phép năm"), giữ chunk mới (2026, "12 ngày phép năm"). Top-1 retrieval đúng doc_id `hr_leave_policy`.

**Cơ chế:** Rule `dynamic_hr_cutoff` đọc `HR_LEAVE_MIN_EFFECTIVE_DATE=2026-01-01` từ `.env`, quarantine tất cả chunk HR có `effective_date < 2026-01-01`.

---

## 4. Expectation evidence

| Expectation | Severity | clean-run | inject-bad |
|-------------|----------|-----------|------------|
| `min_one_row` | halt | OK (6) | OK (10) |
| `refund_no_stale_14d_window` | halt | OK (0 vi phạm) | **SKIPPED** (`--skip-validate`) |
| `unique_chunk_id` | halt | OK (0 duplicate) | **SKIPPED** |
| `no_pii_in_cleaned` | warn | OK (0 PII) | **SKIPPED** |

> Inject-bad bỏ qua expectation gate (`--skip-validate`) — đây là cố ý để chứng minh pipeline **không có guardrail** khi validate bị tắt sẽ ra kết quả sai.

---

## 5. Freshness check (clean-run)

```json
{
  "sla_hours": 24.0,
  "ingest_lag_hours": 116.326,
  "publish_lag_hours": 0.0,
  "latest_exported_at": "2026-04-10T08:00:00",
  "run_timestamp": "2026-04-15T04:19:34+00:00",
  "reason": "freshness_sla_exceeded"
}
```

**Interpret:** `ingest_lag_hours=116.3` >> SLA 24h → data mẫu cũ 4.8 ngày so với thời điểm pipeline chạy. `publish_lag_hours≈0` → index vừa được updated. Đây là **expected behaviour** với data lab — xem `docs/runbook.md` để xử lý trong thực tế.
