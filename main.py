"""
Scribd Downloader - Main Entry Point
Supports both Graphical User Interface (GUI) and Command Line Interface (CLI).
"""

import sys
import argparse
import os

# Ensure UTF-8 output encoding for Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from scribd_downloader import ScribdDownloader, parse_scribd_url


def run_cli_interactive():
    print("=" * 60)
    print("      📄 SCRIBD DOCUMENT DOWNLOADER PRO (CLI MODE)")
    print("=" * 60)

    url = input("\n👉 Nhập đường dẫn (URL) hoặc ID tài liệu Scribd: ").strip()
    if not url:
        print("❌ URL không hợp lệ!")
        return

    try:
        meta = parse_scribd_url(url)
        print(f"✅ Đã tìm thấy tài liệu ID: {meta['doc_id']}")
        print(f"📌 Tiêu đề dự kiến: {meta['title']}")
        print(f"🔗 Link Embed: {meta['embed_url']}")
    except Exception as e:
        print(f"❌ Lỗi link: {e}")
        return

    output_dir = input("\n📁 Nhập thư mục lưu (Nhấn Enter để dùng 'downloads'): ").strip()
    if not output_dir:
        output_dir = "downloads"

    custom_name = input("📝 Nhập tên file PDF (Nhấn Enter để tự động): ").strip()
    if custom_name:
        fname = custom_name if custom_name.lower().endswith(".pdf") else f"{custom_name}.pdf"
    else:
        fname = f"{meta['title']}.pdf"

    output_path = os.path.join(output_dir, fname)

    print("\nChọn định dạng xuất file:")
    print("1. 🌟 Tự động (Giữ nguyên định dạng gốc trên Scribd: DOCX/PPTX/PDF)")
    print("2. 📄 File PDF (.pdf)")
    print("3. 📝 File Word (.docx)")
    print("4. 📊 File PowerPoint (.pptx)")
    fmt_choice = input("Lựa chọn (1/2/3/4, Mặc định 1): ").strip()
    fmt_map = {"1": "auto", "2": "pdf", "3": "docx", "4": "pptx"}
    export_format = fmt_map.get(fmt_choice, "auto")

    cookie_input = input("\n🔑 Cookie Scribd (Dán _scribd_session để tải file gốc S3, Enter để bỏ qua): ").strip()

    print("\nChọn chế độ tải:")
    print("1. ⚡ Tự động xuất file (CDP - Nhanh & Tự động lưu)")
    print("2. 🖨️ Mở cửa sổ In Chrome (Thủ công window.print)")
    choice = input("Lựa chọn (1/2, Mặc định 1): ").strip()
    
    mode = "browser_print" if choice == "2" else "direct_pdf"

    print("\n🚀 Bắt đầu quá trình tải...")

    downloader = ScribdDownloader(scroll_delay=0.5)

    def print_status(msg, prog):
        percent = int(prog * 100)
        print(f"[{percent:3d}%] {msg}")

    try:
        saved_file = downloader.download_document(
            url_or_id=url,
            output_filepath=output_path,
            export_format=export_format,
            mode=mode,
            cookie=cookie_input if cookie_input else None,
            status_callback=print_status
        )
        print(f"\n🎉 THÀNH CÔNG! Đã lưu file tại: {os.path.abspath(saved_file)}")
    except Exception as e:
        print(f"\n❌ LỖI TRONG QUÁ TRÌNH TẢI: {e}")


def main():
    parser = argparse.ArgumentParser(description="Scribd Document Downloader Pro")
    parser.add_argument("--cli", action="store_true", help="Chạy ở chế độ Command Line Interface")
    parser.add_argument("--url", type=str, help="URL hoặc ID của tài liệu Scribd cần tải")
    parser.add_argument("--output", type=str, default="downloads", help="Thư mục lưu file")
    parser.add_argument("--name", type=str, help="Tên file xuất ra")
    parser.add_argument("--format", choices=["auto", "pdf", "docx", "pptx"], default="auto", help="Định dạng xuất file")
    parser.add_argument("--cookie", type=str, default=None, help="Cookie Scribd (_scribd_session) để tải trực tiếp file gốc")
    parser.add_argument("--mode", choices=["direct_pdf", "browser_print"], default="direct_pdf", help="Chế độ xuất file")
    parser.add_argument("--headless", action="store_true", help="Chạy Chrome ở chế độ ẩn (Headless)")
    parser.add_argument("--scroll-delay", type=float, default=0.5, help="Thời gian chờ khi cuộn mỗi trang (giây)")

    args = parser.parse_args()

    # If --url parameter provided directly via CLI
    if args.url:
        meta = parse_scribd_url(args.url)
        base_name = args.name or meta['title']
        out_path = os.path.join(args.output, base_name)

        downloader = ScribdDownloader(headless=args.headless, scroll_delay=args.scroll_delay)
        print(f"Đang tải {args.url} (Định dạng: {args.format}) -> {out_path}...")
        downloader.download_document(
            url_or_id=args.url,
            output_filepath=out_path,
            export_format=args.format,
            mode=args.mode,
            cookie=args.cookie,
            status_callback=lambda msg, prog: print(f"[{int(prog*100)}%] {msg}")
        )
        return

    # If --cli flag passed or user explicitly chose CLI
    if args.cli:
        run_cli_interactive()
        return

    # Default: Launch Scribd Mini App
    try:
        from mini_app import ScribdMiniApp
        app = ScribdMiniApp()
        app.mainloop()
    except Exception as e:
        print(f"Không thể khởi chạy GUI: {e}")
        print("Chuyển sang chế độ CLI...")
        run_cli_interactive()


if __name__ == "__main__":
    main()
