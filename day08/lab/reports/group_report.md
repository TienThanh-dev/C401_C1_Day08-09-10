# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline
Tên nhóm: C401_C1
Thành viên:

| Tên | Vai trò | Email |
|---|---|---|
| Vũ Việt Dũng | Tech Lead | |
| Vũ Tiến Thành |  retrieval Owner | |
| Phạm Minh Trí | Eval Owner | |
| Phan Thị Mai Phương |  retrieval Owner | |
| Nguyễn Mậu Lân  |   Eval Owner | |

Ngày nộp: 13/04/2026

---

## 1. Pipeline nhóm đã xây dựng
Mô tả ngắn gọn pipeline của nhóm:

- **Chunking strategy**: Nhóm sử dụng chunk_size=400 tokens (~1600 ký tự), overlap=80 tokens. Tách theo section headers (`=== ... ===`) rồi mới chia nhỏ theo paragraph vì tài liệu có cấu trúc định dạng rõ ràng, giúp ưu tiên ranh giới tự nhiên trọn vẹn ngữ cảnh của đoạn văn mà không làm phân mảnh thông tin, tránh cắt giữa các điều khoản.  
- **Embedding model đã dùng**: Nhóm sử dụng mô hình local mã nguồn mở `AITeamVN/Vietnamese_Embedding` thay vì OpenAI. Lý do: model này được train đặc thù trên tiếng Việt, phù hợp hơn với corpus chứa chính sách và quy trình tiếng bản địa của công ty.
- **Retrieval mode**: Chuyển từ bản Baseline (Dense) sang bản Variant (Hybrid).  
- **Retrieval variant (Sprint 3)**: Nhóm chọn chế độ Hybrid (Dense kết hợp Sparse BM25) áp dụng thuật toán Reciprocal Rank Fusion (RRF) để kết hợp kết quả, top_k_search=10, top_k_select=3, không có rerank `use_rerank=false`. Lý do: Kho tài liệu chứa cả ngôn ngữ tự nhiên lẫn các mã lỗi/từ khóa kỹ thuật hẹp (như `ERR-403`, `P1`). Hybrid bù đắp nhược điểm bỏ quên từ khóa chính xác của Dense, mang lại Recall bao phủ dữ liệu tốt nhất.

## 2. Quyết định kỹ thuật quan trọng nhất
Chọn 1 quyết định thiết kế mà nhóm thảo luận và đánh đổi nhiều nhất trong lab.

**Quyết định**: Chọn chiến lược Retrieval (Dense vs Hybrid) kết hợp với tinh chỉnh Grounded Prompt tĩnh (thêm Hard Guidelines) thay vì tối ưu Embedding Model.

**Bối cảnh vấn đề**: 
Qua vòng đánh giá Baseline, hệ thống gặp hai lỗi lớn. Một là các truy vấn có mã lỗi/ID đặc thù (VD `q09`) bị thuật toán Dense thuần bỏ lỡ. Hai là hệ thống bị lỗi Hallucination khi đối diện với các câu hỏi không có đủ thông tin, model vẫn vòng vo tự đoán thay vì phải từ chối (Abstain).

**Các phương án đã cân nhắc**:

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| Chuyển sang LLM xịn hơn/Embedding tiếng Việt mạnh hơn | Tăng chất lượng chung, nhạy bén hơn về ngữ nghĩa | Chi phí inference dài hạn cao, vẫn yếu khi matching đúng thuật ngữ ngách |
| Dense retrieval thuần (Baseline) | Đơn giản, độ phức tạp hệ thống thấp | Bỏ sót các query chứa nhiều keyword kỹ thuật (`q07`, `q09`), LLM hay bịa |
| Hybrid retrieval (Dense + BM25) + Set Hard Rule Prompt | Bắt trọn vẹn xác suất của từ khóa hẹp; Lệnh cản LLM hạn chế Hallucination | Cần implement BM25 index và RRF fusion (tăng độ phức tạp hệ thống) |

**Phương án đã chọn và lý do**: 
Nhóm chọn phương án Hybrid Retrieval kết hợp với lập trình Prompt cứng (12 grounded rules) làm variant. BM25 xử lý dứt điểm các mã lỗi mà Dense bỏ lọt, trong khi Hard Prompt như một tấm khiên ép LLM phải nói "Không tìm thấy" khi thiếu evidence, giúp chặn Hallucination mà không phải đổi sang AI/Embedding model cao cấp tốn tài nguyên.

**Bằng chứng từ scorecard/tuning-log**: 
Khi theo dõi tuning-log.md, điểm Context Recall tăng vọt từ 3.2 lên 4.7 sau khi kích hoạt Hybrid. Song song đó, Faithfulness tăng từ 3.5 lên 4.8 nhờ luật prompt strict bắt ép Abstain khi context rỗng. 

## 3. Kết quả grading questions

- **Câu gq06 (Cross-doc synthesis)** pipeline xử lý cực kỳ tốt. Yêu cầu tổng hợp SLA P1 và Access Control SOP được giải quyết dứt điểm do retriever kéo đúng hai file, và pipeline tổng quát đầy đủ quy trình và thời gian 24h.
- **Câu gq03 (Flash Sale)** pipeline bị fail (Trả về False-abstain). Thông tin "Flash Sale không hoàn tiền" và "Đã kích hoạt không hoàn tiền" nằm chung trong policy hoàn tiền. Retriever đem về đúng file nhưng Prompt của generation layer làm quá gắt ép "Chỉ sử dụng context" khiến model rụt rè chối từ kết luận ngoại lệ chồng chéo.
- **Câu gq07 (abstain)** — pipeline xử lý tốt câu trap này. Thông tin hoàn toàn thiếu, mô hình dứt khoát không rơi vào bẫy tự bịa mà trả lời "Không tìm thấy thông tin này trong tài liệu hiện hành", ăn trọn điểm Abstain.

- **Ước tính điểm raw**: 90/98

- **Câu tốt nhất**: ID: gq07 — Lý do: Đây là câu bẫy (Abstain trap) nhưng hệ thống không bịa thêm mà đúng cấu trúc chối từ, chứng tỏ Grounded Validation chạy chuẩn.
- **Câu fail**: ID: gq03 — Root cause: Lỗi tại Generation layer. Prompt quá Strict ("Tuyệt đối không bịa") dẫn đến việc LLM e dè chối từ (False-abstain) dẫu đã kéo đúng source policy.
- **Câu gq07 (abstain)**: Hệ thống đã ghi nhận Abstain đúng chuẩn — minh bạch là tài liệu không chứa thông tin do Prompt có luật Abstain Properly.

## 4. A/B Comparison — Baseline vs Variant
Tóm tắt kết quả A/B thực tế của nhóm từ tuning-log.md.

**Biến đã thay đổi (chỉ 1 biến)**: `retrieval_mode` từ `dense` sang `hybrid`.

| Metric | Baseline | Variant | Delta |
|---|---|---|---|
| Faithfulness | 3.5/5 | 4.8/5 | +1.3 |
| Answer Relevance | 3.8/5 | 4.6/5 | +0.8 |
| Context Recall | 3.2/5 | 4.7/5 | +1.5 |
| Completeness | 3.6/5 | 4.3/5 | +0.7 |

**Kết luận**: 
Variant (Hybrid) thực sự tốt hơn rất nhiều so với Baseline trên các tiêu chí. Context Recall và Faithfulness cải thiện cục bộ (+1.5 và +1.3) bù đắp lỗ hổng bắt trượt Keyword và dập tắt được Hallucination do chèn thêm được Hardcode rules vào kết quả Prompt sau mix BM25.

## 5. Phân công và đánh giá nhóm

**Phân công thực tế**:

| Thành viên | Phần đã làm | Sprint |
|---|---|---|
| Vũ Việt Dũng | Tech Lead: Code pipeline core (`build_context_block`, `build_grounded_prompt`, `rag_answer`), pipeline orchestration | Sprint 2, 3 |
| Vũ Tiến Thành | Retrieval Owner: Implement `index.py`, thiết lập chunking strategy và embedding logic vào ChromaDB | Sprint 1 |
| Phan Thị Mai Phương | Retrieval Owner: Implement các hàm `retrieve_dense()`, `retrieve_sparse()`, `retrieve_hybrid()`, `_get_bm25_index()`, `rerank()`, và `transform_query()` | Sprint 2, 3 |
| Phạm Minh Trí | Eval Owner (1/2): Implement framework `eval.py`, thiết kế scorecard LLM-as-judge cho Faithfulness/Relevance | Sprint 4 |
| Nguyễn Mậu Lân | Eval Owner (2/2): Hoàn thiện `eval.py` chạy batch job, đánh giá Recall/Completeness, phân tích tuning-log | Sprint 4 |

**Điều nhóm làm tốt**: 
Đã triển khai end-to-end framework khá rành mạch từ Indexing cho tới Evaluation. Các module hoàn toàn đóng gói cô lập, giúp A/B testing vô cùng mượt mà. 

**Điều nhóm làm chưa tốt**: 
Quá tập trung làm Retrieval mà chưa lường đến việc Prompt Guardrails làm thụt giảm khả năng kết nối logic (Generative) của LLM trong bài test gq03 và gq05 dẫn đến đánh giá Abstain sai.

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì?
Nhóm sẽ dành thời gian tập trung vào fine-tuning lại Generation Layer. Do Scorecard phơi bày lỗi Trade-off (False-abstain do Prompt quá hà khắc), chúng tôi sẽ nới cấu trúc Prompt: "Nếu thông tin có liên quan trực tiếp, lập tức tổng hợp. Chỉ Abstain khi hoàn toàn mù tịt". Thứ hai, nhóm dự kiến bổ sung Query Expansion ngay từ lớp Query để tăng xác suất hit các file có mã kỹ thuật (vd biến "xin off" thành "Sở lao động/quy định xin nghỉ phép").
