Chương 2. Proposal
Đề tài: A Cloud-Based Online Judge System Using Event-Driven Architecture on AWS (Hệ thống chấm bài lập trình trên nền tảng đám mây sử dụng kiến trúc hướng sự kiện trên AWS)
2.1. Tóm tắt
Hệ thống chấm bài lập trình trên nền tảng đám mây sử dụng kiến trúc hướng sự kiện trên AWS được thiết kế nhằm phục vụ nhu cầu chấm bài lập trình và tổ chức thi lập trình nội bộ cho sinh viên và giảng viên. Hệ thống hỗ trợ quản lý bài tập, nộp bài, chấm điểm tự động và phản hồi kết quả theo thời gian thực, với khả năng hỗ trợ 50 - 100 người dùng đồng thời trong giai đoạn triển khai ban đầu, và có khả năng mở rộng lên quy mô lớn hơn nhờ kiến trúc hướng sự kiện. Nền tảng tận dụng các dịch vụ AWS Serverless để triển khai kiến trúc hướng sự kiện, cho phép xử lý chấm bài bất đồng bộ, mở rộng linh hoạt theo tải và tối ưu chi phí vận hành, đồng thời cung cấp phản hồi kết quả gần thời gian thực cho người dùng, với quyền truy cập được kiểm soát thông qua Amazon Cognito.
2.2. Tuyên bố vấn đề
Vấn đề hiện tại
Quá trình chấm bài tập lập trình hiện tại chủ yếu diễn ra thủ công hoặc dựa trên các máy chủ cục bộ (local server) của trường/câu lạc bộ, vốn rất khó cài đặt và dễ bị sập (quá tải) khi có hàng trăm, nghìn sinh viên cùng nộp bài trong một kỳ thi. Các nền tảng public (như Codeforces, LeetCode) thì không hỗ trợ môi trường lớp học nội bộ. Việc tự duy trì một máy chủ vật lý 24/7 để chạy các hệ thống mã nguồn mở (như DOMjudge) lại tốn kém chi phí vận hành, lãng phí tài nguyên khi không có kỳ thi, và yêu cầu kỹ năng quản trị hệ thống cao từ phía giảng viên.
Giải pháp
Xây dựng nền tảng Online Judge dựa trên kiến trúc Serverless để đảm bảo tính mở rộng tự động. Hệ thống sử dụng Amazon S3 để lưu trữ an toàn ngân hàng câu hỏi và các file Test cases. Luồng dữ liệu nộp bài (submissions) được tiếp nhận qua API Gateway và đưa vào hàng đợi Amazon SQS để tránh nghẽn mạng. Các "Judge Workers" (công nhân chấm bài) sử dụng AWS Fargate để tự động tạo ra các môi trường Docker cô lập (sandbox), thực thi mã nguồn của sinh viên một cách an toàn và chấm điểm độc lập. Phần backend của hệ thống có thể được xây dựng bằng Python (FastAPI) Giao diện web được triển khai qua AWS Amplify, cùng với Amazon Cognito để xác thực quyền truy cập của giảng viên và sinh viên. Tương tự như DOMjudge hay CMS, hệ thống cho phép tạo kỳ thi và quản lý bài tập, nhưng hoạt động hoàn toàn trên Cloud, loại bỏ gánh nặng bảo trì máy chủ và tự động mở rộng (auto-scale) sức mạnh điện toán vào thời điểm diễn ra kỳ thi. 
Flow chuẩn
User → Amplify (frontend)
→ API Gateway
→ Lambda (backend FastAPI)
→ RDS (lưu submission)
→ SQS (queue)
→ Fargate (judge container sandbox)
→ update RDS
→ CloudWatch log toàn bộ
2.3. Kiến trúc giải pháp
User → Frontend → API → Backend → Database
↓
Queue → Worker (judge) 
