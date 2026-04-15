# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Phạm Minh Trí  
**Vai trò:** Cleaning Specialist  
**Ngày nộp:** 15-04-2026  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? 

**File / module:**
Tôi chịu trách nhiệm chính về logic biến đổi và làm sạch dữ liệu trong file `transform/cleaning_rules.py`. Tôi đã triển khai 3 quy tắc mở rộng bao gồm: `mask_pii` (ẩn email/SĐT), `normalize_unicode` (chuẩn hóa văn bản), và `dynamic_hr_cutoff` (lọc chính sách HR theo ngày hiệu lực động).

**Kết nối với thành viên khác:**
Tôi nhận dữ liệu thô từ Dũng sau bước Ingest, thực hiện làm sạch và trả về danh sách các `CleanedRow` kèm theo danh sách `QuarantineRow` cho Lân để thực hiện kiểm tra chất lượng (Expectations). Tôi cũng cung cấp các cột `effective_date` đã chuẩn hóa cho Thành để đo Freshness.

**Bằng chứng (commit / comment trong code):**
Tôi đã định nghĩa class `CleanedRow(BaseModel)` sử dụng Pydantic để thực hiện validate schema ngay tại lớp transform.

---

## 2. Một quyết định kỹ thuật 

Tôi quyết định sử dụng **Pydantic Model** để ép kiểu cho mọi bản ghi sau khi làm sạch. Thay vì chỉ sử dụng dictionary thông thường, việc dùng `CleanedRow` giúp chúng ta bắt được các lỗi dữ liệu tiềm ẩn (như `effective_date` không đúng định dạng `date`) ngay lập tức và đẩy chúng vào quarantine với lý do `pydantic_validation_error`.

Bên cạnh đó, tôi chọn thiết kế rule `dynamic_hr_cutoff` theo hướng đọc biến môi trường `HR_LEAVE_MIN_EFFECTIVE_DATE`. Quyết định này giúp hệ thống đạt tiêu chí Distinction-d vì không hard-code mốc thời gian lọc chính sách. Điều này cho phép đội vận hành thay đổi điều kiện lọc dữ liệu cũ (như chính sách nghỉ phép năm 2025) mà không cần phải can thiệp vào mã nguồn hay deploy lại script, chỉ cần cập nhật file `.env`.

---

## 3. Một lỗi hoặc anomaly đã xử lý 

**Sự cố: Dữ liệu trùng lặp và sai business rule**
Trong quá trình kiểm thử pipeline, tôi phát hiện hai vấn đề chính trong dữ liệu raw: Một là, tồn tại các bản ghi trùng lặp chunk_text. Hai là, nội dung policy refund chứa giá trị sai “14 ngày làm việc” thay vì “7 ngày làm việc”.

**Phát hiện:** Khi kiểm tra file raw, tôi thấy record id 1 và id 2 có nội dung giống hệt nhau. Đồng thời, record id 3 chứa giá trị không đúng với policy hiện hành. Nếu không xử lý, các lỗi này có thể làm sai kết quả truy vấn và ranking trong hệ thống downstream.

**Xử lý:** Tôi áp dụng cơ chế deduplication dựa trên _norm_text và seen_text để loại bỏ bản ghi trùng. Đồng thời, tôi triển khai rule sửa business logic cho policy_refund_v4, thay thế “14 ngày làm việc” bằng “7 ngày làm việc” và gắn tag [cleaned: stale_refund_window].

---

## 4. Bằng chứng trước / sau 

Dưới đây là bằng chứng từ dữ liệu trước và sau khi áp dụng pipeline cleaning:

**RAW (Dòng 3):**
```csv
3,policy_refund_v4,"Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn (ghi chú: bản sync cũ policy-v3 — lỗi migration).",2026-02-01,2026-04-10T08:00:00
```
**CLEANED (artifacts/cleaned/cleaned_clean-run.csv):**
```csv
policy_refund_v4_2_c96089a43e33aa9d,policy_refund_v4,Yêu cầu hoàn tiền được chấp nhận trong vòng 7 ngày làm việc kể từ xác nhận đơn (ghi chú: bản sync cũ policy-v3 — lỗi migration). [cleaned: stale_refund_window],2026-02-01,2026-04-10T08:00:00
```
**So sánh:** Giá trị “14 ngày làm việc” đã được sửa thành “7 ngày làm việc”. Đồng thời, record duplicate (id 2 trong raw) đã bị loại bỏ, giúp giảm dữ liệu trùng và đảm bảo tính chính xác cho cleaned dataset.

---

## 5. Cải tiến tiếp theo 
Nếu có thêm 2 giờ, tôi sẽ triển khai một rule sử dụng thư viện `langdetect` để tự động phát hiện ngôn ngữ của mỗi chunk. Nếu chunk có ngôn ngữ không thuộc danh sách cho phép (ví dụ tiếng Nhật/Hàn lọt vào hệ thống tiếng Việt), tôi sẽ tự động đẩy vào quarantine. Điều này giúp nâng cao độ chính xác cho kết quả tìm kiếm.
