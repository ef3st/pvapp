from __future__ import annotations
from pathlib import Path
from typing import Literal, Optional

class MarkdownStreamlitPage:
    """
    Renderizza un file .md in Streamlit senza alterare il file sorgente.

    Parametri
    ---------
    md_path : str | Path
        Percorso del file Markdown.
    mode : {'auto', 'native', 'html'}
        'native' -> st.markdown (più semplice, super veloce).
        'html'   -> python-markdown + estensioni + code highlight.
        'auto'   -> tenta 'native', altrimenti ripiega su 'html'.
    page_title : Optional[str]
        Titolo della pagina Streamlit; se None prova a estrarlo dal primo header H1 del .md.
    ignore_comments : bool
        Se True, rimuove i commenti dal testo Markdown prima del rendering
        (HTML <!-- --> e forme [//]: # (...), [comment]: <> (...)), ignorando i blocchi di codice.
    """

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
    # API principale
    # -------------------------
    def render(self) -> None:
        """Mostra la pagina in Streamlit. Da chiamare dentro `streamlit run`."""
        import streamlit as st

        # Configura titolo pagina (se possibile)
        title = self.page_title or self._infer_title()
        if title:
            try:
                st.set_page_config(page_title=title, layout="wide")
            except Exception:
                pass

        # Banner titolo (se presente)
        if title:
            # st.title(title)
            ...

        # Scelta modalità
        mode = self.mode
        text = self._get_text_for_render()

        if mode == "auto":
            mode = "html" if self._looks_advanced(text) else "native"

        if mode == "native":
            self._render_native(text)
        else:
            self._render_html(text)

    # -------------------------
    # Implementazioni
    # -------------------------
    def _read(self) -> str:
        if self._content is None:
            self._content = self.md_path.read_text(encoding="utf-8")
        return self._content

    def _get_text_for_render(self) -> str:
        """Restituisce il testo pronto per il rendering (eventualmente senza commenti)."""
        text = self._read()
        if self.ignore_comments:
            text = self._strip_comments(text)
        return text

    def _render_native(self, text: str) -> None:
        """Render via st.markdown: nessuna trasformazione del testo (oltre allo stripping opzionale)."""
        import streamlit as st
        st.markdown(text)

    def _render_html(self, text: str) -> None:
        """Render via Python-Markdown + estensioni utili, senza toccare il file sorgente."""
        import streamlit as st
        from markdown import markdown

        extensions = [
            "fenced_code",
            "codehilite",    # Richiede Pygments per highlight
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
        """Estrae il primo header H1 (# ...) come titolo, se presente."""
        import re
        text = self._read()
        m = re.search(r"^\s*#\s+(.+)$", text, flags=re.MULTILINE)
        return m.group(1).strip() if m else None

    @staticmethod
    def _looks_advanced(text: str) -> bool:
        """Euristiche semplici per capire se servono estensioni avanzate."""
        triggers = ("[^", "]:",  # footnotes/reference-style links
                    "```",       # fenced code
                    "|---",      # tables
                    "{:", ":::", ":::note", ":::info")
        return any(t in text for t in triggers)

    # -------------------------
    # Comment stripping
    # -------------------------
    @staticmethod
    def _strip_comments(text: str) -> str:
        """
        Rimuove commenti HTML <!-- ... --> (inline e multilinea) e righe-commento
        in stile GitHub ([//]: # (...), [//]: # "..." e [comment]: <> (...)),
        ignorando i blocchi di codice fenced (``` o ~~~).
        """
        import re

        lines = text.splitlines(keepends=False)
        out_lines: list[str] = []

        in_fence = False
        fence_delim = None  # '```' o '~~~'
        in_html_block = False

        # Precompila regex per le righe-commento “GitHub-style”
        re_gfm_line = re.compile(
            r'^\s*\[(?:\/\/|comment)\]\s*:\s*(?:#|<>)\s*(?:\((?:[^()]|\\\(|\\\))*\)|"(?:[^"\\]|\\.)*")\s*$'
        )
        re_fence = re.compile(r'^\s*(```|~~~)')  # apertura/chiusura fence

        for raw_line in lines:
            line = raw_line

            # Gestione blocchi di codice fenced: copia tali righe senza toccarle
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
                # Dentro code fence NON tocchiamo nulla
                out_lines.append(line)
                continue

            # Salta le righe di commento stile GFM
            if re_gfm_line.match(line):
                continue

            # Gestione commenti HTML, anche inline e multilinea
            i = 0
            result = ""
            while i < len(line):
                if not in_html_block:
                    start = line.find("<!--", i)
                    if start == -1:
                        # Nessun commento: aggiungi resto
                        result += line[i:]
                        break
                    else:
                        # Aggiungi il testo prima del commento
                        result += line[i:start]
                        # Cerchiamo la chiusura sulla stessa riga
                        end = line.find("-->", start + 4)
                        if end == -1:
                            # Entra in blocco multi-linea; scarta tutto da start in poi
                            in_html_block = True
                            break
                        else:
                            # Rimuovi il segmento commento e continua dopo la chiusura
                            i = end + 3
                            continue
                else:
                    # Siamo dentro un commento HTML multi-linea
                    end = line.find("-->", i)
                    if end == -1:
                        # L'intera riga è ancora nel commento -> scarta
                        result = result  # no-op; non aggiungiamo nulla
                        i = len(line)
                        break
                    else:
                        # Esce dal blocco: continua dopo "-->"
                        in_html_block = False
                        i = end + 3
                        continue

            # Se la riga risultante è vuota (solo commenti) non aggiungerla
            if result.strip() == "":
                continue

            out_lines.append(result)

        # Se il file finisce con un commento HTML non chiuso, semplicemente lo scartiamo
        return "\n".join(out_lines)
