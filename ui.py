import random
from PyQt5.QtWidgets import (
    QWidget, QGridLayout, QScrollArea, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QSizePolicy, QToolButton,
    QShortcut
)
from PyQt5.QtCore  import Qt, QTimer, QTime, QDate, QPoint, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui   import (QPainter, QColor, QBrush, QLinearGradient,
                            QFont, QPen, QKeySequence)
from tile   import Tile, ClockTile, DateTile
from config import load_apps


# ─────────────────────────────────────────────────────────
#  Animated particle background
# ─────────────────────────────────────────────────────────
class ParticleBG(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._pts = [
            dict(x=random.random(), y=random.random(),
                 r=random.uniform(1.2, 3.8),
                 vx=random.uniform(-0.00025, 0.00025),
                 vy=random.uniform(-0.00018, 0.00018),
                 a=random.uniform(0.04, 0.20))
            for _ in range(60)
        ]
        t = QTimer(self); t.timeout.connect(self._step); t.start(40)
 
    def _step(self):
        for p in self._pts:
            p["x"] = (p["x"] + p["vx"]) % 1.0
            p["y"] = (p["y"] + p["vy"]) % 1.0
        self.update()
 
    def paintEvent(self, _):
        W, H = self.width(), self.height()
        pa = QPainter(self)
        pa.setRenderHint(QPainter.Antialiasing)
 
        # deep Win8-style blue-purple background
        grad = QLinearGradient(0, 0, W, H)
        grad.setColorAt(0,   QColor("#0D1A26"))
        grad.setColorAt(0.5, QColor("#0D1A26"))
        grad.setColorAt(1,   QColor("#0D1A26"))
        pa.fillRect(0, 0, W, H, QBrush(grad))
 
        # faint grid
        pa.setPen(QPen(QColor(255, 255, 255, 6), 1))
        for x in range(0, W, 60): pa.drawLine(x, 0, x, H)
        for y in range(0, H, 60): pa.drawLine(0, y, W, y)
 
        # particles
        for p in self._pts:
            pa.setPen(Qt.NoPen)
            pa.setBrush(QColor(255, 255, 255, int(p["a"] * 255)))
            pa.drawEllipse(QPoint(int(p["x"]*W), int(p["y"]*H)),
                           int(p["r"]), int(p["r"]))
        pa.end()
 
 
# ─────────────────────────────────────────────────────────
#  Top bar
# ─────────────────────────────────────────────────────────
class TopBar(QWidget):
    def __init__(self, title="IO", parent=None):
        super().__init__(parent)
        self.setFixedHeight(54)
        self.setStyleSheet("background: rgba(0,0,0,0.32); "
                           "border-bottom: 1px solid rgba(255,255,255,0.07);")
 
        lay = QHBoxLayout(self)
        lay.setContentsMargins(28, 0, 28, 0)
        lay.setSpacing(14)
 
        # Start label
        lbl = QLabel(title)
        f = QFont("Segoe UI Light", 26)
        f.setWeight(QFont.Light)
        lbl.setFont(f)
        lbl.setStyleSheet("color: white; background: transparent;")
        lay.addWidget(lbl)
 
        # Search
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search…")
        self._search.setFixedWidth(200)
        self._search.setStyleSheet("""
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
        """)
        lay.addWidget(self._search)
 
        sp = QWidget(); sp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay.addWidget(sp)
 
        self._clk = QLabel()
        self._clk.setStyleSheet("color: rgba(255,255,255,0.78); font-size: 14px; background: transparent;")
        self._dt  = QLabel()
        self._dt.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 11px; background: transparent;")
        lay.addWidget(self._clk)
        lay.addWidget(self._dt)
 
        usr = QLabel("Admin ▾")
        usr.setStyleSheet("color: rgba(255,255,255,0.70); font-size: 13px; "
                          "margin-left: 10px; background: transparent;")
        lay.addWidget(usr)
 
        t = QTimer(self); t.timeout.connect(self._tick); t.start(1000)
        self._tick()
 
    def _tick(self):
        self._clk.setText(QTime.currentTime().toString("hh:mm:ss"))
        self._dt.setText(QDate.currentDate().toString("ddd, MMM d"))
 
    def connect_search(self, fn):
        self._search.textChanged.connect(fn)
 
 
# ─────────────────────────────────────────────────────────
#  Charms sidebar (slide-in from right)
# ─────────────────────────────────────────────────────────
class CharmsBar(QFrame):
    ITEMS = [("⚙","Settings"),("🔍","Search"),("📤","Share"),
             ("📱","Devices"),("🏠","Start")]
 
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedWidth(64)
        self.setStyleSheet("QFrame { background: rgba(10,8,30,0.93); "
                           "border-left: 1px solid rgba(255,255,255,0.10); }")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 80, 0, 0)
        lay.setSpacing(0)
        for icon, tip in self.ITEMS:
            b = QToolButton()
            b.setText(icon); b.setToolTip(tip); b.setFixedSize(64, 60)
            b.setStyleSheet("QToolButton { color:white; font-size:20px; "
                            "background:transparent; border:none; } "
                            "QToolButton:hover { background:rgba(255,255,255,0.10); }")
            lay.addWidget(b)
        lay.addStretch()
        self._open = False
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(210)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.hide()
 
    def toggle(self, pw, ph):
        if not self._open:
            self.setGeometry(pw, 0, 64, ph)
            self.show(); self.raise_()
            self._anim.setStartValue(self.geometry())
            self._anim.setEndValue(QRect(pw - 64, 0, 64, ph))
            self._anim.start()
            self._open = True
        else:
            self._anim.setStartValue(self.geometry())
            self._anim.setEndValue(QRect(pw, 0, 64, ph))
            self._anim.start()
            self._anim.finished.connect(self.hide)
            self._open = False
 
 
# ─────────────────────────────────────────────────────────
#  Group separator label
# ────────────────────────────────────────────────────────�

class GroupLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        f = QFont("Segoe UI Light", 10)
        f.setWeight(QFont.Light)
        self.setFont(f)
        self.setFixedHeight(28)
        self.setStyleSheet("color: rgba(255,255,255,0.30); "
                           "background: transparent; "
                           "padding-left: 2px;")
 
 
# ─────────────────────────────────────────────────────────
#  Main Dashboard
# ─────────────────────────────────────────────────────────
class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        apps = load_apps()
 
        self.resize(1280, 768)
        self.setMinimumSize(900, 560)

        # particle background
        self._bg = ParticleBG(self)
        self._bg.lower()
 
        # charms
        self._charms = CharmsBar(self)
 
        # root layout
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
 
        self._topbar = TopBar("dot", parent=self)
        root.addWidget(self._topbar)
 
        # scroll area
        scroll = QScrollArea()
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
 
        self._inner = QWidget()
        self._inner.setStyleSheet("background: transparent;")
        self._vlayout = QVBoxLayout(self._inner)
        # Win8: left margin ~28px, top margin below header
        self._vlayout.setContentsMargins(70, 70, 70, 70)   #update this
        self._vlayout.setSpacing(0)
 
        scroll.setWidget(self._inner)
        root.addWidget(scroll)
 
        # charms toggle button
        self._cbtn = QPushButton("⋮", self)
        self._cbtn.setFixedSize(32, 32)
        self._cbtn.setStyleSheet("QPushButton { color:rgba(255,255,255,0.55); "
                                 "font-size:18px; background:transparent; border:none; } "
                                 "QPushButton:hover { color:white; }")
        self._cbtn.clicked.connect(lambda: self._charms.toggle(self.width(), self.height()))
 
        self._all_tiles = []


 
        # ── build the grid ──────────────────────────────
        self._build(apps)
 
        # search
        self._topbar.connect_search(self._filter)
 
        # Escape closes charms
        QShortcut(QKeySequence("Escape"), self,
                  lambda: self._charms.toggle(self.width(), self.height())
                  if self._charms._open else None)
 
    # ── resize ──────────────────────────────────────────
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._bg.setGeometry(0, 0, self.width(), self.height())
        self._cbtn.move(self.width() - 42, 11)
 
    # ── search filter ────────────────────────────────────
    def _filter(self, text):
        txt = text.strip().lower()
        for tile, name in self._all_tiles:
            tile.setVisible(txt == "" or txt in name.lower())
 
    # ── grid builder ─────────────────────────────────────
    def _build(self, apps):
        """
        Single QGridLayout spanning full width.
        Column count = how many BASE-unit columns fit in the window.
        Tiles are bin-packed (left→right, top→bottom) using a 2-D occupancy map.
        Group labels occupy one full row spanning all columns.
        """
        BASE = 140
        GAP  = 8
 
        margins = 56    # 28 left + 28 right
        avail   = self.width() - margins
        COLS = 10
        # single grid layout
        grid_lay = QGridLayout()
        grid_lay.setSpacing(GAP)
        grid_lay.setContentsMargins(0, 0, 0, 0)
        grid_lay.setAlignment(Qt.AlignCenter | Qt.AlignCenter)
 
        self._vlayout.addLayout(grid_lay)
        self._vlayout.addStretch()
 
        # occupancy map
        occ = []
 
        def occupy(r, c, w, h):
            for i in range(r, r + h):
                for j in range(c, c + w):
                    if i < len(occ) and j < len(occ[0]):
                        occ[i][j] = 1
                    else:
                        print(f"Out of bounds: i={i}, j={j}")

        def ensure(n):
            while len(occ) < n:
                occ.append([0] * COLS)
 
        def can_place(r, c, w, h):
            ensure(r + h)
            if c + w > COLS:
                return False
            for i in range(r, r + h):
                for j in range(c, c + w):
                    if occ[i][j] == 1:  
                        return False
            return True
 
        def place_tile(w, h):
            r = 0
            while True:
                ensure(r + h)
                print(r,h,c,w)
                for c in range(COLS - w + 1):
                    if can_place(r, c, w, h):
                        occupy(r, c, w, h) 
                        return r, c
                r += 1
 
        def place_label(text):
            """Span a group label across all columns in the next free full row."""
            r = len(occ)
            ensure(r + 1)
            occupy(r, 0, COLS, 1)
            lbl = GroupLabel(text)
            grid_lay.addWidget(lbl, r, 0, 1, COLS)
 

 

        # ── per-group tiles ───────────────────
        groups: dict[str, list] = {}
        for app in apps:
            groups.setdefault(app.get("group", "Apps"), []).append(app)
 
        for group_name, group_apps in groups.items():
            place_label(group_name.upper())
 
            for app in group_apps:
                aw, ah = app["size"]
                if app.get("row", -1) >= 0 and app.get("col", -1) >= 0:
                    ar, ac = app["row"], app["col"]

                    ensure(ar + ah)   # 🔥 ADD THIS LINE

                    if ac + aw > COLS:
                        print(f"Invalid placement: {app['name']} exceeds column limit")
                        continue

                    occupy(ar, ac, aw, ah)
                else:
                    ar, ac = place_tile(aw, ah)
 
                app_type = app.get("type", "").lower()
                if app_type == "clock":
                    tile = ClockTile(size=app["size"], color=app["color"])
                elif app_type == "date":
                    tile = DateTile(size=app["size"], color=app["color"])
                else:
                    tile = Tile(
                        name  = app["name"],
                        path  = app["path"],
                        size  = app["size"],
                        color = app["color"],
                        icon  = app.get("icon", ""),
                        badge = app.get("badge", ""),
                    )
                self._all_tiles.append((tile, app["name"]))
                grid_lay.addWidget(tile, ar, ac, ah, aw)
 
        # fill empty cells with transparent spacers so column stretch works
        total_rows = len(occ)
        for r in range(total_rows):
            for c in range(COLS):
                if not occ[r][c]:
                    sp = QWidget()
                    sp.setFixedSize(BASE, BASE)
                    sp.setStyleSheet("background: transparent;")
                    grid_lay.addWidget(sp, r, c)
                       
      
              
 
   
