"""
Scribd Downloader GUI Application
Built with CustomTkinter for a modern, sleek desktop interface.
"""

import os
import sys
import time
import threading
import subprocess
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox

from scribd_downloader import ScribdDownloader, parse_scribd_url

# Configure CustomTkinter theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class ScribdApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Scribd PDF Downloader Pro")
        self.geometry("900x720")
        self.minsize(800, 650)

        # App state
        self.is_downloading = False
        self.download_thread = None
        self.default_save_dir = os.path.join(os.path.expanduser("~"), "Downloads", "Scribd_PDFs")
        os.makedirs(self.default_save_dir, exist_ok=True)

        self._create_widgets()

    def _create_widgets(self):
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ------------------- HEADER -------------------
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame,
            text="📄 Scribd Document Downloader Pro",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Tự động cuộn trang, xóa thanh công cụ & xuất file PDF sắc nét",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))

        # ------------------- INPUT CARD -------------------
        input_card = ctk.CTkFrame(self, corner_radius=10)
        input_card.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        input_card.grid_columnconfigure(1, weight=1)

        # URL Input
        url_label = ctk.CTkLabel(input_card, text="Link / ID Scribd:", font=ctk.CTkFont(weight="bold"))
        url_label.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        self.url_textbox = ctk.CTkTextbox(input_card, height=65, font=ctk.CTkFont(size=12))
        self.url_textbox.grid(row=0, column=1, columnspan=2, padx=15, pady=(15, 5), sticky="ew")
        self.url_textbox.insert("1.0", "Dán link tài liệu Scribd vào đây (Hỗ trợ 1 link hoặc nhiều link - mỗi link 1 dòng)...")
        self.url_textbox.bind("<FocusIn>", self._clear_placeholder)

        # Save Directory
        dir_label = ctk.CTkLabel(input_card, text="Thư mục lưu:", font=ctk.CTkFont(weight="bold"))
        dir_label.grid(row=1, column=0, padx=15, pady=10, sticky="w")

        self.dir_entry = ctk.CTkEntry(input_card, font=ctk.CTkFont(size=12))
        self.dir_entry.grid(row=1, column=1, padx=(15, 5), pady=10, sticky="ew")
        self.dir_entry.insert(0, self.default_save_dir)

        browse_btn = ctk.CTkButton(
            input_card,
            text="📁 Chọn...",
            width=90,
            command=self._browse_directory
        )
        browse_btn.grid(row=1, column=2, padx=(5, 15), pady=10)

        # Custom Filename
        fn_label = ctk.CTkLabel(input_card, text="Tên file tùy chỉnh:", font=ctk.CTkFont(weight="bold"))
        fn_label.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="w")

        self.fn_entry = ctk.CTkEntry(
            input_card,
            placeholder_text="Bỏ trống để tự động lấy tên tài liệu Scribd",
            font=ctk.CTkFont(size=12)
        )
        self.fn_entry.grid(row=2, column=1, columnspan=2, padx=15, pady=(0, 15), sticky="ew")

        # ------------------- OPTIONS CARD -------------------
        options_card = ctk.CTkFrame(self, corner_radius=10)
        options_card.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        options_card.grid_columnconfigure((0, 1), weight=1)

        # Export Format
        fmt_label = ctk.CTkLabel(options_card, text="Định dạng xuất file (Giữ nguyên gốc):", font=ctk.CTkFont(weight="bold"))
        fmt_label.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        self.format_var = ctk.StringVar(value="auto")
        self.format_seg = ctk.CTkSegmentedButton(
            options_card,
            values=["🌟 Tự động (Gốc)", "📄 PDF (.pdf)", "📝 Word (.docx)", "📊 PowerPoint (.pptx)"],
            height=32,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.format_seg.set("🌟 Tự động (Gốc)")
        self.format_seg.grid(row=0, column=1, padx=15, pady=(10, 5), sticky="ew")

        # Export Mode
        mode_label = ctk.CTkLabel(options_card, text="Chế độ xuất file:", font=ctk.CTkFont(weight="bold"))
        mode_label.grid(row=1, column=0, padx=15, pady=(5, 5), sticky="w")

        self.mode_var = ctk.StringVar(value="direct_pdf")
        
        mode_rb1 = ctk.CTkRadioButton(
            options_card,
            text="⚡ Tự động xuất file (CDP direct save - Nhanh & Tự động)",
            variable=self.mode_var,
            value="direct_pdf"
        )
        mode_rb1.grid(row=2, column=0, padx=15, pady=5, sticky="w")

        mode_rb2 = ctk.CTkRadioButton(
            options_card,
            text="🖨️ Mở cửa sổ In Chrome (Thủ công window.print)",
            variable=self.mode_var,
            value="browser_print"
        )
        mode_rb2.grid(row=2, column=1, padx=15, pady=5, sticky="w")

        # Switches
        switches_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        switches_frame.grid(row=3, column=0, columnspan=2, padx=15, pady=(5, 10), sticky="ew")

        self.headless_var = ctk.BooleanVar(value=False)
        self.headless_switch = ctk.CTkSwitch(
            switches_frame,
            text="👁️ Ẩn trình duyệt Chrome (Headless mode)",
            variable=self.headless_var
        )
        self.headless_switch.pack(side="left", padx=(0, 20))

        # Scroll Delay Slider
        delay_label = ctk.CTkLabel(switches_frame, text="⏱️ Độ trễ cuộn trang:")
        delay_label.pack(side="left", padx=(10, 5))

        self.delay_slider = ctk.CTkSlider(
            switches_frame,
            from_=0.2,
            to=2.0,
            number_of_steps=18,
            width=140,
            command=self._on_slider_change
        )
        self.delay_slider.set(0.5)
        self.delay_slider.pack(side="left", padx=5)

        self.delay_val_label = ctk.CTkLabel(switches_frame, text="0.5s", font=ctk.CTkFont(weight="bold"))
        self.delay_val_label.pack(side="left", padx=5)

        # ------------------- PROGRESS & CONSOLE -------------------
        progress_card = ctk.CTkFrame(self, corner_radius=10)
        progress_card.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        progress_card.grid_columnconfigure(0, weight=1)
        progress_card.grid_rowconfigure(2, weight=1)

        # Status Label
        self.status_label = ctk.CTkLabel(
            progress_card,
            text="Sẵn sàng thực hiện",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")

        # Progress Bar
        self.progressbar = ctk.CTkProgressBar(progress_card)
        self.progressbar.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        self.progressbar.set(0.0)

        # Console Output
        self.console_textbox = ctk.CTkTextbox(
            progress_card,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#1E1E1E",
            text_color="#D4D4D4"
        )
        self.console_textbox.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.log("Chào mừng! Dán link Scribd và nhấn 'Bắt đầu tải' để bắt đầu.")

        # ------------------- BUTTON BAR -------------------
        button_bar = ctk.CTkFrame(self, fg_color="transparent")
        button_bar.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")

        self.start_btn = ctk.CTkButton(
            button_bar,
            text="🚀 BẮT ĐẦU TẢI",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2B8A3E",
            hover_color="#217031",
            height=40,
            command=self.start_download
        )
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.open_dir_btn = ctk.CTkButton(
            button_bar,
            text="📁 Mở thư mục tải",
            height=40,
            fg_color="#3B5EDB",
            hover_color="#2B44AD",
            command=self._open_output_dir
        )
        self.open_dir_btn.pack(side="left", padx=5)

    def _clear_placeholder(self, event):
        content = self.url_textbox.get("1.0", "end-1c")
        if "Dán link tài liệu Scribd vào đây" in content:
            self.url_textbox.delete("1.0", "end")

    def _browse_directory(self):
        selected = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if selected:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, selected)

    def _on_slider_change(self, value):
        self.delay_val_label.configure(text=f"{value:.1f}s")

    def log(self, message: str):
        timestamp = time.strftime("[%H:%M:%S] ")
        self.console_textbox.insert("end", timestamp + message + "\n")
        self.console_textbox.see("end")

    def update_status(self, text: str, progress: float):
        self.status_label.configure(text=text)
        self.progressbar.set(progress)
        self.log(text)

    def _open_output_dir(self):
        target_dir = self.dir_entry.get().strip()
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        
        if sys.platform == "win32":
            os.startfile(target_dir)
        elif sys.platform == "darwin":
            subprocess.run(["open", target_dir])
        else:
            subprocess.run(["xdg-open", target_dir])

    def start_download(self):
        if self.is_downloading:
            messagebox.showwarning("Thông báo", "Quá trình tải đang diễn ra!")
            return

        raw_input = self.url_textbox.get("1.0", "end-1c").strip()
        if not raw_input or "Dán link tài liệu Scribd vào đây" in raw_input:
            messagebox.showerror("Lỗi", "Vui lòng nhập ít nhất một đường dẫn (URL) tài liệu Scribd!")
            return

        # Parse URLs from input (supports line breaks)
        urls = [line.strip() for line in raw_input.splitlines() if line.strip()]
        
        save_dir = self.dir_entry.get().strip()
        if not save_dir:
            save_dir = self.default_save_dir
            self.dir_entry.insert(0, save_dir)

        custom_filename = self.fn_entry.get().strip()
        mode = self.mode_var.get()
        headless = self.headless_var.get()
        scroll_delay = float(self.delay_slider.get())

        fmt_map = {
            "🌟 Tự động (Gốc)": "auto",
            "📄 PDF (.pdf)": "pdf",
            "📝 Word (.docx)": "docx",
            "📊 PowerPoint (.pptx)": "pptx"
        }
        chosen_fmt = self.format_seg.get()
        export_format = fmt_map.get(chosen_fmt, "auto")

        self.is_downloading = True
        self.start_btn.configure(state="disabled", fg_color="gray")

        # Launch background thread
        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(urls, save_dir, custom_filename, export_format, mode, headless, scroll_delay),
            daemon=True
        )
        self.download_thread.start()

    def _download_worker(self, urls, save_dir, custom_filename, export_format, mode, headless, scroll_delay):
        downloader = ScribdDownloader(
            headless=headless,
            scroll_delay=scroll_delay
        )

        total_urls = len(urls)
        self.log(f"--- Bắt đầu danh sách tải ({total_urls} tài liệu) ---")

        for idx, url in enumerate(urls, start=1):
            try:
                self.log(f"\n[Tài liệu {idx}/{total_urls}] Đang xử lý: {url}")
                
                doc_meta = parse_scribd_url(url)
                
                # Determine file path base
                if custom_filename and total_urls == 1:
                    base_name = os.path.splitext(custom_filename)[0]
                else:
                    base_name = doc_meta['title']

                filepath = os.path.join(save_dir, base_name)

                def callback(status_msg, prog):
                    # Global progress ratio across all items
                    overall_prog = (idx - 1) / total_urls + (prog / total_urls)
                    self.after(0, self.update_status, f"[{idx}/{total_urls}] {status_msg}", overall_prog)

                saved_path = downloader.download_document(
                    url_or_id=url,
                    output_filepath=filepath,
                    export_format=export_format,
                    mode=mode,
                    status_callback=callback
                )
                self.log(f"✅ Đã lưu file: {os.path.basename(saved_path)}")

            except Exception as e:
                err_msg = f"❌ Lỗi khi tải tài liệu {url}: {str(e)}"
                self.after(0, self.log, err_msg)
                self.after(0, self.status_label.configure, err_msg)

        self.after(0, self._on_download_complete)

    def _on_download_complete(self):
        self.is_downloading = False
        self.start_btn.configure(state="normal", fg_color="#2B8A3E")
        self.progressbar.set(1.0)
        self.status_label.configure(text="🎉 Đã hoàn tất tất cả tác vụ!")
        self.log("\n==========================================")
        self.log("✅ TẢI THÀNH CÔNG! Đã lưu các tập tin vào thư mục tải về.")
        self.log("==========================================")
        
        messagebox.showinfo("Thành công", "Đã tải xong các tài liệu Scribd!")


if __name__ == "__main__":
    app = ScribdApp()
    app.mainloop()
