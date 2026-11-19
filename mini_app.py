"""
Scribd Downloader - Mini App (Format-Preserving Edition)
Tự động nhận diện và giữ nguyên định dạng gốc trên Scribd (DOCX, PPTX, PDF).
"""

import os
import sys
import json
import threading
import subprocess
import customtkinter as ctk
from tkinter import filedialog, messagebox

from scribd_downloader import ScribdDownloader, parse_scribd_url, get_scribd_metadata

# Configure CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".scribd_downloader_config.json")


def load_saved_cookie() -> str:
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("cookie", "")
    except Exception:
        pass
    return ""


def save_saved_cookie(cookie: str):
    try:
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["cookie"] = cookie.strip()
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class ScribdFastMiniApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Scribd PDF Downloader")
        self.geometry("580x570")
        self.resizable(False, False)

        # Default Save Directory
        self.default_dir = os.path.join(os.path.expanduser("~"), "Downloads", "Scribd_Files")
        os.makedirs(self.default_dir, exist_ok=True)

        self.is_downloading = False
        self._build_ui()
        self._auto_paste_clipboard()

    def _build_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=25, pady=20)

        # Header Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="⚡ Scribd Downloader Pro",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(anchor="w", pady=(0, 2))

        sub_label = ctk.CTkLabel(
            main_frame,
            text="Tự động trích xuất và lưu tài liệu Scribd sang định dạng PDF sắc nét",
            font=ctk.CTkFont(size=12),
            text_color="#A0AEC0"
        )
        sub_label.pack(anchor="w", pady=(0, 15))

        # 1. LINK INPUT
        link_header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        link_header_frame.pack(fill="x", pady=(0, 4))
        
        link_label = ctk.CTkLabel(link_header_frame, text="1. Link / ID Scribd:", font=ctk.CTkFont(size=13, weight="bold"))
        link_label.pack(side="left")

        self.detected_format_label = ctk.CTkLabel(
            link_header_frame,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38A169"
        )
        self.detected_format_label.pack(side="right")

        self.link_entry = ctk.CTkEntry(
            main_frame,
            placeholder_text="Dán đường dẫn Scribd vào đây...",
            height=38,
            font=ctk.CTkFont(size=13)
        )
        self.link_entry.pack(fill="x", pady=(0, 10))
        self.link_entry.bind("<KeyRelease>", self._on_url_change)

        # 2. FORMAT SELECTOR
        fmt_label = ctk.CTkLabel(main_frame, text="2. Định dạng lưu về máy:", font=ctk.CTkFont(size=13, weight="bold"))
        fmt_label.pack(anchor="w", pady=(0, 4))

        self.format_var = ctk.StringVar(value="pdf")
        
        self.format_seg = ctk.CTkSegmentedButton(
            main_frame,
            values=["📄 PDF (.pdf)"],
            command=self._on_format_change,
            height=36,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.format_seg.set("📄 PDF (.pdf)")
        self.format_seg.pack(fill="x", pady=(0, 12))

        # 3. SAVE DIRECTORY
        dir_label = ctk.CTkLabel(main_frame, text="3. Thư mục lưu file:", font=ctk.CTkFont(size=13, weight="bold"))
        dir_label.pack(anchor="w", pady=(0, 4))

        dir_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        dir_frame.pack(fill="x", pady=(0, 10))

        self.dir_entry = ctk.CTkEntry(
            dir_frame,
            height=36,
            font=ctk.CTkFont(size=12)
        )
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.dir_entry.insert(0, self.default_dir)

        browse_btn = ctk.CTkButton(
            dir_frame,
            text="📁 Chọn...",
            width=85,
            height=36,
            command=self._browse_dir
        )
        browse_btn.pack(side="right")

        # 4. COOKIE SCRIBD (OPTIONAL FOR RAW ORIGINAL FILE)
        cookie_header = ctk.CTkFrame(main_frame, fg_color="transparent")
        cookie_header.pack(fill="x", pady=(0, 4))

        cookie_label = ctk.CTkLabel(
            cookie_header,
            text="4. Cookie Scribd (Tùy chọn - Dùng để lấy File gốc từ S3):",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        cookie_label.pack(side="left")

        help_btn = ctk.CTkButton(
            cookie_header,
            text="❓ Cách lấy",
            width=70,
            height=22,
            font=ctk.CTkFont(size=11),
            fg_color="#4A5568",
            hover_color="#2D3748",
            command=self._show_cookie_help
        )
        help_btn.pack(side="right")

        self.cookie_entry = ctk.CTkEntry(
            main_frame,
            placeholder_text="Dán cookie _scribd_session để lấy file gốc (để trống nếu không có)...",
            height=36,
            font=ctk.CTkFont(size=12)
        )
        self.cookie_entry.pack(fill="x", pady=(0, 15))
        saved_cookie = load_saved_cookie()
        if saved_cookie:
            self.cookie_entry.insert(0, saved_cookie)

        # DOWNLOAD BUTTON
        self.download_btn = ctk.CTkButton(
            main_frame,
            text="⚡ TẢI VỀ MÁY",
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#2B8A3E",
            hover_color="#217031",
            command=self.start_download
        )
        self.download_btn.pack(fill="x", pady=(0, 10))

        # PROGRESS & STATUS
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Sẵn sàng thực hiện",
            font=ctk.CTkFont(size=12),
            text_color="#A0AEC0",
            anchor="w"
        )
        self.status_label.pack(fill="x", pady=(0, 4))

        self.progressbar = ctk.CTkProgressBar(main_frame, height=6)
        self.progressbar.pack(fill="x")
        self.progressbar.set(0)

    def _show_cookie_help(self):
        msg = (
            "📌 CÁCH LẤY COOKIE ĐỂ TẢI TRỰC TIẾP FILE GỐC:\n\n"
            "1. Mở trình duyệt (Chrome/Edge/Cốc Cốc), vào trang scribd.com và đăng nhập tài khoản.\n"
            "2. Bấm phím F12 trên bàn phím để mở Developer Tools.\n"
            "3. Chọn tab 'Application' (hoặc 'Storage') -> mục 'Cookies' -> chọn 'https://www.scribd.com'.\n"
            "4. Tìm dòng tên '_scribd_session', nhấp đúp vào ô 'Value' và Copy toàn bộ chuỗi ký tự.\n"
            "5. Dán vào ô Cookie trên ứng dụng này.\n\n"
            "💡 Nếu bạn không có Cookie, cứ để trống ô này: Ứng dụng sẽ tự động tải 100% nội dung vector & chuyển đổi định dạng chuẩn!"
        )
        messagebox.showinfo("Hướng dẫn lấy Cookie Scribd", msg)

    def _on_format_change(self, val):
        pass

    def _on_url_change(self, event=None):
        url = self.link_entry.get().strip()
        if len(url) > 15 and ("scribd.com" in url or url.isdigit()):
            threading.Thread(target=self._fetch_metadata_preview, args=(url,), daemon=True).start()

    def _fetch_metadata_preview(self, url):
        try:
            meta = get_scribd_metadata(url)
            orig = meta.get("original_extension", "pdf").upper()
            pages = meta.get("page_count")
            page_text = f" - {pages} trang" if pages else ""
            self.after(0, self.detected_format_label.configure, {
                "text": f"Gốc trên Scribd: {orig}{page_text}",
                "text_color": "#38A169"
            })
        except Exception:
            pass

    def _auto_paste_clipboard(self):
        try:
            clip = self.clipboard_get().strip()
            if "scribd.com" in clip or clip.isdigit():
                self.link_entry.insert(0, clip)
                self._on_url_change()
        except Exception:
            pass

    def _browse_dir(self):
        folder = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if folder:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, folder)

    def start_download(self):
        if self.is_downloading:
            return

        url = self.link_entry.get().strip()
        if not url:
            messagebox.showerror("Chưa nhập link", "Vui lòng nhập đường dẫn hoặc ID Scribd!")
            return

        save_dir = self.dir_entry.get().strip() or self.default_dir
        cookie = self.cookie_entry.get().strip()
        if cookie:
            save_saved_cookie(cookie)

        # Only PDF output is supported
        export_format = "pdf"

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⚡ ĐANG TẢI & XỬ LÝ ĐỊNH DẠNG...", fg_color="#4A5568")
        self.progressbar.set(0.1)
        self.status_label.configure(text="Đang kết nối...", text_color="#3182CE")

        # Launch background worker
        threading.Thread(
            target=self._worker,
            args=(url, save_dir, export_format, cookie),
            daemon=True
        ).start()

    def _worker(self, url, save_dir, export_format, cookie):
        try:
            doc_meta = parse_scribd_url(url)
            filepath = os.path.join(save_dir, f"{doc_meta['title']}")

            downloader = ScribdDownloader(headless=True)

            def status_cb(msg, prog):
                self.after(0, self._update_ui, msg, prog)

            saved_path = downloader.download_document(
                url_or_id=url,
                output_filepath=filepath,
                export_format=export_format,
                mode="direct_pdf",
                cookie=cookie if cookie else None,
                status_callback=status_cb
            )

            self.after(0, self._on_success, saved_path)

        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _update_ui(self, status_msg, progress):
        self.status_label.configure(text=status_msg, text_color="#E2E8F0")
        self.progressbar.set(progress)

    def _on_success(self, saved_path):
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⚡ TẢI VỀ MÁY", fg_color="#2B8A3E")
        self.progressbar.set(1.0)
        ext = os.path.splitext(saved_path)[1].upper()
        self.status_label.configure(text=f"✅ Đã tải xong: {os.path.basename(saved_path)} ({ext})", text_color="#38A169")

        # Open folder
        folder = os.path.dirname(saved_path)
        if sys.platform == "win32":
            os.startfile(folder)
            
        messagebox.showinfo("Thành công", f"🎉 Đã tải xong file PDF!\n\nĐịnh dạng: {ext}\nLưu tại: {saved_path}")

    def _on_error(self, err_msg):
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⚡ TẢI VỀ MÁY", fg_color="#2B8A3E")
        self.progressbar.set(0)
        self.status_label.configure(text="❌ Lỗi khi tải", text_color="#E53E3E")
        messagebox.showerror("Lỗi", f"Không thể tải tài liệu:\n{err_msg}")


ScribdMiniApp = ScribdFastMiniApp

if __name__ == "__main__":
    app = ScribdFastMiniApp()
    app.mainloop()
