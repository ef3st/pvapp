import os
from pathlib import Path
import streamlit as st
import streamlit_antd_components as sac
from ...utils.graphics.md_render import MarkdownStreamlitPage


# ---------- Utilities ---------------------------------------------------------
def _read_md_title(md_path: Path) -> str:
    """Return the first-line title of a Markdown file (fallback to filename).
    Strips leading '#' and whitespace.
    """
    try:
        with md_path.open("r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        title = first_line.lstrip("#").strip()
        return title if title else md_path.stem
    except Exception:
        return md_path.stem


def _build_dir_model(base_dir: Path) -> dict:
    """Return a nested dict mirroring folders/files under base_dir (only .md)."""
    tree: dict = {}
    for p in base_dir.rglob("*.md"):
        if not p.is_file():
            continue
        rel_parts = list(p.relative_to(base_dir).parts)
        cursor = tree
        for part in rel_parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[rel_parts[-1]] = p
    return tree


def _model_to_menuitems(
    model: dict, base_dir: Path, index2path: dict, path2index: dict, counter: list[int]
) -> list:
    """Depth-first build of sac.MenuItem list while tracking global indices."""
    items = []

    # Sort folders first, then files (alphabetically)
    dir_names = sorted([k for k, v in model.items() if isinstance(v, dict)])
    file_names = sorted([k for k, v in model.items() if not isinstance(v, dict)])

    # Folders -> nested MenuItem with children
    for dname in dir_names:
        # Reserve an index for the folder tab itself (non-document)
        idx = counter[0]
        counter[0] += 1
        index2path[idx] = None

        children = _model_to_menuitems(
            model[dname], base_dir, index2path, path2index, counter
        )
        items.append(sac.MenuItem(dname, icon="folder", children=children))

    # Files -> leaf MenuItem (selectable document)
    for fname in file_names:
        path = model[fname]  # Path object
        rel = str(path.relative_to(base_dir)).replace(os.sep, "/")
        title = _read_md_title(path)

        idx = counter[0]
        counter[0] += 1
        index2path[idx] = rel
        path2index[rel] = idx

        items.append(sac.MenuItem(title, icon="file-earmark-text"))
    return items


# ---------- Public API --------------------------------------------------------
def menu_kwargs(
    base_dir: str = "docs",
    *,
    key: str = "docs_menu",
    home_label: str = "Home",
    home_icon: str = "house-door-fill",
    color: str = "teal",
    size: str = "md",
) -> dict:
    """Return kwargs for sac.menu to display a hierarchical docs menu.
    The first item is a 'Home' entry not linked to any document.

    It also stores index→path mapping inside st.session_state[f"{key}_index2path"].
    """
    root = Path(base_dir)
    if not root.exists():
        st.error(f"Cartella non trovata: {root.resolve()}")
        return dict(
            items=[sac.MenuItem(home_label, icon=home_icon)],
            index=0,
            return_index=True,
            key=key,
        )

    model = _build_dir_model(root)
    # Build index maps and items
    index2path: dict[int, str | None] = {}
    path2index: dict[str, int] = {}
    counter = [0]

    # Insert 'Home' item at index 0 (no document associated)
    home_item = sac.MenuItem(home_label, icon=home_icon)
    index2path[counter[0]] = None
    counter[0] += 1

    # Build the rest of the menu from the docs tree
    items = [home_item] + _model_to_menuitems(
        model, root, index2path, path2index, counter
    )

    # Restore last selection if still valid, else default to Home (0)
    last_path = st.session_state.get(f"{key}_path")
    if isinstance(last_path, str) and last_path in path2index:
        default_index = path2index[last_path]
    else:
        default_index = None

    # Persist index map for render()
    st.session_state[f"{key}_index2path"] = index2path

    # Return only kwargs for sac.menu (as requested)
    return dict(
        items=items,
        index=default_index,
        return_index=True,  # sac.menu will return an int index
        key=key,
        color=color,
        size=size,
    )


def render(
    selected_index: int,
    *,
    base_dir: str = "docs",
    key: str = "docs_menu",
    mode: str = "native",
) -> None:
    """Render ONLY the Markdown page for the selected index.
    If the index points to Home or a folder (no doc), render nothing.
    """
    # Retrieve mapping created by menu_kwargs()
    index2path: dict[int, str | None] = st.session_state.get(f"{key}_index2path", {})
    if not index2path:
        # Fallback: rebuild minimal mapping to avoid crashes
        root = Path(base_dir)
        model = _build_dir_model(root)
        index2path = {}
        path2index = {}
        counter = [0]
        index2path[counter[0]] = None  # Home
        counter[0] += 1
        _ = _model_to_menuitems(model, root, index2path, path2index, counter)

    rel = index2path.get(selected_index)
    if not rel:
        # Home or folder: nothing to render
        return

    # Persist chosen path and render
    st.session_state[f"{key}_path"] = rel
    abs_path = str(Path(base_dir) / rel)
    MarkdownStreamlitPage(abs_path).render_advanced(
        inline_images=True,
        default_image_width=None,  # qualità nativa immagini
        enable_mermaid=True,
        mermaid_theme="dark",
        mermaid_height=None,  # stima + auto-resize
    )
    # MarkdownStreamlitPage(abs_path, mode=mode).render_with_inline_images(
    #     default_width=800,  # optional
    #     image_root=".",  # base for path that start with '/...'
    #     caption_from_title=True,
    # )
