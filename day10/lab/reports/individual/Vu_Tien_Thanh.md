# Báo cáo cá nhân — Vũ Tiến Thành

**Họ và tên:** Vũ Tiến Thành
**Vai trò:** Monitoring & Ops

---

## 1. Phụ trách

Tôi triển khai `monitoring/freshness_check.py` (2 boundary, Distinction-b) và `docs/runbook.md` (5 incident scenarios). Kết nối với Ingestion Lead qua manifest `latest_exported_at` và `run_timestamp`.

**File & function phụ trách:**

| File | Hàm / thành phần |
|------|-----------------|
| `monitoring/freshness_check.py` | `check_manifest_freshness()` — đo `ingest_lag` và `publish_lag` |
| `monitoring/freshness_check.py` | `parse_iso()` — parse timestamp ISO với UTC fallback |
| `docs/runbook.md` | 5 incident scenarios (Symptom→Detection→Diagnosis→Mitigation→Prevention) |
| `README.md` | Quick Start |


---

## 2. Quyết định kỹ thuật

**SLA dùng `ingest_lag` thay vì `age_hours` trực tiếp:** Slides yêu cầu đo 2 ranh giới. Tôi dùng `ingest_lag_hours` (= `run_timestamp − latest_exported_at`) làm SLA check chính, vì nó phản ánh độ trễ nguồn dữ liệu. `publish_lag_hours` (= `now − run_timestamp`) là chỉ số bổ sung — giúp phân biệt "nguồn data chậm" vs "pipeline ngưng trệ" mà không cần thêm alert phức tạp.

**Fallback `dt_exported or dt_run`:** Nếu manifest không có `latest_exported_at`, fallback về `run_timestamp` để vẫn trả PASS/WARN/FAIL thay vì crash. Missing timestamp → WARN (cần kiểm tra pipeline ghi manifest đúng không).

**Idempotency prune trong embed:** mỗi `run` upsert theo `chunk_id` và xoá id không còn trong cleaned CSV hiện tại — tránh vector stale (chunk "14 ngày" từ `inject-bad`) ảnh hưởng grading.

---

## 3. Sự cố / anomaly

**Symptom:** `freshness_check` trả `FAIL` với `ingest_lag_hours ≈ 122.6h` trên `clean-run`.

**Diagnosis:**
```
cat artifacts/manifests/manifest_clean-run.json
# → latest_exported_at = "2026-04-10T08:00:00"
# → run_timestamp = "2026-04-15T04:19:34+00:00"
# → ingest_lag ≈ 122.6h > sla_hours (24h)
```

**Fix:** Đây là **expected behavior** trên data mẫu lab. Không can thiệp code. Production fix: cron job export định kỳ từ nguồn hoặc điều chỉnh `sla_hours` trong `.env` nếu data mẫu không đại diện cho chu kỳ thực tế.

**Evidence:** log `run_clean-run.log` (run cuối, L83): `ingest_lag_hours: 122.676`, `publish_lag_hours: 0.0`. `publish_lag = 0.0` xác nhận index trong ChromaDB vừa được upsert, vấn đề nằm ở lớp nguồn chứ không phải pipeline.

**Kết luận:** 2 boundary giúp phân biệt rõ nguyên nhân gốc — nguồn data chậm (122.6h) nhưng pipeline đang chạy bình thường (publish_lag = 0.0h).

---

## 4. Before/after

**Log sau `clean-run`:**
```
freshness_check=FAIL {"ingest_lag_hours": 122.33, "publish_lag_hours": 0.0,
                     "latest_exported_at": "2026-04-10T08:00:00",
                     "reason": "freshness_sla_exceeded"}
```

**Log sau `inject-bad` (--skip-validate):**
```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
freshness_check=FAIL {"ingest_lag_hours": 122.418, "publish_lag_hours": 0.0,
                     "reason": "freshness_sla_exceeded"}
```
→ Freshness `ingest_lag_hours` tương đương giữa hai run (≈122.6h) vì nguồn data không đổi. Thay đổi thực sự nằm ở cleaned data: `inject-bad` để stale refund "14 ngày" → expectation FAIL (violations=1); `clean-run` sửa thành "7 ngày" → expectation PASS.

**Metric impact bảng:**

| Hoạt động | Kết quả | Bằng chứng |
|-----------|---------|-----------|
| 2 boundary freshness | `ingest_lag≈122.6h`, `publish_lag=0.0h` | `run_clean-run.log` |
| runbook 5 scenarios | Incident 1–5 tài liệu hóa | `docs/runbook.md` |
| README Quick Start | 1 lệnh `etl_pipeline.py run` | `README.md` |

---

## 5. Cải tiến thêm 2 giờ

Thêm webhook gửi alert tự động khi `freshness_check=FAIL` (hướng production readiness). Kết hợp cron job export định kỳ từ nguồn để giữ `ingest_lag_hours` ≤ 24h — như đã ghi trong Prevention của Incident 1 trong runbook.
