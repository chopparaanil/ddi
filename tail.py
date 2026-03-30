import random
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtGui import QColor, QPainter, QBrush, QLinearGradient, QPen, QFont, QMovie, QPixmap, QPainterPath
from PyQt5.QtWidgets import QFrame, QLabel, QMenu, QMessageBox


def build_launch_command(path, python_executable=None):
    if not path or not path.strip():
        raise ValueError("No command configured.")

    try:
        parts = shlex.split(path)
    except ValueError as exc:
        raise ValueError(f"Invalid launch command: {exc}") from exc

    if not parts:
        raise ValueError("No command configured.")

    python_executable = python_executable or sys.executable
    executable = parts[0]
    expanded = Path(executable).expanduser()
    looks_like_path = "/" in executable or executable.startswith(".") or executable.startswith("~")

    if expanded.suffix == ".py":
        if not expanded.exists():
            raise FileNotFoundError(f"Command not found: {expanded}")
        return [python_executable, str(expanded), *parts[1:]]

    if looks_like_path:
        if not expanded.exists():
            raise FileNotFoundError(f"Command not found: {expanded}")
        return [str(expanded), *parts[1:]]

    resolved = shutil.which(executable)
    if not resolved:
        raise FileNotFoundError(f"Command not found: {executable}")
    return [resolved, *parts[1:]]


def launch_path(path, popen=subprocess.Popen, python_executable=None):
    try:
        command = build_launch_command(path, python_executable=python_executable)
        popen(command)
    except (OSError, ValueError) as exc:
        return False, str(exc)
    return True, None


class RippleOverlay(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._r = 0
        self._cx = 0
        self._cy = 0
        self._a = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self.hide()

    def trigger(self, pos):
        self._cx, self._cy = pos.x(), pos.y()
        self._r = 0
        self._a = 0.32
        self._timer.start(14)
        self.show()

    def _step(self):
        self._r += 16
        self._a -= 0.022
        if self._a <= 0:
            self._timer.stop()
            self.hide()
        self.update()

    def paintEvent(self, _):
        if self._a <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._a)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(QPoint(self._cx, self._cy), self._r, self._r)
        painter.end()


def _clamp_color(color):
    bounded = QColor(color)
    if not bounded.isValid():
        bounded = QColor("#2D6FA3")
    return bounded


def _mix_channel(first, second, ratio):
    return int(first + (second - first) * ratio)


def mix_colors(first, second, ratio):
    left = _clamp_color(first)
    right = _clamp_color(second)
    return QColor(
        _mix_channel(left.red(), right.red(), ratio),
        _mix_channel(left.green(), right.green(), ratio),
        _mix_channel(left.blue(), right.blue(), ratio),
        _mix_channel(left.alpha(), right.alpha(), ratio),
    )


def mute_color(color):
    # Keep just enough tint so neutral tiles still relate to the animated palette.
    return mix_colors(color, QColor("#232A31"), 0.78)


INDIA_TZ = ZoneInfo("Asia/Kolkata")


def india_now():
    return datetime.now(INDIA_TZ)


class Tile(QFrame):
    BASE = 155
    GAP = 15

    def __init__(self, name, path=None, size=(1, 1), color="#FFFFFF", icon="", badge="", texture="", gif=None):
        super().__init__()
        self.path = path
        self._color = QColor(color)
        self._size = size
        self._icon = icon
        self._badge = badge
        self._hovered = False
        self._pressed = False
        self._shimmer = 0.0
        self._shimmer_timer = None
        self._ambient_timer = None
        self._texture_pixmap = None
        self._texture_movie = None

        tile_width = self.BASE * size[0] + self.GAP * (size[0] - 1)
        tile_height = self.BASE * size[1] + self.GAP * (size[1] - 1)
        self.setFixedSize(tile_width, tile_height)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover)
        self.setToolTip(name)

        self._ripple = RippleOverlay(self)
        self._ripple.setGeometry(0, 0, tile_width, tile_height)
        self._load_texture(texture or gif)

        if size[0] >= 2 or size[1] >= 2:
            self._ambient_timer = QTimer(self)
            self._ambient_timer.setInterval(random.randint(3500, 8000))
            self._ambient_timer.timeout.connect(self._start_shimmer)
            self._ambient_timer.start()

    def _load_texture(self, texture):
        if not texture:
            return

        texture_path = Path(texture).expanduser()
        if not texture_path.exists():
            return

        if texture_path.suffix.lower() == ".gif":
            movie = QMovie(str(texture_path))
            if movie.isValid():
                movie.frameChanged.connect(self.update)
                movie.start()
                self._texture_movie = movie
                return

        pixmap = QPixmap(str(texture_path))
        if not pixmap.isNull():
            self._texture_pixmap = pixmap

    def _current_texture(self):
        if self._texture_movie is not None:
            pixmap = self._texture_movie.currentPixmap()
            if not pixmap.isNull():
                return pixmap
        return self._texture_pixmap

    def _has_texture(self):
        pixmap = self._current_texture()
        return pixmap is not None and not pixmap.isNull()

    def _paint_background(self, painter, width, height, color):
        color = mute_color(_clamp_color(color))
        top_color = mix_colors(color, QColor("#58646D"), 0.12)
        bottom_color = mix_colors(color, QColor("#030507"), 0.38)
        accent_color = mix_colors(color, QColor("#C9D4DE"), 0.12)

        texture = self._current_texture()
        if texture is None or texture.isNull():
            fill = QLinearGradient(0, 0, width, height)
            fill.setColorAt(0, top_color)
            fill.setColorAt(0.50, color)
            fill.setColorAt(1, bottom_color)
            painter.fillRect(0, 0, width, height, QBrush(fill))
        else:
            scaled = texture.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            source_x = max(0, (scaled.width() - width) // 2)
            source_y = max(0, (scaled.height() - height) // 2)
            painter.drawPixmap(0, 0, scaled, source_x, source_y, width, height)

            overlay = QLinearGradient(0, 0, width, height)
            tinted = mix_colors(color, QColor("#C8D0D8"), 0.08)
            tinted.setAlpha(10)
            deep = QColor("#030507")
            deep.setAlpha(118)
            overlay.setColorAt(0, tinted)
            overlay.setColorAt(1, deep)
            painter.fillRect(0, 0, width, height, QBrush(overlay))

        sheen = QLinearGradient(0, 0, width, 0)
        sheen.setColorAt(0, QColor(255, 255, 255, 0))
        sheen.setColorAt(0.48, QColor(255, 255, 255, 2))
        sheen.setColorAt(0.58, QColor(255, 255, 255, 9))
        sheen.setColorAt(0.68, QColor(255, 255, 255, 3))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillRect(0, 0, width, height, QBrush(sheen))

        top_band = QLinearGradient(0, 0, width, 0)
        top_band.setColorAt(0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 28))
        top_band.setColorAt(1, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 4))
        painter.fillRect(0, 0, width, 2, QBrush(top_band))

        edge_shadow = QLinearGradient(0, 0, 0, height)
        edge_shadow.setColorAt(0, QColor(0, 0, 0, 14))
        edge_shadow.setColorAt(0.12, QColor(0, 0, 0, 0))
        edge_shadow.setColorAt(0.82, QColor(0, 0, 0, 0))
        edge_shadow.setColorAt(1, QColor(0, 0, 0, 72))
        painter.fillRect(0, 0, width, height, QBrush(edge_shadow))

    def _start_shimmer(self):
        self._shimmer = 0.0
        if self._shimmer_timer is None:
            self._shimmer_timer = QTimer(self)
            self._shimmer_timer.timeout.connect(self._shimmer_step)
        self._shimmer_timer.start(14)

    def _shimmer_step(self):
        self._shimmer += 0.045
        if self._shimmer >= 1.0 and self._shimmer_timer is not None:
            self._shimmer = 0.0
            self._shimmer_timer.stop()
        self.update()

    def _launch(self):
        ok, error = launch_path(self.path)
        if ok:
            return True

        QMessageBox.warning(self, "Launch Failed", f"Unable to open {self.toolTip()}.\n{error}")
        return False

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()
        rect = QRectF(0.5, 0.5, width - 1, height - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        painter.save()
        painter.setClipPath(path)

        color = QColor(self._color)
        if self._pressed:
            color = color.darker(125)
        elif self._hovered:
            color = color.lighter(118)
        self._paint_background(painter, width, height, color)

        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(255, 255, 255, 16))
        gradient.setColorAt(0.34, QColor(255, 255, 255, 2))
        gradient.setColorAt(1, QColor(0, 0, 0, 52))
        painter.fillRect(0, 0, width, height, QBrush(gradient))

        label_fade = QLinearGradient(0, height * 0.58, 0, height)
        label_fade.setColorAt(0, QColor(0, 0, 0, 0))
        label_fade.setColorAt(0.55, QColor(0, 0, 0, 52))
        label_fade.setColorAt(1, QColor(0, 0, 0, 148))
        painter.fillRect(0, 0, width, height, QBrush(label_fade))

        if self._shimmer > 0:
            beam_x = int(width * self._shimmer)
            shimmer_gradient = QLinearGradient(beam_x - 55, 0, beam_x + 25, 0)
            shimmer_gradient.setColorAt(0, QColor(255, 255, 255, 0))
            shimmer_gradient.setColorAt(0.5, QColor(255, 255, 255, 30))
            shimmer_gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.fillRect(0, 0, width, height, QBrush(shimmer_gradient))

        painter.restore()

        text_rect = QRectF(14, height - 31, width - 28, 24)
        name_font = QFont("Segoe UI Semilight", 11)
        name_font.setWeight(QFont.Light)
        painter.setFont(name_font)
        painter.setPen(QColor(0, 0, 0, 110))
        painter.drawText(text_rect.translated(0, 1), Qt.AlignVCenter | Qt.AlignLeft, self.toolTip())
        painter.setPen(QColor(242, 246, 249, 220))
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.toolTip())

        if self._badge:
            radius = 11
            badge_x = width - radius - 7
            badge_y = radius + 5
            painter.setBrush(QColor("#e81123"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(badge_x, badge_y), radius, radius)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(badge_x - radius, badge_y - radius, radius * 2, radius * 2), Qt.AlignCenter, self._badge)

        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 8, 8)

        painter.setPen(QPen(QColor(0, 0, 0, 48), 1))
        painter.drawRoundedRect(QRectF(1.5, 1.5, width - 3, height - 3), 7, 7)

        if self._hovered:
            painter.setPen(QPen(QColor(255, 255, 255, 58), 1))
            painter.drawRoundedRect(QRectF(1.5, 1.5, width - 3, height - 3), 7, 7)

        painter.end()

    def enterEvent(self, _):
        self._hovered = True
        self.update()

    def leaveEvent(self, _):
        self._hovered = False
        self._pressed = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self._ripple.trigger(event.pos())
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = False
            self.update()
            if self.rect().contains(event.pos()) and self.path:
                self._launch()
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        if self.path:
            menu.addAction("Open", self._launch)
        menu.addSeparator()
        menu.addAction("Pin to Start")
        menu.addAction("Unpin from Start")
        menu.exec_(event.globalPos())


class ClockTile(Tile):
    def __init__(self, name="Time", size=(2, 2), color="#2C3E50", texture=""):
        super().__init__(name=name, size=size, color=color, icon="", texture=texture)
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self.update)
        self._tick_timer.start(1000)

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()
        rect = QRectF(0.5, 0.5, width - 1, height - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        painter.save()
        painter.setClipPath(path)

        color = QColor(self._color)
        if self._pressed:
            color = color.darker(125)
        elif self._hovered:
            color = color.lighter(112)
        self._paint_background(painter, width, height, color)

        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(255, 255, 255, 16))
        gradient.setColorAt(0.34, QColor(255, 255, 255, 2))
        gradient.setColorAt(1, QColor(0, 0, 0, 52))
        painter.fillRect(0, 0, width, height, QBrush(gradient))

        label_fade = QLinearGradient(0, height * 0.58, 0, height)
        label_fade.setColorAt(0, QColor(0, 0, 0, 0))
        label_fade.setColorAt(0.55, QColor(0, 0, 0, 52))
        label_fade.setColorAt(1, QColor(0, 0, 0, 148))
        painter.fillRect(0, 0, width, height, QBrush(label_fade))

        painter.restore()

        now = india_now()
        hours_minutes = now.strftime("%H:%M")
        seconds = now.strftime("%S")
        compact = self._size == (1, 1)

        if compact:
            time_font = QFont("Segoe UI Light", 30)
            time_font.setWeight(QFont.Light)
            painter.setFont(time_font)
            painter.setPen(QColor(255, 255, 255))
            compact_rect = QRectF(10, 26, width - 20, 48)
            painter.drawText(compact_rect, Qt.AlignCenter, hours_minutes)

            meta_font = QFont("Segoe UI", 9)
            meta_font.setWeight(QFont.Light)
            painter.setFont(meta_font)
            painter.setPen(QColor(255, 255, 255, 150))
            painter.drawText(QRectF(10, 72, width - 20, 18), Qt.AlignCenter, f"{seconds}  IST")
        else:
            time_font_size = max(28, min(width, height) // 3)
            time_font = QFont("Segoe UI Light", time_font_size)
            time_font.setWeight(QFont.Light)
            painter.setFont(time_font)
            painter.setPen(QColor(255, 255, 255))
            metrics = painter.fontMetrics()
            time_width = metrics.horizontalAdvance(hours_minutes)
            time_height = metrics.height()
            text_x = (width - time_width) // 2
            text_y = int(height * 0.20)
            painter.drawText(text_x, text_y + time_height, hours_minutes)

            seconds_font = QFont("Segoe UI Light", max(14, time_font_size // 3))
            seconds_font.setWeight(QFont.Light)
            painter.setFont(seconds_font)
            painter.setPen(QColor(255, 255, 255, 160))
            second_metrics = painter.fontMetrics()
            seconds_width = second_metrics.horizontalAdvance(seconds)
            painter.drawText(text_x + time_width - seconds_width, text_y + time_height + second_metrics.height() + 2, seconds)

        painter.setPen(QColor(255, 255, 255))
        label_font = QFont("Segoe UI", 11)
        label_font.setWeight(QFont.Light)
        painter.setFont(label_font)
        margin = 9
        painter.drawText(QRectF(margin, height - 28, width - margin * 2, 24), Qt.AlignVCenter | Qt.AlignLeft, self.toolTip())

        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 8, 8)

        painter.setPen(QPen(QColor(0, 0, 0, 48), 1))
        painter.drawRoundedRect(QRectF(1.5, 1.5, width - 3, height - 3), 7, 7)

        if self._hovered:
            painter.setPen(QPen(QColor(255, 255, 255, 58), 1))
            painter.drawRoundedRect(QRectF(1.5, 1.5, width - 3, height - 3), 7, 7)

        painter.end()


class DateTile(Tile):
    def __init__(self, name="Date", size=(1, 2), color="#1A6B8A", texture=""):
        super().__init__(name=name, size=size, color=color, icon="", texture=texture)
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self.update)
        self._tick_timer.start(60_000)

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()
        rect = QRectF(0.5, 0.5, width - 1, height - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        painter.save()
        painter.setClipPath(path)

        color = QColor(self._color)
        if self._pressed:
            color = color.darker(125)
        elif self._hovered:
            color = color.lighter(112)
        self._paint_background(painter, width, height, color)

        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(255, 255, 255, 16))
        gradient.setColorAt(0.34, QColor(255, 255, 255, 2))
        gradient.setColorAt(1, QColor(0, 0, 0, 52))
        painter.fillRect(0, 0, width, height, QBrush(gradient))

        label_fade = QLinearGradient(0, height * 0.58, 0, height)
        label_fade.setColorAt(0, QColor(0, 0, 0, 0))
        label_fade.setColorAt(0.55, QColor(0, 0, 0, 52))
        label_fade.setColorAt(1, QColor(0, 0, 0, 148))
        painter.fillRect(0, 0, width, height, QBrush(label_fade))

        painter.restore()

        today = india_now()
        day_name = today.strftime("%a").upper()
        day_num = str(today.day)
        month_text = today.strftime("%b").upper()
        year_text = today.strftime("%Y")
        center_x = width // 2
        compact = self._size == (1, 1)

        if compact:
            month_font = QFont("Segoe UI", 10)
            month_font.setWeight(QFont.Light)
            month_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
            painter.setFont(month_font)
            painter.setPen(QColor(255, 255, 255, 170))
            painter.drawText(QRectF(10, 24, width - 20, 18), Qt.AlignCenter, month_text)

            day_font = QFont("Segoe UI Light", 42)
            day_font.setWeight(QFont.Light)
            painter.setFont(day_font)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(QRectF(10, 38, width - 20, 48), Qt.AlignCenter, day_num)

            meta_font = QFont("Segoe UI", 9)
            meta_font.setWeight(QFont.Light)
            painter.setFont(meta_font)
            painter.setPen(QColor(255, 255, 255, 150))
            painter.drawText(QRectF(10, 84, width - 20, 16), Qt.AlignCenter, f"{day_name} {year_text}")
        else:
            day_name_font = QFont("Segoe UI Light", max(12, width // 6))
            day_name_font.setWeight(QFont.Light)
            day_name_font.setLetterSpacing(QFont.AbsoluteSpacing, 3)
            painter.setFont(day_name_font)
            painter.setPen(QColor(255, 255, 255, 180))
            day_name_metrics = painter.fontMetrics()
            day_name_width = day_name_metrics.horizontalAdvance(day_name)
            painter.drawText(center_x - day_name_width // 2, int(height * 0.20) + day_name_metrics.ascent(), day_name)

            day_font_size = max(36, min(width, height) // 2)
            day_font = QFont("Segoe UI Light", day_font_size)
            day_font.setWeight(QFont.Light)
            painter.setFont(day_font)
            painter.setPen(QColor(255, 255, 255))
            day_metrics = painter.fontMetrics()
            day_width = day_metrics.horizontalAdvance(day_num)
            painter.drawText(center_x - day_width // 2, int(height * 0.25) + day_name_metrics.height() + day_metrics.ascent(), day_num)

            month_font = QFont("Segoe UI Light", max(10, width // 9))
            month_font.setWeight(QFont.Light)
            painter.setFont(month_font)
            painter.setPen(QColor(255, 255, 255, 160))
            month_metrics = painter.fontMetrics()
            month_year = f"{today.strftime('%B')} {year_text}"
            month_width = month_metrics.horizontalAdvance(month_year)
            painter.drawText(center_x - month_width // 2, int(height * 0.25) + day_name_metrics.height() + day_metrics.height() + month_metrics.ascent() + 4, month_year)

        painter.setPen(QColor(255, 255, 255))
        label_font = QFont("Segoe UI", 11)
        label_font.setWeight(QFont.Light)
        painter.setFont(label_font)
        margin = 9
        painter.drawText(QRectF(margin, height - 28, width - margin * 2, 24), Qt.AlignVCenter | Qt.AlignLeft, self.toolTip())

        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 8, 8)

        painter.setPen(QPen(QColor(0, 0, 0, 48), 1))
        painter.drawRoundedRect(QRectF(1.5, 1.5, width - 3, height - 3), 7, 7)

        if self._hovered:
            painter.setPen(QPen(QColor(255, 255, 255, 58), 1))
            painter.drawRoundedRect(QRectF(1.5, 1.5, width - 3, height - 3), 7, 7)

        painter.end()
