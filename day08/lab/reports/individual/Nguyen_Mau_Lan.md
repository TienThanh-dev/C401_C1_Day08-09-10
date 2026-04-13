# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Mậu Lân  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong vai trò Eval Owner (Sprint 3-4 lead), tôi chịu trách nhiệm test questions, expected evidence, scorecard:

1. CẤU HÌNH: BASELINE_CONFIG (dense) vs VARIANT_CONFIG (hybrid) chỉ thay retrieval_mode
2. SCORING FUNCTIONS: 4 hàm LLM-as-Judge (faithfulness, answer_relevance, context_recall, completeness)
3. SCORECARD RUNNER: `run_scorecard()` chạy 10 test questions, parse LLM output, tạo ab_comparison.csv

Công việc nối trực tiếp: index.py (kiểm tra metadata fields), rag_answer.py (trích expected_sources từ result).

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

**Multi-dimensional Evaluation vs Single Accuracy:** Ban đầu tôi tưởng chỉ cần đếm "đúng/sai". Thực tế, RAG lỗi có 3 chiều riêng:

1. **Retrieval lỗi** → Context Recall = 0 (không bring về expected_sources)
2. **Generation lỗi** → Faithfulness thấp (hallucinate info không có trong chunks)  
3. **Answer không trọn vẹn** → Completeness thấp (missing chi tiết từ expected_answer)

4 metrics tách biệt cho phép **tìm root cause chính xác**, không phải chỉ biết "lỗi ở đâu". Từ đó, variant tuning có strategy rõ ràng: nếu Context Recall = 0 thì thử hybrid/rerank, nếu Completeness thấp thì optimize prompt.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

**Challenge 1 - Test questions chuẩn bị:** Ban đầu tôi nghĩ chỉ cần 10 câu "random" về policy. Nhưng README yêu cầu mỗi câu phải có:
- `expected_answer`: Trích từ tài liệu, từng từ chuẩn xác
- `expected_sources`: Danh sách file cụ thể (policy_refund_v4.txt, sla_p1_2026.txt...)
- `difficulty` & `category`: Để phân loại kết quả

Nếu expected_sources sai, Context Recall sẽ nhầm lẫn.

**Challenge 2 - LLM-as-Judge output parsing:** Model không bao giờ return JSON clean → phải regex, try-except fallback bạn.

**Insight:** Eval Owner không phải "chạy script", mà phải chuẩn bị dữ liệu chính xác (test questions + expected answers), implement robust scoring framework, và giải thích được delta trong A/B comparison.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq03 — "Đơn hàng mua trong chương trình Flash Sale và đã kích hoạt sản phẩm có được hoàn tiền không?"

**Phân tích:**

Pipeline trả lời: *"Không tìm thấy thông tin này trong tài liệu hiện hành"* — đây là **false abstain**, sai hoàn toàn.

**Retrieval layer**: Hoạt động đúng. `retrieve_hybrid()` trả về 3 chunks từ `policy/refund-v4.pdf` với score hợp lý. Source chứa thông tin về ngoại lệ hoàn tiền (Flash Sale, sản phẩm đã kích hoạt).

**Generation layer**: Đây là chỗ sai. Thông tin "Flash Sale không hoàn tiền" và "sản phẩm đã kích hoạt không hoàn tiền" nằm trong phần ngoại lệ của tài liệu. Tuy nhiên, prompt yêu cầu "CHỈ sử dụng thông tin có trong Context" quá strict — khi câu hỏi kết hợp 2 điều kiện (Flash Sale + đã kích hoạt), LLM không tự tin đưa ra kết luận tổng hợp vì sợ vi phạm quy tắc evidence-only.

**Root cause**: Prompt quá defensive → LLM thà abstain còn hơn bị phạt hallucination. Đây là trade-off giữa **precision** (không bịa) và **recall** (không bỏ sót câu trả lời được).

**Variant (hybrid)** không cải thiện vì lỗi ở generation layer, không phải retrieval. Cần fix ở prompt: thêm quy tắc "nếu context chứa thông tin liên quan, PHẢI trả lời dựa trên đó, chỉ abstain khi HOÀN TOÀN không có thông tin".

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

**Cải tiến 1:** Thêm embedding similarity score giữa query và expected_answer (thay LLM judge chậm). Phát hiện nhanh câu hỏi sai, optimize eval cost.

**Cải tiến 2:** Auto-tag lỗi ("retrieval_miss", "hallucination", "generation_incomplete") và suggest variant cụ thể (e.g., "Try hybrid retrieval" hay "Try prompt grounding").

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
