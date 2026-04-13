# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 13/04/2026
**Config:**
```python
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = "gpt-4o-mini"
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 3.5 /5 |
| Answer Relevance | 3.8 /5 |
| Context Recall | 3.2 /5 |
| Completeness | 3.6 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
> **q07 (Approval Matrix)**: Context recall = 1/5 do thuật toán Semantic Dense bỏ lỡ hoàn toàn từ Alias cũ mà người dùng gõ ("Approval Matrix") khi so với nội dung trong docs ("Access Control SOP").
> **q09 (Lỗi ERR-403)**: Baseline cố gắng giải đáp vòng vo bằng logic tự chế của LLM dẫn tới Penalty nặng về lỗi Hallucination thay vì dứt khoát Abstain (từ chối do thiếu docs).

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 13/04/2026
**Biến thay đổi:** Bật `retrieval_mode = "hybrid"` (Giữ nguyên các số khác bằng với Baseline).
**Lý do chọn biến này:**
> Baseline hiện đang bị lọt lưới các keyword hẹp, khó đoán (Code ticket: P1, mã lỗi: ERR-403) do thuật toán Dense chỉ xoáy vào ý nghĩa của câu. Thay vì đổi mô hình Embedding tốn kém, nhóm mix thêm thuật toán Sparse BM25 (Hybrid Keyword) bằng cơ chế RRF fusion. Thuật toán này sinh ra để bắt trọn xác suất xuất hiện của keyword tĩnh, nó là phép biến đổi hoàn hảo nhất và tuân thủ đúng 1 biến tuning.

**Config thay đổi:**
```python
retrieval_mode = "hybrid"   
# use_rerank = False  (Giữ nguyên không đổi)
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 3.5/5 | 4.8/5 | +1.3 |
| Answer Relevance | 3.8/5 | 4.6/5 | +0.8 |
| Context Recall | 3.2/5 | 4.7/5 | +1.5 |
| Completeness | 3.6/5 | 4.3/5 | +0.7 |

**Nhận xét:**
> - Variant 1 nâng đáng kể điểm *Context Recall* (+1.5) vì thuật toán BM25 đã bao quát cả xác suất xuất hiện của từ khóa dị biệt (`q07`, `q09`) mà Dense bỏ quên. Trả về đúng file Access control.
> - Điểm *Faithfulness* cũng tăng vọt do Variant hybrid kết hợp với Hard Rule prompt đã bắt ép được model khai thật là "Không tìm thấy" khi chunk trả về = rỗng.

**Kết luận:**
> Variant 1 (Hybrid RRF) mạnh mẽ và ưu việt hơn mảng Baseline (100% Dense) cả về độ bao phủ dữ liệu mã kỹ thuật cứng lẫn anti-hallucination. Output chính thức dùng bản Variant này

---

## Tóm tắt học được

> Điền sau khi hoàn thành evaluation.

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Bệnh sinh chuyện (Hallucination). Khi người dùng hỏi một khái niệm ngoài dữ liệu traning (như ERR-403), LLM đời cao có xu hướng muốn làm "người tốt" vòng vo cố gắng giải thích bằng dữ liệu nội tại thay vì gọn gàng nhận là mình mù tịt chờ support.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Strategy Hybrid RRF + Lệnh Hardcoded cản LLM trong Prompt.
   > RRF khắc phục mọi nhược điểm của Dense Search với các term ID đặc thù của helpdesk, trong khi Prompt Guardrails là tấm khiên vững chãi chặn "Prompt Injection".

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Thử nghiệm *Query Decomposition* hoặc *Query Expansion* (Dịch ngôn ngữ & sinh từ đồng nghĩa ngữ cảnh) ở khúc đầu để gánh được các câu query mà user gõ teencode (vd: "xin off 3 day rứa SLA ticket bự là nhiu v"). 
