"""可复用 UI 组件 —— Anthropic 品牌调性"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QListWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QIcon

from icon_loader import load_icon


class GhostIconButton(QWidget):
    """幽灵图标按钮：图标 + 下方文字标签，hover 时图标变陶土橙"""
    clicked = pyqtSignal()

    def __init__(self, icon_name: str, label: str, tooltip: str = "", parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.label_text = label
        self._is_active = False
        self._is_hovered = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 2)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        self.btn = QToolButton()
        self.btn.setObjectName("ghostBtn")
        self.btn.setProperty("class", "ghostBtn")
        self.btn.setFixedSize(44, 44)
        self.btn.setIconSize(QSize(24, 24))
        self.btn.setToolTip(tooltip or label)
        self.btn.setIcon(load_icon(icon_name))
        self.btn.clicked.connect(self.clicked)
        layout.addWidget(self.btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.label = QLabel(label)
        self.label.setObjectName("btnLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.label.setStyleSheet("font-size: 11px; color: #6B6862; background: transparent;")
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.setFixedWidth(60)
        self.setMouseTracking(True)
        self.btn.setMouseTracking(True)

    def enterEvent(self, event):
        self._is_hovered = True
        if not self._is_active:
            self.btn.setIcon(load_icon(self.icon_name, color="#CC785C"))
            self.label.setStyleSheet("color: #CC785C; font-size: 11px; background: transparent;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        if not self._is_active:
            self.btn.setIcon(load_icon(self.icon_name))
            self.label.setStyleSheet("color: #6B6862; font-size: 11px; background: transparent;")
        super().leaveEvent(event)

    def set_active(self, active: bool):
        self._is_active = active
        if active:
            self.btn.setIcon(load_icon(self.icon_name, color="#CC785C"))
            self.label.setStyleSheet("color: #CC785C; font-size: 11px; font-weight: bold; background: transparent;")
        else:
            color = "#CC785C" if self._is_hovered else None
            self.btn.setIcon(load_icon(self.icon_name, color=color) if color else load_icon(self.icon_name))
            self.label.setStyleSheet("color: #6B6862; font-size: 11px; background: transparent;")

    def set_icon(self, icon_name: str, color: str = "#6B6862"):
        self.icon_name = icon_name
        self.btn.setIcon(load_icon(icon_name, color=color))


class PrimaryButton(QWidget):
    """陶土橙胶囊主操作按钮，hover 加深"""
    clicked = pyqtSignal()

    def __init__(self, label: str, icon_name: str = "", tooltip: str = "", parent=None):
        super().__init__(parent)
        self.label_text = label
        self._is_active = False
        self._is_hovered = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 2)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        self.btn = QToolButton()
        self.btn.setObjectName("projectionBtn")
        self.btn.setProperty("class", "primaryBtn")
        self.btn.setToolTip(tooltip or label)
        self.btn.setFixedHeight(38)
        self.btn.setIconSize(QSize(20, 20))
        if icon_name:
            self.btn.setIcon(load_icon(icon_name, color="#FFFFFF"))
        self.btn.clicked.connect(self.clicked)
        layout.addWidget(self.btn)

        self.label = QLabel(label)
        self.label.setObjectName("btnLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.label.setStyleSheet("font-size: 11px; font-weight: bold; color: #6B6862; background: transparent;")
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.setFixedWidth(90)
        self.setMouseTracking(True)
        self.btn.setMouseTracking(True)
        self._update_display()

    def enterEvent(self, event):
        self._is_hovered = True
        if not self._is_active:
            self.btn.setIcon(load_icon("projection", color="#FFFFFF"))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        super().leaveEvent(event)

    def _update_display(self):
        if self._is_active:
            self.btn.setProperty("class", "primaryBtnActive")
            self.btn.setText("✕ 取消投放")
            self.btn.setIcon(load_icon("projection_stop", color="#BF4D43"))
            self.label.setStyleSheet("color: #BF4D43; font-size: 11px; font-weight: bold; background: transparent;")
        else:
            self.btn.setProperty("class", "primaryBtn")
            self.btn.setText("◉ 投放")
            self.btn.setIcon(load_icon("projection", color="#FFFFFF"))
            self.label.setStyleSheet("color: #6B6862; font-size: 11px; font-weight: bold; background: transparent;")
        self.btn.style().unpolish(self.btn)
        self.btn.style().polish(self.btn)

    def set_active(self, active: bool):
        self._is_active = active
        self._update_display()

    def set_icon(self, icon_name: str, color: str = "#FFFFFF"):
        self.btn.setIcon(load_icon(icon_name, color=color))


class StatusBadge(QWidget):
    """状态徽标：圆点 + 文字"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(4)

        self.dot = QLabel("●")
        self.dot.setObjectName("statusBadge")
        self.dot.setStyleSheet("font-size: 10px; color: #8F8B82; background: transparent;")
        layout.addWidget(self.dot)

        self.text = QLabel("未投放")
        self.text.setObjectName("statusBadge")
        self.text.setStyleSheet("font-size: 11px; color: #8F8B82; background: transparent;")
        layout.addWidget(self.text)

    def set_state(self, state: str, **kwargs):
        if state == "projecting":
            idx = kwargs.get("screen_index", 1)
            self.dot.setStyleSheet("font-size: 10px; color: #6A7B5D; background: transparent;")
            self.text.setText(f"投放中（屏幕{idx}）")
            self.text.setStyleSheet("font-size: 11px; color: #6A7B5D; font-weight: bold; background: transparent;")
        else:
            self.dot.setStyleSheet("font-size: 10px; color: #8F8B82; background: transparent;")
            self.text.setText("未投放")
            self.text.setStyleSheet("font-size: 11px; color: #8F8B82; background: transparent;")


class MediaListWidget(QListWidget):
    """统一选中态样式的媒体列表"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(False)

    def update_item(self, index: int, name: str, is_playing: bool = False):
        item = self.item(index)
        if not item:
            return
        if is_playing:
            item.setText(f"▶ {name}")
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(QColor("#CC785C"))
        else:
            item.setText(name)
            font = item.font()
            font.setBold(False)
            item.setFont(font)
            item.setForeground(QColor("#141413"))
