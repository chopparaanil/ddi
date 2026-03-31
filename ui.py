import getpass
import math
import os
import random
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QRadialGradient, QFont, QPen, QMovie, QPixmap, QPainterPath
from PyQt5.QtWidgets import (
    QWidget,
    QGridLayout,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFrame,
    QPushButton,
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
    COMET_COUNT = 10
    COMET_MIN_Y = -0.20
    COMET_MAX_Y = 0.32
    COMET_INITIAL_DELAY_STEP = 10
    COMET_INITIAL_DELAY_JITTER = (0, 4)
    COMET_RESPAWN_DELAY = (28, 54)
    COMET_SLOT_DELAY_STEP = 8

    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._theme = {}
        self.set_theme(theme or {})
        self._stars_far = [
            {
                "x": random.random(),
                "y": random.random(),
                "r": random.uniform(0.8, 1.8),
                "vx": random.uniform(-0.00003, 0.00003),
                "vy": random.uniform(-0.00002, 0.00002),
                "a": random.uniform(0.08, 0.28),
            }
            for _ in range(95)
        ]
        self._stars_near = [
            {
                "x": random.random(),
                "y": random.random(),
                "r": random.uniform(1.2, 2.8),
                "vx": random.uniform(-0.00008, 0.00008),
                "vy": random.uniform(-0.00006, 0.00006),
                "a": random.uniform(0.10, 0.40),
            }
            for _ in range(42)
        ]
        self._comets = [
            self._random_comet(slot=index, delay_frames=self._comet_delay(index, initial=True))
            for index in range(self.COMET_COUNT)
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

    def _comet_delay(self, slot, initial=False):
        slot_index = max(0, int(slot or 0))
        if initial:
            return (slot_index * self.COMET_INITIAL_DELAY_STEP) + random.randint(*self.COMET_INITIAL_DELAY_JITTER)

        base_delay, extra_delay = self.COMET_RESPAWN_DELAY
        return base_delay + (slot_index * self.COMET_SLOT_DELAY_STEP) + random.randint(0, extra_delay)

    def _random_comet(self, slot=None, delay_frames=0):
        band_height = (self.COMET_MAX_Y - self.COMET_MIN_Y) / max(1, self.COMET_COUNT)
        if slot is None:
            y = random.uniform(self.COMET_MIN_Y, self.COMET_MAX_Y)
        else:
            band_start = self.COMET_MIN_Y + band_height * slot
            y = random.uniform(band_start + band_height * 0.15, band_start + band_height * 0.85)

        return {
            "slot": slot,
            "x": random.uniform(-0.26, 0.02),
            "y": y,
            "vx": random.uniform(0.0013, 0.0022),
            "vy": random.uniform(0.0010, 0.0017),
            "curve": random.uniform(0.000006, 0.000020),
            "curve_dir": random.choice((-1, 1)),
            "tail": random.uniform(0.11, 0.19),
            "a": random.uniform(0.34, 0.52),
            "life": -delay_frames,
            "ttl": random.randint(150, 240),
            "phase": random.uniform(0.0, math.tau),
        }

    def _step(self):
        for point in self._stars_far:
            point["x"] = (point["x"] + point["vx"]) % 1.0
            point["y"] = (point["y"] + point["vy"]) % 1.0
        for point in self._stars_near:
            point["x"] = (point["x"] + point["vx"]) % 1.0
            point["y"] = (point["y"] + point["vy"]) % 1.0
        for comet in self._comets:
            if comet["life"] < 0:
                comet["life"] += 1
                continue
            comet["life"] += 1
            comet["x"] += comet["vx"]
            comet["y"] += comet["vy"] + math.sin(comet["phase"] + comet["life"] * 0.035) * comet["curve"] * comet["curve_dir"]
            if (
                comet["life"] >= comet["ttl"]
                or comet["x"] - comet["tail"] > 1.08
                or comet["y"] > 1.06
                or comet["x"] < -0.30
            ):
                comet.update(
                    self._random_comet(
                        slot=comet.get("slot"),
                        delay_frames=self._comet_delay(comet.get("slot")),
                    )
                )
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

        grid_color = QColor(self._theme["grid"])
        painter.setPen(QPen(QColor(grid_color.red(), grid_color.green(), grid_color.blue(), 8), 1))
        for x_pos in range(0, width, 72):
            painter.drawLine(x_pos, 0, x_pos, height)
        for y_pos in range(0, height, 72):
            painter.drawLine(0, y_pos, width, y_pos)

        for point in self._stars_far:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, int(point["a"] * 255)))
            painter.drawEllipse(QPoint(int(point["x"] * width), int(point["y"] * height)), int(point["r"]), int(point["r"]))

        for point in self._stars_near:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(220, 236, 255, int(point["a"] * 255)))
            painter.drawEllipse(QPoint(int(point["x"] * width), int(point["y"] * height)), int(point["r"]), int(point["r"]))

        for comet in self._comets:
            if comet["life"] < 0:
                continue

            progress = max(0.0, min(1.0, comet["life"] / comet["ttl"]))
            fade = math.sin(progress * math.pi)
            if fade <= 0.03:
                continue

            head_x = comet["x"] * width
            head_y = comet["y"] * height
            tail_dx = comet["tail"] * width
            slope = comet["vy"] / max(comet["vx"], 0.0001)
            tail_dy = tail_dx * slope

            comet_tail = QLinearGradient(head_x - tail_dx, head_y - tail_dy, head_x, head_y)
            comet_tail.setColorAt(0, QColor(255, 255, 255, 0))
            comet_tail.setColorAt(0.55, QColor(186, 222, 255, min(255, int(comet["a"] * fade * 180))))
            comet_tail.setColorAt(1, QColor(255, 255, 255, min(255, int(comet["a"] * fade * 320))))
            painter.setPen(QPen(QBrush(comet_tail), 2))
            painter.drawLine(int(head_x - tail_dx), int(head_y - tail_dy), int(head_x), int(head_y))

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(244, 249, 255, min(255, int(comet["a"] * fade * 560))))
            painter.drawEllipse(QPoint(int(head_x), int(head_y)), 2, 2)

        vignette = QLinearGradient(0, 0, 0, height)
        vignette.setColorAt(0, QColor(255, 255, 255, 4))
        vignette.setColorAt(0.24, QColor(255, 255, 255, 0))
        vignette.setColorAt(1, QColor(0, 0, 0, 126))
        painter.fillRect(0, 0, width, height, QBrush(vignette))

        painter.end()


class TitleMedia(QWidget):
    def __init__(self, title="IO", background_path="", parent=None):
        super().__init__(parent)
        self._title = title
        self._background_path = ""
        self._pixmap = None
        self._movie = None
        self._sync_width()
        self.set_background(background_path)

    def set_title(self, title):
        self._title = title
        self._sync_width()
        self.update()

    def _sync_width(self):
        self.setFixedSize(max(180, 36 + len(self._title) * 17), 42)

    def set_background(self, background_path):
        self._background_path = background_path or ""
        self._pixmap = None
        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()
            self._movie = None

        if not self._background_path:
            self.update()
            return

        path = Path(self._background_path).expanduser()
        if not path.exists():
            self.update()
            return

        if path.suffix.lower() == ".gif":
            if os.getenv("QT_QPA_PLATFORM", "").lower() == "offscreen":
                self.update()
                return
            movie = QMovie(str(path), b"", self)
            if movie.isValid():
                movie.frameChanged.connect(self.update)
                movie.start()
                self._movie = movie
                self.update()
                return

        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            self._pixmap = pixmap
        self.update()

    def _current_pixmap(self):
        if self._movie is not None:
            pixmap = self._movie.currentPixmap()
            if not pixmap.isNull():
                return pixmap
        return self._pixmap

    def paintEvent(self, _):
        width, height = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0.5, 0.5, width - 1, height - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        painter.save()
        painter.setClipPath(path)

        pixmap = self._current_pixmap()
        if pixmap is not None and not pixmap.isNull():
            scaled = pixmap.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            source_x = max(0, (scaled.width() - width) // 2)
            source_y = max(0, (scaled.height() - height) // 2)
            painter.drawPixmap(0, 0, scaled, source_x, source_y, width, height)
        else:
            fill = QLinearGradient(0, 0, width, height)
            fill.setColorAt(0, QColor(10, 18, 28, 210))
            fill.setColorAt(1, QColor(22, 34, 44, 190))
            painter.fillRect(0, 0, width, height, QBrush(fill))

        overlay = QLinearGradient(0, 0, width, height)
        overlay.setColorAt(0, QColor(8, 12, 16, 38))
        overlay.setColorAt(1, QColor(4, 6, 10, 122))
        painter.fillRect(0, 0, width, height, QBrush(overlay))
        painter.restore()

        painter.setBrush(QColor(255, 255, 255, 18))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(10, 10, 4, height - 20), 2, 2)

        font = QFont("Segoe UI Light", 24)
        font.setWeight(QFont.Light)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        painter.setFont(font)
        text_rect = QRectF(18, 0, width - 28, height)
        painter.setPen(QColor(0, 0, 0, 90))
        painter.drawText(text_rect.translated(0, 1), Qt.AlignVCenter | Qt.AlignLeft, self._title)
        painter.setPen(QColor(245, 248, 251, 242))
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._title)

        painter.setPen(QPen(QColor(255, 255, 255, 24), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 14, 14)
        painter.end()


class TopBar(QWidget):
    def __init__(self, title="IO", parent=None):
        super().__init__(parent)
        self.setFixedHeight(58)
        self.apply_theme({})

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(14)

        self._title_media = TitleMedia(title, parent=self)
        layout.addWidget(self._title_media)

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

        self._user_label = QLabel(getpass.getuser())
        self._user_label.setStyleSheet("color: rgba(255,255,255,0.70); font-size: 13px; margin-left: 10px; background: transparent;")
        layout.addWidget(self._user_label)

        self._gif_toggle = QPushButton("GIF")
        self._gif_toggle.setCheckable(True)
        self._gif_toggle.setChecked(True)
        self._gif_toggle.setFixedSize(44, 24)
        self._gif_toggle.setCursor(Qt.PointingHandCursor)
        self._gif_toggle.setToolTip("Toggle animated tile GIFs")
        self._gif_toggle.setStyleSheet(
            """
            QPushButton {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.18);
                color: rgba(255,255,255,0.86);
                font-size: 10px;
                font-weight: 600;
                border-radius: 12px;
                padding: 0 8px;
            }
            QPushButton:checked {
                background: rgba(126,186,227,0.24);
                border: 1px solid rgba(186,226,255,0.44);
                color: white;
            }
            QPushButton:hover {
                border: 1px solid rgba(255,255,255,0.32);
            }
            """
        )
        layout.addWidget(self._gif_toggle)

    def apply_theme(self, theme):
        topbar_fill = theme.get("topbar_fill", "rgba(3, 12, 19, 0.72)")
        self.setStyleSheet(
            f"background: {topbar_fill}; border-bottom: 1px solid rgba(255,255,255,0.09);"
        )

    def connect_search(self, callback):
        self._search.textChanged.connect(callback)

    def connect_gif_toggle(self, callback):
        self._gif_toggle.toggled.connect(callback)

    def set_title(self, title):
        self._title_media.set_title(title)

    def set_title_background(self, background_path):
        self._title_media.set_background(background_path)

    def set_gif_toggle_state(self, enabled):
        self._gif_toggle.setChecked(bool(enabled))


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
        self._tile_gifs_enabled = True
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

        self._topbar = TopBar("D O T", parent=self)
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
        self._topbar.connect_gif_toggle(self._set_tile_gifs_enabled)

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

    def _set_tile_gifs_enabled(self, enabled):
        self._tile_gifs_enabled = bool(enabled)
        for tile, _ in self._all_tiles:
            tile.set_animated_texture(self._tile_gifs_enabled)

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
                tile = ClockTile(
                    name=app["name"],
                    size=app["size"],
                    color=app["color"],
                    texture=app.get("texture", ""),
                    subtitle=app.get("subtitle", ""),
                    texture_mode=app.get("texture_mode", "cover"),
                )
            elif app_type == "date":
                tile = DateTile(
                    name=app["name"],
                    size=app["size"],
                    color=app["color"],
                    texture=app.get("texture", ""),
                    subtitle=app.get("subtitle", ""),
                    texture_mode=app.get("texture_mode", "cover"),
                )
            else:
                tile = Tile(
                    name=app["name"],
                    subtitle=app.get("subtitle", ""),
                    path=app.get("path"),
                    size=app["size"],
                    color=app["color"],
                    icon=app.get("icon", ""),
                    badge=app.get("badge", ""),
                    texture=app.get("texture", ""),
                    texture_mode=app.get("texture_mode", "cover"),
                )
            tile.set_animated_texture(self._tile_gifs_enabled)
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
        self._topbar.set_gif_toggle_state(self._tile_gifs_enabled)
        title = self._layout_config.get("title", "D O T")
        self._topbar.set_title(title)
        self._topbar.set_title_background(self._layout_config.get("title_background", ""))
        self.setWindowTitle(title)
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
