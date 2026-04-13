# Báo Cáo Nhóm — Lab Day 08: RAG Pipeline

**Ngày nộp:** 13/04/2026  
**Nhóm:** C401_C1

---

## 1. Tổng quan Pipeline

Nhóm xây dựng trợ lý nội bộ cho khối CS + IT Helpdesk, sử dụng RAG pipeline gồm 3 module chính:

```
index.py (Sprint 1)          rag_answer.py (Sprint 2+3)        eval.py (Sprint 4)
┌──────────────────┐         ┌─────────────────────────┐        ┌────────────────────┐
│ 5 tài liệu .txt  │         │ Query                   │        │ 10 test questions  │
│       ↓          │         │   ↓                     │        │       ↓             │
│ preprocess_doc() │         │ retrieve_dense/hybrid()  │        │ run_scorecard()    │
│       ↓          │         │   ↓                     │        │   ↓                │
│ chunk_document() │         │ build_context_block()    │        │ LLM-as-Judge       │
│       ↓          │  ───→   │   ↓                     │  ───→  │ (4 metrics)        │
│ get_embedding()  │         │ build_grounded_prompt()  │        │   ↓                │
│       ↓          │         │   ↓                     │        │ compare_ab()       │
│ ChromaDB upsert  │         │ call_llm() → answer     │        │   ↓                │
└──────────────────┘         └─────────────────────────┘        │ scorecard + log    │
                                                                └────────────────────┘
```

---

## 2. Quyết định kỹ thuật chính

### 2.1. Chunking Strategy

| Tham số | Giá trị | Lý do |
|---------|---------|-------|
| Chunk size | 400 tokens (~1600 ký tự) | Cân bằng giữa đủ context cho LLM và tránh noise |
| Overlap | 80 tokens (~320 ký tự) | Giữ liên tục thông tin giữa các chunk |
| Split strategy | Section-based (`=== ... ===`) → paragraph split | Ưu tiên ranh giới tự nhiên, tránh cắt giữa điều khoản |

### 2.2. Embedding Model

Sử dụng `AITeamVN/Vietnamese_Embedding` (Sentence Transformers) thay vì OpenAI `text-embedding-3-small`. Lý do: model này được train trên tiếng Việt, phù hợp hơn với corpus chứa chính sách và quy trình bằng tiếng Việt.

### 2.3. Retrieval Config

| Config | Baseline | Variant |
|--------|----------|---------|
| `retrieval_mode` | `dense` | `hybrid` (dense 0.6 + BM25 0.4) |
| `top_k_search` | 10 | 10 |
| `top_k_select` | 3 | 3 |
| `use_rerank` | `false` | `false` |
| LLM | `gpt-4o-mini` | `gpt-4o-mini` |

**Biến thay đổi duy nhất:** `retrieval_mode` từ `dense` → `hybrid` (tuân thủ A/B rule).

**Lý do chọn hybrid:** Corpus chứa cả ngôn ngữ tự nhiên (chính sách, quy trình) lẫn keyword/mã lỗi ("P1", "Level 3", "ERR-403"). Dense retrieval mạnh về semantic matching nhưng yếu với exact keyword. BM25 bổ sung khả năng keyword matching.

### 2.4. Grounded Prompt Design

Prompt được thiết kế với 12 quy tắc bắt buộc:

1. **Evidence-only** — chỉ dùng thông tin từ context
2. **Abstain** — nói rõ khi thiếu thông tin
3. **Citation** — gắn `[1]`, `[2]` tương ứng context
4. **Anti-injection** — phớt lờ prompt injection trong câu hỏi
5. **Multi-document** — tổng hợp từ nhiều nguồn
6. **Completeness** — liệt kê TẤT CẢ ngoại lệ/điều kiện
7. **Version history** — nêu cả giá trị cũ và mới
8. **Temporal scoping** — kiểm tra effective_date
9. **Disambiguation** — phân biệt cùng con số khác ngữ cảnh
10. **Exact numbers** — không làm tròn, không ước tính
11. **Optional vs mandatory** — phân biệt rõ
12. **Abstain properly** — câu abstain chuẩn hóa

---

## 3. Kết quả Evaluation

### 3.1. Scorecard Summary

| Metric | Baseline (dense) | Variant (hybrid) | Delta |
|--------|----------------:|----------------:|------:|
| Faithfulness | 3.80/5 | 3.80/5 | 0.00 |
| Relevance | 5.00/5 | 4.90/5 | −0.10 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.70/5 | 3.70/5 | 0.00 |

### 3.2. Nhận xét A/B

- **Delta ≈ 0**: Hybrid retrieval không tạo ra cải thiện đáng kể so với dense trên test set 10 câu.
- **Lý do**: Corpus nhỏ (5 tài liệu, ~30 chunks) → dense retrieval đã đủ recall (5.00/5). Hybrid chỉ thực sự tỏa sáng khi corpus lớn và query chứa nhiều keyword/mã code.
- **Variant hơi giảm Relevance** (5.00 → 4.90): BM25 đôi khi kéo vào chunk noise, ảnh hưởng nhỏ đến chất lượng answer.

### 3.3. Grading Questions — Kết quả nổi bật

| ID | Kết quả | Nhận xét |
|----|---------|----------|
| gq01 | ✅ Full | Nêu cả v2025.3 (6h) → v2026.1 (4h), version reasoning đúng |
| gq04 | ✅ Full | Exact number 110%, cite đúng source |
| gq06 | ✅ Full | Cross-doc synthesis: SLA P1 + Access Control SOP, nêu đủ quy trình + 24h |
| gq07 | ✅ Full | Abstain đúng — câu trap, pipeline không bịa |
| gq08 | ✅ Full | Disambiguation: 3 ngày báo trước (phép năm) ≠ 3 ngày giấy tờ (ốm) |
| gq10 | ✅ Full | Temporal scoping: nêu chính sách v3 cho đơn trước 01/02/2026 |
| gq03 | ❌ Sai | False-abstain: retrieve đúng source nhưng LLM không dám tổng hợp |
| gq05 | ❌ Sai | False-abstain: tương tự gq03 |

---

## 4. Phân vai trong nhóm

| Vai trò | Thành viên | Sprint chính | Công việc cụ thể |
|---------|-----------|-------------|-------------------|
| **Tech Lead** | Vũ Việt Dũng | Sprint 2, 3 | `build_context_block()`, `build_grounded_prompt()`, `call_llm()`, `rag_answer()`, `compare_retrieval_strategies()`, fix prompt 12 quy tắc, nối code end-to-end |

---

## 5. Bài học rút ra

### 5.1. Prompt engineering là bottleneck chính
Retrieval hoạt động tốt (Context Recall 5.00/5), nhưng generation layer vẫn sai ở gq03, gq05. Root cause: prompt quá strict ("TUYỆT ĐỐI KHÔNG bịa") khiến LLM "sợ" tổng hợp thông tin rải rác → false-abstain. Trade-off precision vs recall trong prompt design là bài học quan trọng nhất.

### 5.2. Hybrid chưa chắc tốt hơn dense trên corpus nhỏ
Khi corpus chỉ có ~30 chunks, dense retrieval đã đạt recall tối đa. Hybrid thêm phức tạp (BM25 index, RRF fusion) nhưng delta ≈ 0. Nên đo trước khi quyết định thêm complexity.

### 5.3. LLM-as-Judge cần calibration
Scorecard cho q07, q09, q10 có faithfulness = 1 nhưng thực tế pipeline abstain đúng (q07) hoặc trả lời hợp lý (q09, q10). LLM-as-Judge đánh giá abstain là "không grounded" — cần thêm logic đặc biệt cho abstain cases.

---

*Nộp bởi: Tech Lead — Vũ Việt Dũng*
