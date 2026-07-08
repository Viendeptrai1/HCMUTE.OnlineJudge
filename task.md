# Migration Task List

## Phase 1: Refactor Backend (FastAPI REST API)
- [x] Xóa thư mục giao diện cũ (`apps/web/app/templates`, `apps/web/static`, `templating.py`).
- [x] Cập nhật `apps/web/app/main.py` (xóa StaticFiles, thêm CORSMiddleware).
- [x] Thay đổi cơ chế Auth sang JWT (Tạo module tạo token, sửa login router).
- [x] Sửa dependency `get_current_user` để đọc JWT thay vì Session Cookie.
- [x] Sửa `problems` router: Trả về JSON, nhận Pydantic thay vì Form.
- [x] Sửa `courses` router: Trả về JSON.
- [x] Sửa `contests` router: Trả về JSON.
- [x] Sửa `submissions` router: Trả về JSON.
- [x] Sửa `users` router: Trả về JSON.

## Phase 2: Khởi tạo Frontend Mới (Next.js)
- [x] Chạy lệnh `npx create-next-app` tạo thư mục `apps/frontend`.
- [ ] Cấu hình Axios gọi sang backend `localhost:8000`.
- [ ] Code trang Đăng nhập / Đăng ký.
- [ ] Code trang Danh sách bài tập.
- [ ] Code trang Chi tiết bài tập (có Code Editor).

## Phase 3: Kết nối & AWS Amplify
- [ ] Viết cấu hình `amplify.yml`.
