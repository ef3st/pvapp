# * =============================
# *             GUIDE
# * =============================

"""
Streamlit page helpers for rendering project documentation.

Features
--------
- Build a hierarchical navigation menu from a docs/ folder (Markdown files).
- Map indices ↔ file paths for use with `sac.menu`.
- Render Markdown pages with Mermaid diagrams and inline images.

Notes
-----
- Uses `st.session_state[f"{key}_index2path"]` to persist index ↔ path mapping.
- Designed to integrate with the sidebar menu of the main app.
"""

import os
from pathlib import Path

import streamlit as st
import streamlit_antd_components as sac

from ...utils.graphics.md_render import MarkdownStreamlitPage


# * =========================================================
# *                        UTILITIES
# * =========================================================
def _read_md_title(md_path: Path) -> str:
    """
    Read the first line of a Markdown file as its title.

    Args:
        md_path (Path): Path to the Markdown file.

    Returns:
        str: Title without '#' and leading/trailing whitespace.
             Fallback: filename stem if title not found.
    """
    try:
        with md_path.open("r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        title = first_line.lstrip("#").strip()
        return title if title else md_path.stem
    except Exception:
        return md_path.stem


def _build_dir_model(base_dir: Path) -> dict:
    """
    Recursively build a nested dict mirroring the docs folder structure.

    Args:
        base_dir (Path): Root docs directory.

    Returns:
        dict: Nested {folder: {...}, filename: Path}
    """
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
    """
    Convert a directory model into a list of sac.MenuItem recursively.

    Args:
        model (dict): Tree mapping folders → dict, files → Path.
        base_dir (Path): Base documentation directory.
        index2path (dict): Global index → relative path.
        path2index (dict): Relative path → global index.
        counter (list[int]): Single-element list tracking the next index.

    Returns:
        list: sac.MenuItem entries, sorted (folders first, then files).
    """
    items = []

    # Sort folders then files
    dir_names = sorted([k for k, v in model.items() if isinstance(v, dict)])
    file_names = sorted([k for k, v in model.items() if not isinstance(v, dict)])

    # ---- Folders ----
    for dname in dir_names:
        idx = counter[0]
        counter[0] += 1
        index2path[idx] = None  # Reserve index for folder
        children = _model_to_menuitems(
            model[dname], base_dir, index2path, path2index, counter
        )
        items.append(sac.MenuItem(dname, icon="folder", children=children))

    # ---- Files ----
    for fname in file_names:
        path = model[fname]
        rel = str(path.relative_to(base_dir)).replace(os.sep, "/")
        title = _read_md_title(path)

        idx = counter[0]
        counter[0] += 1
        index2path[idx] = rel
        path2index[rel] = idx

        items.append(sac.MenuItem(title, icon="file-earmark-text"))
    return items


# * =========================================================
# *                        PUBLIC API
# * =========================================================
def menu_kwargs(
    base_dir: str = "docs",
    *,
    key: str = "docs_menu",
    home_label: str = "Home",
    home_icon: str = "house-door-fill",
    color: str = "teal",
    size: str = "md",
) -> dict:
    """
    Return kwargs for `sac.menu` to display a hierarchical docs menu.

    Args:
        base_dir (str): Documentation root directory.
        key (str): Session state key prefix for storing index mappings.
        home_label (str): Label for the "home" entry.
        home_icon (str): Icon for the "home" entry.
        color (str): Menu highlight color.
        size (str): Menu size ("sm", "md", "lg").

    Returns:
        dict: Keyword arguments ready for sac.menu.
    """
    root = Path(base_dir)
    if not root.exists():
        st.error(f"Docs folder not found: {root.resolve()}")
        return dict(
            items=[sac.MenuItem(home_label, icon=home_icon)],
            index=0,
            return_index=True,
            key=key,
        )

    model = _build_dir_model(root)
    index2path: dict[int, str | None] = {}
    path2index: dict[str, int] = {}
    counter = [0]

    # Insert Home item
    home_item = sac.MenuItem(home_label, icon=home_icon)
    index2path[counter[0]] = None
    counter[0] += 1

    items = [home_item] + _model_to_menuitems(
        model, root, index2path, path2index, counter
    )

    # Restore last selection if valid
    last_path = st.session_state.get(f"{key}_path")
    if isinstance(last_path, str) and last_path in path2index:
        default_index = path2index[last_path]
    else:
        default_index = None

    st.session_state[f"{key}_index2path"] = index2path

    return dict(
        items=items,
        index=default_index,
        return_index=True,
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
    """
    Render the Markdown page corresponding to the selected index.

    Args:
        selected_index (int): Index returned by sac.menu.
        base_dir (str): Docs root directory.
        key (str): Session state key prefix.
        mode (str): Render mode (reserved for extensions).

    Notes:
        - If index points to a folder or Home, nothing is rendered.
    """
    index2path: dict[int, str | None] = st.session_state.get(f"{key}_index2path", {})

    # Fallback: rebuild if mapping missing
    if not index2path:
        root = Path(base_dir)
        model = _build_dir_model(root)
        index2path = {}
        path2index = {}
        counter = [0]
        index2path[counter[0]] = None
        counter[0] += 1
        _ = _model_to_menuitems(model, root, index2path, path2index, counter)

    rel = index2path.get(selected_index)
    if not rel:
        return  # Home/folder: nothing to render

    st.session_state[f"{key}_path"] = rel
    abs_path = str(Path(base_dir) / rel)
    MarkdownStreamlitPage(abs_path).render_advanced(
        inline_images=True,
        default_image_width=None,
        enable_mermaid=True,
        mermaid_theme="dark",
        mermaid_height=None,
    )
