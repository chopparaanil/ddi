import subprocess
import random
from PyQt5.QtWidgets import QFrame, QLabel
from PyQt5.QtCore    import Qt, QTimer, QPoint, QRectF
from PyQt5.QtGui     import (QColor, QPainter, QBrush,
                              QLinearGradient, QPen, QFont, QMovie)


class RippleOverlay(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._r = 0; self._cx = 0; self._cy = 0; self._a = 0.0
        self.hide()

    def trigger(self, pos):
        self._cx, self._cy = pos.x(), pos.y()
        self._r = 0; self._a = 0.32
        self._t = QTimer(self)
        self._t.timeout.connect(self._step)
        self._t.start(14)
        self.show()

    def _step(self):
        self._r += 16; self._a -= 0.022
        if self._a <= 0:
            self._t.stop(); self.hide()
        self.update()

    def paintEvent(self, _):
        if self._a <= 0: return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setOpacity(self._a)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawEllipse(QPoint(self._cx, self._cy), self._r, self._r)
        p.end()
 
 
class Tile(QFrame):
    BASE = 155   # one grid unit in pixels  #update this
    GAP  = 15    # gap between tiles

    def __init__(self, name="", path=None, size=(1, 1),
                 color="#FFFFFF", icon="", badge="", gif=None):
        super().__init__()
        self.path     = path
        self._color   = QColor(color)
        self._size    = size
        self._icon    = icon
        self._badge   = badge
        self._hovered = False
        self._pressed = False
        self._shimmer = 0.0
 
        tw = self.BASE * size[0] + self.GAP * (size[0] - 1)
        th = self.BASE * size[1] + self.GAP * (size[1] - 1)
        self.setFixedSize(tw, th)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover)
        # tooltip removed; keep name for rendering
        self._name = name or ""
 
        self._ripple = RippleOverlay(self)
        self._ripple.setGeometry(0, 0, tw, th)
 
        if gif:
            gl = QLabel(self)
            gl.setGeometry(0, 0, tw, th)
            gl.setScaledContents(True)
            self._movie = QMovie(gif)
            gl.setMovie(self._movie)
            self._movie.start()
            gl.lower()
 
        if size[0] >= 2 or size[1] >= 2:
            t = QTimer(self)
            t.setInterval(random.randint(3500, 8000))
            t.timeout.connect(self._start_shimmer)
            t.start()
 
    def _start_shimmer(self):
        self._shimmer = 0.0
        self._sa = QTimer(self)
        self._sa.timeout.connect(self._shimmer_step)
        self._sa.start(14)
 
    def _shimmer_step(self):
        self._shimmer += 0.045
        if self._shimmer >= 1.0:
            self._shimmer = 0.0; self._sa.stop()
        self.update()
 
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
 
        # solid fill — NO border-radius (Win8 exact)
        col = QColor(self._color)
        if self._pressed:   col = col.darker(125)
        elif self._hovered: col = col.lighter(118)
        p.fillRect(0, 0, W, H, col)
 
        # subtle depth gradient
        grad = QLinearGradient(0, 0, 0, H)
        grad.setColorAt(0,   QColor(255, 255, 255, 20))
        grad.setColorAt(0.4, QColor(255, 255, 255, 0))
        grad.setColorAt(1,   QColor(0,   0,   0,   25))
        p.fillRect(0, 0, W, H, QBrush(grad))
 
        # shimmer sweep
        if self._shimmer > 0:
            bx = int(W * self._shimmer)
            sg = QLinearGradient(bx - 55, 0, bx + 25, 0)
            sg.setColorAt(0,   QColor(255, 255, 255, 0))
            sg.setColorAt(0.5, QColor(255, 255, 255, 50))
            sg.setColorAt(1,   QColor(255, 255, 255, 0))
            p.fillRect(0, 0, W, H, QBrush(sg))
 
        # icon — centred, upper 60% of tile
        if self._icon:
            icon_size = max(18, min(W, H) // 3)
            f = QFont("Segoe UI Emoji", icon_size)
            p.setFont(f)
            p.setPen(QColor(255, 255, 255, 215))
            p.drawText(
                QRectF(0, H * 0.10, W, H * 0.60),
                Qt.AlignHCenter | Qt.AlignVCenter,
                self._icon
            )
 
        # name — bottom-left, 11px Segoe UI Light
        p.setPen(QColor(255, 255, 255))
        nf = QFont("Segoe UI", 11)
        nf.setWeight(QFont.Light)
        p.setFont(nf)
        M = 9
        p.drawText(
            QRectF(M, H - 28, W - M * 2, 24),
            Qt.AlignVCenter | Qt.AlignLeft,
            self._name
        )
 
        # badge
        if self._badge:
            R = 11; bx = W - R - 7; by = R + 5
            p.setBrush(QColor("#e81123"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPoint(bx, by), R, R)
            p.setPen(QColor(255, 255, 255))
            p.setFont(QFont("Segoe UI", 8, QFont.Bold))
            p.drawText(QRectF(bx - R, by - R, R * 2, R * 2),
                       Qt.AlignCenter, self._badge)
 
        # hover border
        if self._hovered:
            p.setPen(QPen(QColor(255, 255, 255, 80), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRect(0, 0, W - 1, H - 1)
 
        p.end()
 
    def enterEvent(self, _):  self._hovered = True;  self.update()
    def leaveEvent(self, _):  self._hovered = False; self._pressed = False; self.update()
 
    def mousePressEvent(self, e):
        self._pressed = True
        self._ripple.trigger(e.pos())
        self.update()
 
    def mouseReleaseEvent(self, e):
        self._pressed = False
        self.update()
        if self.rect().contains(e.pos()) and self.path:
            subprocess.Popen(self.path, shell=True)
 
    def contextMenuEvent(self, e):
        from PyQt5.QtWidgets import QMenu
        m = QMenu(self)
        if self.path:
            m.addAction("Open", lambda: subprocess.Popen(self.path, shell=True))
        m.addSeparator()
        m.addAction("Pin to Start")
        m.addAction("Unpin from Start")
        m.exec_(e.globalPos())
 
 
# ─────────────────────────────────────────────────────────
#  Live Clock Tile  — shows HH:MM:SS, updates every second
# ─────────────────────────────────────────────────────────
class ClockTile(Tile):
    """
    A tile that displays a live digital clock.
    Ticks every second and repaints itself.
    Layout:
      - Large HH:MM  centred vertically (upper 55%)
      - Seconds in smaller text just below
      - "Clock" label bottom-left (like all Metro tiles)
    """
    def __init__(self, size=(2, 2), color="#2C3E50"):
        super().__init__(name="Clock", size=size, color=color, icon="")
 
        from PyQt5.QtCore import QDateTime
        self._dt = QDateTime
 
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self.update)
        self._tick_timer.start(1000)
 
    def paintEvent(self, _):
        from PyQt5.QtCore import QDateTime, Qt
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
 
        # ── background
        col = QColor(self._color)
        if self._pressed:   col = col.darker(125)
        elif self._hovered: col = col.lighter(112)
        p.fillRect(0, 0, W, H, col)
 
        # subtle gradient
        grad = QLinearGradient(0, 0, 0, H)
        grad.setColorAt(0,   QColor(255, 255, 255, 18))
        grad.setColorAt(0.5, QColor(255, 255, 255, 0))
        grad.setColorAt(1,   QColor(0,   0,   0,   30))
        p.fillRect(0, 0, W, H, QBrush(grad))
 
        now = QDateTime.currentDateTime()
        hhmm = now.toString("hh:mm")
        ss   = now.toString("ss")
 
        # ── HH:MM  — large, centred, upper area
        time_font_size = max(28, min(W, H) // 3)
        tf = QFont("Segoe UI Light", time_font_size)
        tf.setWeight(QFont.Light)
        p.setFont(tf)
        p.setPen(QColor(255, 255, 255))
        # measure text width to manually centre it
        fm   = p.fontMetrics()
        tw   = fm.width(hhmm)
        th_f = fm.height()
        tx   = (W - tw) // 2
        ty   = int(H * 0.20)
        p.drawText(tx, ty + th_f, hhmm)
 
        # ── seconds  — smaller, right-aligned under HH:MM
        sf = QFont("Segoe UI Light", max(14, time_font_size // 3))
        sf.setWeight(QFont.Light)
        p.setFont(sf)
        p.setPen(QColor(255, 255, 255, 160))
        sfm = p.fontMetrics()
        sw  = sfm.width(ss)
        p.drawText(tx + tw - sw, ty + th_f + sfm.height() + 2, ss)
 
        # ── "Clock" label — bottom-left
        p.setPen(QColor(255, 255, 255))
        lf = QFont("Segoe UI", 11)
        lf.setWeight(QFont.Light)
        p.setFont(lf)
        M = 9
        p.drawText(
            QRectF(M, H - 28, W - M * 2, 24),
            Qt.AlignVCenter | Qt.AlignLeft,
            "Clock"
        )
 
        # hover border
        if self._hovered:
            p.setPen(QPen(QColor(255, 255, 255, 80), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRect(0, 0, W - 1, H - 1)
 
        p.end()
 
 
# ─────────────────────────────────────────────────────────
#  Live Date Tile  — shows day-of-week + full date
# ──────────────────────────────────────────────

class DateTile(Tile):
    """
    A tile that displays the live date.
    Updates at midnight automatically.
    Layout:
      - Short day name (MON) large, top-centre
      - Numeric day (27) very large, centred
      - Month + year small, below
      - "Date" label bottom-left
    """
    def __init__(self, size=(1, 2), color="#1A6B8A"):
        super().__init__(name="Date", size=size, color=color, icon="")
 
        # repaint every minute (date won't change per-second)
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self.update)
        self._tick_timer.start(60_000)
 
    def paintEvent(self, _):
        from PyQt5.QtCore import QDate, Qt
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
 
        # background
        col = QColor(self._color)
        if self._pressed:   col = col.darker(125)
        elif self._hovered: col = col.lighter(112)
        p.fillRect(0, 0, W, H, col)
 
        grad = QLinearGradient(0, 0, 0, H)
        grad.setColorAt(0,   QColor(255, 255, 255, 18))
        grad.setColorAt(0.5, QColor(255, 255, 255, 0))
        grad.setColorAt(1,   QColor(0,   0,   0,   30))
        p.fillRect(0, 0, W, H, QBrush(grad))
 
        today    = QDate.currentDate()
        day_name = today.toString("ddd").upper()   # MON
        day_num  = today.toString("d")             # 27
        month    = today.toString("MMMM")          # March
        year     = today.toString("yyyy")          # 2026
 
        CX = W // 2   # horizontal centre
 
        # ── day name (MON) — top area, small-caps feel
        dnf = QFont("Segoe UI Light", max(12, W // 6))
        dnf.setWeight(QFont.Light)
        dnf.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        p.setFont(dnf)
        p.setPen(QColor(255, 255, 255, 180))
        fm  = p.fontMetrics()
        dnw = fm.width(day_name)
        p.drawText(CX - dnw // 2, int(H * 0.20) + fm.ascent(), day_name)
 
        # ── day number — very large, centred
        day_font_size = max(36, min(W, H) // 2)
        df = QFont("Segoe UI Light", day_font_size)
        df.setWeight(QFont.Light)
        p.setFont(df)
        p.setPen(QColor(255, 255, 255))
        fm2  = p.fontMetrics()
        dnuw = fm2.width(day_num)
        p.drawText(CX - dnuw // 2, int(H * 0.25) + fm.height() + fm2.ascent(), day_num)
 
        # ── month + year — below the number
        mf = QFont("Segoe UI Light", max(10, W // 9))
        mf.setWeight(QFont.Light)
        p.setFont(mf)
        p.setPen(QColor(255, 255, 255, 160))
        fm3   = p.fontMetrics()
        mtext = f"{month} {year}"
        mw    = fm3.width(mtext)
        p.drawText(CX - mw // 2,
                   int(H * 0.25) + fm.height() + fm2.height() + fm3.ascent() + 4,
                   mtext)
 
        # ── "Date" label — bottom-left
        p.setPen(QColor(255, 255, 255))
        lf = QFont("Segoe UI", 11)
        lf.setWeight(QFont.Light)
        p.setFont(lf)
        M = 9
        p.drawText(
            QRectF(M, H - 28, W - M * 2, 24),
            Qt.AlignVCenter | Qt.AlignLeft,
            "Date"
        )
 
        if self._hovered:
            p.setPen(QPen(QColor(255, 255, 255, 80), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRect(0, 0, W - 1, H - 1)
 
        p.end()
  

        
