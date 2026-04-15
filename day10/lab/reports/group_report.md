# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** C401-C1  
**Thành viên & Vai trò:**

| Tên | Vai trò (Day 10) | File & Artifacts |
|:---|:---|:---|
| Vũ Việt Dũng | **Ingestion Lead** | `etl_pipeline.py`, `pipeline_architecture.md`, `artifacts/logs/`, `artifacts/manifests/` |
| Phạm Minh Trí | **Cleaning Specialist** | `cleaning_rules.py`, `data_contract.md`, `data_contract.yaml`, `artifacts/cleaned/` |
| Nguyễn Mậu Lân | **Quality Specialist** | `expectations.py`, `quality_report.md`, `artifacts/quarantine/` |
| Vũ Tiến Thành | **Monitoring & Ops** | `freshness_check.py`, `runbook.md`, `README.md`, `requirements.txt` |
| Phan Thị Mai Phương | **Evaluation Lead** | `eval_retrieval.py`, `grading_run.py`, `group_report.md`, `artifacts/eval/` |

**Ngày nộp:** 2026-04-15  
**Repo:** `TienThanh-dev/C401_C1_Day08-09-10`

---

## 1. Pipeline tổng quan (180 từ)

Hệ thống pipeline Day 10 đại diện cho hạ tầng Ingestion mạnh mẽ, đóng vai trò "người gác cổng" dữ liệu trước khi nạp vào Vector Store phục vụ Agent. Nguồn dữ liệu thô (raw) là file CSV kết hợp từ hệ export nguồn. Trong phiên bản chạy chuẩn (`clean-run`), nhóm nạp **10 bản ghi**, bao gồm các chính sách hoàn tiền, SLA hỗ trợ khách hàng và chính sách nhân sự.

**Luồng xử lý chính:**
1. **Ingest:** Load dữ liệu thô và gắn `run_id` duy nhất cho toàn bộ chu trình xử lý.
2. **Transform:** Áp dụng Clean Rules để chuẩn hóa UTF-8, định dạng ngày tháng ISO, và lọc các dữ liệu lỗi thời.
3. **Quality Gate:** Kiểm tra các bộ tiêu chuẩn (Expectations). Nếu vi phạm mức `halt`, pipeline sẽ dừng ngay lập tức để bảo vệ tính toàn vẹn của Knowledge Base.
4. **Embed:** Sử dụng model `text-embedding-3-small` để vector hóa và thực hiện **idempotent upsert** vào ChromaDB.
5. **Monitor:** Tính toán chỉ số Freshness dựa trên 2 ranh giới (Ingest Lag và Publish Lag).

**Lệnh chạy nòng cốt:** `python etl_pipeline.py run --run-id clean-run`

---

## 2. Cleaning & expectation (210 từ)

Để đảm bảo dữ liệu "sạch" cho RAG, nhóm đã triển khai bộ quy tắc làm sạch dữ liệu và bộ tiêu chuẩn kiểm soát chất lượng vượt xa các yêu cầu baseline.

**Về Cleaning Rules (3 mở rộng):**
- **Rule `mask_pii`:** Sử dụng Regex chuyên sâu để phát hiện và che giấu email/SĐT Việt Nam. Điều này cực kỳ quan trọng trong môi trường doanh nghiệp để tuân thủ bảo mật dữ liệu.
- **Rule `normalize_unicode`:** Đồng bộ encoding về NFC và loại bỏ các ký tự tàng hình (BOM, ZWSP) thường gặp khi export từ Excel, tránh gây nhiễu cho quá trình embedding.
- **Rule `dynamic_hr_cutoff`:** Cho phép điều chỉnh mốc thời gian "policy stale" thông qua biến môi trường `.env`. Điều này giúp hệ thống linh hoạt khi đổi sang kỳ chính sách mới mà không cần can thiệp code.

**Về Expectation Suite (2 mở rộng):**
- **Expectation `unique_chunk_id` (Halt):** Đảm bảo không có ID trùng lặp. Việc trùng ID trong ChromaDB sẽ gây ra lỗi ghi đè dữ liệu sai lệch mà không có cảnh báo nếu không kiểm soát từ lớp này.
- **Expectation `no_pii_in_cleaned` (Warn):** Một lớp bảo vệ thứ hai sau khi mask, cảnh báo cho đội ngũ Ops nếu PII vẫn còn lọt qua các bộ lọc regex.

Ngoài ra, nhóm sử dụng **Pydantic Model Validation** (`CleanedRow`) để kiểm tra cấu trúc dữ liệu nghiêm ngặt trước khi embed, đạt tiêu chí Distinction-a của môn học.

---

## 2a. Bảng metric_impact (Bắt buộc)

Dưới đây là số liệu thống kê thực tế đo được từ các lượt chạy pipeline:

| Rule / Expectation mới | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV) |
|-------------------------|-----------------|---------------------------|-----------------------|
| `mask_pii` | 0 masked | **0 masked** | `cleaned_clean-run.csv` |
| `dynamic_hr_cutoff` | 10 dòng lọt | **4 dòng bị loại** | `run_clean-run.log`: quarantine=4 |
| `pydantic_validation` | N/A | 0 violations (pass) | `run_clean-run.log` exit 0 |
| `unique_chunk_id` (E7) | N/A | 0 duplicate | `run_clean-run.log`: OK |
| `no_pii_in_cleaned` (E8)| 0 row PII | **0 row remaining** | `run_clean-run.log`: OK (warn 0) |

---

## 3. Before / after ảnh hưởng retrieval (230 từ)

Nhóm đã sử dụng kịch bản **Sprint 3 (Inject corruption)** để chứng minh giá trị của Pipeline Observability.

**Thực nghiệm:** Chạy pipeline với `--no-refund-fix --skip-validate`. Tại kịch bản này, rule sửa đổi thời hạn hoàn tiền từ v3 (14 ngày) sang v4 (7 ngày) bị tắt, đồng thời Quality Gate bị bỏ qua.

**Kết quả từ Eval Retrieval (`artifacts/eval/`):**
1. **Scenario `inject-bad`:** Khi đặt câu hỏi về thời hạn hoàn tiền, hệ thống retrieval trả về đoạn văn bản chứa thông tin **"14 ngày làm việc"**. Kết quả cột `hits_forbidden` trả về **`yes`**. Điều này cực kỳ nguy hiểm nếu Agent trả lời khách hàng thông tin sai lệch này.
2. **Scenario `clean-run`:** Nhờ Cleaning Rule số 6 hoạt động, đoạn văn được sửa thành **"7 ngày làm việc [cleaned: stale_refund_window]"**. Eval retrieval ghi nhận `hits_forbidden: no` và câu trả lời top-1 hoàn toàn chính xác theo chính sách v4 hiện hành.

**Bằng chứng định lượng thực tế:**
- file: `artifacts/eval/grading_run.jsonl` -> `hits_forbidden: false` (sau khi fix)
- file: `artifacts/eval/after_clean.csv` -> `hits_forbidden: no`

**Merit Evidence:** Câu hỏi `q_leave_version` đạt `top1_doc_matches: yes` trong clean-run, xác nhận rule lọc chính sách HR cũ (2025) đã hoạt động hoàn hảo, chỉ giữ lại bản 2026.

---

## 4. Freshness & monitoring (120 từ)

Nhóm thiết lập SLA Freshness cho dữ liệu Ingest là **24 giờ**.

- **Thực tế:** Kết quả trả về `FAIL`.
- **Phân tích:** `ingest_lag_hours ≈ 122.6h`. Do file nguồn mẫu gốc có mốc `exported_at = 2026-04-10`, trong khi thời gian pipeline chạy là `2026-04-15`.
- **Giải pháp xử lý:** Trong Runbook (Incident 1), nhóm đã ghi nhận đây là hành vi **expected** với dữ liệu lab. Tuy nhiên, chỉ số `publish_lag_hours = 0.0` lại cho thấy trạng thái index trong ChromaDB là cực kỳ "tươi", vừa được cập nhật ngay lúc đó. Điều này giúp nhóm phân biệt rõ ràng giữa "lỗi do nguồn dữ liệu chậm" và "lỗi do pipeline ngưng trệ".

---

## 5. Liên hệ Day 09 (80 từ)

Bộ dữ liệu tri thức sau khi được pipeline này "làm sạch" sẽ được lưu vào collection `day10_kb`. Các Multi-Agent từ Day 09 có thể truy vấn trực tiếp vào collection này để đảm bảo câu trả lời luôn khớp với các chính sách mới nhất (v4). Nhóm quyết định tách riêng collection giúp tránh tình trạng "Corrupt Data" từ Sprint 3 ảnh hưởng đến hệ thống Agent đang vận hành ổn định trước đó.

---

## 6. Rủi ro còn lại & việc chưa làm (60 từ)

1. **PII Accuracy:** Regex che giấu thông tin hiện tại có thể gây tình trạng "che nhầm" (false positive) với các mã số sản phẩm dài 10-11 chữ số tương tự số điện thoại.
2. **Alerting:** Chưa có hệ thống gửi thông báo tự động (webhook) về Telegram/Slack khi Freshness FAIL.
3. **Advanced Eval:** Cần tích hợp LLM-judge để đánh giá sâu hơn chất lượng các chunk text sau khi đã được clean (ví dụ: kiểm tra tính mạch lạc sau khi mask PII).