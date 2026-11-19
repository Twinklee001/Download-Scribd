# 📄 Scribd Document Downloader Pro

Công cụ tải tài liệu Scribd sang định dạng **PDF (`.pdf`)** chất lượng cao, tự động hóa bằng Python & Selenium WebDriver.

---

## ✨ Tính năng nổi bật

1. **Hỗ trợ tải trực tiếp file PDF từ máy chủ Scribd (Amazon S3) hoặc nạp Vector**:
   - 🔑 **Tùy chọn Cookie**: Chỉ cần dán cookie `_scribd_session` từ trình duyệt, ứng dụng sẽ gửi yêu cầu trực tiếp đến máy chủ Scribd để tải file PDF gốc (nếu tài khoản có quyền tải).
   - 🔄 **Cơ chế Fallback thông minh**: Nếu không có cookie hoặc tài khoản không có quyền tải trực tiếp, ứng dụng tự động chuyển sang chế độ nạp toàn bộ vector của từng trang và xuất ra **PDF** không để sót trang nào.
   - 💾 **Tự động lưu cấu hình**: Ứng dụng tự động ghi nhớ Cookie đã nhập để bạn không cần dán lại nhiều lần.

2. **Giữ nguyên bố cục & chất lượng nội dung trong file PDF**:
   - **Giữ nguyên kích thước & tỷ lệ trang in**: Tự động lấy kích thước thực (`origWidth`, `origHeight`) và hướng trang (`portrait`/`landscape`) để tạo trang PDF chuẩn, không bị méo, cắt lề hay dư trang trắng cuối file.
   - **Bảo toàn 100% nội dung vector & font chữ**: Nạp song song toàn bộ các trang qua engine `DocumentManager` của Scribd, văn bản sắc nét, có thể bôi đen, tìm kiếm và sao chép.

3. **Giao diện người dùng hiện đại (Mini App & Pro GUI)**:
   - Giao diện Dark Mode xây dựng bằng `CustomTkinter`.
   - **Tự động nhận diện metadata khi dán link**: Hiển thị thông tin tài liệu gốc, số trang và tự điền link từ clipboard.
   - **Định dạng lưu về máy cố định**: `📄 PDF (.pdf)` — xuất file PDF vector sắc nét trên cả Mini App, Pro GUI và CLI.
   - **Nút "❓ Cách lấy"**: Bấm để xem hướng dẫn lấy cookie `_scribd_session` nhanh trong vài giây.

---

## 🚀 Hướng dẫn sử dụng

### Cách 1: Chạy bằng giao diện GUI Mini (Khuyên dùng)
- **Cách đơn giản nhất**: Double-click vào file **`run.bat`**.
- Hoặc chạy lệnh trong terminal:
  ```bash
  python mini_app.py
  ```

### Cách 2: Chạy giao diện Pro (Nhiều tùy chọn & tải hàng loạt)
  ```bash
  python gui.py
  ```

### Cách 3: Tải nhanh bằng dòng lệnh CLI
- **Tải tài liệu thành file PDF**:
  ```bash
  python main.py --url "https://www.scribd.com/document/561026256/Sample" --format pdf
  ```
- **Hoặc chạy chế độ CLI tương tác**:
  ```bash
  python main.py --cli
  ```

---

## 📁 Cấu trúc thư mục dự án

```text
Download-Scribd/
├── scribd_downloader.py   # Module lõi (Nạp trang song song, CDP printToPDF, xử lý Cookie)
├── mini_app.py            # Giao diện Mini gọn nhẹ (Xuất PDF)
├── gui.py                 # Giao diện Desktop Pro hỗ trợ nhiều link & tùy chỉnh tham số
├── main.py                # Điểm khởi chạy chính (GUI & CLI)
├── run.bat                # Phím tắt chạy nhanh trên Windows (1-click)
├── .gitignore             # Bỏ qua __pycache__, downloads/ và file tạm
└── README.md              # Hướng dẫn chi tiết
```

---

## 🛠️ Yêu cầu môi trường & Thư viện

- Python 3.8+
- Google Chrome Browser
- Các thư viện Python cần thiết:
  - `selenium`
  - `customtkinter`
  - `pypdf`
  - `PyMuPDF` (`fitz`)
