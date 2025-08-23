from __future__ import annotations
from pathlib import Path
from typing import Literal, Optional
import re


class MarkdownStreamlitPage:
    """
    Renderizza un file .md in Streamlit senza alterare il file sorgente.
    - Le immagini reali (![alt](path)) vengono mostrate con st.image (qualità nativa).
    - I riferimenti interni (![alt](#ancora)) restano INLINE come link [alt](#ancora).

    Parametri
    ---------
    md_path : str | Path
        Percorso del file Markdown.
    mode : {'auto', 'native', 'html'}
        'native' -> st.markdown (semplice).
        'html'   -> python-markdown + estensioni + code highlight.
        'auto'   -> tenta 'native', altrimenti 'html'.
    page_title : Optional[str]
        Titolo pagina (se None prova dal primo H1).
    ignore_comments : bool
        Rimuove commenti HTML e GFM fuori dai code fence.
    """

    # regex immagine markdown + code-fence
    _IMG_RE = re.compile(
        r"!\[(?P<alt>.*?)\]\("
        r"(?P<path>\s*<?[^)\s]+?>?\s*)"
        r'(?P<title>\s+"[^"]*"\s+|\s+\'[^\']*\'\s+|\s+“[^”]*”\s+|\s+«[^»]*»\s+)?'
        r"\)",
        flags=re.DOTALL,
    )
    _FENCE_RE = re.compile(r"^\s*(```|~~~)")

    def __init__(
        self,
        md_path: str | Path,
        mode: Literal["auto", "native", "html"] = "auto",
        page_title: Optional[str] = None,
        ignore_comments: bool = True,
    ):
        self.md_path = Path(md_path)
        if not self.md_path.exists():
            raise FileNotFoundError(f"File Markdown non trovato: {self.md_path}")
        self.mode = mode
        self.page_title = page_title
        self.ignore_comments = ignore_comments
        self._content: Optional[str] = None  # cache

    # -------------------------
    # API principali
    # -------------------------
    def render(self) -> None:
        """Rendering standard: tutto con st.markdown (immagini incluse come <img>)."""
        import streamlit as st

        title = self.page_title or self._infer_title()
        if title:
            try:
                st.set_page_config(page_title=title, layout="wide")
            except Exception:
                pass
        text = self._get_text_for_render()
        mode = self.mode
        if mode == "auto":
            mode = "html" if self._looks_advanced(text) else "native"
        if mode == "native":
            st.markdown(text)
        else:
            self._render_html(text)

    def render_with_inline_images(
        self,
        default_width: Optional[int] = None,
        image_root: Optional[str | Path] = None,
        caption_from_title: bool = True,
    ) -> None:
        """
        Rendering avanzato: testo con st.markdown + immagini reali con st.image.
        I riferimenti ![...](#ancora) restano INLINE come link [..](#..).
        - default_width: pixel per st.image (None = risoluzione nativa, qualità piena).
        - image_root: base per path che iniziano con '/'. Default = cwd.
        - caption_from_title: usa il "title" del markdown come didascalia se presente.
        """
        import streamlit as st

        text = self._get_text_for_render()
        title = self.page_title or self._infer_title()
        if title:
            try:
                st.set_page_config(page_title=title, layout="wide")
            except Exception:
                pass

        base = Path(image_root) if image_root else Path.cwd()

        # Scorri testo, emettendo blocchi e immagini. I riferimenti # restano inline.
        for md_chunk, img in self._iterate_text_and_images_preserving_hash_refs(text):
            if md_chunk.strip():
                st.markdown(md_chunk)
            if img is not None:
                raw_src, alt, title_raw = img
                p = raw_src.replace("\\", "/").strip()
                src = self._resolve_image_path(p, base)
                caption = (
                    self._extract_caption(title_raw) if caption_from_title else None
                )
                # qualità nativa se default_width=None
                st.image(
                    src, caption=caption or (alt if alt else None), width=default_width
                )

    # -------------------------
    # Implementazioni
    # -------------------------
    def _read(self) -> str:
        if self._content is None:
            self._content = self.md_path.read_text(encoding="utf-8")
        return self._content

    def _get_text_for_render(self) -> str:
        text = self._read()
        if self.ignore_comments:
            text = self._strip_comments(text)
        return text

    def _render_html(self, text: str) -> None:
        import streamlit as st
        from markdown import markdown

        extensions = [
            "fenced_code",
            "codehilite",
            "tables",
            "toc",
            "footnotes",
            "attr_list",
            "admonition",
            "sane_lists",
            "def_list",
            "md_in_html",
        ]
        html_body = markdown(text, extensions=extensions, output_format="html5")
        css = """
        <style>
            .markdown-body { max-width: 1100px; margin: 0 auto; padding: 1rem 1.25rem; }
            .markdown-body table { border-collapse: collapse; }
            .markdown-body table, .markdown-body th, .markdown-body td { border: 1px solid #ddd; }
            .markdown-body th, .markdown-body td { padding: 0.5rem; }
            .markdown-body pre { overflow-x: auto; padding: 0.75rem; border-radius: 0.5rem; }
            .markdown-body code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
            .codehilite { background: #f6f8fa; }
        </style>
        """
        wrapped = f'<div class="markdown-body">{html_body}</div>'
        st.components.v1.html(css + wrapped, height=0, scrolling=True)

    # -------------------------
    # Utility
    # -------------------------
    def _infer_title(self) -> Optional[str]:
        import re

        text = self._read()
        m = re.search(r"^\s*#\s+(.+)$", text, flags=re.MULTILINE)
        return m.group(1).strip() if m else None

    @staticmethod
    def _looks_advanced(text: str) -> bool:
        triggers = ("[^", "]:", "```", "|---", "{:", ":::", ":::note", ":::info")
        return any(t in text for t in triggers)

    # -------------------------
    # Parsing: immagini reali vs riferimenti # (inline)
    # -------------------------
    def _iterate_text_and_images_preserving_hash_refs(self, text: str):
        """
        Genera (chunk_testo, (path, alt, title_raw)) per immagini reali.
        I riferimenti ![...](#ancora) vengono lasciati INLINE come link nel chunk di testo.
        Le immagini dentro i code-fence non vengono toccate.
        """
        lines = text.splitlines(keepends=True)
        out_buf: list[str] = []

        in_fence = False
        fence_delim = None
        i = 0
        while i < len(lines):
            line = lines[i]

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
                i += 1
                continue

            if in_fence:
                out_buf.append(line)
                i += 1
                continue

            # testo normale: estrai tutte le immagini/riferimenti
            pos = 0
            while True:
                m = self._IMG_RE.search(line, pos)
                if not m:
                    out_buf.append(line[pos:])
                    break

                # testo prima
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
                    # ➜ riferimento interno: resta inline come link
                    out_buf.append(f"[{alt}]({raw_path_norm})")
                else:
                    # ➜ immagine reale: emetti blocco separato
                    yield ("".join(out_buf), (raw_path_norm, alt, title_raw))
                    out_buf = []

                pos = m.end()

            i += 1

        if out_buf:
            yield ("".join(out_buf), None)

    def _resolve_image_path(self, p: str, image_root: Path) -> str:
        """
        Risolve il path immagine:
        - URL http/https: restituiti tali e quali
        - '/qualcosa': relativo a image_root (default: cwd)
        - relativo: rispetto alla cartella del .md
        """
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

    # -------------------------
    # Comment stripping
    # -------------------------
    @staticmethod
    def _strip_comments(text: str) -> str:
        """
        Rimuove commenti HTML <!-- ... --> (inline e multilinea) e righe-commento
        GFM ([//]: # (...), [comment]: <> (...)), ignorando i code fence.
        """
        re_gfm_line = re.compile(
            r'^\s*\[(?:\/\/|comment)\]\s*:\s*(?:#|<>)\s*(?:\((?:[^()]|\\\(|\\\))*\)|"(?:[^"\\]|\\.)*")\s*$'
        )
        re_fence = re.compile(r"^\s*(```|~~~)")

        lines = text.splitlines(keepends=False)
        out_lines: list[str] = []

        in_fence = False
        fence_delim = None
        in_html_block = False

        for raw_line in lines:
            line = raw_line
            m = re_fence.match(line)
            if m:
                delim = m.group(1)
                if not in_fence:
                    in_fence = True
                    fence_delim = delim
                elif fence_delim == delim:
                    in_fence = False
                    fence_delim = None
                out_lines.append(line)
                continue

            if in_fence:
                out_lines.append(line)
                continue

            if re_gfm_line.match(line):
                continue

            i = 0
            result = ""
            while i < len(line):
                if not in_html_block:
                    start = line.find("<!--", i)
                    if start == -1:
                        result += line[i:]
                        break
                    else:
                        result += line[i:start]
                        end = line.find("-->", start + 4)
                        if end == -1:
                            in_html_block = True
                            break
                        else:
                            i = end + 3
                            continue
                else:
                    end = line.find("-->", i)
                    if end == -1:
                        i = len(line)
                        break
                    else:
                        in_html_block = False
                        i = end + 3
                        continue

            if result.strip() == "":
                continue
            out_lines.append(result)

        return "\n".join(out_lines)
