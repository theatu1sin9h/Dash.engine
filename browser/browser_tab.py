# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""WebEngine page and view for a single browser tab."""

from collections.abc import Callable
import base64
from functools import lru_cache
from html import escape
import logging
from pathlib import Path

from PyQt6.QtCore import QBuffer, QIODevice, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QImage, QImageReader
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView

logger = logging.getLogger(__name__)
MAX_WALLPAPER_BYTES = 5 * 1024 * 1024
MAX_WALLPAPER_PIXELS = 24_000_000
MAX_EMBEDDED_WALLPAPER_BYTES = 1_200_000


def _wallpaper_data_uri(path: str) -> str:
    """Embed a bounded, verified raster image without granting file URL access."""
    if not path:
        return ""
    try:
        image_path = Path(path)
        image_stat = image_path.stat()
        if image_stat.st_size > MAX_WALLPAPER_BYTES:
            logger.warning("New-tab wallpaper exceeds the size limit")
            return ""
    except OSError as error:
        logger.warning("Could not read new-tab wallpaper: %s", error)
        return ""
    return _cached_wallpaper_data_uri(
        str(image_path), image_stat.st_mtime_ns, image_stat.st_size
    )


@lru_cache(maxsize=4)
def _cached_wallpaper_data_uri(path: str, _modified_ns: int, _size: int) -> str:
    try:
        reader = QImageReader(path)
        reader.setDecideFormatFromContent(True)
        image_size = reader.size()
        if (
            image_size.width() <= 0
            or image_size.height() <= 0
            or image_size.width() * image_size.height() > MAX_WALLPAPER_PIXELS
            or bytes(reader.format()).lower()
            not in {b"bmp", b"jpeg", b"jpg", b"png", b"webp"}
        ):
            logger.warning("New-tab wallpaper is unsupported or has excessive dimensions")
            return ""
        image = reader.read()
        if image.isNull():
            logger.warning("Could not decode new-tab wallpaper")
            return ""

        for width in (1920, 1600, 1280):
            target_width = min(width, image.width())
            target_height = min(
                max(1, round(image.height() * target_width / image.width())),
                width,
            )
            scaled = image.scaled(
                target_width,
                target_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ).convertToFormat(QImage.Format.Format_RGB32)
            for quality in (85, 70, 55, 40):
                buffer = QBuffer()
                if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
                    return ""
                if not scaled.save(buffer, b"JPEG", quality):
                    logger.warning("Could not encode new-tab wallpaper")
                    return ""
                image_bytes = bytes(buffer.data())
                buffer.close()
                if len(image_bytes) <= MAX_EMBEDDED_WALLPAPER_BYTES:
                    encoded = base64.b64encode(image_bytes).decode("ascii")
                    return f"data:image/jpeg;base64,{encoded}"
    except OSError as error:
        logger.warning("Could not read new-tab wallpaper: %s", error)
        return ""
    logger.warning("Could not compress new-tab wallpaper to the safe embedded size")
    return ""


def _new_tab_html(
    search_url: str,
    theme: str = "dark",
    background_mode: str = "ambient",
    solid_color: str = "#11151b",
    gradient_start: str = "#090b0f",
    gradient_end: str = "#11151b",
    wallpaper_path: str = "",
) -> str:
    safe_search_url = escape(search_url, quote=True)
    page_theme = "light" if theme == "light" else "dark"
    if not isinstance(background_mode, str) or background_mode not in {
        "ambient", "solid", "gradient", "image"
    }:
        background_mode = "ambient"
    safe_colors = (solid_color, gradient_start, gradient_end)
    if any(
        not isinstance(color, str)
        or len(color) != 7
        or color[0] != "#"
        or any(character not in "0123456789abcdefABCDEF" for character in color[1:])
        for color in safe_colors
    ):
        background_mode = "ambient"
    wallpaper_uri = (
        _wallpaper_data_uri(wallpaper_path) if background_mode == "image" else ""
    )
    if background_mode == "solid":
        custom_background = f"background: {solid_color};"
    elif background_mode == "gradient":
        custom_background = (
            f"background: linear-gradient(135deg, {gradient_start}, {gradient_end});"
        )
    elif background_mode == "image" and wallpaper_uri:
        custom_background = (
            "background-color: #090b0f; "
            "background-image: linear-gradient(rgba(4, 6, 10, .35), "
            f'rgba(4, 6, 10, .35)), url("{wallpaper_uri}"); '
            "background-position: center, center; "
            "background-size: cover, cover; "
            "background-repeat: no-repeat, no-repeat;"
        )
    else:
        custom_background = (
            "background: linear-gradient(145deg, #090b0f, #11151b 52%, #080a0e);"
        )
    custom_background_style = (
        "body[data-custom-background='true'] { "
        f"{custom_background} "
        "}"
        if background_mode != "ambient"
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>New Tab</title>
<style>
  :root {{ color-scheme: {page_theme}; font-family: sans-serif; }}
  * {{ box-sizing: border-box; }}
  html, body {{ width: 100%; min-height: 100%; }}
  body {{ --page-bg: #000; --page-mid: #000; --text: #effff3;
         --secondary: #91aa98; --glass: rgba(0, 0, 0, .78);
         --glass-border: rgba(75, 255, 125, .25);
         --button-text: #031007;
         position: relative; isolation: isolate; margin: 0; min-height: 100vh;
         min-height: 100svh; display: grid; place-items: center;
         overflow-x: hidden; overflow-y: auto; padding: 28px 20px;
         background: #000;
         color: var(--text); }}
  #matrix {{ position: fixed; z-index: 0; inset: 0; width: 100%; height: 100%;
             pointer-events: none; }}
  body[data-theme="light"] {{ --page-bg: #eef1f5; --page-mid: #f8f9fb;
         --text: #effff3; --secondary: #91aa98;
         --glass: rgba(0, 0, 0, .78);
         --glass-border: rgba(75, 255, 125, .25);
         --button-text: #031007;
         background: #000; }}
  {custom_background_style}
  @media (prefers-reduced-motion: reduce) {{
    #matrix {{ display: none; }}
  }}
  .welcome {{ position: relative; z-index: 1; width: min(540px, calc(100vw - 40px));
              text-align: center; }}
  h1 {{ margin: 0 0 24px; font-size: clamp(30px, 6vw, 46px);
        color: #b8ffca; font-weight: 500; letter-spacing: -.04em;
        text-wrap: balance; text-shadow: 0 0 24px rgba(34, 255, 96, .22); }}
  form {{ display: flex; gap: 8px; padding: 7px;
          border: 1px solid var(--glass-border); border-radius: 16px;
          background: var(--glass);
          box-shadow: 0 18px 52px rgba(0, 0, 0, .72),
                      0 0 28px rgba(24, 255, 94, .07),
                      inset 0 1px 0 rgba(255, 255, 255, .035);
          -webkit-backdrop-filter: blur(16px);
          backdrop-filter: blur(16px); }}
  input {{ min-width: 0; flex: 1; border: 0; outline: 0; padding: 10px 12px;
           color: var(--text); background: transparent; font: inherit;
           font-size: 15px; }}
  input::placeholder {{ color: var(--secondary); }}
  form button {{ border: 0; border-radius: 10px; padding: 0 18px;
                 color: var(--button-text); background: #66f58d; font: inherit;
                 font-weight: 600; cursor: pointer; }}
  form button:hover {{ background: #8dffab; }}
  .dismiss {{ position: fixed; z-index: 2; top: 14px; right: 16px; width: 36px;
              height: 36px; border: 1px solid var(--glass-border); border-radius: 11px;
              color: var(--secondary); background: rgba(0, 0, 0, .68); font-size: 22px;
              cursor: pointer; }}
  .dismiss:hover {{ color: var(--text); border-color: #54e987; }}
  .customize {{ position: fixed; z-index: 2; top: 14px; right: 60px;
                min-height: 36px; padding: 0 12px;
                border: 1px solid var(--glass-border); border-radius: 10px;
                color: var(--secondary); background: rgba(0, 0, 0, .68);
                font: inherit; cursor: pointer; }}
  .customize:hover {{ color: var(--text); border-color: #54e987; }}
  @media (max-width: 520px) {{
    body {{ padding: 24px 16px; }}
    h1 {{ margin-bottom: 20px; font-size: clamp(28px, 9vw, 38px); }}
    form {{ gap: 4px; }}
    form button {{ padding-inline: 12px; }}
  }}
  body.dismissed .welcome, body.dismissed .dismiss, body.dismissed .customize
    {{ display: none; }}
</style>
<body data-theme="{page_theme}" data-custom-background="{str(background_mode != 'ambient').lower()}">
<button class="dismiss" type="button" aria-label="Dismiss welcome screen"
        title="Dismiss welcome screen" onclick="document.body.classList.add('dismissed')">×</button>
<button class="customize" type="button" aria-label="Customize new-tab background"
        title="Customize new-tab background"
        onclick="location.href='dash://customize-background'">Customize</button>
<canvas id="matrix" aria-hidden="true"></canvas>
<main class="welcome">
  <h1>It’s yours. Go ahead.</h1>
  <form data-search-url="{safe_search_url}"
        onsubmit="event.preventDefault(); const q=this.elements.q.value.trim();
    if(q) location.href=this.dataset.searchUrl.replace('{{query}}', encodeURIComponent(q));">
    <input name="q" type="search" placeholder="Search or enter address"
           aria-label="Search or enter address" autocomplete="off" autofocus>
    <button type="submit">Go</button>
  </form>
</main>
<script>
  (() => {{
    const canvas = document.getElementById("matrix");
    const context = canvas.getContext("2d");
    const glyphs = Array.from("अआइईउऊऋएऐओऔकखगघचछजझटठडढतथदधनपफबभमयरलवशषसहक्षत्रज्ञ");
    let width = 0;
    let height = 0;
    let particles = [];
    let frame = 0;
    let previousFrame = 0;
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    function makeParticle(randomY = false) {{
      return {{
        x: Math.random() * width,
        y: randomY ? Math.random() * height : -Math.random() * height * 0.3,
        speed: 18 + Math.random() * 66,
        drift: (Math.random() - 0.5) * 18,
        size: 13 + Math.random() * 13,
        alpha: 0.28 + Math.random() * 0.68,
        glyph: glyphs[Math.floor(Math.random() * glyphs.length)]
      }};
    }}

    function resize() {{
      const scale = Math.min(window.devicePixelRatio || 1, 1.5);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.round(width * scale);
      canvas.height = Math.round(height * scale);
      context.setTransform(scale, 0, 0, scale, 0, 0);
      particles = Array.from(
        {{ length: Math.min(150, Math.max(55, Math.round(width * height / 12000))) }},
        () => makeParticle(true)
      );
      context.clearRect(0, 0, width, height);
    }}

    function draw(timestamp) {{
      frame = window.requestAnimationFrame(draw);
      if (document.hidden || timestamp - previousFrame < 40) return;
      const elapsed = Math.min((timestamp - previousFrame) / 1000, 0.08);
      previousFrame = timestamp;
      context.fillStyle = "rgba(0, 0, 0, 0.16)";
      context.fillRect(0, 0, width, height);
      for (const particle of particles) {{
        particle.y += particle.speed * elapsed;
        particle.x += particle.drift * elapsed;
        if (particle.y > height + particle.size || particle.x < -20 || particle.x > width + 20) {{
          Object.assign(particle, makeParticle());
        }}
        context.font = `${{particle.size}}px sans-serif`;
        context.fillStyle = `rgba(66, 255, 112, ${{particle.alpha}})`;
        context.fillText(particle.glyph, particle.x, particle.y);
      }}
    }}

    document.addEventListener("visibilitychange", () => {{
    if (reducedMotion) return;
    if (document.hidden) {{
        window.cancelAnimationFrame(frame);
      }} else {{
        previousFrame = 0;
        frame = window.requestAnimationFrame(draw);
      }}
    }});
    window.addEventListener("resize", resize, {{ passive: true }});
    resize();
    if (!reducedMotion) frame = window.requestAnimationFrame(draw);
  }})();
</script>
</body>
</html>"""


class BrowserPage(QWebEnginePage):
    """Web page that opens requested windows in browser tabs."""

    urlRejected = pyqtSignal(str)
    customizeRequested = pyqtSignal()

    def __init__(
        self,
        profile: QWebEngineProfile,
        parent: QWebEngineView,
        create_tab: Callable[[], QWebEnginePage],
    ) -> None:
        super().__init__(profile, parent)
        self._create_tab = create_tab
        self._allow_embedded_document = False

    def load_embedded_document(self, html: str) -> None:
        self._allow_embedded_document = True
        self.setHtml(html)

    def createWindow(self, window_type: QWebEnginePage.WebWindowType) -> QWebEnginePage:
        del window_type
        return self._create_tab()

    def acceptNavigationRequest(
        self,
        url: QUrl,
        navigation_type: QWebEnginePage.NavigationType,
        is_main_frame: bool,
    ) -> bool:
        del navigation_type
        if (
            url.scheme().lower() == "dash"
            and url.host().lower() == "customize-background"
            and not url.path()
        ):
            self.customizeRequested.emit()
            return False
        if url.scheme().lower() == "data":
            if is_main_frame and self._allow_embedded_document:
                self._allow_embedded_document = False
                return True
            if is_main_frame:
                self.urlRejected.emit(url.toDisplayString())
            return False
        if url.scheme().lower() in {"http", "https"} and url.host():
            return True
        if is_main_frame:
            self.urlRejected.emit(url.toDisplayString())
        return False


class BrowserTab(QWebEngineView):
    """A WebEngine view with browser-owned navigation restrictions."""

    def __init__(
        self,
        profile: QWebEngineProfile,
        create_tab: Callable[[], QWebEnginePage],
        parent=None,
        theme: str = "dark",
        search_url: str = "https://duckduckgo.com/?q={query}",
        background_mode: str = "ambient",
        solid_color: str = "#11151b",
        gradient_start: str = "#090b0f",
        gradient_end: str = "#11151b",
        wallpaper_path: str = "",
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._search_url = search_url
        self._is_new_tab = True
        self._background_mode = background_mode
        self._solid_color = solid_color
        self._gradient_start = gradient_start
        self._gradient_end = gradient_end
        self._wallpaper_path = wallpaper_path
        self.urlChanged.connect(self._track_navigation)
        page = BrowserPage(profile, self, create_tab)
        self.setPage(page)
        page.load_embedded_document(self._new_tab_document())

    def _new_tab_document(self) -> str:
        return _new_tab_html(
            self._search_url,
            self._theme,
            self._background_mode,
            self._solid_color,
            self._gradient_start,
            self._gradient_end,
            self._wallpaper_path,
        )

    def _track_navigation(self, url: QUrl) -> None:
        if url.scheme().lower() in {"http", "https"}:
            self._is_new_tab = False

    def set_appearance(
        self,
        theme: str,
        search_url: str,
        background_mode: str = "ambient",
        solid_color: str = "#11151b",
        gradient_start: str = "#090b0f",
        gradient_end: str = "#11151b",
        wallpaper_path: str = "",
    ) -> None:
        self._theme = theme
        self._search_url = search_url
        self._background_mode = background_mode
        self._solid_color = solid_color
        self._gradient_start = gradient_start
        self._gradient_end = gradient_end
        self._wallpaper_path = wallpaper_path
        if self._is_new_tab:
            self.page().load_embedded_document(self._new_tab_document())

    def show_new_tab(self) -> None:
        self._is_new_tab = True
        self.page().load_embedded_document(self._new_tab_document())
