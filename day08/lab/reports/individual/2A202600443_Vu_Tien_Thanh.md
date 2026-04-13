# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Vũ Tiến Thành  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Em đã làm gì trong lab này? (100-150 từ)

Với vai trò Retrieval Owner, em phụ trách Sprint 1 và hỗ trợ mảng Retrieval ở Sprint 3 — phần **Data Processing + Indexing + Hybrid Search**.

Cụ thể, em đã implement `index.py`:
- **`preprocess_document()`**: trích xuất 4 metadata fields (Source, Department, Effective Date, Access) từ header tài liệu.
- **`chunk_document()` & `_split_by_size()`**: thiết kế chunking kết hợp. Đầu tiên cắt theo section (`=== ... ===`), nếu đoạn quá dài (>400 tokens) thì chia nhỏ theo paragraph, duy trì overlap 80 tokens bằng cách nối đuôi phần cuối tụt lại.
- **`get_embedding()`**: dùng model local `AITeamVN/Vietnamese_Embedding` (SentenceTransformers) để tối ưu ngữ nghĩa tiếng Việt.
- **`build_index()`**: tích hợp ChromaDB, upsert toàn bộ docs kèm embeddings và metadata.

Em hỗ trợ nhóm về các thuật toán trong code lab và hỗ trợ test và đánh giá. Xử lý conflict code và hỗ trợ xử lý lỗi git local.

---

## 2. Điều em hiểu rõ hơn sau lab này (100-150 từ)

Sau lab, em đã thực sự hiểu sự quan trọng của thiết kế dữ liệu tiền xử lý đối với việc Retrieval — phần tìm kiếm quyết định trần chất lượng của Gen. 

Việc chunking không chỉ đơn thuần là cắt chuỗi cứng nhắc. Khi em build `chunk_document()` cắt trên ranh giới tự nhiên (section header), mỗi đoạn văn giữ được ngữ cảnh (ví dụ: ngoại lệ không bị tách khỏi chính sách). Kỹ thuật **overlap** cũng chứng minh được giá trị khi giúp các đoạn liên kết tốt hơn, tránh đứt gãy thông tin đối với các đại từ thay thế ở đầu dòng.

Em cũng nắm được vai trò **Metadata**. ChromaDB dùng metadata để filter (vd: theo `effective_date`). Đây là chìa khóa xử lý các câu hỏi Temporal mà matching vector similarity chịu thua.

---

## 3. Điều em ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều em ngạc nhiên nhất là **khoảng cách giữa Semantic Search (Dense) và Keyword Search (Sparse)**. Khi test thử với câu hỏi chứa mã lỗi (như "ERR-403") hoặc từ viết tắt sát rạt, Dense retrieval với embedding model đôi khi lại tính điểm (cosine similarity) cao cho một đoạn văn bản có nghĩa bao quát nhưng không chứa đúng keyword đó. Đó là lý do nhóm phải phát triển tiếp chiến lược Hybrid (RRF) ở Sprint 3.

Khó khăn lớn nhất em gặp phải là xử lý logic **overlap paragraphs** trong hàm `_split_by_size()`. Cắt chữ cơ học thì dễ, nhưng ghép danh sách các paragraph lại sao cho vừa không vượt giới hạn token (`CHUNK_SIZE`), vừa phải push lại paragraph cũ vào mảng mới để tạo overlap đòi hỏi phải quản lý biến index cẩn thận. Em phải log ra console `debug_chunks.json` nhiều lần để kiểm chứng văn bản không bị đứt gãy.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq08 — "Nhân viên phải báo trước bao nhiêu ngày để xin nghỉ phép năm? Con số này có giống với số ngày cần giấy tờ khi nghỉ ốm không?"

**Phân tích:**

Câu hỏi kiểm tra kỹ năng **Disambiguation** (phân biệt ngữ cảnh của các con số trùng lặp) cần dữ liệu từ đa văn bản. Pipeline xử lý tốt và đúng 10/10.

**Về mặt Retrieval**: Chiến lược Section-based chunking phát huy tác dụng. Retriever lấy được chunk nói về phép năm (báo trước 3 ngày) từ `hr/leave-policy-2026.pdf` và chunk về nghỉ ốm (giấy tờ với 3 ngày liên tiếp) có thể từ `support/helpdesk-faq.md`. Nhờ nhúng `metadata["section"]`, hệ thống mang đủ các chuỗi phân tán về hợp lại.

**Về mặt Generation**: Do input trả về trong suốt cùng prompt grounding quy định bắt buộc "Disambiguation", LLM nhận dạng và đối chiếu được hai con số "3 ngày" nằm ở hai vùng khác nhau và trả lời chính xác, mạch lạc. Đáp án khẳng định sự kết nối tốt giữa chunking chuẩn và prompting kịch liệt.

---

## 5. Nếu có thêm thời gian, em sẽ làm gì? (50-100 từ)

Thứ nhất, em sẽ áp dụng **Semantic Chunking**. Thay vì cắt văn bản tĩnh theo dấu `\n\n`, em sẽ tính cosine similarity giữa các cụm câu liên tiếp, nếu similarity tụt xuống dưới một ngưỡng (threshold) thì mới cắt chunk. Cách này giúp gộp các ý tương đồng chặt chẽ hơn.

Thứ hai, em sẽ thêm luồng **Metadata Filtering / Parent-Child Retriever**. Với các câu hỏi nhạy cảm về thời gian (như gq10), thay vì chỉ phụ thuộc vào LLM đọc raw text, em sẽ viết code parsing query để trích xuất mốc thời gian, sau đó build ChromaDB filter để chỉ lấy các chunk có `effective_date` trùng khớp.

Thứ ba, quan tâm nhiều hơn đến nhóm để nắm chắc mọi việc trước khi có biến cố xảy ra. **Save các file backup** trước khi mất code và các file kết quả quan trọng.

---
