# So sánh Single-Agent (Day 08) vs Multi-Agent (Day 09)

**Nhóm:** C401-C1  
**Ngày:** 14-04-2026

---

## 1. Metrics Comparison

> Dữ liệu Day 08 lấy từ `scorecard_variant.md` (Hybrid mode) và `logs/grading_run.json`.  
> Dữ liệu Day 09 lấy từ `artifacts/eval_report.json` và 15 trace files thực tế.

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| **Avg Latency/câu** | ~11,300 ms | 8,080 ms | -3,220 ms | Day 09 nhanh hơn do không cần chạy full Hybrid (Dense+BM25+RRF), chỉ Dense OpenAI Embedding |
| **Faithfulness** | 3.80/5 | N/A (dùng Confidence) | N/A | Day 09 chuyển sang đo bằng Confidence score thay vì LLM-as-Judge |
| **Relevance** | 4.90/5 | N/A | N/A | Day 09 đo qua route_reason accuracy |
| **Context Recall** | 5.00/5 | 5/5 docs indexed | = | Cả hai đều retrieve đủ 5 tài liệu nội bộ |
| **Completeness** | 3.70/5 | N/A | N/A | Day 09 chuyển sang đo multi-hop accuracy |
| **Avg Confidence** | Không có | 0.438 | N/A | Chỉ Day 09 có metric này nhờ Synthesis Worker tính toán |
| **Routing Accuracy** | N/A (không có routing) | ~95% (14/15 câu đúng) | N/A | Day 08 không có khái niệm routing |
| **Abstain Rate** | 30% (3/10: gq03✗, gq05✗, gq07✓) | 6.7% (1/15: q09 ERR-403) | -23.3% | Day 08 bị False-Abstain ở gq03 và gq05 do Prompt quá strict |
| **HITL Rate** | 0% | 6% (1/15 câu) | +6% | Day 09 an toàn hơn nhờ Human Review cho trường hợp khẩn cấp |
| **MCP Tool Usage** | 0% | 56% (17/30 calls) | +56% | Day 09 mở rộng khả năng qua MCP protocol |
| **Multi-hop Accuracy** | 60% (gq06 đúng, gq03+gq05 sai) | ~100% (q15 trả lời đủ 2 quy trình) | +40% | Cải thiện vượt bậc nhờ Policy Worker chain với MCP search_kb |

---

## 2. Phân tích chi tiết từng điểm khác biệt

### 2.1. Vấn đề False-Abstain của Day 08

Đây là điểm yếu lớn nhất của Single Agent. Từ scorecard Day 08:

| Câu | Kết quả Day 08 | Kết quả Day 09 | Nguyên nhân khác biệt |
|-----|----------------|-----------------|----------------------|
| **gq03** (Flash Sale + đã kích hoạt) | ❌ False-Abstain: "Không tìm thấy thông tin" | ✅ Trả lời đúng: "Không được hoàn tiền (Điều 3)" | Day 09 có `policy_tool_worker` với rule-based exception detection, bắt được keyword "Flash Sale" |
| **gq05** (Contractor Admin Access) | ❌ False-Abstain: "Không tìm thấy thông tin" | ✅ Trả lời đúng: Nêu quy trình cấp quyền Level 4 | Day 09 route sang `policy_tool_worker` → gọi MCP `search_kb` lấy đúng file `access_control_sop.txt` |
| **gq07** (Câu bẫy Abstain) | ✅ Đúng: "Không tìm thấy" | ✅ Đúng: "Không đủ thông tin" | Cả hai hệ thống đều xử lý tốt câu trap |

**Root cause Day 08:** Prompt generation layer quá strict ("Tuyệt đối không bịa") khiến LLM rụt rè từ chối kết luận ngay cả khi đã retrieve đúng source.  
**Giải pháp Day 09:** Tách logic Policy ra Worker riêng với rule-based check trước khi đưa vào LLM synthesis → loại bỏ hoàn toàn False-Abstain.

### 2.2. Khả năng Multi-hop

| Câu | Day 08 | Day 09 |
|-----|--------|--------|
| **gq06/q15** (2AM + Access + SLA) | ✅ Trả lời được quy trình cấp quyền tạm thời 24h | ✅ Trả lời đầy đủ CẢ HAI quy trình: SLA notification + Access escalation |

Bằng chứng từ trace q15 (Day 09):
```json
"workers_called": ["policy_tool_worker", "synthesis_worker"],
"mcp_tools_used": ["search_kb", "get_ticket_info"],
"final_answer": "...1. On-call IT Admin cấp quyền tạm thời (max 24h)... 2. Gửi thông báo Slack #incident-p1 ngay lập tức..."
```

### 2.3. Observability (Khả năng quan sát)

| Khía cạnh | Day 08 | Day 09 |
|-----------|--------|--------|
| **Debug khi sai** | Chỉ thấy input/output cuối cùng. Phải đoán LLM sai ở đâu. | Mỗi trace ghi rõ: `route_reason`, `worker_io_logs`, `history` từng bước. |
| **Thời gian debug** | ~20-30 phút (phải chạy lại từng câu) | ~2-5 phút (mở file JSON, đọc `history` array) |
| **Routing transparency** | Không có — LLM tự quyết định mọi thứ trong 1 prompt | Có `[LangGraph LLM Router]` prefix + `route_reason` giải thích logic |

### 2.4. Khả năng mở rộng (Scalability)

| Kịch bản | Day 08 | Day 09 |
|----------|--------|--------|
| Thêm khả năng "check log server" | Phải viết lại toàn bộ prompt chính | Thêm 1 MCP tool mới + 1 dòng trong Supervisor prompt |
| Thêm ngôn ngữ mới (Tiếng Anh) | Phải duplicate pipeline | Thêm 1 Worker mới, Supervisor tự route |
| Thêm Human Review cho case nhạy cảm | Không thể — pipeline chạy thẳng | Đã built-in: set `risk_high=True` → auto HITL |

---

## 3. Kết luận

### Multi-Agent tốt hơn ở đâu?
1. **Loại bỏ False-Abstain** nhờ tách Policy logic ra Worker riêng (gq03, gq05 từ ❌ → ✅).
2. **Multi-hop accuracy tăng +40%** nhờ MCP tool chaining.
3. **Observability vượt trội** — mỗi câu có trace JSON chi tiết từng bước.
4. **An toàn hơn** — có HITL cho các trường hợp rủi ro cao.

### Multi-Agent yếu hơn ở đâu?
1. **Complexity cao hơn**: Cần maintain nhiều file (graph.py, 3 workers, mcp_server.py) thay vì 1 file `rag_answer.py`.
2. **Confidence score không tương đương** với LLM-as-Judge metrics của Day 08, khó so sánh trực tiếp.

### Bài học rút ra
Kiến trúc Multi-Agent phù hợp cho hệ thống cần **độ tin cậy cao** và **khả năng mở rộng**. Single Agent phù hợp cho prototyping nhanh. Việc chuyển đổi là xứng đáng khi hệ thống cần xử lý các edge cases phức tạp như Flash Sale exceptions hay emergency access procedures.

---
*Dữ liệu Day 08: `results/scorecard_variant.md`, `logs/grading_run.json`*  
*Dữ liệu Day 09: `artifacts/eval_report.json`, 15 trace files trong `artifacts/traces/`*
