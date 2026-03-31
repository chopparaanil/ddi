import config
from config import load_apps, load_dashboard_config, normalize_group_key, parse_int, parse_size


def test_parse_size_accepts_valid_sizes():
    assert parse_size("3x2") == (3, 2)


def test_parse_size_falls_back_for_invalid_values():
    assert parse_size(None) == (1, 1)
    assert parse_size("bad") == (1, 1)


def test_parse_int_returns_default_for_invalid_values():
    assert parse_int("7") == 7
    assert parse_int(None, default=5) == 5
    assert parse_int("abc", default=9) == 9


def test_normalize_group_key_coerces_group_names_to_env_keys():
    assert normalize_group_key("IO Tools") == "IO_TOOLS"
    assert normalize_group_key("Media/Review") == "MEDIA_REVIEW"


def test_load_dashboard_config_reads_group_positions(monkeypatch):
    env = {
        "BOARD_ROWS": "2",
        "GROUP_IO_TOOLS_ROW": "0",
        "GROUP_IO_TOOLS_COL": "1",
    }
    monkeypatch.setattr(config.os, "getenv", lambda key, default=None: env.get(key, default))

    dashboard = load_dashboard_config(["IO Tools", "Media"])

    assert dashboard["board_rows"] == 2
    assert dashboard["groups"]["IO Tools"] == {"row": 0, "col": 1}
    assert dashboard["groups"]["Media"] == {"row": -1, "col": -1}


def test_load_dashboard_config_reads_title(monkeypatch):
    env = {
        "BOARD_TITLE": "Dashboard X",
        "BOARD_TITLE_BACKGROUND": "/tmp/title.gif",
    }
    monkeypatch.setattr(config.os, "getenv", lambda key, default=None: env.get(key, default))

    dashboard = load_dashboard_config([])

    assert dashboard["title"] == "Dashboard X"
    assert dashboard["title_background"] == "/tmp/title.gif"


def test_load_apps_reads_texture_env_var(monkeypatch):
    env = {
        "APP_1_NAME": "One",
        "APP_1_SUBTITLE": "Primary",
        "APP_1_TEXTURE": "/tmp/alpha.gif",
    }
    monkeypatch.setattr(config.os, "getenv", lambda key, default=None: env.get(key, default))

    apps = load_apps()

    assert apps[0]["subtitle"] == "Primary"
    assert apps[0]["texture"] == "/tmp/alpha.gif"


def test_load_apps_falls_back_to_legacy_image_env_var(monkeypatch):
    env = {
        "APP_1_NAME": "One",
        "APP_1_IMAGE": "/tmp/legacy.png",
    }
    monkeypatch.setattr(config.os, "getenv", lambda key, default=None: env.get(key, default))

    apps = load_apps()

    assert apps[0]["texture"] == "/tmp/legacy.png"
