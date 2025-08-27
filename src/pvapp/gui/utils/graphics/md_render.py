from __future__ import annotations
from pathlib import Path
from typing import Literal, Optional
import re

#! CHAT GPT ALERT


class MarkdownStreamlitPage:
    """
    Renderizza un file .md in Streamlit senza alterare il file sorgente.
    Supporta:
      - Modalità 'native' e 'html'
      - Ignora commenti (opzionale)
      - Immagini inline con st.image via render_with_inline_images(...)
      - **Mermaid** nei fenced block ```mermaid (solo in 'html')
    """

    _IMG_RE = re.compile(
        r"!\[(?P<alt>.*?)\]\("
        r"(?P<path>\s*<?[^)\s]+?>?\s*)"
        r'(?P<title>\s+"[^"]*"\s+|\s+\'[^\']*\'\s+|\s+“[^”]*”\s+|\s+«[^»]*»\s+)?'
        r"\)",
        flags=re.DOTALL,
    )
    _FENCE_RE = re.compile(r"^\s*(```|~~~)")

    # NEW: trova fenced blocks mermaid
    _MERMAID_FENCE_RE = re.compile(
        r"(^|\n)[ \t]*```mermaid[^\n]*\n(?P<code>.*?)(?:\n)[ \t]*```[ \t]*(?=\n|$)",
        flags=re.DOTALL,
    )

    def __init__(
        self,
        md_path: str | Path,
        mode: Literal["auto", "native", "html"] = "auto",
        page_title: Optional[str] = None,
        ignore_comments: bool = True,
        enable_mermaid: bool = True,
        mermaid_theme: Literal[
            "default", "neutral", "dark", "forest", "base"
        ] = "default",
        mermaid_cdn: str = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js",
    ):
        self.md_path = Path(md_path)
        if not self.md_path.exists():
            raise FileNotFoundError(f"File Markdown non trovato: {self.md_path}")
        self.mode = mode
        self.page_title = page_title
        self.ignore_comments = ignore_comments
        self.enable_mermaid = enable_mermaid
        self.mermaid_theme = mermaid_theme
        self.mermaid_cdn = mermaid_cdn
        self._content: Optional[str] = None  # cache

    # -------------------------
    # API principale
    # -------------------------
    def render(self) -> None:
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
            # NEW: pre-process mermaid prima di convertire in HTML
            if self.enable_mermaid:
                text = self._convert_mermaid_fences_to_div(text)
            self._render_html(text)

    # (resto dei tuoi metodi per immagini inline, ecc., invariati — li puoi mantenere)

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

        # NEW: se sono presenti div.mermaid, inietto lo script e inizializzo
        needs_mermaid = ('class="mermaid"' in html_body) or (
            "<div class='mermaid'" in html_body
        )

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

        mermaid_script = ""
        if needs_mermaid and self.enable_mermaid:
            mermaid_script = f"""
            <script src="{self.mermaid_cdn}"></script>
            <script>
              (function() {{
                // Evita doppie inizializzazioni
                if (window.__mermaid_initialized__) return;
                window.__mermaid_initialized__ = true;
                const start = () => {{
                  if (window.mermaid) {{
                    window.mermaid.initialize({{ startOnLoad: true, theme: "{self.mermaid_theme}" }});
                    // Render esplicito in caso di dynamic load:
                    window.mermaid.run({{querySelector: '.mermaid'}});
                  }} else {{
                    setTimeout(start, 100);
                  }}
                }};
                start();
              }})();
            </script>
            """

        wrapped = f'<div class="markdown-body">{html_body}</div>'
        st.components.v1.html(css + wrapped + mermaid_script, height=0, scrolling=True)

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
        # Se c'è mermaid, preferisci "html"
        return any(t in text for t in triggers)

    # -------------------------
    # Mermaid helpers (NUOVO)
    # -------------------------
    def _convert_mermaid_fences_to_div(self, text: str) -> str:
        """
        Converte i fenced block ```mermaid ... ``` in <div class="mermaid">...</div>
        così mermaid.js li può renderizzare. Non tocca gli altri blocchi.
        """

        def _repl(m: re.Match) -> str:
            code = m.group("code")
            return f'\n<div class="mermaid">\n{code}\n</div>\n'

        return self._MERMAID_FENCE_RE.sub(_repl, text)

    # --- helper: spezza testo e blocchi mermaid (NUOVO) ---
    def _split_text_and_mermaid_blocks(self, text: str):
        """
        Ritorna una lista di elementi:
          - ("text", chunk_markdown)
          - ("mermaid", codice_mermaid)
        """
        parts = []
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

    # --- helper: stima altezza (NUOVO) ---
    def _estimate_mermaid_height(
        self, code: str, min_h: int = 220, max_h: int = 1800, scale: float = 1.0
    ) -> int:
        """
        Heuristics per stimare l'altezza del diagramma Mermaid.
        Analizza il 'type' del diagramma e conta nodi/righe/relazioni.
        """
        import re, math

        text = code.strip()
        low = text.lower()

        def clamp(v):
            return max(min_h, min(max_h, int(v * scale)))

        # Helpers generici
        lines = [ln for ln in text.splitlines() if ln.strip()]
        n_lines = len(lines)

        # euristica per "nodi" nei flowchart/graph: [ ], ( ), { }, id-->id, subgraph
        def count_flow_nodes_and_edges(s: str):
            n_nodes = len(re.findall(r"\[[^\]]+\]|\([^)]+\)|\{[^}]+\}|\>\)", s)) + len(
                re.findall(r"^\s*[A-Za-z0-9_]+(?=\s*--|\s*-\.)", s, flags=re.MULTILINE)
            )
            n_subgraphs = len(
                re.findall(r"^\s*subgraph\b", s, flags=re.IGNORECASE | re.MULTILINE)
            )
            n_edges = len(re.findall(r"-{1,3}>\>?|={1,3}>|-\.-{0,2}>", s))
            return max(1, n_nodes), n_edges, n_subgraphs

        # Tipo di diagramma
        if low.startswith("sequence") or "sequenceDiagram".lower() in low:
            # sequenceDiagram
            n_part = len(
                re.findall(
                    r"^\s*participant\s+\S+", text, flags=re.IGNORECASE | re.MULTILINE
                )
            )
            n_msgs = len(re.findall(r"--?>|->>|-x>", text))
            n_notes = len(
                re.findall(r"^\s*note\b", text, flags=re.IGNORECASE | re.MULTILINE)
            )
            base = 140
            h = base + n_part * 28 + n_msgs * 22 + n_notes * 20
            # safety net sulle righe
            h = max(h, 120 + n_lines * 18)
            return clamp(h)

        if low.startswith("gantt"):
            # gantt
            n_sections = len(
                re.findall(r"^\s*section\b", text, flags=re.IGNORECASE | re.MULTILINE)
            )
            n_tasks = len(
                re.findall(r"^\s*[^:\n]+\s*:\s*[^:\n]+", text, flags=re.MULTILINE)
            )
            base = 220
            h = base + n_sections * 36 + n_tasks * 30
            return clamp(h)

        if low.startswith("class"):
            # classDiagram
            n_classes = len(
                re.findall(r"^\s*class\s+\S+", text, flags=re.IGNORECASE | re.MULTILINE)
            )
            n_rels = len(re.findall(r"[:<>\-]{2,}", text))
            base = 160
            h = base + n_classes * 42 + n_rels * 4
            h = max(h, 120 + n_lines * 18)
            return clamp(h)

        if low.startswith("state"):
            # stateDiagram / stateDiagram-v2
            n_states = len(
                re.findall(r"^\s*state\s+\S+", text, flags=re.IGNORECASE | re.MULTILINE)
            )
            n_edges = len(re.findall(r"--?>", text))
            base = 160
            h = base + n_states * 30 + n_edges * 6
            h = max(h, 120 + n_lines * 18)
            return clamp(h)

        if low.startswith("pie"):
            # pie
            n_slices = len(re.findall(r'^\s*".*"\s*:\s*\d+', text, flags=re.MULTILINE))
            base = 240
            h = base + n_slices * 24
            return clamp(h)

        # flowchart / graph (TD, LR, RL, BT)
        if low.startswith("graph") or low.startswith("flowchart"):
            n_nodes, n_edges, n_sub = count_flow_nodes_and_edges(text)
            # orientazione: LR/RL = più largo, meno alto; TD/BT = più alto
            orient = "TD"
            m = re.match(
                r"^\s*(graph|flowchart)\s+([A-Za-z]+)", text, flags=re.IGNORECASE
            )
            if m:
                orient = m.group(2).upper()

            base = 150 + n_sub * 60
            if orient in ("LR", "RL"):
                # griglia "larga"
                rows = math.ceil(n_nodes / 5)
                h = base + rows * 70 + min(200, n_edges * 3)
            else:
                # TD/BT: cresce di più in verticale
                h = base + n_nodes * 32 + min(240, n_edges * 4)

            h = max(h, 120 + n_lines * 18)
            return clamp(h)

        # fallback generico
        return clamp(140 + n_lines * 20)

    def render_native_with_mermaid(
        self,
        mermaid_theme: Literal["default", "neutral", "dark", "forest", "base"] = "dark",
        mermaid_cdn: str = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js",
        mermaid_height: int | None = None,
    ) -> None:
        """
        Render 'native' (st.markdown) ma i blocchi ```mermaid vengono renderizzati con mermaid.js.
        - mermaid_theme: 'default' | 'neutral' | 'dark' | 'forest' | 'base'
        - mermaid_height: altezza fissa (px) per ogni diagramma; se None viene stimata dal codice.
        """
        import streamlit as st
        import uuid

        text = self._get_text_for_render()

        # Carica mermaid una sola volta per sessione
        if "__mermaid_loaded__" not in st.session_state:
            st.session_state["__mermaid_loaded__"] = False

        parts = self._split_text_and_mermaid_blocks(text)

        # Se non ci sono blocchi mermaid, fai normale native
        if not any(kind == "mermaid" for kind, _ in parts):
            st.markdown(text)
            return

        for idx, (kind, payload) in enumerate(parts):
            if kind == "text":
                if payload.strip():
                    st.markdown(payload)
                continue

            # kind == "mermaid"
            code = payload.strip()
            el_id = f"mermaid_{uuid.uuid4().hex}"

            # Altezza: fissa o stimata
            height = mermaid_height or self._estimate_mermaid_height(code)

            # HTML per il singolo diagramma
            # Carica lo script solo la prima volta
            script_tag = ""
            if not st.session_state["__mermaid_loaded__"]:
                script_tag = f'<script src="{mermaid_cdn}"></script>'
                st.session_state["__mermaid_loaded__"] = True

            html = f"""
            <div id="{el_id}" class="mermaid" style="margin: 0; padding: 0;">
    {code}
            </div>
            {script_tag}
            <script>
              (function() {{
                function initMermaid() {{
                  if (!window.mermaid) {{ return setTimeout(initMermaid, 80); }}
                  try {{
                    if (!window.__mermaid_initialized__) {{
                      window.__mermaid_initialized__ = true;
                      window.mermaid.initialize({{ startOnLoad: false, theme: "{mermaid_theme}" }});
                    }}
                    // Render solo questo diagramma
                    window.mermaid.run({{ querySelector: '#{el_id}' }});
                  }} catch (e) {{
                    console.error('Mermaid render error:', e);
                  }}
                }}
                initMermaid();
              }})();
            </script>
            """

            # Mostra il diagramma
            st.components.v1.html(html, height=height, scrolling=False)

    # -------------------------
    # Comment stripping (come già avevi)
    # -------------------------
    @staticmethod
    def _strip_comments(text: str) -> str:
        import re

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
