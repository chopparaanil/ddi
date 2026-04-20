import os
from typing import Dict, Iterable

from dotenv import load_dotenv

load_dotenv()


def parse_size(size_str):
    try:
        width, height = size_str.lower().split("x")
        return int(width), int(height)
    except (AttributeError, ValueError):
        return (1, 1)


def parse_int(value, default=-1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_bool(value, default=False):
    if value is None:
        return default

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "off", "disabled"}:
        return False
    return default


def normalize_group_key(name):
    raw = "".join(char if char.isalnum() else "_" for char in str(name).upper())
    while "__" in raw:
        raw = raw.replace("__", "_")
    return raw.strip("_") or "APPS"


def load_dashboard_config(group_names: Iterable[str] = ()) -> Dict[str, object]:
    board_rows = max(1, parse_int(os.getenv("BOARD_ROWS"), 2))
    background_fps = parse_int(os.getenv("BOARD_BACKGROUND_FPS"), 8)
    groups = {}

    for group_name in group_names:
        key = normalize_group_key(group_name)
        groups[group_name] = {
            "row": parse_int(os.getenv(f"GROUP_{key}_ROW"), -1),
            "col": parse_int(os.getenv(f"GROUP_{key}_COL"), -1),
        }

    return {
        "title": os.getenv("BOARD_TITLE", "D O T"),
        "title_background": os.getenv("BOARD_TITLE_BACKGROUND", ""),
        "board_rows": board_rows,
        "groups": groups,
        "bg_start": os.getenv("BOARD_BG_START", "#02050A"),
        "bg_mid": os.getenv("BOARD_BG_MID", "#060B12"),
        "bg_end": os.getenv("BOARD_BG_END", "#0A111B"),
        "grid": os.getenv("BOARD_GRID", "#152637"),
        "glow_primary": os.getenv("BOARD_GLOW_PRIMARY", "#123556"),
        "glow_secondary": os.getenv("BOARD_GLOW_SECONDARY", "#1E4B64"),
        "label_color": os.getenv("BOARD_LABEL_COLOR", "#7FA8C7"),
        "topbar_fill": os.getenv("BOARD_TOPBAR_FILL", "rgba(3, 12, 19, 0.72)"),
        "tile_gifs_enabled": parse_bool(os.getenv("BOARD_TILE_GIFS_ENABLED"), False),
        "background_animation": parse_bool(os.getenv("BOARD_BACKGROUND_ANIMATION"), False),
        "background_fps": min(30, max(1, background_fps)),
    }


def load_apps():
    apps = []
    index = 1
    while True:
        name = os.getenv(f"APP_{index}_NAME")
        if not name:
            break

        texture = os.getenv(f"APP_{index}_TEXTURE") or os.getenv(f"APP_{index}_IMAGE", "")
        apps.append(
            {
                "name": name,
                "subtitle": os.getenv(f"APP_{index}_SUBTITLE", ""),
                "path": os.getenv(f"APP_{index}_PATH", ""),
                "size": parse_size(os.getenv(f"APP_{index}_SIZE", "1x1")),
                "color": os.getenv(f"APP_{index}_COLOR", "#0078D7"),
                "icon": os.getenv(f"APP_{index}_ICON", ""),
                "badge": os.getenv(f"APP_{index}_BADGE", ""),
                "group": os.getenv(f"APP_{index}_GROUP", "Apps"),
                "type": os.getenv(f"APP_{index}_TYPE", ""),
                "texture": texture,
                "texture_mode": os.getenv(f"APP_{index}_TEXTURE_MODE", "cover").strip().lower(),
                "row": parse_int(os.getenv(f"APP_{index}_ROW"), -1),
                "col": parse_int(os.getenv(f"APP_{index}_COL"), -1),
            }
        )
        index += 1

    return apps
