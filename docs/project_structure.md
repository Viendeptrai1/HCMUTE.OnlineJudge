# HCMUTE.OnlineJudge - Kiến trúc & Cấu trúc Dự án

Dự án được thiết kế theo hướng **Monorepo** quản lý bởi trình quản lý thư viện `uv`, ứng dụng chặt chẽ các nguyên lý **SOLID** và **Clean Architecture**.

## 1. Tổng quan cấu trúc Monorepo (Root Level)

```text
HCMUTE.OnlineJudge/
├── apps/                 # Chứa các ứng dụng/services chính
│   ├── web/              # Backend API & Server-rendered UI (FastAPI + Jinja2 + HTMX)
│   └── judge-worker/     # Worker chấm bài tự động chạy nền (Python Sandbox)
├── docs/                 # Tài liệu hệ thống (ERD, API Specs, Cấu trúc dự án)
├── scripts/              # Chứa các script tiện ích (seed data, requeue submissions,...)
├── docker-compose.yml    # Cấu hình môi trường dev local (Postgres, Redis, LocalStack)
├── pyproject.toml        # File quản lý thư viện chung & config linter/formatter (Ruff/Mypy)
├── Makefile              # Các lệnh rút gọn thao tác (make dev, make worker, make seed)
└── README.md             # Tài liệu giới thiệu tổng quan
```

## 2. Kiến trúc Ứng dụng Web (`apps/web`)

Ứng dụng web được chia theo kiến trúc Modular Monolith. Mỗi tính năng nghiệp vụ được đóng gói thành một Module hoàn chỉnh và biệt lập.

```text
apps/web/
├── alembic/              # Thư mục quản lý cấu trúc Database Migration
├── static/               # File tĩnh (CSS build bằng Tailwind CLI, JS, Hình ảnh)
├── tests/                # Thư mục chứa Unit Test & Integration Test
└── app/                  # Chứa toàn bộ source code của Web App
    ├── core/             # Cấu hình cốt lõi (Database session, Settings, Security)
    ├── shared/           # Code tiện ích dùng chung (Observability, Rate Limit, Storage, Base Repository)
    ├── templates/        # Chứa file HTML layouts dùng chung (base.html, navbar)
    ├── main.py           # Entry point của ứng dụng FastAPI
    └── modules/          # Nơi chứa logic nghiệp vụ, chia thư mục theo Domain
        ├── auth/
        ├── contests/     # Quản lý Kỳ thi, Leaderboard
        ├── courses/      # Quản lý Lớp học, Thành viên lớp
        ├── problems/     # Ngân hàng câu hỏi
        ├── submissions/  # Ghi nhận trạng thái bài nộp
        ├── tags/         # Gắn tag phân loại
        ├── testcases/    # Quản lý bộ dữ liệu test
        └── users/        # Quản lý tài khoản
```

## 3. Cấu trúc tiêu chuẩn của một Module (Áp dụng SOLID & Clean Architecture)

Mỗi module trong thư mục `modules/` (ví dụ `modules/courses/`) đều tuân theo thiết kế 5-7 lớp (Layers). Thiết kế này giúp hệ thống siêu dễ mở rộng, dễ test, và không bị phụ thuộc vòng tròn:

| Tên File / Thư mục | Chức năng (Trách nhiệm) | Nguyên lý SOLID nổi bật |
|---|---|---|
| `models.py` | Định nghĩa cấu trúc bảng Database thông qua SQLAlchemy ORM. | **S** - Single Responsibility (Chỉ chứa định nghĩa lược đồ Database, không chứa logic validate). |
| `schemas.py` | Định nghĩa Data Transfer Object (DTO) bằng Pydantic. Đóng vai trò validate Request/Response data. | **S** - Tách riêng phần validate logic của web ra khỏi Database Model. |
| `repository.py` | Tầng tương tác trực tiếp với Database. Kế thừa từ class `SqlAlchemyRepository` ở `shared/`. Đóng gói toàn bộ các câu lệnh SQL ở đây. | **O, L, I** - Mở rộng dựa trên Protocol Generic Repository chung. Có thể thay thế Repository Database khác mà không sửa các hàm gọi. |
| `service.py` | **Tầng chứa Core Business Logic**. Nơi tính toán nghiệp vụ (VD: chấm điểm, xếp hạng). Nhận/trả dữ liệu qua Repository. Đẩy ra các Exception mang tính nghiệp vụ (DomainError). | **S, D** - Service hoàn toàn không dính dáng đến Framework FastAPI hay Database Engine. Nó nhận dependency thông qua Dependency Injection. |
| `dependencies.py`| Cung cấp các Dependency (Service, Repository) cho Router thông qua `Depends()` của FastAPI. | **D** - Dependency Inversion Principle. Đảm bảo lớp trên không phụ thuộc thẳng vào lớp dưới. |
| `router.py` | Nhận HTTP Request, trích xuất dữ liệu, gọi tới `Service` và trả về HTTP Response (HTML hoặc JSON). | **S** - Tầng giao tiếp (Controller). Nó dịch lỗi nghiệp vụ (DomainError) thành HTTP Status (400, 404). |
| `templates/` | Các file giao diện HTML (Jinja2) độc quyền của module này (như `list.html`, `detail.html`, `_row.html`). | |

**Luồng dữ liệu mẫu trong 1 thao tác:**
`Browser` ➡️ `Router` ➡️ `Service` ➡️ `Repository` ➡️ `Database`

## 4. Kiến trúc Hệ thống Chấm bài (`apps/judge-worker`)

Hệ thống được tách hoàn toàn khỏi Web App để đảm bảo độ ổn định và scale độc lập (chạy trên các môi trường cách ly như AWS ECS Fargate):

```text
apps/judge-worker/
├── worker/
│   ├── main.py           # Chạy vòng lặp Long-polling, liên tục lấy message từ SQS (Queue)
│   ├── judge.py          # Lõi chấm điểm: Thực hiện Luồng (Compile -> Vòng lặp Testcases -> Verdict)
│   ├── sandbox.py        # Tương tác với môi trường ảo cách ly an toàn (Isolate / Nsjail / Subprocess)
│   ├── db.py             # Kết nối trực tiếp DB gọn nhẹ để lưu kết quả Verdict
│   ├── storage.py        # Lấy file mã nguồn và bộ testcase từ S3
│   └── languages/        # Cấu hình lệnh Compile & Run riêng cho từng ngôn ngữ (C, C++, Java, Python)
└── Dockerfile            # Containerize worker thành file ảnh để scale-out
```

## 5. Đặc trưng Công nghệ và Quy trình

1. **Typing & Linting Nghiêm Ngặt:** Toàn bộ code Python sử dụng Type-hinting 100%, được kiểm tra lỗi nghiêm ngặt trước khi chạy thông qua `mypy`. Code style được định hình thống nhất bởi công cụ `ruff` tốc độ siêu nhanh.
2. **Quản lý Dependency Tiên Tiến:** Sử dụng thư viện `uv` (viết bằng Rust) làm trình cài đặt thay cho `pip`. File `uv.lock` đóng vai trò khóa chặt mọi version của thư viện, giúp mọi thành viên Dev trên mọi hệ điều hành đều chung 1 phiên bản thư viện y hệt Server.
3. **Mô hình Server-Rendered UI Hiện Đại:** Sử dụng kiến trúc UI tinh gọn (như tư tưởng của nền tảng Codeforces) nhưng tích hợp tính năng mượt mà của SPA (Single Page Application) nhờ sử dụng **HTMX** (tải từng phần tử HTML) kết hợp **Alpine.js**. Không cần Node.js, không cần webpack, build cực kỳ nhẹ nhàng.
4. **Rate Limit & Observability:** Đã được tích hợp In-memory Token-Bucket Middleware chống spam, cùng bộ công cụ Logger & Metrics sẵn sàng cho môi trường Production trên Cloud.
