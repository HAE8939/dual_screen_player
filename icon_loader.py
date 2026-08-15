"""图标加载器 —— 支持 SVG 着色，降级为中文文字"""

import os
import sys
import logging
from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QSize

from theme import CLAY_PRIMARY, TEXT_SECONDARY

logger = logging.getLogger(__name__)

# 兼容 PyInstaller 打包：_MEIPASS 为运行时资源根目录
_BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
ICON_DIR = _BASE_DIR / "img" / "icons"

# 图标名称 → SVG 文件名映射
ICON_FILES = {
    "folder": "folder-input.svg",
    "add": "plus.svg",
    "play": "play.svg",
    "pause": "pause.svg",
    "prev": "chevron-left.svg",
    "next": "chevron-right.svg",
    "mute": "volume-x.svg",
    "unmute": "volume-2.svg",
    "projection": "monitor-play.svg",
    "projection_stop": "monitor-off.svg",
}

# 图标名称 → 中文降级文字
ICON_FALLBACK = {
    "folder": "导入",
    "add": "添加",
    "play": "播放",
    "pause": "暂停",
    "prev": "上一个",
    "next": "下一个",
    "mute": "静音",
    "unmute": "取消静音",
    "projection": "投放",
    "projection_stop": "取消投放",
}


def load_icon(name: str, color: str = TEXT_SECONDARY, size: int = 32) -> QIcon:
    """加载图标，SVG 按 color 着色；不存在则降级为中文文字"""
    svg_path = ICON_DIR / ICON_FILES.get(name, "")
    if svg_path.exists():
        return _load_svg_colored(svg_path, color, size, name)

    fallback = ICON_FALLBACK.get(name, name[:2])
    logger.debug(f"图标 SVG 不存在: {name}，降级为文字: {fallback}")
    return _make_text_icon(fallback, color, size)


def _load_svg_colored(svg_path: Path, color: str, size: int, name: str) -> QIcon:
    """读取 SVG 并用指定颜色渲染（支持高 DPI / 设备像素比）"""
    try:
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtCore import QByteArray
        from PyQt6.QtWidgets import QApplication

        svg_data = svg_path.read_bytes()
        # 替换 SVG 中的 stroke/fill 颜色为指定颜色
        svg_str = svg_data.decode("utf-8")
        # 简单替换：将 black/white/#000 等常见色替换为目标色
        for old in ["#000000", "#000", "black", "#ffffff", "#fff", "white",
                     "stroke=\"currentColor\"", "fill=\"currentColor\""]:
            svg_str = svg_str.replace(old, color)
        svg_data = svg_str.encode("utf-8")

        renderer = QSvgRenderer(QByteArray(svg_data))

        # 高 DPI 渲染：按 devicePixelRatio 放大绘制，再设置 ratio，
        # 避免在 150%/200% 缩放下被拉伸模糊。
        dpr = 1.0
        app = QApplication.instance()
        if app is not None:
            dpr = app.devicePixelRatio()
        if dpr <= 0:
            dpr = 1.0
        render_size = int(round(size * dpr))
        if render_size < 1:
            render_size = 1

        pixmap = QPixmap(QSize(render_size, render_size))
        pixmap.fill(Qt.GlobalColor.transparent)
        pixmap.setDevicePixelRatio(dpr)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)
    except ImportError:
        logger.warning("QtSvg 未安装，图标降级为文字")
        fallback = ICON_FALLBACK.get(name, name[:2])
        return _make_text_icon(fallback, color, size)
    except Exception as e:
        logger.warning(f"SVG 渲染失败: {e}，降级为文字")
        fallback = ICON_FALLBACK.get(name, name[:2])
        return _make_text_icon(fallback, color, size)


def _make_text_icon(text: str, color: str, size: int) -> QIcon:
    """用纯文字创建图标"""
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor(color))
    font = painter.font()
    font.setPixelSize(max(10, size // 3))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
    painter.end()
    return QIcon(pixmap)
