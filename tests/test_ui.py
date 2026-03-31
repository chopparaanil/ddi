from PyQt5.QtCore import QPoint, QPointF, Qt
from PyQt5.QtGui import QColor, QMovie, QPixmap, QWheelEvent
from PyQt5.QtWidgets import QWidget

import ui
from tail import Tile
from ui import Dashboard, HorizontalScrollArea, ParticleBG


def make_app(name, group="Apps", row=-1, col=-1, size=(1, 1), app_type="", texture="", subtitle=""):
    return {
        "name": name,
        "subtitle": subtitle,
        "path": "",
        "size": size,
        "color": "#123456",
        "icon": "",
        "badge": "",
        "group": group,
        "type": app_type,
        "texture": texture,
        "row": row,
        "col": col,
    }


def write_test_gif(path):
    path.write_bytes(
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
        b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
        b"\x00\x02\x02L\x01\x00;"
    )


def test_dashboard_filter_only_hides_non_matching_tiles(qapp):
    window = Dashboard(apps=[make_app("Alpha"), make_app("Beta")])
    tiles = {name: tile for tile, name in window._all_tiles}

    window._filter("alp")

    assert tiles["Alpha"].isHidden() is False
    assert tiles["Beta"].isHidden() is True

    window._filter("")

    assert tiles["Alpha"].isHidden() is False
    assert tiles["Beta"].isHidden() is False


def test_horizontal_scroll_area_maps_mouse_wheel_to_horizontal_scroll(qapp):
    area = HorizontalScrollArea()
    content = QWidget()
    content.resize(2000, 200)
    area.setWidget(content)
    area.resize(400, 200)
    area.show()
    qapp.processEvents()

    start = area.horizontalScrollBar().value()
    event = QWheelEvent(
        QPointF(20, 20),
        QPointF(20, 20),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.ScrollUpdate,
        False,
    )
    area.wheelEvent(event)

    assert area.horizontalScrollBar().value() > start


def test_dashboard_uses_horizontal_scrolling(qapp):
    window = Dashboard(apps=[make_app("Alpha", group="One"), make_app("Beta", group="Two")])

    assert window._scroll.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert window._scroll.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff


def test_dashboard_builds_live_tiles_without_crashing(qapp):
    apps = [make_app("Clock", app_type="clock", size=(2, 2)), make_app("Date", app_type="date", size=(1, 2))]

    window = Dashboard(apps=apps)

    assert len(window._all_tiles) == 2


def test_dashboard_passes_texture_to_tiles(qapp, tmp_path):
    texture = tmp_path / "tile.png"
    pixmap = QPixmap(12, 12)
    pixmap.fill(QColor("#224466"))
    assert pixmap.save(str(texture))

    window = Dashboard(apps=[make_app("Textured", texture=str(texture))])
    tile, _ = window._all_tiles[0]

    assert tile._has_texture() is True


def test_dashboard_passes_subtitle_to_tiles(qapp):
    window = Dashboard(apps=[make_app("Alpha", subtitle="Primary Tool")])
    tile, _ = window._all_tiles[0]

    assert tile._subtitle == "Primary Tool"


def test_dashboard_gif_toggle_pauses_and_restores_tile_animation(qapp, tmp_path):
    texture = tmp_path / "tile.gif"
    write_test_gif(texture)

    window = Dashboard(apps=[make_app("Animated", texture=str(texture))])
    qapp.processEvents()

    tile, _ = window._all_tiles[0]

    assert tile._texture_movie is not None
    assert tile._texture_movie.state() == QMovie.Running

    window._topbar._gif_toggle.click()
    qapp.processEvents()

    assert window._tile_gifs_enabled is False
    assert tile._texture_movie.state() == QMovie.Paused

    window._build(window._apps)
    qapp.processEvents()
    rebuilt_tile, _ = window._all_tiles[0]

    assert rebuilt_tile._texture_movie is not None
    assert rebuilt_tile._texture_movie.state() == QMovie.Paused

    window._topbar._gif_toggle.click()
    qapp.processEvents()

    assert window._tile_gifs_enabled is True
    assert rebuilt_tile._texture_movie.state() == QMovie.Running


def test_particle_bg_staggers_comet_delays(qapp):
    bg = ParticleBG()

    initial_delays = sorted(-comet["life"] for comet in bg._comets)

    assert len(bg._comets) == bg.COMET_COUNT
    assert initial_delays[1] - initial_delays[0] >= (bg.COMET_INITIAL_DELAY_STEP - bg.COMET_INITIAL_DELAY_JITTER[1])
    assert initial_delays[-1] - initial_delays[0] >= (bg.COMET_INITIAL_DELAY_STEP * (bg.COMET_COUNT - 1)) - bg.COMET_INITIAL_DELAY_JITTER[1]


def test_particle_bg_respawn_delay_grows_by_slot(qapp, monkeypatch):
    bg = ParticleBG()
    monkeypatch.setattr(ui.random, "randint", lambda start, end: 0)

    assert bg._comet_delay(0) == bg.COMET_RESPAWN_DELAY[0]
    assert bg._comet_delay(bg.COMET_COUNT - 1) == bg.COMET_RESPAWN_DELAY[0] + ((bg.COMET_COUNT - 1) * bg.COMET_SLOT_DELAY_STEP)


def test_dashboard_uses_board_spacing_constant():
    assert Dashboard.SECTION_SPACING == Tile.GAP * 2


def test_dashboard_places_groups_using_env_columns(qapp, monkeypatch):
    monkeypatch.setattr(
        ui,
        "load_dashboard_config",
        lambda group_names: {
            "board_rows": 2,
            "groups": {
                "One": {"row": 0, "col": 1},
                "Two": {"row": 1, "col": 1},
            },
        },
    )

    window = Dashboard(apps=[make_app("Alpha", group="One"), make_app("Beta", group="Two")])
    window.show()
    qapp.processEvents()

    positions = {spec["name"]: spec["container"].pos() for spec in window._group_specs}

    assert positions["One"].x() == positions["Two"].x()
    assert positions["One"].y() < positions["Two"].y()


def test_dashboard_uses_column_stacking_before_expanding_right(qapp, monkeypatch):
    monkeypatch.setattr(
        ui,
        "load_dashboard_config",
        lambda group_names: {
            "board_rows": 2,
            "groups": {name: {"row": -1, "col": -1} for name in group_names},
        },
    )

    apps = [
        make_app("One", group="IO", size=(1, 1)),
        make_app("Two", group="Pipeline", size=(1, 1)),
        make_app("Three", group="Media", size=(1, 1)),
        make_app("Four", group="Utility", size=(1, 1)),
    ]
    window = Dashboard(apps=apps)

    positions = {spec["name"]: (spec["container"].x(), spec["container"].y()) for spec in window._group_specs}

    assert positions["IO"][0] == positions["Pipeline"][0]
    assert positions["IO"][1] < positions["Pipeline"][1]
    assert positions["Media"][0] > positions["IO"][0]
    assert positions["Media"][0] == positions["Utility"][0]
    assert positions["Media"][1] < positions["Utility"][1]


def test_dashboard_resize_rebuild_keeps_groups_visible(qapp):
    window = Dashboard(apps=[make_app("Alpha", group="One"), make_app("Beta", group="Two")])
    window.show()
    qapp.processEvents()

    window.resize(1800, 1000)
    qapp.processEvents()

    assert any(not spec["container"].isHidden() for spec in window._group_specs)
    assert len(window._all_tiles) == 2


def test_dashboard_uses_configured_title(qapp, monkeypatch):
    monkeypatch.setattr(
        ui,
        "load_dashboard_config",
        lambda group_names: {
            "title": "Workbench",
            "title_background": "/tmp/title.gif",
            "board_rows": 2,
            "groups": {name: {"row": -1, "col": -1} for name in group_names},
        },
    )

    window = Dashboard(apps=[make_app("Alpha")])

    assert window.windowTitle() == "Workbench"
    assert window._topbar._title_media._title == "Workbench"
    assert window._topbar._title_media._background_path == "/tmp/title.gif"
