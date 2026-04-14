# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Vũ Tiến Thành  
**Vai trò trong nhóm:** Worker Owner (Retrieval Specialist)  
**Ngày nộp:** 14-04-2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi phụ trách xây dựng và duy trì hệ thống truy xuất dữ liệu (Retrieval), một thành phần sống còn cho bất kỳ hệ thống AI Agent nào. Công việc của tôi là đảm bảo Agent luôn tìm thấy đúng bằng chứng (chunks) từ hàng trăm trang tài liệu nội bộ của công ty.

**Module/file tôi chịu trách nhiệm:**
- **File chính:** `workers/retrieval.py`.
- **Functions tôi implement:** `_get_collection`, `_get_embedding_fn`, `retrieve_dense`, `run`.
- **Cách công việc của tôi kết nối với phần của thành viên khác:** Tôi nhận `task` từ Supervisor của Dũng và cung cấp `retrieved_chunks` cho Synthesis Worker của Trí. Tôi cũng phối hợp với Lân để đảm bảo cấu trúc Chunking khớp với Docs.
- **Bằng chứng:** Code logic xử lý ChromaDB trong `retrieval.py`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Cài đặt cơ chế **Self-healing Indexing** ngay trong Worker thay vì dùng script rời.

**Lý do:** Trong quá trình làm việc nhóm, các thành viên thường xuyên cấu hình sai thư mục `chroma_db` hoặc đổi model embedding dẫn đến lỗi "Collection Not Found". Thay vì bắt anh em phải chạy tay script index, tôi đã tích hợp logic: Nếu tìm DB không thấy hoặc DB trống, Worker sẽ tự động quét thư mục `data/docs/` và nạp lại dữ liệu ngay lập tức.

**Trade-off đã chấp nhận:** Lần chạy đầu tiên của hệ thống sẽ bị chậm thêm khoảng 15-20 giây để indexing, nhưng đổi lại tính tiện dụng là tuyệt đối cho người dùng cuối.

**Bằng chứng từ trace/code:**
Trong `workers/retrieval.py`:
```python
if collection.count() == 0:
    should_reindex = True
    print(f"🚀 Self-healing: Tự động Indexing dữ liệu...")
# Tiếp theo: quét _DATA_DOCS_PATH, split theo đề mục ===,
# add từng chunk với metadata {source, chunk} vào collection
```
Bằng chứng thực tế: Hệ thống tự nạp lại 5 tài liệu IT/HR khi bạn khởi chạy project lần đầu mà không cần tác động thủ công.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Trả về kết quả rỗng (Empty Results) do sai lệch Vector Dimension.

**Symptom:** Khi chuyển từ OpenAI sang model Embedding nội bộ, hệ thống không báo lỗi nhưng luôn trả về `[]` cho mọi câu hỏi, mặc dù tài liệu vẫn nằm đó.

**Root cause:** Khi khởi tạo ChromaDB, hệ thống lưu vết dimension của model trước đó. Model mới có số chiều khác nên không thể thực hiện phép so sánh Cosine Similarity.

**Cách sửa:** Tôi đã sửa hàm `_get_collection` để kiểm tra tính tương thích của Model. Nếu phát hiện thay đổi cấu hình, Agent sẽ tự động xóa collection lỗi và tạo mới.

**Bằng chứng trước/sau:**
- **Trước khi sửa:** Trace log ghi nhận `retrieved_chunks: []` -> Confidence: 0.1.
- **Sau khi sửa:** Trace log ghi nhận `retrieved_chunks: [3 entries]` -> Answer trả về thông tin SLA chuẩn xác.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?** 
Xây dựng được một Worker ổn định, có khả năng tự phục hồi (Self-healing). Việc tối ưu hóa Metadata giúp Synthesis Worker trích dẫn được chính xác tên file tài liệu trong câu trả lời.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?** 
Tôi chưa triển khai được cơ chế Hybrid Search (Dense + Sparse) như ở Day 08 do giới hạn thời gian tích hợp vào LangGraph.

**Nhóm phụ thuộc vào tôi ở đâu?** 
Nếu Retrieval của tôi không kéo được dữ liệu, toàn bộ pipeline của nhóm sẽ chỉ trả về "Tôi không biết" vì Synthesis không có context để làm việc.

**Phần tôi phụ thuộc vào thành viên khác:** 
Tôi cần Dũng gửi đúng `task` đã được làm sạch (cleaned) để tăng độ chính xác của Vector Search.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thử **Reranking** vì trace của câu `q07` cho thấy thỉnh thoảng Chunk đúng bị đẩy xuống vị trí số 3. Tôi muốn dùng một model reranker nhẹ (như BGE-Reranker) để đưa bằng chứng quan trọng nhất lên đầu.

---
*Lưu file: reports/individual/Vu_Tien_Thanh.md*
