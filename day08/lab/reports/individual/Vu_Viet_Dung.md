# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Vũ Việt Dũng  
**Vai trò trong nhóm:** Tech Lead  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Với vai trò Tech Lead, tôi chịu trách nhiệm chính ở Sprint 2 và Sprint 3 — phần **Generation + Pipeline orchestration** trong `rag_answer.py`.

Cụ thể, tôi implement 5 hàm cốt lõi:
- **`build_context_block()`**: format chunks thành context có đánh số `[1]`, `[2]` kèm metadata để LLM trích dẫn.
- **`build_grounded_prompt()`**: thiết kế prompt với 12 quy tắc grounding (evidence-only, abstain, citation, multi-document, temporal scoping, disambiguation, exact numbers...).
- **`call_llm()`**: gọi OpenAI API (`gpt-4o-mini`, temperature=0).
- **`rag_answer()`**: orchestrate pipeline — chọn retriever → rerank → truncate → build prompt → generate → extract sources.
- **`compare_retrieval_strategies()`**: công cụ A/B so sánh dense vs hybrid.

Ngoài ra, tôi nối code end-to-end: đảm bảo output `index.py` khớp input `rag_answer.py`, và output `rag_answer()` đúng format cho `eval.py`.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab, tôi hiểu sâu hơn về **grounded prompting** — không phải chỉ nói "trả lời từ context" là đủ. Khi viết prompt ban đầu chỉ có 4 quy tắc cơ bản, pipeline vẫn bịa thêm thông tin hoặc bỏ sót ngoại lệ. Tôi phải lần lượt thêm từng quy tắc cụ thể: MULTI-DOCUMENT (buộc LLM tổng hợp nhiều nguồn), EXACT NUMBERS (cấm làm tròn số), TEMPORAL SCOPING (kiểm tra effective_date), DISAMBIGUATION (phân biệt con số cùng giá trị nhưng khác ngữ cảnh).

Điều thứ hai là **pipeline debugging theo tầng**. Khi câu trả lời sai, không thể đổ lỗi chung cho "AI sai". Phải trace ngược: retrieval có lấy đúng chunk không → context có đủ thông tin không → prompt có hướng dẫn đúng không → LLM có tuân thủ prompt không. Mỗi tầng có failure mode riêng và cách fix riêng.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều ngạc nhiên nhất là **prompt càng strict càng dễ false-abstain**. Ban đầu tôi thiết kế prompt ép LLM "TUYỆT ĐỐI KHÔNG bịa" — kết quả là pipeline đúng abstain cho gq07 (câu trap, 10/10 điểm), nhưng lại sai abstain cho gq03 (Flash Sale) và gq05 (Contractor Admin Access). Cả hai câu đều retrieve đúng source (`policy/refund-v4.pdf` và `it/access-control-sop.md`), nhưng LLM vẫn nói "không tìm thấy" — vì thông tin nằm rải ở nhiều đoạn trong context và prompt quá nghiêm khiến model "sợ" tổng hợp.

Khó khăn thứ hai là **encoding trên Windows** — PowerShell không hiển thị tiếng Việt, phải thêm `sys.stdout.reconfigure(encoding='utf-8')` ở đầu mỗi file.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq03 — "Đơn hàng mua trong chương trình Flash Sale và đã kích hoạt sản phẩm có được hoàn tiền không?"

**Phân tích:**

Pipeline trả lời: *"Không tìm thấy thông tin này trong tài liệu hiện hành"* — đây là **false abstain**, sai hoàn toàn.

**Retrieval layer**: Hoạt động đúng. `retrieve_hybrid()` trả về 3 chunks từ `policy/refund-v4.pdf` với score hợp lý. Source chứa thông tin về ngoại lệ hoàn tiền (Flash Sale, sản phẩm đã kích hoạt).

**Generation layer**: Đây là chỗ sai. Thông tin "Flash Sale không hoàn tiền" và "sản phẩm đã kích hoạt không hoàn tiền" nằm trong phần ngoại lệ của tài liệu. Tuy nhiên, prompt yêu cầu "CHỈ sử dụng thông tin có trong Context" quá strict — khi câu hỏi kết hợp 2 điều kiện (Flash Sale + đã kích hoạt), LLM không tự tin đưa ra kết luận tổng hợp vì sợ vi phạm quy tắc evidence-only.

**Root cause**: Prompt quá defensive → LLM thà abstain còn hơn bị phạt hallucination. Đây là trade-off giữa **precision** (không bịa) và **recall** (không bỏ sót câu trả lời được).

**Variant (hybrid)** không cải thiện vì lỗi ở generation layer, không phải retrieval. Cần fix ở prompt: thêm quy tắc "nếu context chứa thông tin liên quan, PHẢI trả lời dựa trên đó, chỉ abstain khi HOÀN TOÀN không có thông tin".

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Thứ nhất, tôi sẽ **tinh chỉnh prompt để giảm false-abstain** — scorecard cho thấy gq03 và gq05 bị abstain sai dù retrieval đúng. Cần thêm quy tắc: "Nếu context chứa thông tin liên quan, PHẢI trả lời, chỉ abstain khi HOÀN TOÀN không có thông tin."

Thứ hai, tôi sẽ **thử rerank (cross-encoder)** — code `rerank()` đã implement sẵn với `ms-marco-MiniLM-L-6-v2`. Scorecard baseline vs hybrid có delta ≈ 0 (Faithfulness 3.80 vs 3.80), giả thuyết là rerank sẽ cải thiện vì loại noise chunks trước khi đưa vào prompt.

---

*File: `reports/individual/Vu_Viet_Dung.md`*
