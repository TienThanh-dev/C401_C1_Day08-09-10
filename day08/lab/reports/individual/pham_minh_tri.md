# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phạm Minh Trí  
**Vai trò trong nhóm:** Eval Owner 
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

    - Trong lab này, tôi đóng vai trò Eval Owner, phụ trách chính ở Sprint 3 và Sprint 4. Ở Sprint 3, tôi xây dựng bộ test questions và định nghĩa expected evidence (expected_sources) cho từng câu hỏi để làm ground truth cho việc đánh giá retrieval. Sang Sprint 4, tôi implement hệ thống scorecard, bao gồm các hàm chấm điểm theo 4 metrics: faithfulness, answer relevance, context recall và completeness.
    - Ngoài ra, tôi thiết kế pipeline chạy evaluation end-to-end và xây dựng chức năng A/B testing để so sánh baseline (dense retrieval) với variant (hybrid retrieval). Công việc của tôi kết nối trực tiếp với phần retrieval và generation của các thành viên khác, giúp nhóm đo lường được hiệu quả của các cải tiến và đưa ra quyết định tuning dựa trên dữ liệu.
_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

    - Sau lab này, tôi hiểu rõ hơn về evaluation trong hệ thống RAG, đặc biệt là sự khác biệt giữa các metrics. Ví dụ, context recall phản ánh chất lượng retrieval, trong khi faithfulness đánh giá việc câu trả lời có bám sát context hay không. Điều này giúp tách biệt lỗi đến từ retrieval hay generation.
    - Ngoài ra, tôi cũng hiểu rõ hơn về A/B testing trong AI systems. Việc chỉ thay đổi một biến giúp xác định chính xác yếu tố nào tạo ra cải thiện. Nếu thay đổi nhiều thứ cùng lúc, sẽ rất khó kết luận nguyên nhân. Đây là một nguyên tắc quan trọng khi tuning hệ thống AI trong thực tế.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

    - Điều khiến tôi bất ngờ là việc thiết kế test questions và expected evidence khó hơn tôi nghĩ. Nếu expected_sources không chính xác hoặc không đầy đủ, thì metric context recall sẽ sai lệch, dẫn đến đánh giá sai cả pipeline.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)



**Câu hỏi:** "Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?"

**Phân tích:**

    - Đây là một câu hỏi khó vì tài liệu không cung cấp thông tin trực tiếp về trường hợp VIP, mà chỉ có chính sách hoàn tiền chung. Ở baseline (dense retrieval), hệ thống thường trả lời theo hướng suy luận, có thể thêm thông tin không có trong tài liệu, dẫn đến faithfulness thấp (hallucination nhẹ). Mặc dù relevance vẫn tương đối cao vì trả lời đúng chủ đề, nhưng completeness và grounding không đảm bảo.
    - Về context recall, hệ thống vẫn retrieve đúng tài liệu policy/refund-v4.pdf, nên điểm recall không phải vấn đề chính. Tuy nhiên, điểm quan trọng là expected_sources chỉ chứa 1 tài liệu, nhưng câu hỏi lại yêu cầu thông tin không tồn tại trong đó. Điều này khiến evaluation cần kiểm tra khả năng abstain đúng cách, thay vì trả lời “bịa”.
    - Ở variant (hybrid retrieval), hệ thống có xu hướng ổn định hơn trong việc retrieve đúng tài liệu và, nếu prompt được thiết kế tốt, sẽ trả lời theo hướng: “tài liệu không đề cập đến trường hợp VIP”. Khi đó, faithfulness và relevance đều cao hơn.
    - Qua câu này, tôi nhận ra rằng evaluation không chỉ đo khả năng trả lời đúng, mà còn đo khả năng không trả lời khi không có dữ liệu, và việc thiết kế expected_answer + expected_sources cho các câu “insufficient context” là rất quan trọng.

_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

- Nếu có thêm thời gian, tôi sẽ thử bổ sung bước reranking sau retrieval, vì kết quả evaluation cho thấy dù đã retrieve đúng tài liệu nhưng thứ tự các chunk chưa tối ưu, ảnh hưởng đến completeness của câu trả lời. Ngoài ra, tôi sẽ cải thiện bộ expected_sources, đặc biệt với các câu hỏi khó hoặc mơ hồ, vì thực tế eval cho thấy việc định nghĩa ground truth chưa chính xác có thể làm sai lệch metric context recall và dẫn đến kết luận không đúng về chất lượng hệ thống.
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
