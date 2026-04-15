# Báo cáo cá nhân

**Họ và tên:** Nguyễn Mậu Lân  
**Vai trò:** Quality Specialist 
**Ngày nộp:** 2026-04-15  
**Độ dài:** ~480 từ

---

## 1. Phụ trách

Tôi chịu trách nhiệm thiết kế và triển khai tầng kiểm soát chất lượng dữ liệu tại module `quality/expectations.py` (bao gồm các bộ tiêu chuẩn mở rộng E10–E12). Tôi nhận dữ liệu `cleaned_rows` từ Trí (Cleaning) để kiểm định trước khi chuyển giao cho Dũng (Lead) nạp vào database. Kết quả kiểm tra được xuất ra `ExpectationResult` và phối hợp với Phương để tổng hợp vào `quality_report.md`.

**Bằng chứng:** Triển khai hàm `run_expectations` và định nghĩa logic quét PII/Duplicate ID trong repo của nhóm.

---

## 2. Quyết định kỹ thuật

**Chiến lược Severity (Halt vs Warn):**
* **Halt cho `unique_chunk_id`:** Tôi quyết định dừng khẩn cấp pipeline nếu phát hiện trùng ID. Trong hệ thống RAG (ChromaDB), việc trùng ID nhưng khác nội dung sẽ gây ghi đè dữ liệu hoặc làm nhiễu kết quả tìm kiếm Top-K, phá vỡ tính nhất quán của "Source of Truth".
* **Warn cho `no_pii_in_cleaned`:** Do các biểu thức Regex quét thông tin cá nhân (PII) dễ gặp lỗi nhận diện nhầm (False Positive), tôi chỉ đặt mức cảnh báo. Điều này giúp duy trì sự thông suốt của pipeline trong khi vẫn đảm bảo team Ops có thể truy vết và kiểm tra thủ công qua log.

**Idempotency:** Tôi ủng hộ việc kiểm soát chặt chẽ trạng thái dữ liệu để đảm bảo khi chạy lại pipeline (re-run), hệ thống luôn trả về kết quả đồng nhất, đặc biệt là loại bỏ hoàn toàn các vector cũ gây nhiễu sau khi đã inject dữ liệu mới.

---

## 3. Sự cố / Anomaly đã xử lý

**Phát hiện Stale Refund Policy:**
Trong lượt chạy thử nghiệm Sprint 3 với cấu hình `inject-bad` (tắt logic fix refund), bộ Expectation của tôi đã phát hiện lỗi rò rỉ dữ liệu lỗi thời.

* **Sự cố:** Rule `refund_no_stale_14d_window` báo FAIL khi phát hiện cụm từ "14 ngày làm việc" (quy định cũ) trong tài liệu `policy_refund_v4`.
* **Xử lý:** Nhờ thiết lập mức độ `halt`, pipeline đã dừng lại đúng như thiết kế, ngăn chặn việc nạp chính sách sai lệch vào hệ thống tư vấn. Tôi đã trích xuất danh sách record vi phạm gửi cho tầng Cleaning để hiệu chỉnh lại logic trong `cleaning_rules.py`.

---

## 4. Before / After

**Log kiểm định (`artifacts/logs/run_inject-bad.log`):**
* **Trước (lỗi):** `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`. Hệ thống báo lỗi nghiêm trọng và yêu cầu dừng pipeline.
* **Sau (chuẩn):** `expectation[refund_no_stale_14d_window] OK (halt) :: violations=0`. Chỉ số vi phạm về 0 sau khi áp dụng logic sửa lỗi.

**Đánh giá:** File `artifacts/eval/before_after_eval.csv` xác nhận dòng `q_refund_window` đã chuyển từ trạng thái có lỗi sang `hits_forbidden=no`.

---

## 5. Cải tiến thêm 2 giờ

**Chuyên nghiệp hóa với Great Expectations:**
Tôi sẽ tích hợp thư viện **Great Expectations** để thay thế các hàm kiểm tra thủ công. Việc này không chỉ giúp chuẩn hóa bộ quy tắc kiểm định mà còn tự động sinh ra các báo cáo **Data Docs (HTML)** trực quan. Điều này cho phép các bên liên quan (như Product Owner) theo dõi "sức khỏe" dữ liệu theo thời gian thực mà không cần đọc log kỹ thuật phức tạp.

