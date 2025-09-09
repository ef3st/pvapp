from __future__ import annotations
from pathlib import Path
from typing import Literal, Optional, Iterable, Tuple
import re, uuid


class MarkdownStreamlitPage:
    """
    Render a Markdown file in Streamlit **without changing the source**.

    What it does
    ------------
    - Text in **native** Streamlit markdown (`st.markdown`).
    - **Inline images**: real images `![alt](path)` are rendered with `st.image`
      (local paths resolved; quality preserved). Hash refs `![x](#anchor)` stay inline links.
    - **Mermaid**: fenced blocks ```mermaid ... ``` are rendered with mermaid.js
      (auto-resize the iframe after SVG render).

    Constructor defaults (so you can just call `render()`)
    ------------------------------------------------------
    default_inline_images : bool = True
    default_image_width   : int | None = None   # None = native resolution
    default_image_root    : str | Path | None = None  # base for "/path" images
    default_caption_from_title : bool = True

    default_enable_mermaid : bool = True
    default_mermaid_theme  : {'default','neutral','dark','forest','base'} = 'dark'
    default_mermaid_cdn    : str = 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'
    default_mermaid_height : int | None = None  # None = smart estimate + auto-resize
    ------
    Note:
        Quick start
        -----------
        >>> page = MarkdownStreamlitPage("docs/page.md", default_mermaid_theme="forest")
        >>> page.render()  # uses the defaults above

        Or override per call:
        >>> page.render_advanced(inline_images=True, enable_mermaid=False)
    """

    # --- Regexes --------------------------------------------------------------
    # Markdown image: ![alt](path "title")
    _IMG_RE = re.compile(
        r"!\[(?P<alt>.*?)\]\("
        r"(?P<path>\s*<?[^)\s]+?>?\s*)"
        r'(?P<title>\s+"[^"]*"\s+|\s+\'[^\']*\'\s+|\s+“[^”]*”\s+|\s+«[^»]*»\s+)?'
        r"\)",
        flags=re.DOTALL,
    )

    # Fenced code markers at line start: ``` or ~~~
    _FENCE_RE = re.compile(r"^\s*(```|~~~)")

    # Mermaid fenced block — very permissive:
    # - supports ``` or ~~~
    # - allows spaces after mermaid and any attrs { ... }
    # - captures matching closing fence (same kind/length)
    _MERMAID_FENCE_RE = re.compile(
        r"(^|\n)[ \t]*(?P<fence>```+|~~~+)[ \t]*mermaid[^\n]*\n"
        r"(?P<code>.*?)(?:\n)[ \t]*(?P=fence)[ \t]*(?=\n|$)",
        flags=re.DOTALL | re.IGNORECASE,
    )

    def __init__(
        self,
        md_path: str | Path,
        page_title: Optional[str] = None,
        ignore_comments: bool = True,
        # defaults for render()
        default_inline_images: bool = True,
        default_image_width: Optional[int] = None,
        default_image_root: Optional[str | Path] = None,
        default_caption_from_title: bool = True,
        default_enable_mermaid: bool = True,
        default_mermaid_theme: Literal[
            "default", "neutral", "dark", "forest", "base"
        ] = "dark",
        default_mermaid_cdn: str = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js",
        default_mermaid_height: Optional[int] = None,
    ):
        self.md_path = Path(md_path)
        if not self.md_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {self.md_path}")
        self.page_title = page_title
        self.ignore_comments = ignore_comments
        self._content: Optional[str] = None  # cache

        # store defaults for render()
        self._defaults = dict(
            inline_images=default_inline_images,
            default_image_width=default_image_width,
            image_root=default_image_root,
            caption_from_title=default_caption_from_title,
            enable_mermaid=default_enable_mermaid,
            mermaid_theme=default_mermaid_theme,
            mermaid_cdn=default_mermaid_cdn,
            mermaid_height=default_mermaid_height,
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def render(self) -> None:
        """
        Convenience: render using constructor defaults.

        Returns:
            None
        ------
        Note:
        """
        self.render_advanced(**self._defaults)

    def render_advanced(
        self,
        inline_images: bool = True,
        default_image_width: Optional[int] = None,
        image_root: Optional[str | Path] = None,
        caption_from_title: bool = True,
        enable_mermaid: bool = True,
        mermaid_theme: Literal["default", "neutral", "dark", "forest", "base"] = "dark",
        mermaid_cdn: str = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js",
        mermaid_height: Optional[int] = None,
    ) -> None:
        import streamlit as st

        title = self.page_title or self._infer_title()
        if title:
            try:
                st.set_page_config(page_title=title, layout="wide")
            except Exception:
                pass

        text = self._get_text_for_render()
        base = Path(image_root) if image_root else Path.cwd()

        if "__mermaid_loaded__" not in st.session_state:
            st.session_state["__mermaid_loaded__"] = (
                False  # ok lasciarlo, ma non lo usiamo più come guard
            )

        parts = (
            self._split_text_and_mermaid_blocks(text)
            if enable_mermaid
            else [("text", text)]
        )

        for kind, payload in parts:
            if kind == "text":
                if inline_images:
                    for (
                        md_chunk,
                        img,
                    ) in self._iter_text_and_images_preserving_hash_refs(payload):
                        if md_chunk.strip():
                            st.markdown(md_chunk)
                        if img is not None:
                            raw_src, alt, title_raw = img
                            p = raw_src.replace("\\", "/").strip()
                            src = self._resolve_image_path(p, base)
                            caption = (
                                self._extract_caption(title_raw)
                                if caption_from_title
                                else None
                            )
                            st.image(
                                src,
                                caption=caption or (alt if alt else None),
                                width=default_image_width,
                            )
                else:
                    if payload.strip():
                        st.markdown(payload)

            elif kind == "mermaid":
                code = payload.strip()
                el_id = f"mermaid_{uuid.uuid4().hex}"
                height = mermaid_height or self._estimate_mermaid_height(code)

                # carica sempre lo script nello stesso iframe del diagramma
                p = Path(mermaid_cdn)
                if p.exists():  # file locale: inline
                    try:
                        js = p.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        js = p.read_bytes().decode("utf-8", errors="ignore")
                    script_tag = f"<script>{js}</script>"
                else:  # URL: usa src
                    script_tag = f'<script src="{mermaid_cdn}"></script>'

                html = f"""
                <div id="{el_id}" class="mermaid" style="margin:0; padding:0;">
    {code}
                </div>
                {script_tag}
                <script>
                  (function() {{
                    function resizeIframe() {{
                      try {{
                        var el = document.getElementById("{el_id}");
                        if (!el) return;
                        var svg = el.querySelector('svg');
                        if (!svg) return;
                        var bbox = svg.getBBox ? svg.getBBox() : null;
                        var h = Math.max(220, (bbox ? bbox.height : svg.scrollHeight) + 24);
                        h = Math.min(1800, Math.max(200, Math.round(h)));
                        if (window.frameElement) {{
                          window.frameElement.style.height = h + 'px';
                        }}
                      }} catch (e) {{}}
                    }}
                    function init() {{
                      if (!window.mermaid) {{ return setTimeout(init, 80); }}
                      try {{
                        if (!window.__mermaid_initialized__) {{
                          window.__mermaid_initialized__ = true;
                          window.mermaid.initialize({{ startOnLoad: false, theme: "{mermaid_theme}", securityLevel: "loose" }});
                        }}
                        window.mermaid.run({{ querySelector: '#{el_id}' }}).then(resizeIframe);
                        var obs = new MutationObserver(resizeIframe);
                        obs.observe(document.getElementById("{el_id}"), {{ childList: true, subtree: true }});
                        window.addEventListener('load', resizeIframe);
                        window.addEventListener('resize', resizeIframe);
                        setTimeout(resizeIframe, 200);
                        setTimeout(resizeIframe, 600);
                      }} catch (e) {{ console.warn(e); }}
                    }}
                    init();
                  }})();
                </script>
                """
                st.components.v1.html(html, height=height, scrolling=False)

    # -------------------------------------------------------------------------
    # Internals
    # -------------------------------------------------------------------------
    def _read(self) -> str:
        if self._content is None:
            self._content = self.md_path.read_text(encoding="utf-8")
        return self._content

    def _get_text_for_render(self) -> str:
        text = self._read()
        if self.ignore_comments:
            text = self._strip_comments(text)
        return text

    # --- Images ---------------------------------------------------------------
    def _iter_text_and_images_preserving_hash_refs(
        self, text: str
    ) -> Iterable[Tuple[str, Optional[Tuple[str, str, str]]]]:
        """
        Yield (markdown_chunk, image_tuple) outside fenced code; hash-refs stay inline.

        Args:
            text (str): The text to process

        Returns:
            Iterable[Tuple[str, Optional[Tuple[str, str, str]]]]: The chunks and images
        ------
        Note:
        """
        lines = text.splitlines(keepends=True)
        out_buf: list[str] = []
        in_fence = False
        fence_delim = None

        for line in lines:
            mf = self._FENCE_RE.match(line)
            if mf:
                d = mf.group(1)
                if not in_fence:
                    in_fence = True
                    fence_delim = d
                elif fence_delim == d:
                    in_fence = False
                    fence_delim = None
                out_buf.append(line)
                continue

            if in_fence:
                out_buf.append(line)
                continue

            pos = 0
            while True:
                m = self._IMG_RE.search(line, pos)
                if not m:
                    out_buf.append(line[pos:])
                    break

                before = line[pos : m.start()]
                if before:
                    out_buf.append(before)

                alt = (m.group("alt") or "").strip()
                raw_path = (m.group("path") or "").strip()
                raw_path = (
                    raw_path[1:-1]
                    if (raw_path.startswith("<") and raw_path.endswith(">"))
                    else raw_path
                )
                title_raw = (m.group("title") or "").strip()
                raw_path_norm = raw_path.replace("\\", "/").strip()

                if raw_path_norm.startswith("#"):
                    # riferimento interno
                    out_buf.append(f"[{alt}]({raw_path_norm})")
                elif "img.shields.io" in raw_path_norm:
                    # è un badge -> lascialo inline nel testo
                    out_buf.append(m.group(0))  # la stringa intera ![...](...)
                else:
                    # immagine reale: gestiscila con st.image
                    yield ("".join(out_buf), (raw_path_norm, alt, title_raw))
                    out_buf = []

                pos = m.end()

        if out_buf:
            yield ("".join(out_buf), None)

    def _resolve_image_path(self, p: str, image_root: Path) -> str:
        if p.lower().startswith(("http://", "https://")):
            return p
        if p.startswith("/"):
            return str((image_root / p.lstrip("/")).resolve())
        return str((self.md_path.parent / p).resolve())

    @staticmethod
    def _extract_caption(title_field: str) -> Optional[str]:
        if not title_field:
            return None
        t = title_field.strip()
        quotes = [('"', '"'), ("'", "'"), ("“", "”"), ("«", "»")]
        for ql, qr in quotes:
            if t.startswith(ql) and t.endswith(qr) and len(t) >= 2:
                return t[1:-1].strip()
        return t

    # --- Mermaid --------------------------------------------------------------
    def _split_text_and_mermaid_blocks(self, text: str) -> list[Tuple[str, str]]:
        """
        Return [("text", chunk), ("mermaid", code), ...] segments.

        Args:
            text (str): The text to split

        Returns:
            list[Tuple[str, str]]: The segments
        ------
        Note:
        """
        parts: list[Tuple[str, str]] = []
        last = 0
        for m in self._MERMAID_FENCE_RE.finditer(text):
            start, end = m.span()
            if start > last:
                parts.append(("text", text[last:start]))
            parts.append(("mermaid", m.group("code")))
            last = end
        if last < len(text):
            parts.append(("text", text[last:]))
        return parts

    def _estimate_mermaid_height(
        self, code: str, min_h: int = 220, max_h: int = 1800, scale: float = 1.0
    ) -> int:
        """
        Smart initial height guess per diagram type; JS will auto-resize afterwards.

        Args:
            code (str): The mermaid code
            min_h (int): Minimum height
            max_h (int): Maximum height
            scale (float): Scale factor

        Returns:
            int: The estimated height
        ------
        Note:
        """
        import re as _re, math as _math

        text = code.strip()
        low = text.lower()

        def clamp(v):
            return max(min_h, min(max_h, int(v * scale)))

        lines = [ln for ln in text.splitlines() if ln.strip()]
        n_lines = len(lines)

        if low.startswith("sequence") or "sequencediagram" in low:
            n_part = len(
                _re.findall(r"^\s*participant\s+\S+", text, flags=_re.I | _re.M)
            )
            n_msgs = len(_re.findall(r"--?>|->>|-x>", text))
            n_notes = len(_re.findall(r"^\s*note\b", text, flags=_re.I | _re.M))
            h = max(120 + n_lines * 18, 140 + n_part * 28 + n_msgs * 22 + n_notes * 20)
            return clamp(h)

        if low.startswith("gantt"):
            n_sec = len(_re.findall(r"^\s*section\b", text, flags=_re.I | _re.M))
            n_tasks = len(_re.findall(r"^\s*[^:\n]+\s*:\s*[^:\n]+", text, flags=_re.M))
            return clamp(220 + n_sec * 36 + n_tasks * 30)

        if low.startswith("class"):
            n_classes = len(_re.findall(r"^\s*class\s+\S+", text, flags=_re.I | _re.M))
            n_rels = len(_re.findall(r"[:<>\-]{2,}", text))
            h = max(120 + n_lines * 18, 160 + n_classes * 42 + n_rels * 4)
            return clamp(h)

        if low.startswith("state"):
            n_states = len(_re.findall(r"^\s*state\s+\S+", text, flags=_re.I | _re.M))
            n_edges = len(_re.findall(r"--?>", text))
            h = max(120 + n_lines * 18, 160 + n_states * 30 + n_edges * 6)
            return clamp(h)

        if low.startswith("pie"):
            n_slices = len(_re.findall(r'^\s*".*"\s*:\s*\d+', text, flags=_re.M))
            return clamp(240 + n_slices * 24)

        if low.startswith("graph") or low.startswith("flowchart"):
            n_nodes = len(
                _re.findall(r"\[[^\]]+\]|\([^)]+\)|\{[^}]+\}|\>\)", text)
            ) + len(
                _re.findall(r"^\s*[A-Za-z0-9_]+(?=\s*--|\s*-\.)", text, flags=_re.M)
            )
            n_nodes = max(1, n_nodes)
            n_edges = len(_re.findall(r"-{1,3}>\>?|={1,3}>|-\.-{0,2}>", text))
            n_sub = len(_re.findall(r"^\s*subgraph\b", text, flags=_re.I | _re.M))
            orient = "TD"
            m = _re.match(r"^\s*(graph|flowchart)\s+([A-Za-z]+)", text, flags=_re.I)
            if m:
                orient = m.group(2).upper()
            base = 150 + n_sub * 60
            if orient in ("LR", "RL"):
                rows = _math.ceil(n_nodes / 5)
                h = base + rows * 70 + min(200, n_edges * 3)
            else:
                h = base + n_nodes * 32 + min(240, n_edges * 4)
            h = max(h, 120 + n_lines * 18)
            return clamp(h)

        return clamp(140 + n_lines * 20)

    # --- Comments -------------------------------------------------------------
    @staticmethod
    def _strip_comments(text: str) -> str:
        """
        Strip HTML comments and GFM one-line comments outside fenced code blocks.

        Args:
            text (str): The text to strip

        Returns:
            str: The stripped text
        ------
        Note:
        """
        re_gfm_line = re.compile(
            r'^\s*\[(?:\/\/|comment)\]\s*:\s*(?:#|<>)\s*(?:\((?:[^()]|\\\(|\\\))*\)|"(?:[^"\\]|\\.)*")\s*$'
        )
        re_fence = re.compile(r"^\s*(```|~~~)")
        lines = text.splitlines(keepends=False)
        out: list[str] = []
        in_fence = False
        fence_delim = None
        in_html = False

        for raw in lines:
            line = raw
            mf = re_fence.match(line)
            if mf:
                d = mf.group(1)
                if not in_fence:
                    in_fence = True
                    fence_delim = d
                elif fence_delim == d:
                    in_fence = False
                    fence_delim = None
                out.append(line)
                continue

            if in_fence:
                out.append(line)
                continue

            if re_gfm_line.match(line):
                continue

            i = 0
            res = ""
            while i < len(line):
                if not in_html:
                    s = line.find("<!--", i)
                    if s == -1:
                        res += line[i:]
                        break
                    res += line[i:s]
                    e = line.find("-->", s + 4)
                    if e == -1:
                        in_html = True
                        break
                    i = e + 3
                else:
                    e = line.find("-->", i)
                    if e == -1:
                        i = len(line)
                        break
                    in_html = False
                    i = e + 3
            if res.strip():
                out.append(res)
        return "\n".join(out)

    # --- Title ---------------------------------------------------------------
    def _infer_title(self) -> Optional[str]:
        m = re.search(r"^\s*#\s+(.+)$", self._read(), flags=re.MULTILINE)
        return m.group(1).strip() if m else None
