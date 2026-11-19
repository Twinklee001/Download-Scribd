# 📄 Scribd Document Downloader Pro

Công cụ tải tài liệu Scribd sang định dạng **PDF, Word (.docx), PowerPoint (.pptx)** chất lượng cao, tự động hóa bằng Python & Selenium WebDriver.

---

## ✨ Tính năng nổi bật

1. **Hỗ trợ tải trực tiếp File gốc nguyên bản từ máy chủ Scribd (Amazon S3)**:
   - 🔑 **Tùy chọn Cookie**: Chỉ cần dán cookie `_scribd_session` từ trình duyệt, ứng dụng sẽ gửi yêu cầu trực tiếp đến máy chủ Scribd và kéo **chính xác 100% file gốc (.docx, .pptx, .pdf)** do người đăng tải lên.
   - 🔄 **Cơ chế Fallback thông minh**: Nếu không có cookie hoặc tài khoản không có quyền tải file gốc, ứng dụng tự động chuyển sang chế độ nạp toàn bộ vector và bóc tách dữ liệu 100% không để sót trang nào.
   - 💾 **Tự động lưu cấu hình**: Ứng dụng tự động ghi nhớ Cookie đã nhập để bạn không cần dán lại nhiều lần.

2. **Giữ nguyên định dạng gốc của file trên Scribd**:
   - 🌟 **Tự động nhận diện định dạng gốc**: Tự động phát hiện tài liệu tải lên Scribd vốn là **Microsoft Word (`.docx`)**, **PowerPoint (`.pptx`)** hay **Adobe PDF (`.pdf`)** để xuất ra đúng tệp tương ứng.
   - **Giữ nguyên bố cục & tỷ lệ trang in**: Tự động lấy kích thước thực (`origWidth`, `origHeight`) và hướng trang (`portrait`/`landscape`) để tạo file chuẩn A4, Letter hoặc Slide 16:9, không bị méo mó, cắt lề hay sinh viền trắng thừa.
   - **Bảo toàn 100% nội dung vector & font chữ**: Nạp song song toàn bộ các trang qua engine `DocumentManager` của Scribd, văn bản sắc nét, có thể tìm kiếm và sao chép.

3. **Giao diện người dùng hiện đại (GUI & Mini App)**:
   - Giao diện Dark Mode đẹp mắt xây dựng bằng `CustomTkinter`.
   - **Tự động nhận diện metadata khi dán link**: Hiển thị ngay định dạng gốc, số trang và tiêu đề chuẩn tiếng Việt.
   - **Tùy chọn định dạng tải về**:
     - `🌟 Tự động (Gốc)`: Tự chọn đuôi file phù hợp với tài liệu gốc trên Scribd.
     - `📄 PDF (.pdf)`: Xuất file PDF vector chất lượng cao.
     - `📝 Word (.docx)`: Chuyển đổi sang file Word có thể chỉnh sửa bảng biểu, chữ viết.
     - `📊 PowerPoint (.pptx)`: Chuyển đổi slide bài giảng sang file trình chiếu.
   - **Nút "❓ Cách lấy"**: Bấm để xem hướng dẫn trực quan cách lấy cookie `_scribd_session` trong 10 giây.

---

## 🚀 Hướng dẫn sử dụng

### Cách 1: Chạy bằng giao diện GUI Mini (Khuyên dùng)
- **Cách đơn giản nhất**: Double-click vào file **`run.bat`**.
- HOẶC chạy lệnh trong terminal:
  ```bash
  python mini_app.py
  ```

### Cách 2: Chạy giao diện Pro (Nhiều tùy chọn & Batch Mode)
  ```bash
  python gui.py
  ```

### Cách 3: Tải nhanh bằng dòng lệnh CLI
- **Tải tự động giữ nguyên định dạng gốc**:
  ```bash
  python main.py --url "https://www.scribd.com/document/561026256/Sample" --format auto
  ```
- **Tải chỉ định dạng Word (.docx) hoặc PDF**:
  ```bash
  python main.py --url "https://www.scribd.com/document/561026256/Sample" --format docx
  ```

---

## 📁 Cấu trúc thư mục dự án

```
Auto down Scribd/
├── scribd_downloader.py   # Module lõi (Xử lý tải song song, giữ định dạng, CDP, DOCX, PPTX)
├── mini_app.py            # Giao diện Mini gọn nhẹ, tự động phát hiện định dạng gốc
├── gui.py                 # Giao diện Desktop Pro đầy đủ tính năng
├── main.py                # Điểm khởi chạy chính (GUI & CLI)
├── run.bat                # Phím tắt chạy nhanh trên Windows (1-click)
└── README.md              # Hướng dẫn chi tiết
```

---

## 🛠️ Yêu cầu môi trường & Thư viện

- Python 3.8+
- Google Chrome Browser
- Đã cài đặt các thư viện cần thiết:
  - `selenium`
  - `customtkinter`
  - `pypdf`
  - `pdf2docx`
  - `python-docx`
  - `python-pptx`
  - `PyMuPDF (fitz)`
