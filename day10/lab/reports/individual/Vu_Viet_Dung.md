# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Data Observability

**Họ và tên:** Vũ Việt Dũng  
**Vai trò:** Ingestion Lead  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (125 từ)

**File / module & Artifacts:**
Trong vai trò Ingestion Lead, tôi chịu trách nhiệm thiết kế kiến trúc tổng thể và điều phối toàn bộ workflow của hệ thống pipeline. Các tệp tôi trực tiếp phát triển bao gồm `etl_pipeline.py`, tài liệu `pipeline_architecture.md`, cùng hệ thống quản lý siêu dữ liệu tại `artifacts/logs/` và `artifacts/manifests/`.

**Kết nối với thành viên khác:**
Tôi xây dựng hàm `cmd_run` làm xương sống kết nối 4 giai đoạn cốt lõi: Ingest -> Transform (Trí) -> Quality Gate (Lân) -> Embed. Tôi cung cấp `run_id` xuyên suốt các bước nhằm đảm bảo tính toàn vẹn và xuất file phục vụ bước đánh giá Retrieval (Phương).

**Bằng chứng (commit / comment trong code):**
Tôi đã lập trình cơ chế ghi log tập trung Dual-Logger (ghi ra file và console đồng thời) và hàm `_build_embedding_fn` để thực hiện Idempotent Upsert dữ liệu vào ChromaDB, đảm bảo hệ thống Ingestion hoạt động chuẩn xác và có thể Audit dễ dàng.

---

## 2. Một quyết định kỹ thuật (145 từ)

**Quyết định: Xây dựng cơ chế rẽ nhánh (Fallback) cho Logging và Encoding**

**Bối cảnh:** 
Hệ thống Pipeline hoạt động như một tiến trình ngầm xử lý hàng loạt, việc theo dõi trạng thái Real-time qua Console là cần thiết cho đội ngũ Ops. Tuy nhiên, terminal của nền tảng Windows thường sử dụng các codepage không tương thích hoàn toàn chuẩn UTF-8 (như 1258 hoặc 932).

**Triển khai & Lý do:**
Trong `etl_pipeline.py`, tôi quyết định bọc hàm `print()` mặc định bởi một khối `try-except UnicodeEncodeError` bên trong hàm log tùy chỉnh. Thay vì để hệ thống crash văng lỗi khi in các ký tự đặc biệt (ví dụ: mũi tên `→` hay cụm từ có dấu phức tạp), hệ thống sẽ tự động bắt lỗi và fallback về việc encode lại chuỗi thông báo với tham số `errors='replace'`. 

Quyết định này mang tính đánh đổi: hy sinh đôi chút tính thẩm mỹ trên console (hiển thị ký tự `?` cho các font chữ lỗi) để bảo vệ tính bền vững (robustness) của toàn bộ Data Pipeline. Nó đảm bảo luồng Ingest không bao giờ bị đứt gãy vô lý, trong khi file log chính trong `artifacts/logs/` (nơi lưu trữ Audit) vẫn giữ định dạng chuẩn xác 100%.

---

## 3. Một lỗi hoặc anomaly đã xử lý (145 từ)

**Sự cố: Pipeline ngưng cấp phát dữ liệu do UnicodeEncodeError**

**Phát hiện:** 
Khi chạy thử nghiệm pipeline ở kịch bản `inject-bad` (với cờ `--skip-validate`), luồng tiến trình bị dừng đột ngột (crash) tại giai đoạn chuyển giao giữa Quality Gate và nhúng Embed. Dữ liệu traceback chỉ ra lỗi `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'`. Sự cố này tạo ra một dị thường (anomaly) nguy hiểm: bước Transform báo thành công, tài nguyên đã được xử lý nhưng ChromaDB lại không có bất kỳ vector nào được cập nhật.

**Xử lý:** 
Tôi đã thực hiện hai hành động khắc phục triệt để:
1. **Fix Tạm thời:** Truy vết các thông báo hệ thống và thay ráp toàn bộ ký tự mũi tên Unicode (`→`) bằng chuỗi text ASCII thuần túy (`->`).
2. **Fix Gốc rễ:** Tích hợp logic Fallback Encoding vào hàm `log` (đã phân tích ở phần Quyết định Kỹ thuật). Xử lý này đảm bảo pipeline sẽ tự động bypass các lỗi mã hóa console thiết bị, tiếp tục đưa luồng dữ liệu vào vectorizer bằng thuật toán `text-embedding-3-small`.

Kết quả, hệ thống hoàn thành xuất sắc kịch bản Inject PII mà không gặp gián đoạn.

---

## 4. Bằng chứng trước / sau (115 từ)

Dưới đây là trích lục từ Audit Log minh chứng hoạt động của Pipeline ở nhánh tiêu chuẩn (`clean-run`), thể hiện hiệu quả từ vai trò phân luồng của Ingestion Lead:

**Log clean-run (metadata):**
```text
run_id=clean-run
raw_records=11
cleaned_records=7
quarantine_records=4
manifest_written=artifacts\manifests\manifest_clean-run.json
PIPELINE_OK
```

**Phân tích ảnh hưởng (Before/After):** 
Bằng chứng này chứng minh luồng Ingestion đã hấp thụ đủ **11 bản ghi gốc** (before) từ file CSV thô chứa nhiễu. Đi qua tổ hợp pipeline biến đổi, metadata xuất ra file `manifest_clean-run.json` minh bạch hóa việc có **7 bản ghi** tinh khiết được đưa vào ChromaDB thành công (after), và **4 bản ghi** bị chặn lại bắn vào vùng quarantine do vi phạm rule chính sách cũ. Kết quả khẳng định pipeline có tính Deterministic và độ Auditability tin cậy cao.

---

## 5. Cải tiến tiếp theo (70 từ)

**Nâng cấp tự động hóa Near-real-time Ingestion:**
Nếu được cấp thêm 2 giờ làm việc, tôi sẽ sử dụng thư viện `watchdog` phát triển một **Watcher Daemon** chạy ngầm ở chế độ phục vụ. Khi đó, cứ mỗi tệp `.csv` thả vào `data/raw/` sẽ tự động trigger pipeline, thay vì phải chạy bằng lệnh thủ công. Điều này nâng tầm hệ thống lên kiến trúc Event-Driven, giảm độ trễ xuất bản (Publish Lag) xuống mức mili-giây.