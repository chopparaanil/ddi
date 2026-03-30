import getpass
import random

from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QRadialGradient, QFont, QPen, QKeySequence
from PyQt5.QtWidgets import (
    QWidget,
    QGridLayout,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFrame,
    QSizePolicy,
)

from config import load_apps, load_dashboard_config
from layout import compute_board_layout, compute_compact_group_layout
from tail import Tile, ClockTile, DateTile


class HorizontalScrollArea(QScrollArea):
    def wheelEvent(self, event):
        horizontal_bar = self.horizontalScrollBar()
        pixel_delta = event.pixelDelta()
        angle_delta = event.angleDelta()

        movement = 0
        if not pixel_delta.isNull():
            movement = -pixel_delta.x() if pixel_delta.x() else -pixel_delta.y()
        elif not angle_delta.isNull():
            movement = -(angle_delta.x() if angle_delta.x() else angle_delta.y())

        if movement:
            horizontal_bar.setValue(horizontal_bar.value() + movement)
            event.accept()
            return

        super().wheelEvent(event)


class ParticleBG(QWidget):
    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._theme = {}
        self.set_theme(theme or {})
        self._pts = [
            {
                "x": random.random(),
                "y": random.random(),
                "r": random.uniform(1.2, 3.8),
                "vx": random.uniform(-0.00025, 0.00025),
                "vy": random.uniform(-0.00018, 0.00018),
                "a": random.uniform(0.04, 0.20),
            }
            for _ in range(60)
        ]
        timer = QTimer(self)
        timer.timeout.connect(self._step)
        timer.start(40)

    def set_theme(self, theme):
        self._theme = {
            "bg_start": theme.get("bg_start", "#08121C"),
            "bg_mid": theme.get("bg_mid", "#0D1822"),
            "bg_end": theme.get("bg_end", "#12324A"),
            "grid": theme.get("grid", "#1B3E57"),
            "glow_primary": theme.get("glow_primary", "#0E6BA8"),
            "glow_secondary": theme.get("glow_secondary", "#11806A"),
        }
        self.update()

    def _step(self):
        for point in self._pts:
            point["x"] = (point["x"] + point["vx"]) % 1.0
            point["y"] = (point["y"] + point["vy"]) % 1.0
        self.update()

    def paintEvent(self, _):
        width, height = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0, QColor(self._theme["bg_start"]))
        gradient.setColorAt(0.52, QColor(self._theme["bg_mid"]))
        gradient.setColorAt(1, QColor(self._theme["bg_end"]))
        painter.fillRect(0, 0, width, height, QBrush(gradient))

        glow_primary = QRadialGradient(width * 0.18, height * 0.18, width * 0.44)
        glow_primary.setColorAt(0, QColor(self._theme["glow_primary"] + "36"))
        glow_primary.setColorAt(0.55, QColor(self._theme["glow_primary"] + "10"))
        glow_primary.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(0, 0, width, height, QBrush(glow_primary))

        glow_secondary = QRadialGradient(width * 0.78, height * 0.76, width * 0.40)
        glow_secondary.setColorAt(0, QColor(self._theme["glow_secondary"] + "2C"))
        glow_secondary.setColorAt(0.55, QColor(self._theme["glow_secondary"] + "0D"))
        glow_secondary.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(0, 0, width, height, QBrush(glow_secondary))

        vignette = QLinearGradient(0, 0, 0, height)
        vignette.setColorAt(0, QColor(255, 255, 255, 6))
        vignette.setColorAt(0.22, QColor(255, 255, 255, 0))
        vignette.setColorAt(1, QColor(0, 0, 0, 96))
        painter.fillRect(0, 0, width, height, QBrush(vignette))

        grid_color = QColor(self._theme["grid"])
        painter.setPen(QPen(QColor(grid_color.red(), grid_color.green(), grid_color.blue(), 16), 1))
        for x_pos in range(0, width, 60):
            painter.drawLine(x_pos, 0, x_pos, height)
        for y_pos in range(0, height, 60):
            painter.drawLine(0, y_pos, width, y_pos)

        painter.setPen(QPen(QColor(grid_color.red(), grid_color.green(), grid_color.blue(), 7), 1))
        for offset in range(-height, width, 120):
            painter.drawLine(offset, 0, offset + height, height)

        for point in self._pts:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, int(point["a"] * 255)))
            painter.drawEllipse(QPoint(int(point["x"] * width), int(point["y"] * height)), int(point["r"]), int(point["r"]))

        painter.end()


class TopBar(QWidget):
    def __init__(self, title="IO", parent=None):
        super().__init__(parent)
        self.setFixedHeight(58)
        self.apply_theme({})

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(14)

        label = QLabel(title)
        font = QFont("Segoe UI Light", 28)
        font.setWeight(QFont.Light)
        label.setFont(font)
        label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(label)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search")
        self._search.setFixedWidth(200)
        self._search.setStyleSheet(
            """
            QLineEdit {
                background: rgba(255,255,255,0.09);
                border: 1px solid rgba(255,255,255,0.18);
                color: white; padding: 5px 12px; font-size: 12px;
                border-radius: 1px;
            }
            QLineEdit:focus {
                background: rgba(255,255,255,0.16);
                border: 1px solid rgba(255,255,255,0.45);
            }
            """
        )
        layout.addWidget(self._search)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(spacer)

        user_label = QLabel(getpass.getuser())
        user_label.setStyleSheet("color: rgba(255,255,255,0.70); font-size: 13px; margin-left: 10px; background: transparent;")
        layout.addWidget(user_label)

    def apply_theme(self, theme):
        topbar_fill = theme.get("topbar_fill", "rgba(3, 12, 19, 0.72)")
        self.setStyleSheet(
            f"background: {topbar_fill}; border-bottom: 1px solid rgba(255,255,255,0.09);"
        )

    def connect_search(self, callback):
        self._search.textChanged.connect(callback)


class GroupLabel(QLabel):
    HEIGHT = 30

    def __init__(self, text, color="#7FA8C7"):
        super().__init__(text)
        font = QFont("Segoe UI Semilight", 10)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 1.6)
        self.setFont(font)
        self.setFixedHeight(self.HEIGHT)
        self.setStyleSheet(
            f"color: {color}; background: transparent; padding-left: 2px; text-transform: uppercase;"
        )


class Dashboard(QWidget):
    SECTION_SPACING = Tile.GAP * 2
    H_MARGIN = 36
    TOP_MARGIN = 30
    BOTTOM_MARGIN = 6

    def __init__(self, apps=None):
        super().__init__()
        self._apps = load_apps() if apps is None else list(apps)
        self._current_filter = ""
        self._group_specs = []
        self._groups = []
        self._all_tiles = []
        self._tile_row_capacity = -1

        self.resize(1280, 768)
        self.setMinimumSize(900, 560)

        self._layout_config = load_dashboard_config(())
        self._bg = ParticleBG(self, theme=self._layout_config)
        self._bg.lower()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._topbar = TopBar("dot", parent=self)
        root.addWidget(self._topbar)

        self._scroll = HorizontalScrollArea()
        self._scroll.setStyleSheet(
            """
            QScrollArea { background: transparent; border: none; }
            QScrollBar:horizontal {
                background: rgba(10, 12, 14, 0.92);
                height: 18px;
                margin: 0 18px 0 18px;
                border: 1px solid rgba(139, 184, 216, 0.18);
            }
            QScrollBar::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(118, 128, 138, 0.92),
                    stop:1 rgba(71, 79, 88, 0.92));
                min-width: 120px;
                border: 1px solid rgba(255, 255, 255, 0.22);
            }
            QScrollBar::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(148, 158, 168, 0.98),
                    stop:1 rgba(86, 94, 102, 0.98));
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 18px;
                background: rgba(18, 20, 23, 0.96);
                border: none;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: rgba(255, 255, 255, 0.05);
            }
            """
        )
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setWidgetResizable(False)
        self._scroll.horizontalScrollBar().setSingleStep(Tile.BASE + Tile.GAP)

        self._inner = QWidget()
        self._inner.setStyleSheet("background: transparent;")
        self._scroll.setWidget(self._inner)
        root.addWidget(self._scroll)

        self._build(self._apps)
        self._topbar.connect_search(self._filter)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._bg.setGeometry(0, 0, self.width(), self.height())

        tile_rows = self._available_tile_rows()
        if tile_rows != self._tile_row_capacity:
            self._build(self._apps)
        else:
            self._arrange_groups()

    def _group_apps(self, apps):
        groups = {}
        for app in apps:
            groups.setdefault(app.get("group", "Apps"), []).append(app)
        return groups

    def _available_tile_rows(self):
        viewport_height = max(0, self._scroll.viewport().height())
        usable_height = viewport_height - self.TOP_MARGIN - self.BOTTOM_MARGIN
        tile_area = usable_height - GroupLabel.HEIGHT - Tile.GAP
        return max(1, int((tile_area + Tile.GAP) // (Tile.BASE + Tile.GAP)))

    def _clear_board(self):
        for spec in self._group_specs:
            spec["container"].deleteLater()
        self._group_specs = []
        self._groups = []
        self._all_tiles = []

    def _update_inner_size(self, width, height):
        viewport_width = self._scroll.viewport().width()
        viewport_height = self._scroll.viewport().height()
        self._inner.resize(max(width, viewport_width), max(height, viewport_height))
        self._inner.setMinimumSize(max(width, viewport_width), max(height, viewport_height))

    def _filter(self, text):
        self._current_filter = text
        query = text.strip().lower()
        for spec in self._group_specs:
            visible = 0
            for tile, name in spec["tiles"]:
                matched = not query or query in name.lower()
                tile.setHidden(not matched)
                if matched:
                    visible += 1
            spec["container"].setHidden(visible == 0)
        self._arrange_groups()

    def _build_group(self, group_name, group_apps, max_tile_rows, group_position):
        items, total_rows, used_cols = compute_compact_group_layout(group_apps, max_rows=max_tile_rows, max_cols=10)

        container = QWidget(self._inner)
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Tile.GAP)

        label = GroupLabel(group_name.upper(), color=self._layout_config.get("label_color", "#7FA8C7"))
        layout.addWidget(label)

        grid = QGridLayout()
        grid.setSpacing(Tile.GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.addLayout(grid)

        tiles = []
        for item in items:
            app = item["app"]
            app_type = app.get("type", "").lower()
            if app_type == "clock":
                tile = ClockTile(name=app["name"], size=app["size"], color=app["color"], texture=app.get("texture", ""))
            elif app_type == "date":
                tile = DateTile(name=app["name"], size=app["size"], color=app["color"], texture=app.get("texture", ""))
            else:
                tile = Tile(
                    name=app["name"],
                    path=app.get("path"),
                    size=app["size"],
                    color=app["color"],
                    icon=app.get("icon", ""),
                    badge=app.get("badge", ""),
                    texture=app.get("texture", ""),
                )
            tiles.append((tile, app["name"]))
            self._all_tiles.append((tile, app["name"]))
            grid.addWidget(tile, item["row"], item["col"], item["row_span"], item["col_span"])

        for row in range(total_rows):
            for col in range(used_cols):
                if grid.itemAtPosition(row, col) is not None:
                    continue
                spacer = QWidget()
                spacer.setFixedSize(Tile.BASE, Tile.BASE)
                spacer.setStyleSheet("background: transparent;")
                grid.addWidget(spacer, row, col)

        group_width = used_cols * Tile.BASE + max(0, used_cols - 1) * Tile.GAP
        group_height = GroupLabel.HEIGHT + Tile.GAP + total_rows * Tile.BASE + max(0, total_rows - 1) * Tile.GAP
        container.setFixedSize(group_width, group_height)
        container.adjustSize()
        return {
            "name": group_name,
            "container": container,
            "tiles": tiles,
            "width": group_width,
            "height": group_height,
            "board_row": group_position.get("row", -1),
            "board_col": group_position.get("col", -1),
        }

    def _populate_groups(self):
        self._clear_board()
        grouped_apps = self._group_apps(self._apps)
        self._layout_config = load_dashboard_config(grouped_apps.keys())
        self._bg.set_theme(self._layout_config)
        self._topbar.apply_theme(self._layout_config)
        self._tile_row_capacity = self._available_tile_rows()

        for group_name, group_apps in grouped_apps.items():
            position = self._layout_config["groups"].get(group_name, {"row": -1, "col": -1})
            spec = self._build_group(group_name, group_apps, self._tile_row_capacity, position)
            self._group_specs.append(spec)
            self._groups.append((spec["container"], spec["tiles"]))

    def _arrange_groups(self):
        visible_specs = [
            spec for spec in self._group_specs if any(not tile.isHidden() for tile, _ in spec["tiles"])
        ]
        if visible_specs:
            available_height = max(0, self._scroll.viewport().height() - self.TOP_MARGIN - self.BOTTOM_MARGIN)
            placements, board_height, board_width = compute_board_layout(
                visible_specs,
                rows=self._layout_config.get("board_rows", 2),
                gap=self.SECTION_SPACING,
                max_height=available_height,
            )
        else:
            placements, board_height, board_width = [], 0, 0

        for spec in self._group_specs:
            spec["container"].hide()

        for item in placements:
            container = item["container"]
            container.move(self.H_MARGIN + item["x"], self.TOP_MARGIN + item["y"])
            container.show()

        total_width = self.H_MARGIN * 2 + board_width
        total_height = self.TOP_MARGIN + self.BOTTOM_MARGIN + board_height
        self._update_inner_size(total_width, total_height)

    def _build(self, apps):
        self._apps = list(apps)
        self._populate_groups()
        if self._current_filter:
            self._filter(self._current_filter)
        else:
            self._arrange_groups()
