from PyQt5.QtCore import QPoint, QPointF, Qt
from PyQt5.QtGui import QColor, QPixmap, QWheelEvent
from PyQt5.QtWidgets import QWidget

import ui
from tail import Tile
from ui import Dashboard, HorizontalScrollArea


def make_app(name, group="Apps", row=-1, col=-1, size=(1, 1), app_type="", texture=""):
    return {
        "name": name,
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
