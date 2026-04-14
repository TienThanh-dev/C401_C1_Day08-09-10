# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Phạm Minh Trí  
**Vai trò trong nhóm:** Worker Owner 
**Ngày nộp:** 14-04-2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi phụ trách khâu cuối cùng của pipeline: Synthesis Worker và hệ thống Evaluation. Công việc của tôi là đảm bảo rằng tất cả các dữ liệu mà đồng đội thu thập được sẽ được LLM trình bày một cách dễ hiểu, chính xác và có trích dẫn nguồn đầy đủ.

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/synthesis.py`, `eval_trace.py`.
- Functions tôi implement: `synthesize()`, `_build_context()`, `_estimate_confidence()`, `run()`.

**Cách công việc của tôi kết nối với phần của thành viên khác:** Tôi chịu trách nhiệm xây dựng Synthesis Worker, là bước cuối trong pipeline multi-agent, có nhiệm vụ tổng hợp dữ liệu từ: retrieved_chunks (retrieval worker) và policy_result (policy worker) để tạo ra final_answer, sources và confidence.

**Bằng chứng:** Logic tính toán Confidence trong `synthesis.py`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi thiết kế hàm _estimate_confidence() để tính confidence heuristic thay vì gọi thêm LLM.

**Lý do:** Tôi lựa chọn sử dụng phương pháp heuristic để ước tính confidence trong hàm _estimate_confidence() thay vì gọi thêm một mô hình LLM để đánh giá (LLM-as-Judge). Quyết định này xuất phát từ yêu cầu tối ưu hiệu năng của toàn bộ pipeline multi-agent. Việc gọi thêm một LLM sẽ làm tăng đáng kể độ trễ (latency) và chi phí tính toán, trong khi hệ thống cần phản hồi gần real-time. Bằng cách tận dụng trực tiếp các thông tin đã có sẵn từ retrieval như score của các chunks và trạng thái của policy_result, tôi có thể tính toán confidence với chi phí rất thấp nhưng vẫn phản ánh được mức độ tin cậy tương đối của câu trả lời. Ngoài ra, cách tiếp cận này giúp hệ thống đơn giản hơn, dễ debug hơn vì toàn bộ logic đều nằm trong code thay vì phụ thuộc vào một model bên ngoài. Mặc dù độ chính xác có thể không cao bằng phương pháp dùng LLM để chấm điểm, tôi đánh giá rằng trade-off này là hợp lý trong bối cảnh của bài lab và yêu cầu hiệu năng của hệ thống.

**Trade-off đã chấp nhận:** Độ chính xác thấp hơn LLM-as-Judge, không hiểu semantic sâu của câu trả lời

**Bằng chứng từ trace/code:**
Trong `workers/synthesis.py`:
```python
if chunks:
        avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)
    else:
        avg_score = 0
    exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))
    confidence = min(0.95, avg_score - exception_penalty)
```
Bằng chứng từ trace: route=rag+policy, conf=0.88, 132ms.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Trích dẫn nguồn (Citation) bị sai lệch hoặc trùng lặp.

**Symptom:** Câu trả lời của Agent thường xuyên viết `[1], [1], [2]` hoặc trích dẫn vào các số không tồn tại khi tổng hợp context từ nhiều nguồn.

**Root cause:** Logic lấy danh sách source bị trùng lặp do Retrieval trả về nhiều chunk từ cùng một file, và Synthesis không quản lý được index của các file này một cách duy nhất.

**Cách sửa:** Tôi đã viết lại hàm xử lý source trong `synthesis.py`, sử dụng `Set` để lọc unique sources và map lại index từ 1 đến N ngay trước khi đưa vào Prompt của LLM.

**Bằng chứng trước/sau:**
- **Trước khi sửa:** Trích dẫn rối loạn, người dùng không biết file nào là file nào.
- **Sau khi sửa:** Trace log ghi nhận `sources: ["sla_p1_2026.txt", "access_control_sop.txt"]` và Answer trích dẫn chuẩn xác `[1], [2]`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?** 
- Xây dựng được bộ công cụ `eval_trace.py` mạnh mẽ.
- Thiết kế Synthesis Worker rõ ràng, tách biệt logic.
- Có logging đầy đủ.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?** 
- Phần System Prompt của Synthesis Worker đôi khi vẫn hơi rườm rà, dẫn đến câu trả lời dài hơn mức cần thiết ở những câu hỏi đơn giản.

**Nhóm phụ thuộc vào tôi ở đâu?** 
- Toàn bộ câu trả lời cuối cùng.
- Nếu synthesis sai thì cả hệ thống sai.

**Phần tôi phụ thuộc vào thành viên khác:** 
- Retrieval phải trả chunk chất lượng
- Policy worker phải detect exception đúng

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ triển khai **A/B Testing cho Prompt** vì trace của các câu hỏi SLA cho thấy cùng một context nhưng cách LLM hành văn đôi khi bị mất các ý chi tiết nhỏ. Tôi muốn dùng `eval_trace.py` để so sánh trực tiếp 2 phiên bản Prompt Synthesis.

---

