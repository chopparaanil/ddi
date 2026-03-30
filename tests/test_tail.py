import base64

from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QMessageBox

import tail
from tail import INDIA_TZ, Tile, build_launch_command, india_now, launch_path


def test_build_launch_command_wraps_python_scripts(tmp_path):
    script = tmp_path / "tool.py"
    script.write_text("print(1)\n")

    command = build_launch_command(f"{script} --flag", python_executable="/usr/bin/python3")

    assert command == ["/usr/bin/python3", str(script), "--flag"]


def test_launch_path_reports_missing_commands():
    ok, error = launch_path("/path/to/missing")

    assert ok is False
    assert "Command not found" in error


def test_tile_launch_shows_message_when_command_fails(qapp, monkeypatch):
    messages = []
    tile = Tile("Broken", path="/path/to/missing")

    monkeypatch.setattr(tail, "launch_path", lambda path: (False, "Command not found: /path/to/missing"))
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: messages.append(args[2]))

    assert tile._launch() is False
    assert messages == ["Unable to open Broken.\nCommand not found: /path/to/missing"]


def test_tile_loads_static_texture(qapp, tmp_path):
    texture = tmp_path / "tile.png"
    pixmap = QPixmap(12, 12)
    pixmap.fill(QColor("#336699"))
    assert pixmap.save(str(texture))

    tile = Tile("Textured", texture=str(texture))

    assert tile._texture_pixmap is not None
    assert tile._has_texture() is True


def test_tile_loads_gif_texture(qapp, tmp_path):
    texture = tmp_path / "tile.gif"
    texture.write_bytes(base64.b64decode("R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="))

    tile = Tile("Animated", texture=str(texture))
    qapp.processEvents()

    assert tile._texture_movie is not None
    assert tile._texture_movie.isValid() is True


def test_india_now_uses_indian_timezone():
    now = india_now()

    assert getattr(now.tzinfo, "key", None) == INDIA_TZ.key
