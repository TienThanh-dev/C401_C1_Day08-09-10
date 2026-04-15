# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Phan Thị Mai Phương  
**Vai trò:** Evaluation Lead  
**Ngày nộp:** 2026-04-15  
**Độ dài:** ~450 từ (mẫu)

---

## 1. Phụ trách

**File / module:**
Tôi chịu trách nhiệm về pha cuối cùng của pipeline — Evaluation:

* `eval_retrieval.py`: đo lường chất lượng retrieval. 
* `grading_run.py`: xuất kết quả định dạng JSONL cho giảng viên. 
* `reports/group_report.md`

**Kết nối với thành viên khác:**
Module này sẽ nhận dữ liệu từ collection ChromaDB do Dũng nạp vào. Các file đã được làm sạch của Trí và các thông báo lỗi của Lân sẽ được sử dụng để làm đối chứng cho kết quả đánh giá. Kết quả phần eval sẽ xác nhận pipeline của cả nhóm có thực sự "sạch" hay không.

**Bằng chứng:**
Tôi đã thiết kế logic quét keyword `must_not_contain` trên toàn bộ tập hợp top-k chunk để phát hiện dấu hiệu của dữ liệu lỗi thời (stale data). Ngoài ra, tôi sử dụng embedding function từ cấu hình môi trường để đảm bảo quá trình truy vấn nhất quán với dữ liệu đã được nạp vào Vector Store.

---

## 2. Quyết định kỹ thuật

**Về Chiến lược Scan Top-K cho Hits Forbidden:**

Một quyết định kỹ thuật quan trọng mà tôi thực hiện là yêu cầu kiểm tra cột `hits_forbidden` bằng cách gộp toàn bộ nội dung của top-3 (hoặc top-k) chunk lại thành một chuỗi văn bản duy nhất (`blob`) thay vì chỉ kiểm tra chunk đứng đầu (top-1).

Lý do của quyết định này xuất phát từ bản chất của hệ thống RAG: Đôi khi chunk đúng vẫn đứng ở vị trí số 1, nhưng các chunk sai (stale) vẫn lọt vào top-3. Nếu chúng ta chỉ nhìn vào top-1, chúng ta sẽ lầm tưởng hệ thống đã sạch. Tuy nhiên, khi Agent đọc context, nó sẽ thấy cả thông tin cũ (14 ngày) và mới (7 ngày), dẫn đến việc sinh ra câu trả lời mâu thuẫn hoặc gây nhầm lẫn. Bằng cách thiết lập `hits_forbidden=yes` nếu bất kỳ chunk nào trong top-k chứa từ khóa cấm, nó đã buộc  pipeline phải đạt được mức độ nhất quán cao trong Vector Store, bằng cách phát hiện mọi dấu hiệu của dữ liệu không mong muốn xuất hiện trong top-k kết quả retrieval, đảm bảo Agent giảm thiểu rủi ro "nhiễu" bởi dữ liệu cũ.

---

## 3. Sự cố / anomaly

**Sự cố: False Negative trong Evaluation**

Trong những lần chạy đầu tiên của lượt `inject-bad`, kết quả eval của tôi vẫn báo `hits_forbidden=no` mặc dù tôi biết chắc chắn dữ liệu xấu đã được nạp vào.

**Phát hiện:** Tôi kiểm tra file `artifacts/eval/after_inject_bad.csv` và thấy rằng dù dữ liệu thô có lỗi, nhưng ID của chunk lỗi lại khác với ID của chunk sạch trước đó. Do bộ nhớ đệm (cache) của ChromaDB hoặc do logic prune chưa được kích hoạt, hệ thống vẫn ưu tiên lấy ra các chunk cũ đã được fix từ các lượt chạy trước.

**Xử lý:** Tôi đã phối hợp cùng với Dũng (Lead) để thực hiện lệnh xóa thủ công collection (`col.delete()`) và chạy lại toàn bộ quy trình. Sau đó, tôi bổ sung một bước kiểm tra trong `eval_retrieval.py` để in ra preview của top-1 doc. Lỗi này giúp nhóm nhận ra tầm quan trọng của tính **Idempotency** và bước **Prune** (xóa dữ liệu thừa) sau mỗi lần nạp, đảm bảo rằng Vector Store luôn chỉ chứa đúng những gì có trong file Cleaned CSV mới nhất.

---

## 4. Before/after

Dưới đây là bằng chứng đanh thép nhất về hiệu quả của pipeline do tôi thực hiện đánh giá:

**Bảng so sánh từ artifacts/eval/ (Câu hỏi q_refund_window):**

| Lượt chạy (Run ID) | `hits_forbidden` | `top1_preview` |
|-------------------|------------------|----------------|
| **inject-bad**    | **yes**          | "...14 ngày làm việc... lỗi migration" |
| **clean-run**     | **no**           | "...7 ngày làm việc... [cleaned: stale...]" |

Chứng cứ này cho thấy khi không có rule làm sạch, hệ thống retrieval đã bị nhiễm độc bởi dữ liệu v3 cũ, và Quality Gate đã hoạt động chính xác để đưa kết quả về trạng thái an toàn trong lượt chạy chuẩn.

---

## 5. Cải tiến thêm 2 giờ

**Tích hợp LLM-based Evaluation:**
Nếu có thêm 2 giờ, tôi sẽ nâng cấp `eval_retrieval.py` để sử dụng OpenAI `gpt-4o-mini` làm "Giám khảo" (LLM-judge). Thay vì chỉ tìm kiếm từ khóa một cách cứng nhắc, LLM sẽ đánh giá độ chính xác về mặt ngữ nghĩa của các chunk được trả về. Điều này giúp phát hiện được những lỗi tinh vi hơn mà phương pháp tìm kiếm keyword đơn giản có thể bỏ sót, nâng cấp hệ thống observability.
