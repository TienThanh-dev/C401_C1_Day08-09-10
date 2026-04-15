# Runbook — Lab Day 10 (incident response)

> Mỗi mục: Symptom → Detection → Diagnosis → Mitigation → Prevention

---

## 0. Freshness check — cách dùng và ý nghĩa PASS/WARN/FAIL

### Lệnh chạy

```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_clean-run.json
```

Output format: `{STATUS} {detail_json}`

**Ví dụ thực tế (clean-run):**
```
FAIL {"sla_hours": 24.0, "ingest_lag_hours": 116.326, "publish_lag_hours": 0.0, "latest_exported_at": "2026-04-10T08:00:00", "run_timestamp": "2026-04-15T04:19:34+00:00", "age_hours_checked": 116.326, "reason": "freshness_sla_exceeded"}
```

### Ý nghĩa trạng thái

| Status | Điều kiện | Hành động |
|--------|-----------|-----------|
| **PASS** | `ingest_lag_hours <= sla_hours` (24h) | Không cần làm gì — data tươi |
| **WARN** | Manifest không có timestamp (`latest_exported_at` rỗng) | Kiểm tra pipeline có ghi manifest đúng không |
| **FAIL** | `ingest_lag_hours > sla_hours` | Xem Incident 1 bên dưới để xử lý |

### 2 boundary đo được

| Boundary | Công thức | Ý nghĩa |
|----------|-----------|---------|
| `ingest_lag_hours` | `run_timestamp - latest_exported_at` | Data đã "cũ" bao lâu khi pipeline nhận vào |
| `publish_lag_hours` | `now - run_timestamp` | Index trong ChromaDB đã lỗi thời bao lâu |

SLA (24h) áp trên `ingest_lag_hours`. `publish_lag_hours` là thông tin bổ sung.

---

## Incident 1: `freshness_check=FAIL` — Data quá cũ vượt SLA

**Symptom:** Log cuối pipeline in `freshness_check=FAIL`, `ingest_lag_hours > 24`.

**Detection:** `monitoring/freshness_check.py` so `latest_exported_at` với `now`, trả `FAIL` nếu `age_hours > sla_hours`.

**Diagnosis:**
```bash
# Kiểm tra manifest
cat artifacts/manifests/manifest_{run_id}.json
# Xem trường latest_exported_at và run_timestamp
```

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|-----------------|
| 1 | Kiểm tra `latest_exported_at` trong manifest | Thấy ngày export cũ hơn 24h |
| 2 | So với `run_timestamp` | Tính `ingest_lag = run_timestamp - exported_at` |
| 3 | Xác nhận: data mẫu hay data thật? | Nếu data mẫu lab → expected behaviour |

**Mitigation:**
- Data mẫu lab (exported 2026-04-10): `freshness_check=FAIL` là **expected** — không cần xử lý
- Data thật: yêu cầu team source cấp export mới → rerun pipeline với `--run-id fresh-{date}`

**Prevention:** Thiết lập cron job export định kỳ từ nguồn; alert kênh `#data-ops` khi `ingest_lag_hours > 24`.

---

## Incident 2: Expectation HALT — Pipeline dừng giữa chừng

**Symptom:** Pipeline exit 1, log in `HALT triggered by expectation[X]`.

**Detection:** `quality/expectations.py` — bất kỳ expectation severity=`halt` nào fail.

**Diagnosis:**
```bash
# Xem log
cat artifacts/logs/run_{run_id}.log | grep -i halt

# Xem quarantine để hiểu data nào bị flag
cat artifacts/quarantine/quarantine_{run_id}.csv
```

| Expectation | Nguyên nhân thường gặp |
|-------------|----------------------|
| `refund_no_stale_14d_window` | Chunk "14 ngày" lọt qua clean (tắt `apply_refund_window_fix`) |
| `unique_chunk_id` | Hash collision hoặc logic `_stable_chunk_id` sai |
| `hr_leave_no_stale_10d_annual` | Chunk cũ lọt qua vì `HR_LEAVE_MIN_EFFECTIVE_DATE` sai |

**Mitigation:** Sửa cleaning rule → rerun `python etl_pipeline.py run --run-id fix-{date}`

**Prevention:** Thêm unit test cho from hàm `clean_rows` trước khi merge code mới.

---

## Incident 3: Stale refund window — Agent trả "14 ngày" sai

**Symptom:** Agent / retrieval trả lời "14 ngày làm việc" thay vì "7 ngày làm việc".

**Detection:** `eval_retrieval.py` → `hits_forbidden=yes` cho `q_refund_window`.

**Diagnosis:**
```bash
python eval_retrieval.py --out artifacts/eval/debug_eval.csv
# Xem cột hits_forbidden và top1_preview
```

**Mitigation:**
1. Kiểm tra `artifacts/cleaned/cleaned_{run_id}.csv` — có chunk "14 ngày" không?
2. Nếu có → `apply_refund_window_fix` bị tắt → rerun với flag đúng
3. Nếu không → `data/docs/policy_refund_v4.txt` bị sửa nhầm → restore từ git

**Prevention:** Expectation `refund_no_stale_14d_window` (severity=halt) ngăn trường hợp này trước khi embed.

---

## Incident 4: `unknown_doc_id` quarantine tăng đột biến

**Symptom:** `quarantine_records` tăng bất thường; quarantine CSV có nhiều `reason=unknown_doc_id`.

**Detection:** Log `quarantine_records=N` lớn hơn expected; quarantine CSV có doc_id lạ.

**Diagnosis:**
```bash
cat artifacts/quarantine/quarantine_{run_id}.csv
# Lọc cột reason=unknown_doc_id, xem doc_id nào lạ
```

**Mitigation:** Nếu doc mới hợp lệ → thêm vào `ALLOWED_DOC_IDS` trong `cleaning_rules.py` và `data_contract.yaml` → rerun.

**Prevention:** Đồng bộ `ALLOWED_DOC_IDS` với `contracts/data_contract.yaml:allowed_doc_ids` trước khi deploy doc mới.

---

## Incident 5: PII còn sót — E8 warn xuất hiện

**Symptom:** Log in `expectation[no_pii_in_cleaned] WARN :: pii_remaining_count=N > 0`.

**Detection:** E8 `no_pii_in_cleaned` (severity=warn) quét regex email/SĐT trong cleaned.

**Diagnosis:**
```bash
# Tìm dòng có PII trong cleaned CSV
python -c "
import csv, re
pii = re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.]+\b|\b0\d{9,10}\b')
with open('artifacts/cleaned/cleaned_{run_id}.csv') as f:
    for r in csv.DictReader(f):
        if pii.search(r['chunk_text']):
            print(r['chunk_id'], r['chunk_text'][:80])
"
```

**Mitigation:** Kiểm tra `mask_pii` rule — regex có cover format PII trong chunk không? Mở rộng pattern nếu cần.

**Prevention:** E8 warn thay vì halt vì PII trong lab không phải rủi ro thực tế; trong production đổi sang halt.
