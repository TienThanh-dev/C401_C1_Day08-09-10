# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Mậu Lân  
**Vai trò trong nhóm:** Trace & Docs Owner  
**Ngày nộp:** 14-04-2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ cách phần nào? (100–150 từ)

Tôi phụ trách khâu quản trị "hiệp ước" giữa các Agent (Contracts) và toàn bộ hồ sơ kỹ thuật, báo cáo của nhóm. Vai trò của tôi là đảm bảo sự thống nhất về mặt dữ liệu giữa các thành viên và chịu trách nhiệm cao nhất về tính tuân thủ (compliance) của dự án so với file `SCORING.md`.

**Module/file tôi chịu trách nhiệm:**
- **File chính:** `contracts/worker_contracts.yaml`, `docs/system_architecture.md`, `docs/single_vs_multi_comparison.md`.
- **Functions tôi implement:** Tôi không viết nhiều logic core nhưng tôi "code" cấu trúc dữ liệu YAML cho các worker và viết báo cáo so sánh metrics.
- **Cách công việc của tôi kết nối với phần của thành viên khác:** Tôi đưa ra "luật chơi" (Contract) để Dũng, Thành, Phương và Trí phải tuân theo khi trả dữ liệu về State chung. Nếu các Agent không gửi đúng format tôi quy định, Graph sẽ không thể vận hành.
- **Bằng chứng:** File `worker_contracts.yaml` quy định rõ ràng input/output cho từng node.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Chuyển đổi toàn bộ hệ thống lưu vết từ Text log sang **JSONL Trace format**.

**Lý do:** Ở Day 08, nhóm gặp khó khăn khi so sánh các lần chạy vì log chỉ là các chuỗi văn bản dài dằng dặc, không thể phân tích bằng code. Tôi đã đề xuất và triển khai cấu trúc lưu vết dưới dạng JSONL, trong đó mỗi câu hỏi là một object chứa đầy đủ `history`, `worker_io_logs`, và `metadata`.

**Trade-off đã chấp nhận:** Sẽ mất công hơn khi setup (phải viết hàm save_trace phức tạp), nhưng bù lại khâu Evaluation và Debug sau này trở nên cực kỳ nhàn hạ và khoa học.

**Bằng chứng từ trace/code:**
Trong `contracts/worker_contracts.yaml`:
```yaml
output:
  worker_io_logs:
    type: array
    required: true
    description: "Nhật ký input/output của worker trong lượt chạy"
```
Bằng chứng thực tế: Hệ thống đã sinh ra file `eval_report.json` tự động tổng hợp số liệu từ các file JSONL này, một điều mà Day 08 không thể làm được.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Sự không đồng nhất về kiểu dữ liệu (Data Type Mismatch) giữa Worker Output và State Schema.

**Symptom:** Graph thường xuyên báo lỗi `ValidationError` khi chuyển từ Retrieval sang Synthesis. Agent bị dừng đột ngột (Aborted).

**Root cause:** Worker Retrieval trả về một list các Object, nhưng Synthesis lại mong đợi một list các String. Sự nhầm lẫn này do các bạn triển khai code độc lập mà chưa nhìn vào bản thiết kế chung.

**Cách sửa:** Tôi đã cập nhật lại `worker_contracts.yaml` một cách chi tiết nhất có thể, đồng thời viết một script kiểm tra schema nhỏ để validate output của từng worker. Tôi buộc các bạn phải sửa code để khớp 100% với contract đã cam kết.

**Bằng chứng trước/sau:**
- **Trước khi sửa:** Trace log bị ngắt quãng, supervisor không nhận được dữ liệu hợp lệ.
- **Sau khi sửa:** Đồ thị LangGraph chạy thông suốt, dữ liệu được truyền qua lại giữa 4 nodes (`supervisor` -> `retrieval` -> `policy` -> `synthesis`) mà không gặp bất kỳ lỗi schema nào.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?** 
Quản lý hồ sơ và tài liệu hóa dự án một cách cực kỳ chi tiết. Các file báo cáo so sánh `single_vs_multi_comparison.md` của tôi giúp người đọc thấy rõ được giá trị của việc nâng cấp lên Multi-Agent.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?** 
Tôi chưa đóng góp được nhiều vào việc tối ưu hóa thuật toán AI bên trong các worker, chủ yếu tập trung vào phần "vỏ" và quy trình.

**Nhóm phụ thuộc vào tôi ở đâu?** 
Nếu không có các bản Contract của tôi, nhóm sẽ mất rất nhiều thời gian để "mò" xem các Worker của nhau đang gửi gì, nhận gì.

**Phần tôi phụ thuộc vào thành viên khác:** 
Tôi phụ thuộc 100% vào kết quả chạy của Trí (Evaluation) để có số liệu viết báo cáo so sánh.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ xây dựng một **Dashboard Visualization** đơn giản bằng Streamlit để hiển thị trực quan đồ thị LangGraph và các trace kết quả, thay vì bắt người dùng phải đọc qua các file JSON thô. Trace của q15 cho thấy việc quan sát luồng Agent chuyển động rất thú vị và có giá trị giáo dục cao.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
