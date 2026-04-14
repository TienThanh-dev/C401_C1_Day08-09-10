# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Phan Thị Mai Phương  
**Vai trò trong nhóm:** MCP Owner  
**Ngày nộp:** 14-04-2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi phụ trách phần implement và hoàn thiện tính năng cho Agent thông qua hệ thống **MCP (Model Context Protocol)** và xử lý logic chính sách nâng cao. Đây là phần giúp Agent có thể thực thi các "hành động" thay vì chỉ trả lời văn bản đơn thuần.

**Module/file tôi chịu trách nhiệm:**
- **File chính:** `mcp_server.py`, `workers/policy_tool.py`.
- **Functions tôi implement:** `dispatch_tool`, `analyze_policy`, `get_ticket_info`.
- **Cách công việc của tôi kết nối với phần của thành viên khác:** Tôi nhận lệnh từ Supervisor của Dũng và gọi các MCP Tools. Kết quả thực thi tool của tôi được đưa vào `policy_result` để Synthesis Worker của Trí tổng hợp.
- **Bằng chứng:** Hệ thống dispatcher trong `mcp_server.py`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Sử dụng **Module-based Tool Dispatcher** cho MCP Server thay vì triển khai HTTP server thực thụ.

**Lý do:** Trong phạm vi Lab 09, việc dựng một HTTP Server thực sự sẽ làm tăng độ trễ mạng và độ phức tạp khi deploy trên máy chấm của Mentor. Tôi đã quyết định dùng một lớp Dispatcher nội bộ (In-process) để giả lập hành vi của MCP. Cách này giúp hệ thống chạy nhanh hơn đáng kể trong khi vẫn giữ nguyên kiến trúc gọi Tool thông qua Schema.

**Trade-off đã chấp nhận:** Mất đi tính đối thoại qua mạng (Network portability) nhưng tăng độ ổn định cho bài nộp local.

**Bằng chứng từ trace/code:**
Trong `mcp_server.py`:
```python
def dispatch_tool(self, tool_name: str, input_data: dict):
    tool_fn = TOOL_REGISTRY[tool_name]
    try:
        result = tool_fn(**tool_input)
        return result
```
Bằng chứng từ trace q15: `mcp_tools_used: [{"tool": "get_ticket_info", "output": {"priority": "P1", ...}}]`.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Output bị lỗi encoding khi in tiếng Việt trên Windows terminal.

**Symptom:** print bị lỗi ký tự

**Root cause:** sys.stdout không dùng UTF-8

**Cách sửa:**
```python
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except AttributeError:
        pass
```

**Bằng chứng trước/sau:**
- **Trước khi sửa:** KhÃ´ng thá»ƒ query ChromaDB
- **Sau khi sửa:** Không thể query ChromaDB

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?** 

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?** 
Tôi chưa tận dụng hết các tool MCP nâng cao như `create_ticket` vào pipeline chính do lo ngại về độ trễ của AI khi suy luận quá nhiều bước.

**Nhóm phụ thuộc vào tôi ở đâu?** 
Toàn bộ các câu hỏi về chính sách đặc thù (Refund, Access Level) của nhóm sẽ bị sai nếu phần Policy Worker của tôi không hoạt động chính xác.

**Phần tôi phụ thuộc vào thành viên khác:** 
Tôi phụ thuộc vào Dũng (Supervisor) để biết khi nào cần gọi tool nào, nếu Supervisor route sai thì Worker của tôi sẽ không có cơ hội thực thi.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ triển khai **Tool-call Validation** vì trace của câu `q15` cho thấy thỉnh thoảng AI gửi sai định dạng `ticket_id` vào MCP Tool. Tôi muốn thêm một lớp kiểm tra schema chặt chẽ ngay tại cửa ngõ của MCP Server.


