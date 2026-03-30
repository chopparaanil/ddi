import os
from dotenv import load_dotenv

load_dotenv()


def parse_size(size_str):
    try:
        w, h = size_str.lower().split("x")
        return int(w), int(h)
    except:
        return (1, 1)


def parse_int(value, default=-1):
    try:
        return int(value)
    except:
        return default


def load_apps():
    apps = []
    i = 1
    while True:
        name = os.getenv(f"APP_{i}_NAME")
        if not name:
            break
        apps.append({
            "name":  name,
            "path":  os.getenv(f"APP_{i}_PATH", ""),
            "size":  parse_size(os.getenv(f"APP_{i}_SIZE", "1x1")),
            "color": os.getenv(f"APP_{i}_COLOR", "#0078D7"),
            "icon":  os.getenv(f"APP_{i}_ICON",  ""),
            "badge": os.getenv(f"APP_{i}_BADGE", ""),
            "group": os.getenv(f"APP_{i}_GROUP", "Apps"),
            "type":  os.getenv(f"APP_{i}_TYPE",  ""),   # "clock" | "date" | ""

            "row": parse_int(os.getenv(f"APP_{i}_ROW"), -1),
            "col": parse_int(os.getenv(f"APP_{i}_COL"), -1),
        })
        i += 1

    return  apps
