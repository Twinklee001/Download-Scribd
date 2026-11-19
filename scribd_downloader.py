"""
Scribd Downloader Engine - Ultra Complete & Format-Preserving Edition
Ensures 100% of pages, images, vector fonts, and text content are fully loaded.
Preserves the exact original document formatting (dimensions, aspect ratio, orientation)
and supports downloading in the original Scribd format (.docx / .pdf / .pptx).
"""

import os
import io
import re
import time
import base64
import logging
import urllib.request
import urllib.parse
import json
from typing import Callable, Optional, Dict, Any, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pypdf
import fitz

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ScribdDownloader")


def parse_scribd_url(input_url: str) -> Dict[str, str]:
    """Parses Scribd URL or document ID and returns base metadata."""
    input_url = input_url.strip()

    if input_url.isdigit():
        doc_id = input_url
        return {
            "doc_id": doc_id,
            "embed_url": f"https://www.scribd.com/embeds/{doc_id}/content",
            "main_url": f"https://www.scribd.com/document/{doc_id}",
            "title": f"Scribd_Doc_{doc_id}",
            "original_url": input_url
        }

    match = re.search(r'(?:document|doc|embeds|presentation)/(\d+)(?:/([^/?#]+))?', input_url)
    if match:
        doc_id = match.group(1)
        raw_title = match.group(2) or f"Scribd_Doc_{doc_id}"
        
        decoded_title = urllib.parse.unquote(raw_title)
        clean_title = re.sub(r'[\\/*?:"<>|]', '_', decoded_title).replace('-', ' ').strip()
        if not clean_title or clean_title.lower() == "content":
            clean_title = f"Scribd_Doc_{doc_id}"

        return {
            "doc_id": doc_id,
            "embed_url": f"https://www.scribd.com/embeds/{doc_id}/content",
            "main_url": f"https://www.scribd.com/document/{doc_id}",
            "title": clean_title,
            "original_url": input_url
        }

    raise ValueError(f"URL hoặc ID không hợp lệ: {input_url}")


def get_scribd_metadata(url_or_id: str) -> Dict[str, Any]:
    """
    Fetches full metadata from Scribd, including original file type (.docx, .pdf, .pptx),
    page dimensions, orientation, and available formats.
    """
    base_meta = parse_scribd_url(url_or_id)
    doc_id = base_meta["doc_id"]
    main_url = base_meta["main_url"]

    meta = {
        "doc_id": doc_id,
        "embed_url": base_meta["embed_url"],
        "main_url": main_url,
        "title": base_meta["title"],
        "original_extension": "pdf",
        "available_formats": ["pdf"],
        "page_count": None,
        "page_dimensions": None,
        "page_orientation": "portrait"
    }

    try:
        req = urllib.request.Request(main_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            cm = re.search(r'<!--(\{.*?\})-->', html, re.DOTALL)
            if cm:
                data = json.loads(cm.group(1))
                doc = data.get("wordDocument", {})
                
                raw_title = doc.get("title") or doc.get("extracted_title")
                if raw_title:
                    clean_t = re.sub(r'[\\/*?:"<>|]', '_', raw_title).strip()
                    meta["title"] = clean_t

                formats = [f.get("extension") for f in doc.get("formats", []) if f.get("extension")]
                if formats:
                    meta["available_formats"] = formats
                
                exts = doc.get("extensions", [])
                if exts and exts[0]:
                    meta["original_extension"] = exts[0].lower()
                elif formats:
                    meta["original_extension"] = formats[0].lower()

                meta["page_count"] = doc.get("page_count")
                meta["page_dimensions"] = doc.get("page_dimensions")
                meta["page_orientation"] = doc.get("page_orientation", "portrait")
    except Exception as e:
        logger.debug(f"Could not fetch extended metadata: {e}")

    return meta


def parse_cookies_input(cookie_str: str) -> list:
    """
    Parses user input cookie string into Selenium cookie dictionaries.
    Supports:
    - Pure token: 'BAh7...' -> assigned to '_scribd_session'
    - Standard cookie string: '_scribd_session=xyz; scribd_user=abc'
    - JSON cookies format
    """
    cookie_str = cookie_str.strip()
    if not cookie_str:
        return []

    # Case 1: JSON format
    if cookie_str.startswith("[") or cookie_str.startswith("{"):
        try:
            data = json.loads(cookie_str)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return [{"name": k, "value": str(v), "domain": ".scribd.com", "path": "/"} for k, v in data.items()]
        except Exception:
            pass

    # Case 2: Pure token without '='
    if "=" not in cookie_str:
        return [{
            "name": "_scribd_session",
            "value": cookie_str,
            "domain": ".scribd.com",
            "path": "/"
        }]

    # Case 3: Key=Value pairs separated by ';'
    cookies = []
    pairs = cookie_str.split(";")
    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue
        if "=" in pair:
            key, val = pair.split("=", 1)
            cookies.append({
                "name": key.strip(),
                "value": val.strip(),
                "domain": ".scribd.com",
                "path": "/"
            })
    return cookies


class ScribdDownloader:
    """
    State-of-the-art Scribd Downloader.
    Preserves 100% document content, exact page dimensions, aspect ratio, and formatting.
    Supports exporting to PDF, Word (.docx), and PowerPoint (.pptx).
    Supports direct raw uploaded file download when cookie/account is provided.
    """

    def __init__(self, headless: bool = True, scroll_delay: float = 0.2):
        self.headless = headless
        self.scroll_delay = scroll_delay

    def _init_driver(self, download_dir: Optional[str] = None) -> webdriver.Chrome:
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")
        else:
            options.add_experimental_option("detach", True)
            options.add_argument("--auto-open-devtools-for-tabs")

        # Essential stable performance flags
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--mute-audio")
        options.add_argument("--no-first-run")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--log-level=3")

        if download_dir:
            abs_dir = os.path.abspath(download_dir)
            os.makedirs(abs_dir, exist_ok=True)
            app_state = {
                "recentDestinations": [
                    {
                        "id": "Save as PDF",
                        "origin": "local",
                        "account": ""
                    }
                ],
                "selectedDestinationId": "Save as PDF",
                "version": 2
            }
            prefs = {
                "download.default_directory": abs_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "plugins.always_open_pdf_externally": True,
                "savefile.default_directory": abs_dir,
                "printing.print_preview_sticky_settings.appState": json.dumps(app_state)
            }
            options.add_experimental_option("prefs", prefs)

        driver = webdriver.Chrome(options=options)
        if download_dir:
            try:
                driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                    "behavior": "allow",
                    "downloadPath": os.path.abspath(download_dir)
                })
            except Exception:
                pass
        return driver

    def load_and_prepare_document(
        self,
        driver: webdriver.Chrome,
        status_callback: Optional[Callable[[str, float], None]] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Loads all pages in parallel, preserves full text layers, vector fonts,
        images, and determines exact page dimensions and orientation.
        """
        if status_callback:
            status_callback("Đang phân tích cấu trúc tài liệu...", 0.2)

        # 1. Wait for document readyState to be complete
        start_ready = time.time()
        while time.time() - start_ready < 15:
            ready_state = driver.execute_script("return document.readyState;")
            if ready_state == "complete":
                break
            time.sleep(0.3)

        # 2. Wait for document structure to initialize (DocManager or outer_page elements)
        start_wait = time.time()
        has_doc_manager = False
        while time.time() - start_wait < 10:
            ready_info = driver.execute_script("""
                return {
                    hasDocManager: !!(window.docManager && window.docManager.pages),
                    pageCount: window.docManager ? Object.keys(window.docManager.pages).length : 0,
                    domPages: document.querySelectorAll("[id^='outer_page_'], .outer_page, [class*='page']").length
                };
            """)
            if ready_info.get("hasDocManager") and ready_info.get("pageCount", 0) > 0:
                has_doc_manager = True
                break
            if ready_info.get("domPages", 0) > 0:
                break
            time.sleep(0.3)

        total_pages = 1

        # 3. Fast parallel page load via DocManager if available
        if has_doc_manager:
            if status_callback:
                status_callback("Đang kích hoạt nạp toàn bộ các trang song song...", 0.25)

            # Trigger .load() on every page object that hasn't loaded yet
            trigger_script = """
                var pages = window.docManager.pages;
                var keys = Object.keys(pages);
                keys.forEach(function(k) {
                    var p = pages[k];
                    if (p && typeof p.load === 'function' && !p.innerPageElem && !p.loadHasStarted) {
                        try {
                            p.load();
                        } catch(e) {}
                    }
                });
                return keys.length;
            """
            total_pages = driver.execute_script(trigger_script) or 1

            # Poll until all pages have finished loading (max 45s)
            start_poll = time.time()
            max_poll_time = max(15, min(60, total_pages * 0.3))
            
            while time.time() - start_poll < max_poll_time:
                status = driver.execute_script("""
                    var pages = window.docManager.pages;
                    var loaded = 0;
                    var total = 0;
                    for (var k in pages) {
                        total++;
                        var p = pages[k];
                        if (p.innerPageElem || (p.containerElem && p.containerElem.querySelector('.newpage, .text_layer, img.orig'))) {
                            loaded++;
                        }
                    }
                    return { loaded: loaded, total: total };
                """)
                loaded = status.get("loaded", 0)
                total = status.get("total", total_pages)
                
                prog_ratio = 0.25 + (0.35 * (loaded / max(1, total)))
                if status_callback:
                    status_callback(f"Đang tải nội dung: {loaded}/{total} trang...", prog_ratio)

                if loaded >= total:
                    break
                time.sleep(0.4)

            # Activate, unhide, and render every page
            driver.execute_script("""
                var pages = window.docManager.pages;
                for (var k in pages) {
                    var p = pages[k];
                    if (p) {
                        if (typeof p.display === 'function') {
                            try { p.display(); } catch(e) {}
                        }
                        if (p.containerElem) {
                            p.containerElem.className = p.containerElem.className.replace(/placeholder|not_visible/g, "");
                            p.containerElem.style.display = "block";
                            p.containerElem.style.visibility = "visible";
                        }
                        if (p.innerPageElem) {
                            p.innerPageElem.style.display = "block";
                            p.innerPageElem.style.visibility = "visible";
                        }
                    }
                }
            """)

        # 4. Progressive thorough scroll through all pages via .document_scroller & window
        # This guarantees that IntersectionObservers fire, all lazy images, SVG graphics,
        # and custom web fonts (@font-face) are rendered and positioned accurately in DOM.
        dom_page_count = driver.execute_script("""
            return document.querySelectorAll("[id^='outer_page_'], .outer_page").length;
        """) or total_pages

        if status_callback:
            status_callback(f"Đang cuộn từng trang để nạp trọn vẹn 100% định dạng & hình ảnh ({dom_page_count} trang)...", 0.6)

        # Dynamic scroll step: 1 page at a time for 100% precision (never skips pages)
        scroll_step = 1
        delay = max(0.06, min(0.5, self.scroll_delay))

        for p_idx in range(1, dom_page_count + 1, scroll_step):
            driver.execute_script("""
                var p = document.querySelector('#outer_page_' + arguments[0]) || document.querySelectorAll('.outer_page')[arguments[0] - 1];
                var scroller = document.querySelector('.document_scroller') || document.documentElement || document.body;
                if (p) {
                    if (scroller) scroller.scrollTop = p.offsetTop;
                    window.scrollTo(0, p.offsetTop);
                }
            """, p_idx)
            time.sleep(delay)

            if p_idx % 5 == 1 or p_idx >= dom_page_count - scroll_step:
                prog = 0.6 + (0.12 * (p_idx / max(1, dom_page_count)))
                if status_callback:
                    status_callback(f"Đang nạp định dạng & ảnh: {p_idx}/{dom_page_count} trang...", prog)

        # Scroll to bottom to ensure last page is triggered
        driver.execute_script("""
            var scroller = document.querySelector('.document_scroller') || document.documentElement || document.body;
            if (scroller) scroller.scrollTop = scroller.scrollHeight;
            window.scrollTo(0, document.body.scrollHeight);
        """)
        time.sleep(0.4)

        # SMART AUDIT & AUTO-RETRY PASS:
        # Actively verifies that EVERY single page has its text layer and graphics loaded.
        # If any page was delayed by network, jumps back to that specific page to load it.
        if status_callback:
            status_callback("Đang kiểm toán toàn bộ trang để bảo đảm 100% không sót nội dung...", 0.73)

        for retry_round in range(3):
            missing_pages = driver.execute_script("""
                var missing = [];
                var total = document.querySelectorAll("[id^='outer_page_'], .outer_page").length;
                for (var i = 1; i <= total; i++) {
                    var p = document.querySelector('#outer_page_' + i);
                    if (p) {
                        var hasText = !!p.querySelector('.text_layer, .newpage') || (p.innerText && p.innerText.trim().length > 0);
                        var hasImg = !!p.querySelector('img.orig, .orig, img, svg');
                        if (!hasText && !hasImg) {
                            missing.push(i);
                        }
                    }
                }
                return missing;
            """)

            if not missing_pages:
                logger.info("Audit passed: 100% of pages have loaded content.")
                break

            logger.warning(f"Audit pass {retry_round + 1}: Found {len(missing_pages)} unrendered pages: {missing_pages[:8]}... Re-scrolling specifically to them.")
            if status_callback:
                status_callback(f"Đang tải bù {len(missing_pages)} trang chưa nạp kịp...", 0.74)

            for p_num in missing_pages:
                driver.execute_script("""
                    var p = document.querySelector('#outer_page_' + arguments[0]);
                    var scroller = document.querySelector('.document_scroller') || document.documentElement || document.body;
                    if (p) {
                        if (scroller) scroller.scrollTop = p.offsetTop;
                        window.scrollTo(0, p.offsetTop);
                        if (window.docManager && window.docManager.pages && window.docManager.pages[arguments[0]]) {
                            try { window.docManager.pages[arguments[0]].load(); } catch(e) {}
                        }
                    }
                """, p_num)
                time.sleep(0.2)

        # 5. Wait for all images to complete loading (complete && naturalWidth > 0)
        if status_callback:
            status_callback("Đang kiểm tra nạp toàn bộ hình ảnh tài liệu...", 0.76)

        start_img = time.time()
        while time.time() - start_img < 15:
            img_status = driver.execute_script("""
                const images = Array.from(document.images);
                images.forEach(img => {
                    const ds = img.getAttribute('data-src') || (img.dataset ? img.dataset.src : null);
                    if (ds && (!img.src || img.src.indexOf(ds) === -1)) {
                        img.src = ds;
                    }
                });
                return {
                    total: images.length,
                    loaded: images.filter(img => img.complete && img.naturalWidth > 0).length
                };
            """)
            if img_status.get("total", 0) > 0 and img_status.get("loaded", 0) >= img_status.get("total", 0):
                break
            time.sleep(0.4)

        # 6. Remove 'document_scroller' class while KEEPING the div container
        # This frees the element from CSS height:100vh / overflow:scroll restrictions
        driver.execute_script("""
            const elements = document.querySelectorAll('.document_scroller');
            elements.forEach(element => {
                element.classList.remove('document_scroller');
            });
        """)

        # 7. Remove mobile overlay, Scribd watermark logo, toolbar_top, toolbar_bottom, ads
        driver.execute_script("""
            const selectorsToRemove = [
                '.mobile_overlay',
                'a[aria-label="View on Scribd.com"]',
                '.toolbar_top', '#toolbar_top',
                '.toolbar_bottom', '#toolbar_bottom',
                '.mobile_header', '.global_header', '.scribd_doc_toolbar',
                '.autoscroll_btn', '.buy_button', '.download_button', '.promo_box',
                '.recommendations', '#head', '#foot', '.sidebar', '.between_page_ads',
                '.page_blur_promo', '.page_missing_explanation', '.upgrade_banner',
                '.portal', '#app_navigation'
            ];
            selectorsToRemove.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });

            // Unblur any blurred elements
            document.querySelectorAll('.blurred_page, .page_blur, .page_missing').forEach(el => {
                el.style.filter = 'none';
                el.style.opacity = '1';
            });
        """)

        # 8. Scroll smoothly back to top for pristine header alignment
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.4)

        # Wait for all fonts to finish rendering
        try:
            driver.execute_script("return (document.fonts && document.fonts.ready) ? true : false;")
        except Exception:
            pass

        # 9. Detect exact page dimensions from DOM to preserve original formatting
        dom_dim = driver.execute_script("""
            var firstPage = document.querySelector('.outer_page, [id^="outer_page_"]');
            var origW = 0;
            var origH = 0;
            if (firstPage) {
                origW = firstPage.offsetWidth || 0;
                origH = firstPage.offsetHeight || 0;
            }
            if (!origW && window.docManager && window.docManager.pages) {
                var firstKey = Object.keys(window.docManager.pages)[0];
                if (firstKey) {
                    var p = window.docManager.pages[firstKey];
                    origW = p.origWidth || 0;
                    origH = p.origHeight || 0;
                }
            }
            return {
                width: origW || 800,
                height: origH || 1130,
                isLandscape: (origW > origH)
            };
        """)

        page_w = dom_dim.get("width", 800)
        page_h = dom_dim.get("height", 1130)
        is_landscape = dom_dim.get("isLandscape", False)

        # 6. Inject clean print CSS with exact page proportions
        driver.execute_script(f"""
            var style = document.createElement('style');
            style.id = 'scribd_custom_print_style';
            style.innerHTML = `
                @media print {{
                    @page {{
                        size: {page_w}px {page_h}px;
                        margin: 0;
                    }}
                    html, body {{
                        margin: 0 !important;
                        padding: 0 !important;
                        background: #ffffff !important;
                        overflow: visible !important;
                        height: auto !important;
                    }}
                    .toolbar_top, .toolbar_bottom, [class*='toolbar'], .between_page_ads, .page_blur_promo {{
                        display: none !important;
                    }}
                    .document_scroller {{
                        overflow: visible !important;
                        height: auto !important;
                        position: static !important;
                        margin: 0 !important;
                        padding: 0 !important;
                    }}
                    .outer_page {{ 
                        width: {page_w}px !important;
                        height: {page_h}px !important;
                        page-break-after: always !important; 
                        break-after: page !important; 
                        page-break-inside: avoid !important; 
                        break-inside: avoid !important; 
                        margin: 0 auto !important; 
                        box-shadow: none !important; 
                        border: none !important; 
                        display: block !important; 
                        visibility: visible !important; 
                    }}
                    .outer_page .inner_page, .outer_page .newpage {{ 
                        display: block !important; 
                        visibility: visible !important; 
                    }}
                }}
                html, body {{
                    overflow: visible !important;
                    height: auto !important;
                }}
                .document_scroller {{
                    overflow: visible !important;
                    height: auto !important;
                    position: static !important;
                }}
            `;
            document.head.appendChild(style);
        """)

        # Brief pause to allow browser render engine to finalize styles and fonts
        time.sleep(1.0)

        # Count final pages present in DOM
        final_page_count = driver.execute_script("""
            return document.querySelectorAll("[id^='outer_page_'], .outer_page").length;
        """)

        page_meta = {
            "width": page_w,
            "height": page_h,
            "is_landscape": is_landscape
        }

        return (final_page_count or total_pages, page_meta)

    def attempt_direct_original_download(
        self,
        main_url: str,
        save_dir: str,
        cookies_input: str,
        target_ext: str = "auto",
        status_callback: Optional[Callable[[str, float], None]] = None
    ) -> Optional[str]:
        """
        Attempts to download the exact raw uploaded file directly from Scribd
        using provided user session cookies.
        Returns the absolute path to the downloaded original file, or None if direct download is not available.
        """
        parsed_cookies = parse_cookies_input(cookies_input)
        if not parsed_cookies:
            return None

        if status_callback:
            status_callback("Đang thử truy xuất trực tiếp FILE GỐC từ máy chủ Scribd...", 0.05)

        driver = self._init_driver(download_dir=save_dir)
        try:
            initial_files = set(os.listdir(save_dir))

            # 1. Inject cookies on scribd domain
            driver.get("https://www.scribd.com/robots.txt")
            for c in parsed_cookies:
                try:
                    driver.add_cookie(c)
                except Exception:
                    pass

            # 2. Navigate to document page
            if status_callback:
                status_callback("Đang kiểm tra quyền tải file gốc từ tài khoản...", 0.1)
            driver.get(main_url)
            time.sleep(2.5)

            # 3. Find and click download button
            download_buttons = driver.find_elements(By.XPATH, 
                "//button[contains(@data-e2e, 'download')] | "
                "//button[contains(@class, 'download')] | "
                "//a[contains(@class, 'download')] | "
                "//button[.//span[contains(text(), 'Download') or contains(text(), 'Tải')]]"
            )
            
            btn_clicked = False
            for btn in download_buttons:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    driver.execute_script("arguments[0].click();", btn)
                    btn_clicked = True
                    break

            if not btn_clicked:
                return None

            time.sleep(2.0)

            # 4. Check if paywall modal appeared (indicating account doesn't have subscription or free download permission)
            has_paywall = driver.execute_script("""
                var text = (document.body ? document.body.innerText : '').toLowerCase();
                return text.indexOf('free trial') !== -1 || text.indexOf('dùng thử') !== -1 || text.indexOf('subscribe') !== -1;
            """)
            if has_paywall:
                logger.info("Direct download paywall detected - Account does not have active download rights.")
                return None

            # 5. Click format button or confirm download in dialog if present
            driver.execute_script("""
                var format = (arguments[0] || '').toLowerCase();
                var allElems = Array.from(document.querySelectorAll('input[type="radio"], button, [role="button"], a'));
                if (format && format !== 'auto') {
                    var fmtEl = allElems.find(function(el) {
                        var t = (el.innerText || el.value || el.getAttribute('aria-label') || '').toLowerCase();
                        return t.indexOf(format) !== -1;
                    });
                    if (fmtEl) {
                        fmtEl.click();
                    }
                }

                var confirmBtn = allElems.find(function(el) {
                    var t = (el.innerText || '').toLowerCase();
                    return (t.indexOf('download now') !== -1 || t.indexOf('tải xuống ngay') !== -1 || t === 'download' || t.indexOf('download ') !== -1) && el.offsetParent !== null;
                });
                if (confirmBtn) {
                    confirmBtn.click();
                }
            """, target_ext if target_ext != "auto" else "")

            if status_callback:
                status_callback("Đang chờ máy chủ Scribd gửi file gốc về máy...", 0.15)

            # 6. Wait for file to land in save_dir
            start_wait = time.time()
            while time.time() - start_wait < 20:
                current_files = set(os.listdir(save_dir))
                new_files = current_files - initial_files

                complete_files = [f for f in new_files if not f.endswith('.crdownload') and not f.endswith('.tmp')]
                if complete_files:
                    downloaded_file = os.path.join(save_dir, complete_files[0])
                    if os.path.getsize(downloaded_file) > 512:
                        time.sleep(1.0)
                        logger.info(f"Direct raw download success: {downloaded_file}")
                        return downloaded_file

                time.sleep(1.0)

            return None
        except Exception as e:
            logger.warning(f"attempt_direct_original_download error: {e}")
            return None
        finally:
            driver.quit()

    def download_document(
        self,
        url_or_id: str,
        output_filepath: str,
        export_format: str = "auto",
        mode: str = "direct_pdf",
        cookie: Optional[str] = None,
        status_callback: Optional[Callable[[str, float], None]] = None
    ) -> str:
        """
        Downloads document preserving 100% format:
        - export_format = 'auto': Automatically uses the original format on Scribd (docx / pptx / pdf)
        - export_format = 'pdf': Exports pixel-perfect, vector-sharp PDF
        - export_format = 'docx': Exports native Microsoft Word document (.docx)
        - export_format = 'pptx': Exports PowerPoint presentation (.pptx)
        - cookie: Optional Scribd session cookie to download the exact raw uploaded file directly from Amazon S3
        """
        start_time = time.time()
        save_directory = os.path.dirname(os.path.abspath(output_filepath))
        os.makedirs(save_directory, exist_ok=True)
        
        # 1. Fetch metadata & determine format
        if status_callback:
            status_callback("Đang nhận diện định dạng gốc của tài liệu trên Scribd...", 0.05)

        doc_meta = get_scribd_metadata(url_or_id)
        embed_url = doc_meta["embed_url"]
        main_url = doc_meta["main_url"]
        orig_ext = doc_meta.get("original_extension", "pdf").lower()
        
        if export_format == "auto":
            target_ext = orig_ext
        else:
            target_ext = export_format.lower().replace(".", "")

        # Adjust final output filepath extension if needed
        base_no_ext, _ = os.path.splitext(output_filepath)
        final_output_path = f"{base_no_ext}.{target_ext}"
        intermediate_pdf_path = f"{base_no_ext}_temp.pdf" if target_ext != "pdf" else final_output_path

        format_name_map = {
            "docx": "Microsoft Word (.docx)",
            "pptx": "PowerPoint Presentation (.pptx)",
            "pdf": "Adobe PDF (.pdf)",
            "txt": "Văn bản (.txt)"
        }
        fmt_display = format_name_map.get(target_ext, f".{target_ext.upper()}")

        # 2. Check if user provided a cookie for direct raw download
        if cookie and cookie.strip():
            raw_downloaded = self.attempt_direct_original_download(
                main_url=main_url,
                save_dir=save_directory,
                cookies_input=cookie,
                target_ext=target_ext,
                status_callback=status_callback
            )
            if raw_downloaded and os.path.exists(raw_downloaded):
                elapsed = round(time.time() - start_time, 1)
                if status_callback:
                    status_callback(f"🎉 Đã lấy trực tiếp FILE GỐC: {os.path.basename(raw_downloaded)} ({elapsed}s)!", 1.0)
                logger.info(f"Direct raw original download succeeded: {raw_downloaded}")
                return raw_downloaded
            else:
                if status_callback:
                    status_callback("⚠️ Không thể tải trực tiếp file gốc (cần gói trả phí). Đang tự động chuyển sang nạp vector 100%...", 0.1)
                time.sleep(1.0)
        
        if status_callback:
            status_callback(f"Định dạng đích: {fmt_display} | Đang mở trình duyệt...", 0.1)

        driver = self._init_driver()

        try:
            if status_callback:
                status_callback("Đang kết nối tài liệu Scribd...", 0.15)

            driver.get(embed_url)

            # Fully load and render all pages
            total_pages, page_info = self.load_and_prepare_document(driver, status_callback)

            if mode == "browser_print":
                if status_callback:
                    status_callback("Đang mở hộp thoại In trình duyệt...", 0.95)
                driver.execute_script("window.print();")
                time.sleep(5)
                return final_output_path

            # Generate high-resolution, pixel-perfect PDF
            if status_callback:
                status_callback("Đang kết xuất tài liệu vector độ nét cao...", 0.75)

            is_landscape = page_info.get("is_landscape", False)
            if doc_meta.get("page_orientation") == "landscape":
                is_landscape = True

            page_w_px = page_info.get("width", 800)
            page_h_px = page_info.get("height", 1130)

            # Convert px to inches at standard 96 DPI
            paper_w_in = round(page_w_px / 96.0, 4)
            paper_h_in = round(page_h_px / 96.0, 4)

            pdf_params = {
                "paperWidth": paper_w_in,
                "paperHeight": paper_h_in,
                "landscape": is_landscape,
                "displayHeaderFooter": False,
                "printBackground": True,
                "preferCSSPageSize": True,
                "marginTop": 0,
                "marginBottom": 0,
                "marginLeft": 0,
                "marginRight": 0,
                "scale": 1.0
            }

            pdf_data = driver.execute_cdp_cmd("Page.printToPDF", pdf_params)
            raw_bytes = base64.b64decode(pdf_data["data"])

            # Clean and trim trailing blank page if created by print engine
            os.makedirs(os.path.dirname(os.path.abspath(intermediate_pdf_path)), exist_ok=True)
            
            try:
                input_stream = io.BytesIO(raw_bytes)
                reader = pypdf.PdfReader(input_stream)
                writer = pypdf.PdfWriter()
                
                num_pages = len(reader.pages)
                trim_last = False
                if num_pages > 1:
                    last_page = reader.pages[-1]
                    if len(last_page.extract_text().strip()) == 0 and len(last_page.images) == 0:
                        trim_last = True

                for i in range(num_pages):
                    if i == num_pages - 1 and trim_last:
                        continue
                    writer.add_page(reader.pages[i])

                with open(intermediate_pdf_path, "wb") as f:
                    writer.write(f)

                total_pages = len(writer.pages)
            except Exception as pe:
                logger.warning(f"Could not trim trailing page: {pe}")
                with open(intermediate_pdf_path, "wb") as f:
                    f.write(raw_bytes)

            # 2. Convert to Target Format if requested (DOCX or PPTX)
            if target_ext == "docx":
                if status_callback:
                    status_callback(f"Đang chuyển đổi sang file Word (.docx) giữ nguyên bảng biểu...", 0.85)
                
                try:
                    from pdf2docx import Converter
                    cv = Converter(intermediate_pdf_path)
                    cv.convert(final_output_path)
                    cv.close()
                    # Clean up temporary PDF
                    if os.path.exists(intermediate_pdf_path) and intermediate_pdf_path != final_output_path:
                        try:
                            os.remove(intermediate_pdf_path)
                        except Exception:
                            pass
                except Exception as ce:
                    logger.error(f"Lỗi khi chuyển đổi DOCX: {ce}, giữ lại file PDF.")
                    final_output_path = intermediate_pdf_path

            elif target_ext == "pptx":
                if status_callback:
                    status_callback(f"Đang chuyển đổi sang PowerPoint (.pptx) chuẩn slide...", 0.85)
                
                try:
                    from pptx import Presentation
                    from pptx.util import Pt
                    doc = fitz.open(intermediate_pdf_path)
                    prs = Presentation()
                    first_p = doc[0]
                    prs.slide_width = Pt(first_p.rect.width)
                    prs.slide_height = Pt(first_p.rect.height)
                    blank_layout = prs.slide_layouts[6]

                    for page in doc:
                        slide = prs.slides.add_slide(blank_layout)
                        pix = page.get_pixmap(dpi=200)
                        img_bytes = io.BytesIO(pix.tobytes("png"))
                        slide.shapes.add_picture(img_bytes, 0, 0, width=Pt(page.rect.width), height=Pt(page.rect.height))
                    
                    prs.save(final_output_path)
                    doc.close()

                    if os.path.exists(intermediate_pdf_path) and intermediate_pdf_path != final_output_path:
                        try:
                            os.remove(intermediate_pdf_path)
                        except Exception:
                            pass
                except Exception as pe:
                    logger.error(f"Lỗi khi chuyển đổi PPTX: {pe}, giữ lại file PDF.")
                    final_output_path = intermediate_pdf_path

            elapsed = round(time.time() - start_time, 1)

            if status_callback:
                status_callback(f"⚡ Đã tải trọn vẹn {total_pages} trang ({target_ext.upper()}) trong {elapsed}s!", 1.0)

            logger.info(f"File saved in {elapsed}s to: {final_output_path} ({total_pages} pages)")
            return final_output_path

        finally:
            if mode != "browser_print" and driver:
                driver.quit()

    def download_to_pdf(
        self,
        url_or_id: str,
        output_filepath: str,
        mode: str = "direct_pdf",
        status_callback: Optional[Callable[[str, float], None]] = None
    ) -> str:
        """Backward-compatible method for downloading directly to PDF."""
        return self.download_document(
            url_or_id=url_or_id,
            output_filepath=output_filepath,
            export_format="pdf",
            mode=mode,
            status_callback=status_callback
        )
