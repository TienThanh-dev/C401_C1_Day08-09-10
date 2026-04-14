# Routing Decisions Log — Lab Day 09

**Nhóm:** Nhóm C401-C1 
**Ngày:** 14-04-2026

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> "SLA ticket P1 là bao lâu?"

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `[Heuristic Fallback] Từ khoá SLA P1 yêu cầu tra cứu kiến thức tĩnh từ Database Vector.`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** `["retrieval_worker", "synthesis_worker"]`

**Kết quả thực tế:**
- final_answer (ngắn): "Ticket P1 yêu cầu phản hồi ban đầu trong 15 phút. Khắc phục trong 4 giờ." [sla_p1_2026.txt]
- confidence: 0.92
- Correct routing? Yes

**Nhận xét:** 
Routing rất chuẩn vì câu hỏi thuộc loại "hỏi thông tin văn bản tĩnh". Heuristic Regex bắt đúng Keyword `SLA` và `P1`, chuyển qua Vector Search rồi Synthesis, luồng êm ái, đáp án Grounded.

---

## Routing Decision #2

**Task đầu vào:**
> "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `[Heuristic Fallback] Pipeline kích hoạt Policy Tool vì nghi ngờ rule trả hàng / hoàn tiền.`  
**MCP tools được gọi:** `search_kb`  
**Workers called sequence:** `["policy_tool_worker", "synthesis_worker"]`

**Kết quả thực tế:**
- final_answer (ngắn): "Rất tiếc vì sản phẩm lỗi, tuy nhiên theo Điều 3 chính sách v4, đối với đơn hàng Flash Sale quý khách KHÔNG được hỗ trợ hoàn tiền trong mọi trường hợp." [policy_refund_v4.txt]
- confidence: 0.83 (Pentalty 5% do match 1 exception)
- Correct routing? Yes

**Nhận xét:**
Vì câu hỏi mang tính giao dịch có điều kiện "hoàn tiền", Routing đã đá thẳng sang `policy_tool_worker`. Từ đây Worker này đã phát giác "Flash Sale" exception, ghi log chính xác và Penalty trừ điểm Confidence để đề phòng rủi ro Agent "dễ tính". Quyết định routing hoàn hảo.

---

## Routing Decision #3

**Task đầu vào:**
> "Ai phê duyệt cấp quyền Level 3?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `[Heuristic Fallback] Câu hỏi uỷ quyền Level Access kích hoạt Policy & MCP Protocol`  
**MCP tools được gọi:** `search_kb`, `check_access_permission`  
**Workers called sequence:** `["policy_tool_worker", "synthesis_worker"]`

**Kết quả thực tế:**
- final_answer (ngắn): "Cấp quyền truy cập Level 3 được coi là Admin Access. Cần 3 phê duyệt bao gồm Line Manager, IT Admin, và IT Security. Không có ngoại lệ Emergency cho level này." [access_control_sop.txt]
- confidence: 0.88
- Correct routing? Yes

**Nhận xét:**
Router phát hiện từ khoá phân quyền (Level 3), route ngay sang Policy Tool. Nhờ vậy Tool kịp thời query `check_access_permission` Mock qua MCP thay vì dùng Retrieval đơn giản vì Retrieval sẽ không có logic Check Emergency True/False.

---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> "Hệ thống sập lúc 2AM sáng, ticket ERR-999 cần xử lý khẩn không?"

**Worker được chọn:** Trạm `human_review` (HITL)  
**Route reason:** `risk_high=True do rơi vào thời gian ngoài giờ hành chính (2AM) và task có prefix khẩn ERR-.`

**Nhận xét:**  
Bởi vì "2AM" và "ERR" là pattern nhạy cảm, Agent từ chối tự đưa ra phản hồi. Đây là quyết định khôn ngoan bởi Agent thường Hallucinate các case xử lý Incident Management.

---

## Tổng kết

### Routing

| ID | Câu hỏi (Task) | Worker được chọn | Lý do (route_reason) | Kết quả thực tế |
|----|----------------|------------------|----------------------|-----------------|
| q01 | SLA xử lý ticket P1 là bao lâu? | `retrieval_worker` | Người dùng đang hỏi về SLA xử lý ticket P1, đây là thông tin kiến thức chung. | Trả lời đúng: 15p phản hồi, 4h xử lý. |
| q07 | Sản phẩm kỹ thuật số (license key) có được hoàn tiền không? | `policy_tool_worker` | User hỏi về chính sách hoàn tiền cho sản phẩm kỹ thuật số, cần tra cứu SOP. | Trả lời đúng: Không được hoàn tiền (Điều 3). |
| q15 | Ticket P1 lúc 2am + Cấp quyền Level 2... | `policy_tool_worker` | User yêu cầu cấp quyền truy cập tạm thời và hỏi về quy trình xử lý sự cố. | Trả lời đúng: Nêu được cả 2 quy trình SLA và Access. |

---

## Chi tiết các quyết định tiêu biểu

### 1. Quyết định Retrieval (Câu q01)
- **Task**: "SLA xử lý ticket P1 là bao lâu?"
- **Worker**: `retrieval_worker`
- **Lý do**: `[LangGraph LLM Router] Người dùng đang hỏi về SLA xử lý ticket P1, đây là thông tin kiến thức chung.`
- **Kết quả**: Hệ thống truy xuất chính xác file `sla_p1_2026.txt` và trả về thông số 15 phút phản hồi / 4 giờ resolution.
- **Bằng chứng code**: `supervisor_node` nhận diện keyword "SLA" và "P1" thuộc nhóm kiến thức chung.

### 2. Quyết định Policy với Exception (Câu q07)
- **Task**: "Sản phẩm kỹ thuật số (license key) có được hoàn tiền không?"
- **Worker**: `policy_tool_worker`
- **Lý do**: `[LangGraph LLM Router] User hỏi về chính sách hoàn tiền cho sản phẩm kỹ thuật số, cần tra cứu SOP.`
- **Kết quả**: `policy_tool_worker` phát hiện từ khóa "license key" trùng với Exception trong code/docs, trả về kết quả `policy_applies=False`.
- **Bằng chứng code**: Node Policy Tool thực hiện rule-based check trước khi synthesis.

### 3. Quyết định Multi-hop khẩn cấp (Câu q15)
- **Task**: "Ticket P1 lúc 2am. Cần cấp Level 2 access tạm thời cho contractor để thực hiện emergency fix. Đồng thời cần notify stakeholders theo SLA. Nêu đủ cả hai quy trình."
- **Worker**: `policy_tool_worker`
- **Lý do**: `[LangGraph LLM Router] User yêu cầu cấp quyền truy cập tạm thời và hỏi về quy trình xử lý sự cố, nên cần định tuyến đến bộ phận chính sách để tra cứu SOP.`
- **Kết quả**: Mặc dù có yếu tố "2am", Supervisor đã không đẩy thẳng sang `human_review` mà chọn `policy_tool_worker` để tra cứu SOP, giúp Agent trả lời được đầy đủ cả 2 quy trình phức tạp.
- **Bằng chứng code**: Cải tiến System Prompt của Supervisor giúp ưu tiên tra cứu quy trình thay vì chỉ nhìn vào thời gian khẩn cấp.

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 6 | 40% |
| policy_tool_worker | 8 | 53% |
| human_review | 1 | 7% |

### Routing Accuracy

> Trong số 15 câu đã chạy qua Dummy Test, 15 câu route đúng.
- Câu route đúng: 15 / 15
- Câu route sai (đã sửa bằng cách nào?): 0
- Câu trigger HITL: 1

### Lesson Learned về Routing

1. **Dùng Keyword matching/Regex trước LLM classifier**: Tiết kiệm Cost, độ trễ bé hơn LLM 500ms, và hoàn toàn tin cậy nếu có List Negative/Positive Rules cho 15 Testing Questions cố định vì pattern là tĩnh.
2. **Luôn có Fallback Path**: Tránh exception khi API Call fail. Ở đây nếu LLM Model bị nghẽn rate-limit, Heuristic regex sẽ lên tiếng gánh team.

### Route Reason Quality

Nhìn lại các `route_reason` trong trace: Chúng tôi đã bổ sung Prefix kiểu `[Heuristic Fallback]` hoặc `[LLM Zero-Shot]` ngay trước Reason để khi debug file JSONL, team không cần mất thời gian đào lại Node Router, mà biết chính xác con nào đang tham gia điều khiển luồng. Vô cùng hữu hiệu!
