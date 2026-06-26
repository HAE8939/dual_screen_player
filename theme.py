"""MT-Player 主题系统 —— Anthropic 品牌调性"""

# === 主色: Anthropic 标志性陶土橙 (Clay/Coral) ===
CLAY_PRIMARY = "#CC785C"
CLAY_HOVER = "#B05730"
CLAY_PRESSED = "#9A4A28"
CLAY_SUBTLE = "#EBDDD5"

# === 中性: 象牙 / 纸感暖白 ===
BG_CANVAS = "#F0EEE6"
BG_PAPER = "#FAF9F5"
BG_TITLEBAR = "#E8E5DB"

# === 文字: 暖黑, 非纯黑 ===
TEXT_PRIMARY = "#141413"
TEXT_SECONDARY = "#6B6862"
TEXT_MUTED = "#8F8B82"

# === 描边 / 分隔 ===
BORDER_DEFAULT = "#DAD9D4"
BORDER_STRONG = "#C2C0B6"

# === 语义色 ===
SUCCESS = "#6A7B5D"
DANGER = "#BF4D43"

# === 圆角 ===
RADIUS_SM = "6px"
RADIUS_MD = "10px"
RADIUS_PILL = "999px"

# === 字体 ===
FONT_FAMILY = '"Inter", "Microsoft YaHei", "Segoe UI", sans-serif'
FONT_SIZE_BODY = "13px"
FONT_SIZE_TITLE = "17px"
FONT_SIZE_BADGE = "11px"
FONT_SIZE_SMALL = "12px"

# === 深色主题 Token ===
DARK_BG_CANVAS = "#262625"
DARK_BG_PAPER = "#2E2E2D"
DARK_BG_TITLEBAR = "#1F1F1E"
DARK_TEXT_PRIMARY = "#F0EEE6"
DARK_TEXT_SECONDARY = "#A09D96"
DARK_TEXT_MUTED = "#6B6862"
DARK_BORDER_DEFAULT = "#3A3A38"
DARK_BORDER_STRONG = "#4A4A48"


def build_stylesheet(theme="light"):
    """构建完整 QSS 样式表"""
    if theme == "dark":
        return _dark_stylesheet()
    return _light_stylesheet()


def _light_stylesheet():
    return f"""
    /* === 全局 === */
    QWidget {{
        background-color: {BG_CANVAS};
        color: {TEXT_PRIMARY};
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_BODY};
    }}

    /* === 标题栏 === */
    QWidget#titleBar {{
        background-color: {BG_TITLEBAR};
        border-bottom: 1px solid {BORDER_DEFAULT};
    }}
    QLabel#titleLabel {{
        color: {TEXT_PRIMARY};
        font-size: 18px;
        font-weight: bold;
        background: transparent;
    }}
    QLabel#versionLabel {{
        color: {TEXT_SECONDARY};
        font-size: 9px;
        background: transparent;
    }}

    /* === 退出按钮 === */
    QToolButton#exitBtn {{
        color: {TEXT_SECONDARY};
        font-size: 16px;
        font-weight: bold;
        background: transparent;
        border: none;
        border-radius: 16px;
    }}
    QToolButton#exitBtn:hover {{
        background-color: {DANGER};
        color: white;
    }}

    /* === 屏幕选择 === */
    QLabel#screenLabel {{
        color: {TEXT_SECONDARY};
        font-size: {FONT_SIZE_SMALL};
        background: transparent;
    }}
    QComboBox {{
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_DEFAULT};
        padding: 4px 24px 4px 8px;
        font-size: {FONT_SIZE_SMALL};
        border-radius: {RADIUS_SM};
    }}
    QComboBox:hover {{
        border-color: {BORDER_STRONG};
    }}
    QComboBox::drop-down {{
        background-color: transparent;
        border: none;
        width: 24px;
    }}
    QComboBox::down-arrow {{
        image: none;
        background: transparent;
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid {TEXT_SECONDARY};
        margin: 0 -6px 0 0;
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        selection-background-color: {CLAY_SUBTLE};
        selection-color: {CLAY_PRIMARY};
        font-size: {FONT_SIZE_SMALL};
        border: 1px solid {BORDER_DEFAULT};
        border-radius: {RADIUS_SM};
        padding: 2px;
    }}

    /* === 状态徽标 === */
    QLabel#statusBadge {{
        font-size: {FONT_SIZE_BADGE};
        padding-left: 8px;
        background: transparent;
    }}

    /* === 选项卡 === */
    QTabWidget::pane {{
        border: 1px solid {BORDER_DEFAULT};
        border-radius: {RADIUS_SM};
        background-color: {BG_PAPER};
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {TEXT_SECONDARY};
        padding: 6px 16px;
        border: none;
        border-bottom: 2px solid transparent;
        font-size: {FONT_SIZE_SMALL};
    }}
    QTabBar::tab:selected {{
        color: {CLAY_PRIMARY};
        border-bottom: 2px solid {CLAY_PRIMARY};
        font-weight: bold;
    }}
    QTabBar::tab:hover {{
        color: {TEXT_PRIMARY};
    }}

    /* === 列表 === */
    QListWidget {{
        background-color: {BG_PAPER};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_DEFAULT};
        border-radius: {RADIUS_SM};
        font-size: 14px;
        padding: 2px;
    }}
    QListWidget::item {{
        padding: 6px 8px;
        border-radius: {RADIUS_SM};
        border-left: 3px solid transparent;
    }}
    QListWidget::item:selected {{
        background-color: {CLAY_SUBTLE};
        color: {CLAY_PRIMARY};
        font-weight: bold;
        border-left: 3px solid {CLAY_PRIMARY};
    }}
    QListWidget::item:hover:!selected {{
        background-color: {BG_CANVAS};
    }}

    /* === 幽灵图标按钮 (通用) === */
    QToolButton.ghostBtn {{
        background-color: transparent;
        border: none;
        border-radius: {RADIUS_MD};
        padding: 8px;
        min-width: 44px;
        min-height: 44px;
    }}
    QToolButton.ghostBtn:hover {{
        background-color: {CLAY_SUBTLE};
    }}
    QToolButton.ghostBtn:pressed {{
        background-color: {BORDER_DEFAULT};
    }}

    /* === 投放按钮 (主操作) === */
    QToolButton.primaryBtn {{
        background-color: {CLAY_PRIMARY};
        color: white;
        border: none;
        border-radius: {RADIUS_PILL};
        padding: 8px 20px;
        font-weight: bold;
        font-size: {FONT_SIZE_BODY};
    }}
    QToolButton.primaryBtn:hover {{
        background-color: {CLAY_HOVER};
    }}
    QToolButton.primaryBtn:pressed {{
        background-color: {CLAY_PRESSED};
    }}

    /* === 投放中状态 (描边态) === */
    QToolButton.primaryBtnActive {{
        background-color: transparent;
        color: {DANGER};
        border: 2px solid {DANGER};
        border-radius: {RADIUS_PILL};
        padding: 6px 18px;
        font-weight: bold;
        font-size: {FONT_SIZE_BODY};
    }}
    QToolButton.primaryBtnActive:hover {{
        background-color: {DANGER};
        color: white;
    }}

    /* === 按钮文字标签 === */
    QLabel#btnLabel {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
        background: transparent;
        qproperty-alignment: AlignCenter;
    }}

    /* === 预览面板 === */
    QLabel#previewTitle {{
        background-color: {BG_TITLEBAR};
        color: {TEXT_MUTED};
        font-size: {FONT_SIZE_BADGE};
        padding: 6px;
        border-left: 1px solid {BORDER_DEFAULT};
        border-bottom: 1px solid {BORDER_DEFAULT};
    }}
    QLabel#previewLabel {{
        background-color: {BG_PAPER};
        color: {TEXT_MUTED};
        font-size: {FONT_SIZE_SMALL};
        border-left: 1px solid {BORDER_DEFAULT};
    }}

    /* === Toast === */
    QLabel#toastLabel {{
        background-color: {CLAY_PRIMARY};
        color: white;
        padding: 12px 24px;
        border-radius: {RADIUS_MD};
        font-size: {FONT_SIZE_BODY};
        font-weight: bold;
    }}

    /* === 退出对话框 === */
    QDialog {{
        background-color: {BG_CANVAS};
    }}
    QToolButton#exitDialogBtn {{
        color: {DANGER};
        font-weight: bold;
    }}

    /* === 按钮栏容器 === */
    QWidget#buttonBar {{
        background-color: {BG_CANVAS};
        border-top: 1px solid {BORDER_DEFAULT};
    }}

    /* === ScrollBar === */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER_DEFAULT};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {BORDER_STRONG};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    """


def _dark_stylesheet():
    return f"""
    /* === 全局 === */
    QWidget {{
        background-color: {DARK_BG_CANVAS};
        color: {DARK_TEXT_PRIMARY};
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_BODY};
    }}

    /* === 标题栏 === */
    QWidget#titleBar {{
        background-color: {DARK_BG_TITLEBAR};
        border-bottom: 1px solid {DARK_BORDER_DEFAULT};
    }}
    QLabel#titleLabel {{
        color: {DARK_TEXT_PRIMARY};
        font-size: 18px;
        font-weight: bold;
        background: transparent;
    }}
    QLabel#versionLabel {{
        color: {DARK_TEXT_SECONDARY};
        font-size: 9px;
        background: transparent;
    }}

    /* === 退出按钮 === */
    QToolButton#exitBtn {{
        color: {DARK_TEXT_SECONDARY};
        font-size: 16px;
        font-weight: bold;
        background: transparent;
        border: none;
        border-radius: 16px;
    }}
    QToolButton#exitBtn:hover {{
        background-color: {DANGER};
        color: white;
    }}

    /* === 屏幕选择 === */
    QLabel#screenLabel {{
        color: {DARK_TEXT_SECONDARY};
        font-size: {FONT_SIZE_SMALL};
        background: transparent;
    }}
    QComboBox {{
        background-color: {DARK_BG_PAPER};
        color: {DARK_TEXT_PRIMARY};
        border: 1px solid {DARK_BORDER_DEFAULT};
        padding: 4px 24px 4px 8px;
        font-size: {FONT_SIZE_SMALL};
        border-radius: {RADIUS_SM};
    }}
    QComboBox:hover {{
        border-color: {DARK_BORDER_STRONG};
    }}
    QComboBox::drop-down {{
        background-color: transparent;
        border: none;
        width: 24px;
    }}
    QComboBox::down-arrow {{
        image: none;
        background: transparent;
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid {DARK_TEXT_SECONDARY};
        margin: 0 -6px 0 0;
    }}
    QComboBox QAbstractItemView {{
        background-color: {DARK_BG_PAPER};
        color: {DARK_TEXT_PRIMARY};
        selection-background-color: {CLAY_SUBTLE};
        selection-color: {CLAY_PRIMARY};
        font-size: {FONT_SIZE_SMALL};
        border: 1px solid {DARK_BORDER_DEFAULT};
        border-radius: {RADIUS_SM};
        padding: 2px;
    }}

    /* === 状态徽标 === */
    QLabel#statusBadge {{
        font-size: {FONT_SIZE_BADGE};
        padding-left: 8px;
        background: transparent;
    }}

    /* === 选项卡 === */
    QTabWidget::pane {{
        border: 1px solid {DARK_BORDER_DEFAULT};
        border-radius: {RADIUS_SM};
        background-color: {DARK_BG_PAPER};
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {DARK_TEXT_SECONDARY};
        padding: 6px 16px;
        border: none;
        border-bottom: 2px solid transparent;
        font-size: {FONT_SIZE_SMALL};
    }}
    QTabBar::tab:selected {{
        color: {CLAY_PRIMARY};
        border-bottom: 2px solid {CLAY_PRIMARY};
        font-weight: bold;
    }}
    QTabBar::tab:hover {{
        color: {DARK_TEXT_PRIMARY};
    }}

    /* === 列表 === */
    QListWidget {{
        background-color: {DARK_BG_PAPER};
        color: {DARK_TEXT_PRIMARY};
        border: 1px solid {DARK_BORDER_DEFAULT};
        border-radius: {RADIUS_SM};
        font-size: 14px;
        padding: 2px;
    }}
    QListWidget::item {{
        padding: 6px 8px;
        border-radius: {RADIUS_SM};
        border-left: 3px solid transparent;
    }}
    QListWidget::item:selected {{
        background-color: {CLAY_SUBTLE};
        color: {CLAY_PRIMARY};
        font-weight: bold;
        border-left: 3px solid {CLAY_PRIMARY};
    }}
    QListWidget::item:hover:!selected {{
        background-color: {DARK_BG_CANVAS};
    }}

    /* === 幽灵图标按钮 === */
    QToolButton.ghostBtn {{
        background-color: transparent;
        border: none;
        border-radius: {RADIUS_MD};
        padding: 8px;
        min-width: 44px;
        min-height: 44px;
    }}
    QToolButton.ghostBtn:hover {{
        background-color: {CLAY_SUBTLE};
    }}
    QToolButton.ghostBtn:pressed {{
        background-color: {DARK_BORDER_DEFAULT};
    }}

    /* === 投放按钮 === */
    QToolButton.primaryBtn {{
        background-color: {CLAY_PRIMARY};
        color: white;
        border: none;
        border-radius: {RADIUS_PILL};
        padding: 8px 20px;
        font-weight: bold;
        font-size: {FONT_SIZE_BODY};
    }}
    QToolButton.primaryBtn:hover {{
        background-color: {CLAY_HOVER};
    }}
    QToolButton.primaryBtn:pressed {{
        background-color: {CLAY_PRESSED};
    }}

    /* === 投放中状态 === */
    QToolButton.primaryBtnActive {{
        background-color: transparent;
        color: {DANGER};
        border: 2px solid {DANGER};
        border-radius: {RADIUS_PILL};
        padding: 6px 18px;
        font-weight: bold;
        font-size: {FONT_SIZE_BODY};
    }}
    QToolButton.primaryBtnActive:hover {{
        background-color: {DANGER};
        color: white;
    }}

    /* === 按钮文字标签 === */
    QLabel#btnLabel {{
        color: {DARK_TEXT_SECONDARY};
        font-size: 11px;
        background: transparent;
        qproperty-alignment: AlignCenter;
    }}

    /* === 预览面板 === */
    QLabel#previewTitle {{
        background-color: {DARK_BG_TITLEBAR};
        color: {DARK_TEXT_MUTED};
        font-size: {FONT_SIZE_BADGE};
        padding: 6px;
        border-left: 1px solid {DARK_BORDER_DEFAULT};
        border-bottom: 1px solid {DARK_BORDER_DEFAULT};
    }}
    QLabel#previewLabel {{
        background-color: {DARK_BG_PAPER};
        color: {DARK_TEXT_MUTED};
        font-size: {FONT_SIZE_SMALL};
        border-left: 1px solid {DARK_BORDER_DEFAULT};
    }}

    /* === Toast === */
    QLabel#toastLabel {{
        background-color: {CLAY_PRIMARY};
        color: white;
        padding: 12px 24px;
        border-radius: {RADIUS_MD};
        font-size: {FONT_SIZE_BODY};
        font-weight: bold;
    }}

    /* === 按钮栏 === */
    QWidget#buttonBar {{
        background-color: {DARK_BG_CANVAS};
        border-top: 1px solid {DARK_BORDER_DEFAULT};
    }}

    /* === ScrollBar === */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {DARK_BORDER_DEFAULT};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {DARK_BORDER_STRONG};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    """
