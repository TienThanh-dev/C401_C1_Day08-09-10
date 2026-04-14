# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Vũ Việt Dũng  
**Vai trò trong nhóm:** Supervisor Owner (Tech Lead)  
**Ngày nộp:** 14-04-2026  
**Độ dài:** ~680 từ

---

## 1. Tôi phụ trách phần nào? (150–200 từ)

Trong Sprint 1 và Sprint 4 của Lab Day 09, tôi đảm nhận vai trò Tech Lead, tập trung toàn lực vào việc thiết kế kiến trúc lõi của hệ thống Multi-Agent và trực tiếp lập trình bộ não điều phối (Orchestrator/Supervisor). Mục tiêu cốt lõi của tôi là chuyển đổi hệ thống RAG tuyến tính đơn giản từ Lab 08 thành một đồ thị động (Directed Acyclic Graph) có khả năng định tuyến thông minh, có thể xử lý các câu hỏi chứa yếu tố ngoại lệ bằng cách ủy quyền cho các Agent chuyên biệt. 

**Cụ thể, các tác vụ và module tôi trực tiếp implement gồm:**
- Xây dựng file `graph.py` với cấu trúc LangGraph bao gồm các hàm `supervisor_node()`, định nghĩa `StateGraph` và thiết lập các edge (cạnh) để điều hướng luồng dữ liệu giữa các node (như Retrieval, Policy Tool, Synthesis).
- Tích hợp bộ cấu trúc dữ liệu chung (`AgentState`) để lưu thiết lập toàn bộ lịch sử hội thoại, nhật ký trace (`mcp_tools_used`, `workers_called`) làm tiền đề cho quá trình tự động Grading.
- Xây dựng phần core của `eval_trace.py` nhằm tự động hóa luồng chạy hàng loạt trên bộ 10 câu hỏi grading bí mật, thu thập các metric quan trọng (latency, hitl_triggered).

**Sự liên kết với các thành viên khác:**
Tôi đóng vai trò là "trạm trung chuyển" - nhận input từ người dùng, gọi các module tác vụ do Thành (Retrieval) và Phương (Policy Tool/MCP) xây dựng, sau đó điều hướng thông tin trả về đưa cho Trí (Synthesis) tổng hợp. Bằng chứng mã nguồn xuất hiện rõ trong file `graph.py` với đánh dấu quyền ưu tiên và commit code của riêng tôi.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** 
Thay vì sử dụng Prompt-based Classifier (yêu cầu LLM trả về chuỗi text thuần túy), tôi quyết định áp dụng **Pydantic Structured Output** qua API `llm.with_structured_output()` để ép Supervisor phải tuân thủ nghiêm ngặt định dạng đầu ra cho việc định tuyến.

**Lý do và Trade-off:** 
Trong giai đoạn đầu tiên của phân đoạn Sprint 1, hệ thống thường xuyên đối mặt với sự cố crash trên toàn đồ thị. Nguyên nhân là do LLM đôi khi trả lời dài dòng kiểu "Tôi sẽ chuyển yêu cầu cho retrieval_worker" thay vì chỉ in ra tên đích đến. Việc dùng Pydantic kèm thuộc tính enum cho trường `supervisor_route` đảm bảo 100% LLM chỉ được phép trả về đúng tên Worker hợp lệ. 
Bên cạnh đó, tôi ép LLM phải suy luận logic từ trước thông qua trường `route_reason`. Trade-off ở đây là độ trễ (latency) của hệ thống sẽ tăng cường thêm khoảng 300ms do LLM phải tiêu tốn thêm token để giải thích lý do, nhưng bù lại, tỷ lệ lỗi định tuyến giảm xuống ngưỡng 0%.

**Bằng chứng từ trace log thực tế:** 
Khi xem xét log ở tệp `grading_run.jsonl`, đặc biệt ở một câu dạng khó bậc nhất (multi-hop) như `gq09`, hệ thống LangGraph LLM Router đã trích xuất lý do siêu chuẩn:
```json
"supervisor_route": "policy_tool_worker",
"route_reason": "[LangGraph LLM Router] User yêu cầu thông tin về quy trình xử lý sự cố P1 và cấp quyền truy cập tạm thời, thuộc về chính sách và quy trình."
```
Đầu ra này được truyền đi hoàn toàn an toàn mà không phải vấp bất cứ lỗi phân tách chuỗi string nào.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Vấn đề lỗi gặp phải:** 
Vào giai đoạn tích hợp cuối của Sprint 4, đường ống pipeline liên tục bị ngắt (crash) ngay khi bắt đầu tự động xuất file log đánh giá, tung ra màn hình Terminal thông báo: `UnicodeDecodeError: 'cp1258' codec can't decode byte 0x90 in position 66...`. Lỗi này chặn quá trình Logging, khiến file `.jsonl` không thể ghi hoặc chứa chuỗi rỗng.

**Nguyên nhân (Root Cause):** 
Do tôi sử dụng môi trường hệ điều hành Windows, trình phiên dịch Python tự cấu hình bảng mã thông thường cho các thao tác đọc ghi ổ đĩa là CP1258 hoặc Windows-1252. Trong khi đó, văn bản mà các LLM Agent trả về là mã UTF-8 do có nhiều ký tự tiếng Việt. Khi thuật toán gọi vào lệnh `json.dumps()` sau đó đẩy thẳng biến ghi `open('artifacts/grading_run.jsonl', 'w')`, các byte tiếng Việt gốc bị dội lại do bảng mặc định không cho phép lưu trữ chéo.

**Cách khắc phục và Bằng chứng:** 
Tôi phải tiến hành rà soát để "vá" thao tác đọc/ghi toàn dự án để thêm khai báo mã hóa tường minh (phổ biến nhất ở file `eval_trace.py`). Cụ thể, tôi sửa dòng lệnh ghi file trước kia thành:
`with open("artifacts/grading_run.jsonl", "w", encoding="utf-8") as out:` 
đi kèm là bổ sung thuộc tính `ensure_ascii=False` ở phần thư viện `json`. Sau nỗ lực này, pipeline chạy một mạch 10 câu suôn sẻ không vướng một cảnh báo Unicode nào, kiểm chứng trong log file đã hiển thị mượt mà định dạng tiếng Việt.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Điểm cộng xuất sắc:** 
Khả năng điều phối tổng thê. Tôi thấy khá hài lòng lúc tự xây dựng xong bộ khung StateGraph vững chắc. Bằng việc định hình sẵn các giao thức thông báo giữa State variables, quá trình gắn nối code từ 4 kỹ sư nhóm khác chỉ tốn chừng 30 phút vào tối muộn cuối.

**Điểm yếu cần cải thiện:** 
Sự sa đà vào tính toàn vẹn và độ chuẩn khiến tôi hoàn toàn phớt lờ đi việc xem xét nâng cao tốc độ xử lý trả lời (Latency) cho sản phẩm cuối. Độ trễ trung bình sau khi đếm theo file grading_run của mình rơi vào hơn 7.4s – khá chậm lúc đưa ra làm hệ thống Customer Service theo thời gian thực. Tùy chọn gọi Node bất đồng bộ (Async call on edges) chưa có cơ hội phát huy.

**Mức độ phụ thuộc chéo:** 
Đội ngũ thực sự phụ thuộc trọn vẹn vào source `graph.py` của tôi để chạy tích hợp. Bản thân tôi cũng lại nương nhờ cực nhiều vào thiết kế cấu trúc kiểu dữ liệu của hợp đồng Lân tạo ra ban đầu ở file `worker_contracts.yaml`. 

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ dành thời gian để nhúng ngay một **Self-Correction Node (Reflection)** vào luồng đồ thị. Việc phân tích trace log của sai lầm ở câu `gq10` (Hoàn tiền sản phẩm lỗi của đợt Flash Sale) cho thấy Agent đã bị mắc bẫy thiên kiến và bỏ lỡ một dòng ngoại lệ nhỏ nằm tít phía dưới tài liệu, dẫn đến từ chối yêu cầu sai. Tôi nhắm tới việc cài thêm một chốt kiểm duyệt "LLM-as-a-Judge" chặn tại đoạn cuối trước khi chốt hạ đáp án: *"Kiểm tra lại xem vừa nãy có bỏ sót Exception rule nào giấu kỹ không?"* nhằm dập tắt triệt để sai lầm Accuracy tương tự.

---
*Lưu file: reports/individual/Vu_Viet_Dung.md*
