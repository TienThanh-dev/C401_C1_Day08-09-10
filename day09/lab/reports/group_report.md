# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** C401-C1  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Vũ Việt Dũng | Tech Lead & Orchestrator |  |
| Vũ Tiến Thành | Supervisor Owner |  |
| Phạm Minh Trí | Worker Owner |  |
| Phan Thị Mai Phương | MCP Owner |  |
| Nguyễn Mậu Lân | Trace & Docs Owner |  |

**Ngày nộp:** 14-04-2026
**Repo:** `C401_C1_Day08-09-10/day09/lab`
**Độ dài khuyến nghị:** 600–1000 từ

---

## 1. Kiến trúc nhóm đã xây dựng (180–200 từ)

**Hệ thống tổng quan:**
Nhóm đã xây dựng hệ thống Multi-Agent dựa trên Pattern **Supervisor-Worker** sử dụng framework **LangGraph**. Các thành phần giao tiếp thông qua một `AgentState` tập trung, đảm bảo tính nhất quán dữ liệu xuyên suốt đồ thị. Hệ thống bao gồm 1 Supervisor và 3 Worker chuyên biệt, kết hợp cùng 1 luồng Human-in-the-loop (HITL):
1. **Supervisor Agent**: Sử dụng Model `gpt-4o-mini` với Pydantic Structured Output để định tuyến chính xác dựa trên ý định người dùng.
2. **Retrieval Worker**: Chuyên trách truy xuất dữ liệu từ ChromaDB với cơ chế **Self-healing** (tự động phát hiện Dimension Mismatch và Re-index khi thay đổi mô hình Embedding).
3. **Policy Tool Worker**: Xử lý các nghiệp vụ phức tạp về chính sách (Refund, Access Level) và tích hợp **MCP Server** để gọi công cụ mở rộng.
4. **Synthesis Worker**: Tổng hợp câu trả lời dựa trên context, đảm bảo tính grounding và thực hiện logic Abstain (từ chối trả lời) khi thiếu bằng chứng tài liệu.

**Routing logic cốt lõi:**
Supervisor điều phối dựa trên schema `RouteDecision`, phân loại input vào các nhánh:
- **Retrieval**: Cho các truy vấn thông tin tĩnh (SLA, FAQ).
- **Policy/Tools**: Cho yêu cầu thực thi cần tra cứu SOP hoặc gọi API Jira/Access qua MCP.
- **Human Review**: Kích hoạt luồng HITL (Pause/Interrupt) khi gặp sự cố không xác định hoặc mức độ rủi ro cao (Risk High).

**MCP tools đã tích hợp:**
- `search_kb`: Tra cứu nội bộ qua giao thức MCP.
- `get_ticket_info`: Truy xuất trạng thái ticket Jira thời gian thực.
- `check_access_permission`: Kiểm tra điều kiện cấp quyền theo SOP.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Chuyển đổi từ kiến trúc RAG Monolithic (Day 08) sang mô hình **Multi-Agent Supervisor-Worker** sử dụng LangGraph.

**Bối cảnh vấn đề:**
Trong Lab Day 08, hệ thống đơn Agent gặp hiện tượng "nhiễu context" khi xử lý các câu hỏi chứa nhiều ngoại lệ chính sách (ví dụ: Hoàn tiền Flash Sale hoặc truy cập 2AM). Ranh giới giữa việc tìm kiếm kiến thức và thực thi quy trình bị xóa nhòa khiến Prompt trở nên quá tải, AI thường xuyên bỏ sót các Exception Rules quan trọng hoặc nhầm lẫn giữa các tập hồ sơ tài liệu khác nhau.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Router Chain đơn giản | Triển khai nhanh, độ trễ (latency) thấp. | Khó xử lý các yêu cầu phức tạp (multi-hop), khả năng quan sát và debug từng bước kém. |
| **LangGraph Supervisor** | Kiểm soát trạng thái (State) mạnh mẽ, dễ dàng tích hợp HITL và tách biệt logic các Worker. | Độ phức tạp cao hơn, phát sinh thêm độ trễ do cần qua node Supervisor trung gian. |

**Phương án đã chọn và lý do:**
Nhóm ưu tiên chọn **LangGraph Supervisor**. Lý do cốt lõi là khả năng **tách biệt rủi ro (Risk Isolation)**. Logic kiểm tra Policy phức tạp được đóng gói riêng trong `policy_tool_worker`, giúp node `synthesis_worker` chỉ tập trung vào việc tổng hợp câu trả lời grounded mà không bị phân tâm bởi các quy tắc logic rẽ nhánh. Hơn nữa, kiến thức về trạng thái (State management) của LangGraph cho phép chúng tôi lưu trữ lịch sử chuyển đổi (`history`) và nhật ký I/O chi tiết của từng Worker, hỗ trợ debugging cực kỳ hiệu quả so với cấu trúc Chain tuyến tính. Việc tích hợp **Human-in-the-loop (HITL)** làm chốt chặn cuối cùng cho các case rủi ro cao (System Crash) cũng là một lợi thế tuyệt đối của giải pháp này.

**Bằng chứng từ trace/code:**
Trong kết quả chạy grading thực tế của câu **gq09** (Sự cố P1 lúc 2AM), Supervisor đã đưa ra quyết định định tuyến chính xác tuyệt đối:
```json
"supervisor_route": "policy_tool_worker",
"route_reason": "[LangGraph LLM Router] User yêu cầu thông tin về quy trình xử lý sự cố P1 và cấp quyền truy cập tạm thời, thuộc về chính sách và quy trình."
```

---

## 3. Kết quả grading questions (150–200 từ)

Sau khi chạy pipeline với grading_questions.json (public lúc 17:00), đồ thị LangGraph đã định tuyến thành công các câu hỏi dựa trên intent của người dùng.

**Tổng điểm raw ước tính:** 91 / 96

**Câu pipeline xử lý tốt nhất:**
**ID:** gq09 — **Lý do tốt:** Phản hồi truy xuất xuất sắc dữ liệu từ nhiều nguồn khác nhau (multi-hop). Mặc dù là câu hỏi khó nhất yêu cầu cả quy trình xử lý SLA cho P1 lúc 2AM lẫn chính sách cấp quyền Level 2, Supervisor đã ưu tiên policy_tool_worker để gọi nhiều bộ MCP tools (search_kb, get_ticket_info). synthesis_worker xử lý rất tốt việc gộp 2 thông tin riêng biệt này thành một đáp án rành mạch.

**Câu pipeline fail hoặc partial:**
**ID:** gq10 — **Fail ở đâu:** Chặn hoàn tiền sai quy định đối với sản phẩm Flash Sale bị lỗi từ nhà sản xuất.
**Root cause:** System search quá tập trung vào keyword 'Flash Sale' nên node retrieval đẩy cao context cấm hoàn tiền Flash Sale, làm mờ đi Exception clause 'Sản phẩm lỗi nhà sản xuất có thể yêu cầu trong vòng 5 ngày' nằm ở phần điều kiện phụ, dẫn đến câu trả lời thiếu thông tin.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?
Hệ thống xử lý hoàn hảo với câu trả lời: *'Không đủ thông tin trong tài liệu nội bộ.'* cùng confidence = 0.3. Hệ thống tránh được hallucination nhờ quy tắc Abstain cứng trong system prompt của synthesis_worker.

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?
Trace ghi nhận danh sách 2 workers được gọi vào flow là ['policy_tool_worker', 'synthesis_worker']. Kết quả trả về đạt 16/16 xuất sắc vì trình bày đủ thứ tự xử lý SLA P1 và liệt kê đúng điều kiện On-call IT admin cấp quyền 24h được Tech Lead phê duyệt.

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

**Metric thay đổi rõ nhất (có số liệu):**
- **Sự bùng nổ của Latency**: Độ trễ tăng từ ~4s lên trung bình ~8.1s. Đây là trade-off tất yếu để đổi lấy độ chính xác ("Phanh" hệ thống lại để Supervisor suy nghĩ).
- **Traceability (Khả năng quan sát)**: Day 09 vượt trội hoàn toàn. Chúng tôi có nhật ký `route_reason` cho mỗi câu hỏi, cho biết tại sao Agent lại chọn đường đó, trong khi Day 08 là một "hộp đen" chỉ có kết quả cuối cùng.

**Điều nhóm bất ngờ nhất:**
Đó là sự ổn định của **Self-healing** trong node Retrieval. Việc tách biệt node cho phép chúng tôi cài đặt logic kiểm tra tính tương thích của Vector DB ngay khi khởi động mà không làm treo luồng chính (Main Thread), giúp hệ thống luôn trong trạng thái sẵn sàng phục vụ.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**
Đối với các câu hỏi FAQ đơn giản (ví dụ: "SLA là gì?"), việc đi qua Supervisor -> Worker -> Synthesis thực sự gây lãng phí tài khoản API và tăng độ trễ không cần thiết. Trong tương lai, nhóm sẽ cân nhắc luồng "Fast-path" cho các câu hỏi phổ thông.

---

## 5. Phân công và đánh giá nhóm

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Vũ Việt Dũng | **Tech Lead**: Thiết kế đồ thị LangGraph, điều phối logic Supervisor và xử lý lỗi Encoding hệ thống. | 1, 4 |
| Vũ Tiến Thanh | **Retrieval Owner**: Triển khai `retrieval.py` và cơ chế Self-healing cho ChromaDB. | 1, 2 |
| Phan Thị Mai Phương | **MCP & Policy Owner**: Phát triển `policy_tool.py` và hệ thống Tool Dispatcher trong `mcp_server.py`. | 2, 3 |
| Phạm Minh Trí | **Synthesis & Eval Owner**: Xây dựng prompt grounded cho Synthesis và bộ công cụ đánh giá `eval_trace.py`. | 3, 4 |
| Nguyễn Mậu Lân | **Contract & Docs**: Thiết kế Schema tại `worker_contracts.yaml` và hoàn thiện hồ sơ kỹ thuật. | 4 |

**Điều nhóm làm tốt:**
- **Sự nhất quán của Contract**: Việc thống nhất Schema từ đầu giúp tích hợp 5 Module từ 5 thành viên khác nhau vào đồ thị chỉ trong 30 phút mà không gặp lỗi Mismatch.
- **Xử lý ngoại lệ**: Code xử lý được các lỗi đặc thù của Windows (Encoding UTF-8) và các trường hợp API Timeout.

**Điều nhóm làm chưa tốt:**
- **Tốc độ Evaluation**: Việc chạy 30 câu test mất gần 5 phút, cần cải tiến bằng cách chạy Parallel (song song) các câu hỏi không phụ thuộc nhau.
- **Abstain Rate**: Một số câu hỏi do Embedding model chưa tối ưu nên `confidence` còn thấp dù có thông tin trong tài liệu.

**Nếu làm lại, nhóm sẽ thay đổi gì?**
Nhóm sẽ triển khai **MCP qua giao thức HTTP** thực tế để cho phép mở rộng hệ thống sang các ngôn ngữ khác (ngoài Python). Ngoài ra, sẽ sử dụng **LLM-as-a-Judge** để chấm điểm tự động cho bước Synthesis thay vì dùng heuristic đơn giản, giúp bộ chỉ số đánh giá khách quan hơn.

---
*File này lưu tại: `reports/group_report.md`* 3, 4 |
| Nguyễn Mậu Lân | Contract & Documentation: Thiết kế `contracts/worker_contracts.yaml`, hoàn thiện Hồ sơ kỹ thuật (`docs/`). | 4 |

**Điều nhóm làm tốt:**
- Phối hợp và chia tách module cực kỳ rõ ràng: Mỗi thành viên phụ trách một Worker/Node độc lập, giúp việc tích hợp vào Graph diễn ra trơn tru mà không bị xung đột code.
- Giải quyết dứt điểm các lỗi kỹ thuật ngách như Unicode Encoding và Dimension Mismatch, đảm bảo hệ thống "Plug-and-Play" trên mọi máy của thành viên.
- Khả năng tự học nhanh: Toàn đội đã nắm bắt được khái niệm LangGraph và MCP chỉ trong thời gian ngắn.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**
- Thời gian chạy Evaluation còn chậm do tính chất tuần tự của Pipeline Multi-agent.
- Việc thống nhất Schema cho `AgentState` ban đầu mất nhiều thời gian thảo luận để đảm bảo tính nhất quán giữa các Worker.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**
Nhóm sẽ thiết kế thêm các Automated Unit Tests cho từng Worker ngay từ đầu Sprint 1 thay vì đợi đến Sprint 4 mới chạy Integration Test. Điều này sẽ giúp phát hiện lỗi "Abstain nhầm" hoặc "Route sai" sớm hơn.
Nhóm sẽ tích hợp **LLM-as-a-Judge** để tự động chấm điểm Confidence thay vì dùng heuristic (distance score). Ngoài ra, sẽ triển khai MCP qua giao thức HTTP thực tế thay vì gọi Module trong-process để hệ thống sẵn sàng cho việc deploy lên Cloud.

---
*File này lưu tại: `reports/group_report.md`*
