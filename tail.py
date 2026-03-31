import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF, QVariantAnimation
from PyQt5.QtGui import QColor, QPainter, QBrush, QLinearGradient, QRadialGradient, QPen, QFont, QFontDatabase, QFontMetrics, QMovie, QPixmap, QPainterPath
from PyQt5.QtWidgets import QFrame, QMenu, QMessageBox


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
    return mix_colors(color, QColor("#232A31"), 0.78)


TITLE_FONT_FAMILIES = (
    "Bebas Neue",
    "Oswald",
    "Archivo Narrow",
    "Liberation Sans Narrow",
    "Arial Narrow",
    "Nimbus Sans Narrow",
    "DejaVu Sans Condensed",
    "Helvetica Neue",
    "Impact",
)
_TITLE_FONT_FAMILY = None


def title_font_family():
    global _TITLE_FONT_FAMILY
    if _TITLE_FONT_FAMILY is not None:
        return _TITLE_FONT_FAMILY

    available = set(QFontDatabase().families())
    for family in TITLE_FONT_FAMILIES:
        if family in available:
            _TITLE_FONT_FAMILY = family
            return family

    _TITLE_FONT_FAMILY = "DejaVu Sans Condensed"
    return _TITLE_FONT_FAMILY


INDIA_TZ = ZoneInfo("Asia/Kolkata")


def india_now():
    return datetime.now(INDIA_TZ)


class Tile(QFrame):
    BASE = 155
    GAP = 15
    BORDER_RADIUS = 18
    HOVER_SCALE_GAIN = 0.025

    def __init__(self, name="", path=None, size=(1, 1), color="#FFFFFF", icon="", badge="", texture="", gif=None, subtitle="", texture_mode="cover"):
        super().__init__()
        self.path = path
        self._color = QColor(color)
        self._size = size
        self._icon = icon
        self._badge = badge
        self._hovered = False
        self._pressed = False
        self._texture_pixmap = None
        self._texture_movie = None
        self._textures_animated = True
        self._texture_mode = texture_mode if texture_mode in {"cover", "contain"} else "cover"
        self._name = name or ""
        self._subtitle = subtitle or ""
        self._hover_progress = 0.0

        tile_width = self.BASE * size[0] + self.GAP * (size[0] - 1)
        tile_height = self.BASE * size[1] + self.GAP * (size[1] - 1)
        self.setFixedSize(tile_width, tile_height)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover)

        self._ripple = RippleOverlay(self)
        self._ripple.setGeometry(self.rect())
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(120)
        self._hover_anim.setStartValue(0.0)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.valueChanged.connect(self._set_hover_progress)
        self._load_texture(texture or gif)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._ripple.setGeometry(self.rect())
        self._ripple.raise_()

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

    def set_animated_texture(self, enabled):
        self._textures_animated = bool(enabled)
        if self._texture_movie is not None:
            self._texture_movie.setPaused(not self._textures_animated)
        self.update()

    def _tile_rect(self):
        return QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)

    def _set_hover_progress(self, value):
        self._hover_progress = float(value)
        self.update()

    def _start_hover_animation(self, target):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(float(target))
        self._hover_anim.start()

    def _tile_path(self, rect):
        path = QPainterPath()
        path.addRoundedRect(rect, self.BORDER_RADIUS, self.BORDER_RADIUS)
        return path

    def _display_color(self):
        color = _clamp_color(self._color)
        if self._pressed:
            return color.darker(128)
        if self._hovered:
            return color.lighter(114)
        return color

    def _marker_text(self):
        icon = str(self._icon or "").strip()
        if icon and len(icon) <= 3:
            return icon.upper()

        tokens = [token for token in self._name.replace("_", " ").split() if token]
        if not tokens:
            return "APP"
        return "".join(token[0] for token in tokens[:2]).upper()

    def _elided_text(self, painter, text, max_width):
        return painter.fontMetrics().elidedText(text, Qt.ElideRight, max(20, int(max_width)))

    def _title_line_candidates(self, title):
        words = [word for word in title.split() if word]
        if len(words) <= 1:
            return [[title]]

        candidates = []
        for split_at in range(1, len(words)):
            candidates.append([" ".join(words[:split_at]), " ".join(words[split_at:])])
        return candidates

    def _line_spacing_plan(self, font, lines):
        metrics = QFontMetrics(font)
        widths = [metrics.horizontalAdvance(line) for line in lines]
        target_width = max(widths, default=0)
        spacings = [font.letterSpacing()] * len(lines)
        return spacings, widths, target_width

    def _fit_title_layout(self, title, max_width):
        title = title.upper()
        compact_length = max(1, len(title.replace(" ", "")))
        base_spacing = 2 if compact_length <= 4 else 1 if compact_length <= 8 else 0
        base_font_size = 20 if len(title.split()) == 1 else 18
        multiline_candidates = self._title_line_candidates(title)
        prefer_multiline = len(title.split()) > 1

        for spacing in range(base_spacing, -1, -1):
            for font_size in range(base_font_size, 8, -1):
                candidate_font = QFont(title_font_family(), font_size)
                candidate_font.setWeight(QFont.Black)
                candidate_font.setBold(True)
                candidate_font.setStretch(75)
                candidate_font.setStyleStrategy(QFont.PreferAntialias)
                candidate_font.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
                metrics = QFontMetrics(candidate_font)

                best_layout = None
                layouts = multiline_candidates if prefer_multiline else [[title]]
                for lines in layouts:
                    widths = [metrics.horizontalAdvance(line) for line in lines]
                    if max(widths) > max_width:
                        continue

                    width_delta = abs(widths[0] - widths[-1]) if len(widths) == 2 else widths[0]
                    score = (width_delta, max(widths))
                    if best_layout is None or score < best_layout["score"]:
                        line_spacings, adjusted_widths, target_width = self._line_spacing_plan(candidate_font, lines)
                        best_layout = {
                            "font": candidate_font,
                            "lines": lines,
                            "max_width": target_width,
                            "line_spacings": line_spacings,
                            "line_widths": adjusted_widths,
                            "score": score,
                        }

                if best_layout is not None:
                    return best_layout

                if prefer_multiline and metrics.horizontalAdvance(title) <= max_width:
                    line_spacings, adjusted_widths, target_width = self._line_spacing_plan(candidate_font, [title])
                    return {
                        "font": candidate_font,
                        "lines": [title],
                        "max_width": target_width,
                        "line_spacings": line_spacings,
                        "line_widths": adjusted_widths,
                    }

        fallback_font = QFont(title_font_family(), 8)
        fallback_font.setWeight(QFont.Black)
        fallback_font.setBold(True)
        fallback_font.setStretch(75)
        fallback_font.setStyleStrategy(QFont.PreferAntialias)
        fallback_font.setLetterSpacing(QFont.AbsoluteSpacing, 0)
        metrics = QFontMetrics(fallback_font)
        fallback_lines = multiline_candidates[-1] if prefer_multiline else [title]
        fitted_lines = [metrics.elidedText(line, Qt.ElideRight, int(max_width)) for line in fallback_lines]
        line_spacings, adjusted_widths, max_line_width = self._line_spacing_plan(fallback_font, fitted_lines)
        return {
            "font": fallback_font,
            "lines": fitted_lines,
            "max_width": max_line_width,
            "line_spacings": line_spacings,
            "line_widths": adjusted_widths,
        }

    def _paint_background(self, painter, rect, color):
        width = int(rect.width())
        height = int(rect.height())
        base = mute_color(_clamp_color(color))
        top_color = mix_colors(base, QColor("#95B6CF"), 0.18)
        bottom_color = mix_colors(base, QColor("#020406"), 0.52)
        accent_color = mix_colors(base, QColor("#E4EEF6"), 0.22)

        texture = self._current_texture()
        if texture is None or texture.isNull():
            fill = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
            fill.setColorAt(0, top_color)
            fill.setColorAt(0.48, base)
            fill.setColorAt(1, bottom_color)
            painter.fillRect(rect, QBrush(fill))
        else:
            fill = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
            fill.setColorAt(0, top_color)
            fill.setColorAt(0.48, base)
            fill.setColorAt(1, bottom_color)
            painter.fillRect(rect, QBrush(fill))

            aspect_mode = Qt.KeepAspectRatio if self._texture_mode == "contain" else Qt.KeepAspectRatioByExpanding
            scaled = texture.scaled(width, height, aspect_mode, Qt.SmoothTransformation)
            draw_x = rect.left() + (width - scaled.width()) / 2
            draw_y = rect.top() + (height - scaled.height()) / 2
            painter.drawPixmap(int(draw_x), int(draw_y), scaled)

            texture_overlay = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
            bright_tint = mix_colors(base, QColor("#D9E8F4"), 0.14)
            bright_tint.setAlpha(34)
            deep_shadow = QColor("#020406")
            deep_shadow.setAlpha(146)
            texture_overlay.setColorAt(0, bright_tint)
            texture_overlay.setColorAt(1, deep_shadow)
            painter.fillRect(rect, QBrush(texture_overlay))

        top_glow = QRadialGradient(rect.left() + width * 0.22, rect.top() + height * 0.16, max(width, height) * 0.55)
        top_glow.setColorAt(0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 72))
        top_glow.setColorAt(0.45, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 22))
        top_glow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(rect, QBrush(top_glow))

        horizon_glow = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        horizon_glow.setColorAt(0, QColor(255, 255, 255, 26))
        horizon_glow.setColorAt(0.35, QColor(255, 255, 255, 3))
        horizon_glow.setColorAt(1, QColor(0, 0, 0, 86))
        painter.fillRect(rect, QBrush(horizon_glow))

        painter.setPen(QPen(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 11), 1))
        for offset in range(-height, width, 26):
            painter.drawLine(int(rect.left()) + offset, int(rect.top()), int(rect.left()) + offset + height, int(rect.bottom()))

        top_band = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top())
        top_band.setColorAt(0, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 58))
        top_band.setColorAt(1, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 6))
        painter.fillRect(QRectF(rect.left(), rect.top(), rect.width(), 3), QBrush(top_band))

    def _paint_shell(self, painter):
        rect = self._tile_rect()
        painter.save()
        painter.setClipPath(self._tile_path(rect))
        self._paint_background(painter, rect, self._display_color())
        painter.restore()
        return rect

    def _draw_marker_chip(self, painter):
        text = self._marker_text()
        chip_width = max(48, 22 + (len(text) * 10))
        chip_rect = QRectF(14, 14, chip_width, 24)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(6, 10, 13, 138 if self._hovered else 118))
        painter.drawRoundedRect(chip_rect, 12, 12)

        accent = mix_colors(self._display_color(), QColor("#EDF7FF"), 0.35)
        painter.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 220))
        painter.drawRoundedRect(QRectF(chip_rect.left() + 7, chip_rect.top() + 5, 4, chip_rect.height() - 10), 2, 2)

        font = QFont("Segoe UI", 9)
        font.setWeight(QFont.DemiBold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 1.1)
        painter.setFont(font)
        painter.setPen(QColor(237, 245, 251, 220))
        painter.drawText(chip_rect.adjusted(16, 0, -10, 0), Qt.AlignVCenter | Qt.AlignLeft, text)

    def _draw_standard_content(self, painter):
        title = (self._name or "App").strip()
        subtitle = str(self._subtitle or "").strip().upper()
        subtitle_font = QFont("Segoe UI", 8)
        subtitle_font.setWeight(QFont.DemiBold)
        subtitle_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        subtitle_metrics = QFontMetrics(subtitle_font)

        banner_left = 12
        content_left_inset = 20
        content_right_inset = 12
        inner_text_width = self.width() - banner_left - content_left_inset - content_right_inset
        subtitle_label = subtitle_metrics.elidedText(subtitle, Qt.ElideRight, max(28, inner_text_width)) if subtitle else ""
        subtitle_width = subtitle_metrics.horizontalAdvance(subtitle_label) if subtitle_label else 0
        layout = self._fit_title_layout(title, max(42, inner_text_width))
        fitted_font = layout["font"]
        fitted_lines = layout["lines"]
        line_spacings = layout.get("line_spacings", [fitted_font.letterSpacing()] * len(fitted_lines))
        metrics = QFontMetrics(fitted_font)
        line_gap = 2 if len(fitted_lines) > 1 else 0
        subtitle_gap = 3 if subtitle else 0
        text_height = (metrics.height() * len(fitted_lines)) + (line_gap * max(0, len(fitted_lines) - 1))
        content_height = (subtitle_metrics.height() if subtitle else 0) + subtitle_gap + text_height
        banner_height = content_height + 10
        content_width = max(layout["max_width"], subtitle_width)
        banner_width = min(self.width() - 12, content_width + content_left_inset + content_right_inset)
        banner_top = self.height() - banner_height - 14
        banner_rect = QRectF(banner_left, banner_top, banner_width, banner_height)
        title_rect = banner_rect.adjusted(content_left_inset, 5, -content_right_inset, -5)
        actual_text_width = title_rect.width()

        if max(layout["max_width"], subtitle_width) > actual_text_width:
            layout = self._fit_title_layout(title, actual_text_width)
            fitted_font = layout["font"]
            fitted_lines = layout["lines"]
            line_spacings = layout.get("line_spacings", [fitted_font.letterSpacing()] * len(fitted_lines))
            metrics = QFontMetrics(fitted_font)
            line_gap = 2 if len(fitted_lines) > 1 else 0
            subtitle_gap = 3 if subtitle else 0
            subtitle_label = subtitle_metrics.elidedText(subtitle, Qt.ElideRight, max(28, int(actual_text_width))) if subtitle else ""
            subtitle_width = subtitle_metrics.horizontalAdvance(subtitle_label) if subtitle_label else 0
            text_height = (metrics.height() * len(fitted_lines)) + (line_gap * max(0, len(fitted_lines) - 1))
            content_height = (subtitle_metrics.height() if subtitle else 0) + subtitle_gap + text_height
            banner_height = content_height + 10
            content_width = max(layout["max_width"], subtitle_width)
            banner_width = min(self.width() - 12, content_width + content_left_inset + content_right_inset)
            banner_top = self.height() - banner_height - 14
            banner_rect = QRectF(banner_left, banner_top, banner_width, banner_height)
            title_rect = banner_rect.adjusted(content_left_inset, 5, -content_right_inset, -5)

        banner_fill = QLinearGradient(banner_rect.left(), banner_rect.top(), banner_rect.left(), banner_rect.bottom())
        banner_fill.setColorAt(0, QColor(10, 14, 20, 88))
        banner_fill.setColorAt(0.5, QColor(18, 24, 30, 122))
        banner_fill.setColorAt(1, QColor(12, 16, 22, 96))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(banner_fill))
        painter.drawRoundedRect(banner_rect, 14, 14)

        painter.setBrush(QColor(255, 255, 255, 24))
        painter.drawRoundedRect(QRectF(banner_rect.left() + 1, banner_rect.top() + 1, banner_rect.width() - 2, 1.5), 1, 1)

        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(banner_rect.adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)

        accent_rect = QRectF(banner_rect.left() + 8, banner_rect.top() + 7, 3, banner_rect.height() - 14)
        accent_color = mix_colors(self._display_color(), QColor("#DCEBFA"), 0.58)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 210))
        painter.drawRoundedRect(accent_rect, 2, 2)

        glow_rect = QRectF(banner_rect.left(), banner_rect.top() - 6, banner_rect.width(), banner_rect.height() + 12)
        glow = QLinearGradient(0, glow_rect.top(), 0, glow_rect.bottom())
        glow.setColorAt(0, QColor(255, 255, 255, 0))
        glow.setColorAt(0.5, QColor(255, 255, 255, 10))
        glow.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillRect(glow_rect, QBrush(glow))

        y_offset = title_rect.top()
        if subtitle_label:
            painter.setFont(subtitle_font)
            subtitle_rect = QRectF(title_rect.left(), y_offset, title_rect.width(), subtitle_metrics.height())
            painter.setPen(QColor(0, 0, 0, 72))
            painter.drawText(subtitle_rect.translated(0, 1), Qt.AlignLeft | Qt.AlignVCenter, subtitle_label)
            painter.setPen(QColor(205, 214, 223, 190))
            painter.drawText(subtitle_rect, Qt.AlignLeft | Qt.AlignVCenter, subtitle_label)
            y_offset += subtitle_metrics.height() + subtitle_gap

        for line, spacing in zip(fitted_lines, line_spacings):
            line_font = QFont(fitted_font)
            line_font.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
            painter.setFont(line_font)
            line_rect = QRectF(title_rect.left(), y_offset, title_rect.width(), metrics.height())
            painter.setPen(QColor(0, 0, 0, 90))
            painter.drawText(line_rect.translated(0, 1), Qt.AlignLeft | Qt.AlignVCenter, line)
            painter.setPen(QColor(255, 255, 255, 28))
            painter.drawText(line_rect.translated(0, -0.5), Qt.AlignLeft | Qt.AlignVCenter, line)
            painter.setPen(QColor(236, 240, 244, 238))
            painter.drawText(line_rect, Qt.AlignLeft | Qt.AlignVCenter, line)
            y_offset += metrics.height() + line_gap

    def _draw_title_panel(self, painter):
        panel_rect = QRectF(12, self.height() - 52, self.width() - 24, 38)
        panel_fill = QColor(5, 8, 11, 170 if self._hovered else 150)
        painter.setPen(Qt.NoPen)
        painter.setBrush(panel_fill)
        painter.drawRoundedRect(panel_rect, 14, 14)

        accent = mix_colors(self._display_color(), QColor("#E8F4FF"), 0.34)
        painter.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 200))
        painter.drawRoundedRect(QRectF(panel_rect.left() + 8, panel_rect.top() + 8, 3, panel_rect.height() - 16), 2, 2)

        title_font = QFont("Segoe UI Semilight", 11)
        title_font.setWeight(QFont.Light)
        painter.setFont(title_font)
        title_rect = panel_rect.adjusted(18, 8, -12, -8)
        label = self._elided_text(painter, self._name, title_rect.width())
        painter.setPen(QColor(0, 0, 0, 120))
        painter.drawText(title_rect.translated(0, 1), Qt.AlignVCenter | Qt.AlignLeft, label)
        painter.setPen(QColor(243, 247, 250, 228))
        painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft, label)

    def _draw_badge(self, painter):
        if not self._badge:
            return

        radius = 12
        center = QPoint(self.width() - radius - 10, radius + 10)
        painter.setPen(QPen(QColor(255, 255, 255, 55), 1))
        painter.setBrush(QColor("#D72638"))
        painter.drawEllipse(center, radius, radius)

        font = QFont("Segoe UI", 8)
        font.setWeight(QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2), Qt.AlignCenter, str(self._badge))

    def _draw_frame(self, painter, rect):
        outer = QPen(QColor(255, 255, 255, 24), 1)
        inner = QPen(QColor(0, 0, 0, 58), 1)
        accent = mix_colors(self._display_color(), QColor("#FFFFFF"), 0.38)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(outer)
        painter.drawRoundedRect(rect, self.BORDER_RADIUS, self.BORDER_RADIUS)

        painter.setPen(inner)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), self.BORDER_RADIUS - 1, self.BORDER_RADIUS - 1)

        if self._hovered:
            painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 110), 1))
            painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), self.BORDER_RADIUS - 0.5, self.BORDER_RADIUS - 0.5)

    def _launch(self):
        ok, error = launch_path(self.path)
        if ok:
            return True

        QMessageBox.warning(self, "Launch Failed", f"Unable to open {self._name or 'tile'}.\n{error}")
        return False

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.save()

        scale = 1.0 + (self.HOVER_SCALE_GAIN * self._hover_progress)
        if scale != 1.0:
            center_x = self.width() / 2
            center_y = self.height() / 2
            painter.translate(center_x, center_y)
            painter.scale(scale, scale)
            painter.translate(-center_x, -center_y)

        rect = self._paint_shell(painter)
        self._draw_standard_content(painter)
        self._draw_badge(painter)
        self._draw_frame(painter, rect)
        painter.restore()
        painter.end()

    def enterEvent(self, _):
        self._hovered = True
        self._start_hover_animation(1.0)

    def leaveEvent(self, _):
        self._hovered = False
        self._pressed = False
        self._start_hover_animation(0.0)

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
    def __init__(self, name="Time", size=(2, 2), color="#2C3E50", texture="", subtitle="", texture_mode="cover"):
        super().__init__(name=name, size=size, color=color, icon="", texture=texture, subtitle=subtitle, texture_mode=texture_mode)
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self.update)
        self._tick_timer.start(1000)

    def _marker_text(self):
        return "IST"

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.save()

        scale = 1.0 + (self.HOVER_SCALE_GAIN * self._hover_progress)
        if scale != 1.0:
            center_x = self.width() / 2
            center_y = self.height() / 2
            painter.translate(center_x, center_y)
            painter.scale(scale, scale)
            painter.translate(-center_x, -center_y)

        rect = self._paint_shell(painter)

        now = india_now()
        hours_minutes = now.strftime("%H:%M")
        seconds = now.strftime("%S")
        meta_text = now.strftime("%a  %d %b").upper()
        compact = self._size == (1, 1)

        if compact:
            time_font = QFont("Segoe UI Light", 31)
            time_font.setWeight(QFont.Light)
            painter.setFont(time_font)
            painter.setPen(QColor(250, 252, 253))
            painter.drawText(QRectF(10, 38, self.width() - 20, 44), Qt.AlignCenter, hours_minutes)

            meta_font = QFont("Segoe UI", 9)
            meta_font.setWeight(QFont.Light)
            painter.setFont(meta_font)
            painter.setPen(QColor(241, 247, 251, 165))
            painter.drawText(QRectF(10, 82, self.width() - 20, 18), Qt.AlignCenter, f"{seconds}  {meta_text}")
        else:
            time_font_size = max(40, min(self.width(), self.height()) // 3)
            time_font = QFont("Segoe UI Light", time_font_size)
            time_font.setWeight(QFont.Light)
            painter.setFont(time_font)
            painter.setPen(QColor(250, 252, 253))
            painter.drawText(QRectF(18, 50, self.width() - 36, 74), Qt.AlignLeft | Qt.AlignVCenter, hours_minutes)

            seconds_rect = QRectF(22, 122, 54, 24)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(6, 10, 13, 118))
            painter.drawRoundedRect(seconds_rect, 12, 12)
            painter.setPen(QColor(239, 247, 252, 195))
            seconds_font = QFont("Segoe UI", 9)
            seconds_font.setWeight(QFont.DemiBold)
            painter.setFont(seconds_font)
            painter.drawText(seconds_rect, Qt.AlignCenter, seconds)

            meta_font = QFont("Segoe UI", 10)
            meta_font.setWeight(QFont.Light)
            painter.setFont(meta_font)
            painter.setPen(QColor(243, 248, 251, 168))
            painter.drawText(QRectF(86, 121, self.width() - 110, 26), Qt.AlignVCenter | Qt.AlignLeft, meta_text)

        self._draw_frame(painter, rect)
        painter.restore()
        painter.end()


class DateTile(Tile):
    def __init__(self, name="Date", size=(1, 2), color="#1A6B8A", texture="", subtitle="", texture_mode="cover"):
        super().__init__(name=name, size=size, color=color, icon="", texture=texture, subtitle=subtitle, texture_mode=texture_mode)
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self.update)
        self._tick_timer.start(60_000)

    def _marker_text(self):
        return "CAL"

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.save()

        scale = 1.0 + (self.HOVER_SCALE_GAIN * self._hover_progress)
        if scale != 1.0:
            center_x = self.width() / 2
            center_y = self.height() / 2
            painter.translate(center_x, center_y)
            painter.scale(scale, scale)
            painter.translate(-center_x, -center_y)

        rect = self._paint_shell(painter)

        today = india_now()
        day_name = today.strftime("%A").upper()
        day_num = str(today.day)
        month_text = today.strftime("%b").upper()
        year_text = today.strftime("%Y")
        compact = self._size == (1, 1)

        if compact:
            month_font = QFont("Segoe UI", 10)
            month_font.setWeight(QFont.DemiBold)
            month_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.4)
            painter.setFont(month_font)
            painter.setPen(QColor(239, 247, 252, 180))
            painter.drawText(QRectF(10, 40, self.width() - 20, 18), Qt.AlignCenter, month_text)

            day_font = QFont("Segoe UI Light", 44)
            day_font.setWeight(QFont.Light)
            painter.setFont(day_font)
            painter.setPen(QColor(250, 252, 253))
            painter.drawText(QRectF(10, 52, self.width() - 20, 54), Qt.AlignCenter, day_num)

            meta_font = QFont("Segoe UI", 9)
            meta_font.setWeight(QFont.Light)
            painter.setFont(meta_font)
            painter.setPen(QColor(243, 248, 251, 162))
            painter.drawText(QRectF(10, 100, self.width() - 20, 16), Qt.AlignCenter, f"{today.strftime('%a').upper()}  {year_text}")
        else:
            month_font = QFont("Segoe UI", 11)
            month_font.setWeight(QFont.DemiBold)
            month_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.8)
            painter.setFont(month_font)
            painter.setPen(QColor(240, 247, 252, 176))
            painter.drawText(QRectF(18, 54, self.width() - 36, 18), Qt.AlignCenter, month_text)

            day_font_size = max(54, min(self.width(), self.height()) // 2)
            day_font = QFont("Segoe UI Light", day_font_size)
            day_font.setWeight(QFont.Light)
            painter.setFont(day_font)
            painter.setPen(QColor(250, 252, 253))
            painter.drawText(QRectF(12, 66, self.width() - 24, 98), Qt.AlignCenter, day_num)

            weekday_font = QFont("Segoe UI", 11)
            weekday_font.setWeight(QFont.Light)
            weekday_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
            painter.setFont(weekday_font)
            painter.setPen(QColor(243, 248, 251, 170))
            weekday_rect = QRectF(18, 154, self.width() - 36, 18)
            weekday = self._elided_text(painter, day_name, weekday_rect.width())
            painter.drawText(weekday_rect, Qt.AlignCenter, weekday)

            year_font = QFont("Segoe UI", 10)
            year_font.setWeight(QFont.Light)
            painter.setFont(year_font)
            painter.setPen(QColor(243, 248, 251, 138))
            painter.drawText(QRectF(18, 176, self.width() - 36, 18), Qt.AlignCenter, year_text)

        self._draw_frame(painter, rect)
        painter.restore()
        painter.end()
