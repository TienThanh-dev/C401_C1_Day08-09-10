# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phan Thị Mai Phương 
**Vai trò trong nhóm:** Retrieval Owner 
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, em chủ yếu làm phần retrieval của pipeline, tập trung vào Sprint 2 và Sprint 3 - **`rag_owner.py`**:
- **`retrieve_dense()`**: ở Sprint 2, để query dữ liệu từ ChromaDB bằng embedding. 
- **`retrieve_sparse()`** - BM25: Ở Sprint 3, bằng cách so trực tiếp từ. 
- **`retrieve_hybrid()`**: kết hợp cả hai **`retrieve_dense()`** và **`retrieve_sparse()`** để cải thiện việc tìm tài liệu. 
- **`rerank()`** để lọc lại các kết quả đã tìm được, chọn ra những đoạn thật sự liên quan trước khi đưa vào LLM (top đầu)
Những phần này sẽ quyết định LLM đọc gì để ra được câu trả lời.

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau khi làm lab, em đã nhận ra được việc để có thể query ra được thông tin như mong muốn không hề dễ, và trong khi dense retrieval tập trung vào việc hiểu ý nghĩa tổng thể, nó lại dễ miss những keyword cần thiết. Còn sparse retrieval lại ngược lại, nó chỉ chăm chăm vào sự chính xác của từ thay vì sự liền mạch của cả đoạn, và paraphrase trở thành điểm yếu của phương pháp này. Điều đó khiến cho việc kết hợp cả hai thật cần thiết đối với một số câu hỏi đặc thù. Bên cạnh đó, rerank cũng giúp giảm mức độ rộng của các kết quả tìm kiếm. 

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều em thấy bất ngờ là đôi lúc retrieve nhìn qua thì “có vẻ đúng”, nhưng khi đưa vào LLM thì câu trả lời vẫn sai hoặc thiếu ý. Sau khi xem kỹ thì mới nhận ra là các chunk đó chỉ liên quan chung chung, chứ không chứa đúng thông tin cần thiết. Thậm chí có những câu trả lời dù đúng, nhưng vẫn bị thừa ý, hay đúng hơn là cho thêm câu không cần thiết và dài dòng, lan man.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

Câu hỏi: q07 — “Approval Matrix để cấp quyền hệ thống là tài liệu nào?”

Phân tích:

Với câu này, baseline trả lời sai (Faithfulness = 1), dù vẫn lấy được đúng tài liệu (Recall = 5). Tức là hệ thống có “tìm thấy” thông tin, nhưng khi trả lời thì model lại không nối được “Approval Matrix” với tên mới là “Access Control SOP”, nên tự đoán → bị lệch.

Em thấy lỗi chính nằm ở phần retrieval chưa làm nổi bật đúng đoạn quan trọng, nên khi đưa vào LLM thì nó không hiểu rõ context và trả lời sai.

Sang hybrid thì em nghĩ sẽ cải thiện vì có thêm keyword, nhưng thực tế gần như không khác (vẫn sai). Điều này cho thấy chỉ thêm hybrid thôi chưa đủ, mà có thể cần rerank hoặc làm rõ context hơn để model nhìn ra được mapping này.

_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, em sẽ thử kết hợp rerank với hybrid retrieval, vì kết quả eval cho thấy dù đã retrieve đúng tài liệu (Recall cao) nhưng model vẫn trả lời sai do không chọn đúng chunk quan trọng. Ngoài ra, em cũng muốn tune lại cách build context (ví dụ làm nổi bật đoạn chứa thông tin chính) vì có những câu như q07, thông tin có sẵn nhưng không đủ rõ để model sử dụng đúng.
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
