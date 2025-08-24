"""
DocBundler: merges README.md and all .md files inside /docs (recursively)
into a single PDF, embedding referenced images inline.

Backends supported (pick what's easiest on your machine):
  - playwright  (Chromium headless; no native libs. Run: `poetry add playwright` + `poetry run playwright install chromium`)
  - weasyprint  (HTML→PDF; needs Cairo/Pango/GDK-PixBuf system libs)
  - pdfkit      (needs wkhtmltopdf installed system-wide; set WKHTMLTOPDF_BINARY on Windows if needed)
  - pypandoc    (needs Pandoc and usually LaTeX for PDF)

Run as Streamlit app:
  streamlit run doc_bundler.py

Inside the app: choose backend, click "Generate PDF" (or use the HTML fallback) and download.
"""

from __future__ import annotations

from dataclasses import dataclass
import sys, asyncio
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# Markdown → HTML
import markdown as md
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote

# Optional backend: WeasyPrint
try:
    from weasyprint import HTML, CSS  # type: ignore

    _WEASYPRINT_AVAILABLE = True
except Exception:  # pragma: no cover
    _WEASYPRINT_AVAILABLE = False

# ---------- Core bundler ---------- #

# Windows asyncio fix for Playwright / subprocess
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

# Backend flags (auto-detect availability)
_BACKENDS = {
    "playwright": False,
    "weasyprint": _WEASYPRINT_AVAILABLE,
    "pdfkit": False,
    "pypandoc": False,
}

# Optional backend: pdfkit (wkhtmltopdf)
try:
    import pdfkit  # type: ignore

    _BACKENDS["pdfkit"] = True
except Exception:
    pass

# Optional backend: pypandoc (Pandoc/LaTeX)
try:
    import pypandoc  # type: ignore

    _BACKENDS["pypandoc"] = True
except Exception:
    pass

# Optional backend: Playwright (Chromium headless)
try:
    from playwright.sync_api import sync_playwright  # type: ignore

    _BACKENDS["playwright"] = True
except Exception:
    pass

DEFAULT_CSS = """
@page { size: A4; margin: 24mm 18mm; }
html { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
body { font-size: 12pt; line-height: 1.5; color: #111; }
h1, h2, h3, h4 { page-break-after: avoid; }
h1 { font-size: 24pt; margin-top: 1.2em; }
h2 { font-size: 18pt; margin-top: 1em; }
h3 { font-size: 14pt; margin-top: 0.8em; }
code, kbd, samp { font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; font-size: 0.95em; background: #f6f8fa; padding: .15em .35em; border-radius: 4px; }
pre { background: #f6f8fa; border-radius: 6px; padding: 10px; overflow-x:auto; }
pre code { background: transparent; }
img { max-width: 100%; height: auto; }
.table-of-contents ul { list-style: none; padding-left: 0; }
.table-of-contents { page-break-before: always; }
.table-of-contents a { text-decoration: none; color: #0366d6; }
hr { border: none; border-top: 1px solid #ddd; margin: 24px 0; }
.file-sep { margin: 40px 0; border: 0; border-top: 2px solid #e5e7eb; }
.cover { text-align: center; margin-top: 30mm; }
.cover h1 { font-size: 28pt; margin-bottom: 0.2em; }
.cover .meta { color: #555; }
.cover .icon { width: 128px; height: 128px; display:block; margin: 0 auto 12px; opacity: .85; }
.cover .subtitle { font-size: 14pt; color: #333; margin-top: 8px; }
"""


@dataclass
class DocBundlerConfig:
    project_root: Path
    readme_path: Path = Path("README.md")
    docs_dir: Path = Path("docs")
    title: str = "PVApp \n Project Documentation"
    author: Optional[str] = None
    css: str = DEFAULT_CSS
    include_toc: bool = True
    backend: str = (
        "auto"  # "auto" | "playwright" | "weasyprint" | "pdfkit" | "pypandoc"
    )
    subtitle: Optional[str] = "GUIDE FOR USERS AND PROGRAMMERS"
    cover_icon: Optional[str] = (
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/icons/journal-text.svg"
    )


class DocBundler:  # updated to include Pygments CSS + robust image resolver
    def __init__(self, config: DocBundlerConfig):
        self.cfg = config
        self.root = self.cfg.project_root.resolve()
        self.readme_path = (self.root / self.cfg.readme_path).resolve()
        self.docs_dir = (self.root / self.cfg.docs_dir).resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"Project root not found: {self.root}")

    # ---- Public API ---- #
    def build_pdf_bytes(self) -> bytes:
        """Render full HTML and convert it to PDF using the selected backend."""
        html = self._render_full_html()
        backend = self._select_backend()

        if backend == "weasyprint":
            html_obj = HTML(string=html, base_url=str(self.root))
            return html_obj.write_pdf(stylesheets=[CSS(string=self.cfg.css)])

        elif backend == "pdfkit":
            # pdfkit expects wkhtmltopdf system binary
            import os
            import pdfkit  # type: ignore

            cfg = None
            wkhtml_bin = os.getenv("WKHTMLTOPDF_BINARY")
            if wkhtml_bin:
                try:
                    cfg = pdfkit.configuration(wkhtmltopdf=wkhtml_bin)
                except Exception:
                    cfg = None
            return pdfkit.from_string(html, False, configuration=cfg)

        elif backend == "pypandoc":
            import pypandoc  # type: ignore

            pdf_path = self.root / "_docbundler_temp.pdf"
            pypandoc.convert_text(
                html, to="pdf", format="html", outputfile=str(pdf_path)
            )
            data = pdf_path.read_bytes()
            try:
                pdf_path.unlink(missing_ok=True)
            except Exception:
                pass
            return data

        elif backend == "playwright":
            from playwright.sync_api import sync_playwright  # type: ignore

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                page.set_content(html, wait_until="load")
                try:
                    page.emulate_media(media="print")
                except Exception:
                    pass
                try:
                    page.wait_for_load_state("networkidle")
                except Exception:
                    pass
                pdf_bytes = page.pdf(
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                    margin={
                        "top": "24mm",
                        "right": "18mm",
                        "bottom": "24mm",
                        "left": "18mm",
                    },
                )
                context.close()
                browser.close()
                return pdf_bytes

        else:
            raise RuntimeError(
                "No PDF backend available. Install one of: playwright, weasyprint, pdfkit(wkhtmltopdf), pypandoc(Pandoc/LaTeX)."
            )

    def build_html_string(self) -> str:
        """Return the full HTML string (useful for manual PDF printing or debugging)."""
        return self._render_full_html()

    # ---- Internals ---- #
    def _render_full_html(self) -> str:
        # Build cover first
        cover_html = self._cover_html()
        # Build sections (README + docs)
        section_parts: List[str] = []
        if self.readme_path.exists():
            section_parts.append(self._file_section(self.readme_path))
        if self.docs_dir.exists():
            for md_path in self._iter_markdown_files(self.docs_dir):
                section_parts.append(self._file_section(md_path))
        sections_body = "".join(section_parts)
        # Build TOC from sections only (will render on a new page)
        toc_html = self._toc_html(sections_body) if self.cfg.include_toc else ""
        # Assemble final HTML: cover → TOC → sections
        return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>{self.cfg.title}</title>
<style>{self.cfg.css}
{self._pygments_css()}</style>
</head>
<body>
{cover_html}
{toc_html}
{sections_body}
</body>
</html>"""

    def _cover_html(self) -> str:
        author_html = (
            f"<div class='meta'>Author: {self.cfg.author}</div>"
            if self.cfg.author
            else ""
        )
        icon_html = (
            f"<img src='{self.cfg.cover_icon}' class='icon' alt='journal-text'/>"
            if self.cfg.cover_icon
            else ""
        )
        subtitle_html = (
            f"<div class='subtitle'>{self.cfg.subtitle}</div>"
            if self.cfg.subtitle
            else ""
        )
        return f"""
<section class="cover">
  {icon_html}
  <h1>{self.cfg.title}</h1>
  {subtitle_html}
  {author_html}
  <div class='meta'>{self.root.name} — {self.root}</div>
</section>
<hr class="file-sep"/>
"""

    def _iter_markdown_files(self, base: Path) -> Iterable[Path]:
        """Stable order: first by depth, then alphabetical path."""
        md_files: List[Tuple[int, str, Path]] = []
        for p in base.rglob("*.md"):
            if p.is_file():
                rel = p.relative_to(base)
                md_files.append((len(rel.parts), str(rel).lower(), p))
        md_files.sort()
        for _, __, p in md_files:
            yield p

    def _file_section(self, path: Path, explicit_title: Optional[str] = None) -> str:
        rel = path.relative_to(self.root)
        md_text = path.read_text(encoding="utf-8", errors="ignore")
        html = self._markdown_to_html(md_text, base_dir=path.parent)
        soup = BeautifulSoup(html, "html.parser")
        first_h = soup.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        if first_h:
            section_title = first_h.get_text(strip=True)
            first_h.decompose()
        else:
            section_title = explicit_title or self._prettify_name(rel.stem)
        html_no_first = str(soup)
        return f"""
<section id="{self._slug(section_title)}">
  <h1>{section_title}</h1>
  {html_no_first}
</section>
<hr class="file-sep"/>
"""

    def _markdown_to_html(self, md_text: str, base_dir: Path) -> str:
        # 1) Markdown -> HTML
        html = md.markdown(
            md_text,
            extensions=[
                "extra",  # tables, fenced code blocks
                "toc",  # generate ids
                "codehilite",  # code highlight wrappers
                "sane_lists",
            ],
            output_format="html5",
        )
        # 2) Post-process links and images
        soup = BeautifulSoup(html, "html.parser")

        # Convert image src to data URI to embed inline
        for img in soup.find_all("img"):
            src = img.get("src")
            if not src:
                continue
            data_uri = self._path_to_data_uri(base_dir, src)
            if data_uri:
                img["src"] = data_uri
            else:
                # make absolute to help PDF engine resolve it
                abs_path = (base_dir / src).resolve()
                img["src"] = abs_path.as_uri() if abs_path.exists() else src

        # Make .md links non-broken in PDF: drop extension or convert to anchors
        for a in soup.find_all("a"):
            href = a.get("href")
            if not href:
                continue
            if href.lower().endswith(".md"):
                a["href"] = "#"

        return str(soup)

    def _path_to_data_uri(self, base_dir: Path, href: str) -> Optional[str]:
        try:
            if not href:
                return None
            # Keep embedded images as-is
            if href.startswith("data:"):
                return href
            # Normalize separators and decode URL-encoded paths
            h = href.strip().replace("\\", "/")
            parsed = urlparse(h)
            # Leave remote images to the browser
            if parsed.scheme in {"http", "https"}:
                return None
            clean = unquote(parsed.path or "").lstrip("./")

            candidates: List[Path] = []
            try:
                if (":" in h[:3]) or h.startswith("\\"):
                    candidates.append(Path(h).resolve())
            except Exception:
                pass
            if clean.startswith("/"):
                # Absolute-like path -> relative to project root and docs root
                candidates.append((self.root / clean.lstrip("/")).resolve())
                candidates.append((self.docs_dir / clean.lstrip("/")).resolve())
            else:
                candidates.append((base_dir / clean).resolve())
                candidates.append((self.docs_dir / clean).resolve())
                # If MD is deep and uses paths like "../img/foo.png"
                try:
                    candidates.append((base_dir.resolve() / clean).resolve())
                except Exception:
                    pass

            # Fallback: search by filename around base_dir and docs_dir
            target = None
            for c in candidates:
                if c.exists() and c.is_file():
                    target = c
                    break
            if target is None:
                try:
                    name = Path(clean).name
                    for root in {base_dir, base_dir.parent, self.docs_dir, self.root}:
                        for found in root.rglob(name):
                            if found.is_file():
                                target = found
                                raise StopIteration
                except StopIteration:
                    pass

            if target is None:
                return None

            mime = self._guess_mime(target.suffix.lower())
            import base64

            b64 = base64.b64encode(target.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{b64}"
        except Exception:
            return None

    def _guess_mime(self, ext: str) -> str:
        return {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }.get(ext, "application/octet-stream")

    def _slug(self, s: str) -> str:
        return "".join(ch if ch.isalnum() else "-" for ch in s).strip("-").lower()

    def _prettify_name(self, name: str) -> str:
        n = name.replace("_", " ").replace("-", " ").strip()
        return " ".join(w.capitalize() for w in n.split()) or name

    def _toc_html(self, body_html: str) -> str:
        # Build a simple TOC from <h1>
        soup = BeautifulSoup(body_html, "html.parser")
        items = []
        for h1 in soup.find_all("h1"):
            sec = h1.find_parent("section")
            if not sec or not sec.get("id"):
                continue
            items.append((sec.get("id"), h1.get_text(strip=True)))
        if not items:
            return ""
        lis = "\n".join(
            f"<li><a href='#{sid}'>{md.util.AtomicString(title)}</a></li>"
            for sid, title in items
        )
        return f"""
<nav class="table-of-contents">
  <h2>Indice</h2>
  <ul>
    {lis}
  </ul>
</nav>
<hr class="file-sep"/>
"""

    def _pygments_css(self) -> str:
        """Return Pygments CSS if available, otherwise empty string."""
        try:
            from pygments.formatters import HtmlFormatter  # type: ignore

            return HtmlFormatter(style="default").get_style_defs(".codehilite")
        except Exception:
            return ""

    def _select_backend(self) -> str:
        # Resolve backend preference
        pref = (self.cfg.backend or "auto").lower()
        if pref != "auto":
            if not _BACKENDS.get(pref):
                raise RuntimeError(f"Backend '{pref}' not available.")
            return pref
        # auto preference: playwright → weasyprint → pdfkit → pypandoc
        for name in ("playwright", "weasyprint", "pdfkit", "pypandoc"):
            if _BACKENDS.get(name):
                return name
        return "none"


# ---------- Streamlit app ---------- #


def _run_streamlit():  # pragma: no cover
    import streamlit as st

    st.set_page_config(page_title="DocBundler PDF", layout="centered")
    st.title("📄 DocBundler: README + docs ➜ PDF")
    st.write("Merge README.md and /docs/**/*.md into a single downloadable PDF.")

    project_root = st.text_input("Project root", value=str(Path.cwd()))
    readme_path = st.text_input("README path", value="README.md")
    docs_dir = st.text_input("Docs folder", value="docs")
    title = st.text_input("PDF title", value=f"PVApp {"\n"} Project Documentation")
    author = st.text_input("Author (optional)", value="")
    subtitle = st.text_input("Subtitle", value="GUIDE FOR USERS AND PROGRAMMERS")
    icon_url = st.text_input(
        "Cover icon URL (optional)",
        value="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/icons/journal-text.svg",
    )
    include_toc = st.checkbox("Include TOC", value=True)

    # Backend selector
    avail = [k for k, v in _BACKENDS.items() if v]
    backend = st.selectbox(
        "PDF backend",
        options=["auto", "playwright", "weasyprint", "pdfkit", "pypandoc"],
        index=0,
        help=f"Available now: {', '.join(avail) or 'none'}.",
    )

    st.caption(
        "Tip: For Playwright, run `poetry add playwright` and then `poetry run playwright install chromium`."
    )

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate PDF"):
            try:
                cfg = DocBundlerConfig(
                    project_root=Path(project_root),
                    readme_path=Path(readme_path),
                    docs_dir=Path(docs_dir),
                    title=title,
                    author=author or None,
                    subtitle=subtitle or None,
                    cover_icon=icon_url or None,
                    include_toc=include_toc,
                    backend=backend,
                )
                bundler = DocBundler(cfg)
                pdf_bytes = bundler.build_pdf_bytes()
                st.success("PDF ready!")
                st.download_button(
                    label="⬇️ Download PDF",
                    data=pdf_bytes,
                    file_name=f"{Path(project_root).name or 'documentation'}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                import traceback

                st.error(f"Error while generating PDF: {e}")
                st.code(traceback.format_exc())
                st.info("Detected backends: " + (", ".join(avail) or "none"))
    with col2:
        if st.button("Export HTML (fallback)"):
            try:
                cfg = DocBundlerConfig(
                    project_root=Path(project_root),
                    readme_path=Path(readme_path),
                    docs_dir=Path(docs_dir),
                    title=title,
                    author=author or None,
                    include_toc=include_toc,
                    backend=backend,
                )
                bundler = DocBundler(cfg)
                html_str = bundler.build_html_string()
                st.success("HTML ready!")
                st.download_button(
                    label="⬇️ Download HTML",
                    data=html_str.encode("utf-8"),
                    file_name=f"{Path(project_root).name or 'documentation'}.html",
                    mime="text/html",
                )
            except Exception as e:
                import traceback

                st.error(f"Error while exporting HTML: {e}")
                st.code(traceback.format_exc())


if __name__ == "__main__":  # pragma: no cover
    # Allows: streamlit run doc_bundler.py
    try:
        import streamlit as st  # noqa: F401

        _run_streamlit()
    except ModuleNotFoundError:
        # Fallback: quick local HTML for CLI testing
        cfg = DocBundlerConfig(project_root=Path.cwd())
        bundler = DocBundler(cfg)
        html = bundler.build_html_string()
        Path("bundle_preview.html").write_text(html, encoding="utf-8")
        print(
            "Created bundle_preview.html — open it in the browser or use Streamlit for PDF."
        )
