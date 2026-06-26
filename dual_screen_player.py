import sys
import os
import logging
import argparse
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QListWidget, QToolButton, QFileDialog,
    QSystemTrayIcon, QMenu, QMessageBox, QTabWidget, QListWidgetItem,
    QStackedWidget, QDialog, QDialogButtonBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer, QSize, QThread
from PyQt6.QtGui import QIcon, QPixmap, QAction, QColor, QPainter, QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from media_library import MediaLibrary, SUPPORTED_VIDEO_EXTS, SUPPORTED_IMAGE_EXTS, __version__
from player_controller import PlayerController

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WINDOW_WIDTH = 820
WINDOW_HEIGHT = 420
PREVIEW_PANEL_WIDTH = 260
ICON_SIZE = 32
PREVIEW_UPDATE_INTERVAL = 1000


def resource_path(relative_path):
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class ToastLabel(QLabel):
    """非阻塞 Toast 提示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setStyleSheet(
            "background-color: rgba(0, 120, 212, 220); color: white; "
            "padding: 12px 24px; border-radius: 8px; font-size: 13px; font-weight: bold;"
        )
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, duration_ms: int = 2500):
        self.setText(text)
        self.adjustSize()
        if self.parent():
            p = self.parent()
            self.move(
                (p.width() - self.width()) // 2,
                (p.height() - self.height()) // 2,
            )
        self.show()
        self.raise_()
        self._timer.start(duration_ms)


class LoadingOverlay(QWidget):
    """副屏加载中覆盖层"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel("正在加载媒体…")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 18px; font-weight: bold; background: transparent;")
        layout.addWidget(self.label)
        self.hide()

    def show_loading(self):
        self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()

    def hide_loading(self):
        self.hide()


class PlayerWindow(QMainWindow):
    """全屏播放器窗口"""
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, screen_geometry):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setGeometry(screen_geometry)
        self.setStyleSheet("background-color: black;")

        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        self.video_widget.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.video_widget)
        self.stacked_widget.addWidget(self.image_label)
        self.setCentralWidget(self.stacked_widget)

        self.loading_overlay = LoadingOverlay(self)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)

        self.video_list = []
        self.image_list = []
        self.current_index = -1
        self.is_image_mode = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.is_image_mode and 0 <= self.current_index < len(self.image_list):
            self._rescale_current_image()
        if self.loading_overlay.isVisible():
            self.loading_overlay.setGeometry(self.rect())

    def _rescale_current_image(self):
        if 0 <= self.current_index < len(self.image_list):
            pixmap = QPixmap(self.image_list[self.current_index])
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.stacked_widget.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.image_label.setPixmap(scaled)

    def set_video_list(self, video_list):
        self.video_list = video_list
        self.is_image_mode = False
        if video_list:
            self.loading_overlay.show_loading()
            self.play_video(0)

    def set_image_list(self, image_list):
        self.image_list = image_list
        self.is_image_mode = True
        self.media_player.stop()
        if image_list:
            self.play_image(0)

    def play_video(self, index):
        if 0 <= index < len(self.video_list):
            self.current_index = index
            self.is_image_mode = False
            self.stacked_widget.setCurrentWidget(self.video_widget)
            url = QUrl.fromLocalFile(self.video_list[index])
            self.media_player.setSource(url)
            self.media_player.play()
            self.loading_overlay.hide_loading()
            self.currentIndexChanged.emit(index)

    def play_image(self, index):
        if 0 <= index < len(self.image_list):
            self.current_index = index
            self.is_image_mode = True
            self.stacked_widget.setCurrentWidget(self.image_label)
            self._rescale_current_image()
            self.currentIndexChanged.emit(index)

    def on_media_status_changed(self, status):
        if self.is_image_mode:
            return
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.video_list:
                next_index = (self.current_index + 1) % len(self.video_list)
                self.play_video(next_index)
        elif status in (QMediaPlayer.MediaStatus.InvalidMedia, QMediaPlayer.MediaStatus.NoMedia):
            logger.warning(f"媒体加载失败: index={self.current_index}")
            if self.video_list:
                next_index = (self.current_index + 1) % len(self.video_list)
                self.play_video(next_index)

    def pause_play(self):
        if self.is_image_mode:
            return True
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            return False
        else:
            self.media_player.play()
            return True

    def toggle_mute(self):
        current_state = self.audio_output.isMuted()
        self.audio_output.setMuted(not current_state)
        return self.audio_output.isMuted()

    def prev_video(self):
        if self.is_image_mode:
            if self.image_list:
                idx = (self.current_index - 1) % len(self.image_list)
                self.play_image(idx)
        else:
            if self.video_list:
                idx = (self.current_index - 1) % len(self.video_list)
                self.play_video(idx)

    def next_video(self):
        if self.is_image_mode:
            if self.image_list:
                idx = (self.current_index + 1) % len(self.image_list)
                self.play_image(idx)
        else:
            if self.video_list:
                idx = (self.current_index + 1) % len(self.video_list)
                self.play_video(idx)


class ExitDialog(QDialog):
    """退出确认三选一对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("退出 MT-Player")
        self.setFixedSize(320, 140)
        layout = QVBoxLayout(self)
        label = QLabel("请选择操作：")
        label.setStyleSheet("font-size: 14px;")
        layout.addWidget(label)

        btn_box = QDialogButtonBox()
        self.btn_minimize = btn_box.addButton("最小化到托盘", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_exit = btn_box.addButton("退出程序", QDialogButtonBox.ButtonRole.DestructiveRole)
        self.btn_cancel = btn_box.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        self.btn_exit.setStyleSheet("color: #e81123; font-weight: bold;")
        layout.addWidget(btn_box)

        self.result_action = None
        self.btn_minimize.clicked.connect(lambda: self._set_result("minimize"))
        self.btn_exit.clicked.connect(lambda: self._set_result("exit"))
        self.btn_cancel.clicked.connect(lambda: self._set_result("cancel"))

    def _set_result(self, action):
        self.result_action = action
        self.accept()


class VideoPlayerApp(QMainWindow):
    """主控制窗口"""

    def __init__(self, headless=False):
        super().__init__()

        self.setWindowTitle("MT-Player")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
            }
            QListWidget {
                background-color: #e0e0e0;
                color: #000000;
                border: 1px solid #888;
                font-size: 14px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                padding: 5px;
                margin: 0;
                width: 40px;
                height: 40px;
                border-radius: 20px;
            }
            QToolButton:hover {
                background-color: rgba(255,255,255,0.1);
            }
            QToolButton:pressed {
                background-color: rgba(255,255,255,0.2);
            }
            QTabBar::tab {
                background-color: #3d3d3d;
                color: #e0e0e0;
                padding: 5px 15px;
                border: 1px solid #555;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
        """)

        self.headless = headless
        self.library = MediaLibrary()
        self.controller = PlayerController(self)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === 标题栏 ===
        title_bar = QWidget()
        title_bar.setFixedHeight(56)
        title_bar.setStyleSheet("background-color: #000000;")
        title_layout = QHBoxLayout()
        title_label = QLabel()
        title_label.setText(
            f"<span style='font-size: 18px;'>MT-Player</span>"
            f"&nbsp;&nbsp;<span style='font-size: 9px;'>BY:HAE v{__version__}</span>"
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        title_layout.addWidget(title_label)

        self.btn_exit_app = QToolButton()
        self.btn_exit_app.setText("✕")
        self.btn_exit_app.setFixedSize(32, 32)
        self.btn_exit_app.setStyleSheet(
            "QToolButton { color: #e0e0e0; font-size: 16px; font-weight: bold; }"
            "QToolButton:hover { background-color: #e81123; color: white; }"
        )
        self.btn_exit_app.setToolTip("退出程序")
        self.btn_exit_app.clicked.connect(self._on_exit_clicked)
        title_layout.addWidget(self.btn_exit_app)
        title_bar.setLayout(title_layout)
        main_layout.addWidget(title_bar)

        # === 屏幕选择区域 ===
        screen_layout = QHBoxLayout()
        screen_layout.setContentsMargins(10, 5, 10, 5)
        screen_label = QLabel("屏幕选择：")
        screen_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        self.screen_combo = QComboBox()
        self.screen_combo.setFixedHeight(20)
        self.screen_combo.setStyleSheet("""
            QComboBox {
                background-color: #353535;
                color: #e0e0e0;
                border: 1px solid #555;
                padding: 3px;
                padding-right: 20px;
                font-size: 12px;
                border-radius: 3px;
            }
            QComboBox::drop-down {
                background-color: #454545;
                border: none;
                border-left: 1px solid #555;
                width: 20px;
                subcontrol-origin: border;
                subcontrol-position: top right;
            }
            QComboBox::down-arrow {
                image: none;
                background-color: transparent;
                width: 6px;
                height: 6px;
                border-right: 2px solid #e0e0e0;
                border-bottom: 2px solid #e0e0e0;
                margin: -2px -8px 0 0;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e0e0e0;
                selection-background-color: #0078d4;
                selection-color: white;
                font-size: 12px;
                border: 1px solid #444;
            }
        """)
        screen_layout.addWidget(screen_label)
        screen_layout.addWidget(self.screen_combo)

        self.status_badge = QLabel("● 未投放")
        self.status_badge.setStyleSheet(
            "color: #888; font-size: 11px; padding-left: 8px;"
        )
        screen_layout.addWidget(self.status_badge)
        screen_layout.addStretch()

        screen_widget = QWidget()
        screen_widget.setFixedHeight(30)
        screen_widget.setLayout(screen_layout)
        main_layout.addWidget(screen_widget)

        # === 选项卡 ===
        self.tab_widget = QTabWidget()
        self.tab_widget.setFixedHeight(210)

        list_stylesheet = """
            QListWidget {
                background-color: #e0e0e0;
                color: #000000;
                border: 1px solid #888;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 5px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
            }
            QListWidget::item:hover {
                background-color: #d0d0d0;
            }
        """

        self.video_list_widget = QListWidget()
        self.video_list_widget.setStyleSheet(list_stylesheet)
        self.image_list_widget = QListWidget()
        self.image_list_widget.setStyleSheet(list_stylesheet)

        self.tab_widget.addTab(self.video_list_widget, "视频列表")
        self.tab_widget.addTab(self.image_list_widget, "图片列表")
        main_layout.addWidget(self.tab_widget)

        # === 按钮栏 ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.setContentsMargins(10, 5, 10, 5)

        btn_defs = [
            ("img/从文件夹导入.png", "folder", "从文件夹导入", self.controller.addFilesRequested, None),
            ("img/添加视频.png", "add_file", "添加文件", self.controller.addFilesRequested, None),
            ("img/播放.png", "play_pause", "播放/暂停", None, None),
            ("img/上一个.png", "prev", "上一个", None, None),
            ("img/下一个.png", "next", "下一个", None, None),
            ("img/取消静音.png", "mute", "静音/取消静音", None, None),
            ("img/继续投放.png", "projection", "投放/取消投放", None, None),
        ]

        self.buttons = {}
        for icon_path, name, tooltip, _, _ in btn_defs:
            btn = self._create_tool_button(icon_path, name, tooltip)
            self.buttons[name] = btn
            button_layout.addWidget(btn)

        self.btn_folder = self.buttons["folder"]
        self.btn_add_file = self.buttons["add_file"]
        self.btn_play_pause = self.buttons["play_pause"]
        self.btn_prev = self.buttons["prev"]
        self.btn_next = self.buttons["next"]
        self.btn_mute = self.buttons["mute"]
        self.btn_projection = self.buttons["projection"]

        button_widget = QWidget()
        button_widget.setFixedHeight(38)
        button_widget.setStyleSheet("background-color: #1e1e1e;")
        button_widget.setLayout(button_layout)
        main_layout.addWidget(button_widget)

        left_container = QWidget()
        left_container.setLayout(main_layout)

        outer_layout = QHBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(left_container)

        # 右侧预览面板
        preview_container = QVBoxLayout()
        preview_container.setContentsMargins(0, 0, 0, 0)
        preview_title = QLabel("目标屏幕预览")
        preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_title.setStyleSheet(
            "background-color: #111; color: #888; font-size: 11px; "
            "padding: 4px; border-left: 1px solid #444; border-bottom: 1px solid #444;"
        )
        preview_container.addWidget(preview_title)

        self.preview_label = QLabel("无信号")
        self.preview_label.setFixedWidth(PREVIEW_PANEL_WIDTH)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet(
            "background-color: #111; color: #555; font-size: 12px; border-left: 1px solid #444;"
        )
        preview_container.addWidget(self.preview_label)

        preview_wrapper = QWidget()
        preview_wrapper.setLayout(preview_container)
        outer_layout.addWidget(preview_wrapper)

        central_widget.setLayout(outer_layout)

        # 状态
        self.player_window = None
        self.is_muted = False
        self.current_mode = "video"
        self.is_projecting = False
        self._projection_debounce = False

        self.init_screens()

        self.toast = ToastLabel(self)

        self.screen_combo.currentIndexChanged.connect(self._on_screen_changed)

        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(PREVIEW_UPDATE_INTERVAL)
        self.preview_timer.timeout.connect(self.update_screen_preview)
        if not headless:
            self.preview_timer.start()

        # 按钮信号
        self.btn_folder.clicked.connect(self._on_add_folder)
        self.btn_add_file.clicked.connect(self._on_add_files)
        self.btn_play_pause.clicked.connect(self._on_toggle_play_pause)
        self.btn_prev.clicked.connect(self._on_prev)
        self.btn_next.clicked.connect(self._on_next)
        self.btn_mute.clicked.connect(self._on_toggle_mute)
        self.btn_projection.clicked.connect(self._on_toggle_projection)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # MediaLibrary 信号 → 同步列表 UI
        self.library.videosChanged.connect(self._sync_video_list_ui)
        self.library.imagesChanged.connect(self._sync_image_list_ui)

        self.setup_tray_icon()

    def _create_tool_button(self, icon_rel_path, name, tooltip):
        btn = QToolButton()
        btn.setObjectName(name)
        btn.setToolTip(tooltip)
        icon_path = resource_path(icon_rel_path)
        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            btn.setText(tooltip[:2])
            btn.setStyleSheet("color: #e0e0e0; font-size: 10px;")
        else:
            pixmap = pixmap.scaled(
                ICON_SIZE, ICON_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            btn.setIcon(QIcon(pixmap))
        return btn

    def _update_button_icon(self, button, icon_rel_path):
        icon_path = resource_path(icon_rel_path)
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                ICON_SIZE, ICON_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            button.setIcon(QIcon(pixmap))

    def init_screens(self):
        app = QApplication.instance()
        screens = app.screens()
        self.screen_combo.clear()
        for i, screen in enumerate(screens):
            geo = screen.geometry()
            is_primary = screen == app.primaryScreen()
            label = f"屏幕 {i+1} ({geo.width()}x{geo.height()})" + (" [主屏]" if is_primary else "")
            self.screen_combo.addItem(label, screen)

    def _on_screen_changed(self, index):
        self.update_screen_preview()
        if self.is_projecting:
            self.toast.show_message("切换屏幕需重新投放", 2000)

    def _on_tab_changed(self, index):
        self.current_mode = "video" if index == 0 else "image"
        if self.is_projecting and self.player_window and self.player_window.isVisible():
            self._sync_projection_content()

    def _sync_projection_content(self):
        if not self.player_window or not self.player_window.isVisible():
            return
        try:
            self.player_window.currentIndexChanged.disconnect()
        except TypeError:
            pass

        snap = self.library.snapshot()
        if self.current_mode == "video":
            if snap['videos']:
                self.player_window.set_video_list(snap['videos'])
                self.player_window.currentIndexChanged.connect(self._sync_video_list_selection)
            else:
                self.toast.show_message("视频列表为空")
                return
        else:
            if snap['images']:
                self.player_window.set_image_list(snap['images'])
                self.player_window.currentIndexChanged.connect(self._sync_image_list_selection)
            else:
                self.toast.show_message("图片列表为空")
                return

    def start_projection(self):
        snap = self.library.snapshot()
        if self.current_mode == "video":
            content_list = snap['videos']
        else:
            content_list = snap['images']

        if not content_list:
            self.toast.show_message("列表为空，请先添加媒体文件")
            return

        target_screen = self.screen_combo.currentData()
        if not target_screen:
            logger.error("无法获取屏幕对象")
            return

        if not self._check_different_screen(target_screen):
            self.toast.show_message("投放屏幕不能与应用所在屏幕相同")
            return

        if self._projection_debounce:
            return
        self._projection_debounce = True
        QTimer.singleShot(500, lambda: setattr(self, '_projection_debounce', False))

        self.player_window = PlayerWindow(target_screen.geometry())

        if self.current_mode == "video":
            self.player_window.set_video_list(content_list)
            self.player_window.currentIndexChanged.connect(self._sync_video_list_selection)
        else:
            self.player_window.set_image_list(content_list)
            self.player_window.currentIndexChanged.connect(self._sync_image_list_selection)

        self.player_window.showFullScreen()
        self.is_projecting = True
        self._update_projection_ui()
        logger.info(f"开始投放{self.current_mode}内容")

    def _check_different_screen(self, target_screen):
        app = QApplication.instance()
        main_window_screen = app.screenAt(self.geometry().center())
        return target_screen != main_window_screen

    def stop_projection(self):
        if self.player_window:
            try:
                self.player_window.currentIndexChanged.disconnect()
            except TypeError:
                pass
            self.player_window.media_player.stop()
            self.player_window.close()
            self.player_window = None
        self.is_projecting = False
        self._update_projection_ui()

    def _update_projection_ui(self):
        if self.is_projecting:
            self.btn_projection.setToolTip("取消投放")
            self._update_button_icon(self.btn_projection, "img/取消投放.png")
            idx = self.screen_combo.currentIndex()
            self.status_badge.setText(f"● 投放中（屏幕{idx + 1}）")
            self.status_badge.setStyleSheet("color: #4ec9b0; font-size: 11px; padding-left: 8px;")
        else:
            self.btn_projection.setToolTip("投放/取消投放")
            self._update_button_icon(self.btn_projection, "img/继续投放.png")
            self.status_badge.setText("● 未投放")
            self.status_badge.setStyleSheet("color: #888; font-size: 11px; padding-left: 8px;")

    def update_screen_preview(self):
        if self.headless or not self.isVisible():
            return
        app = QApplication.instance()
        screen = self.screen_combo.currentData() or app.primaryScreen()
        if not screen:
            return
        try:
            geo = screen.geometry()
            pix = screen.grabWindow(0, geo.x(), geo.y(), geo.width(), geo.height())
            if pix and not pix.isNull():
                target_size = self.preview_label.size()
                scaled = pix.scaled(
                    target_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.preview_label.setPixmap(scaled)
        except Exception as e:
            logger.debug(f"预览更新异常: {e}")

    def setup_tray_icon(self):
        tray_icon_path = resource_path("img/app.ico")
        if Path(tray_icon_path).exists():
            icon = QIcon(tray_icon_path)
        else:
            png_path = resource_path("img/app.png")
            if Path(png_path).exists():
                icon = QIcon(png_path)
            else:
                icon = QIcon()

        self.tray_icon = QSystemTrayIcon(icon, self)
        menu = QMenu()
        restore_action = QAction("显示主窗口", self)
        quit_action = QAction("退出", self)
        restore_action.triggered.connect(self.show)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(restore_action)
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def _on_exit_clicked(self):
        self.show()
        self._ask_exit()

    def _ask_exit(self):
        dialog = ExitDialog(self)
        dialog.exec()
        action = dialog.result_action
        if action == "minimize":
            self.hide()
            self.tray_icon.showMessage(
                "MT-Player", "程序已最小化到系统托盘",
                QSystemTrayIcon.MessageIcon.Information, 2000,
            )
        elif action == "exit":
            self._quit_app()
        # cancel → do nothing

    def _quit_app(self):
        if self.player_window:
            self.player_window.media_player.stop()
            self.player_window.close()
        QApplication.quit()

    def closeEvent(self, event):
        self._ask_exit()
        event.ignore()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.headless:
            self.preview_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.preview_timer.stop()

    def _sync_video_list_selection(self, index):
        snap = self.library.snapshot()
        self._sync_list_selection(self.video_list_widget, snap['videos'], index)

    def _sync_image_list_selection(self, index):
        snap = self.library.snapshot()
        self._sync_list_selection(self.image_list_widget, snap['images'], index)

    def _sync_list_selection(self, list_widget, paths, index):
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if i == index and i < len(paths):
                file_name = Path(paths[i]).name
                item.setText(f"▶ {file_name}")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor("#0078d4"))
            else:
                file_name = Path(paths[i]).name if i < len(paths) else ""
                if file_name:
                    item.setText(file_name)
                    font = item.font()
                    font.setBold(False)
                    item.setFont(font)
                    item.setForeground(QColor("#000000"))
        list_widget.setCurrentRow(index)

    def _on_toggle_play_pause(self):
        if not self.is_projecting:
            self.toast.show_message("请先点击投放按钮")
            return
        player = self.player_window
        if player:
            is_playing = player.pause_play()
            icon_name = "img/暂停.png" if is_playing else "img/播放.png"
            self._update_button_icon(self.btn_play_pause, icon_name)

    def _on_toggle_mute(self):
        if not self.is_projecting:
            self.toast.show_message("请先点击投放按钮")
            return
        player = self.player_window
        if player:
            is_muted = player.toggle_mute()
            self.is_muted = is_muted
            icon_name = "img/静音.png" if is_muted else "img/取消静音.png"
            self._update_button_icon(self.btn_mute, icon_name)
            self.toast.show_message("已静音" if is_muted else "已取消静音", 1500)

    def _on_prev(self):
        if not self.is_projecting:
            self.toast.show_message("请先点击投放按钮")
            return
        if self.player_window:
            self.player_window.prev_video()

    def _on_next(self):
        if not self.is_projecting:
            self.toast.show_message("请先点击投放按钮")
            return
        if self.player_window:
            self.player_window.next_video()

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if not folder:
            return
        new_paths = []
        try:
            for file in Path(folder).iterdir():
                if file.is_file():
                    new_paths.append(str(file.resolve()))
        except Exception as e:
            logger.error(f"读取文件夹出错: {e}")
            self.toast.show_message(f"读取文件夹失败")
            return

        result = self.library.add(new_paths)
        added = len(result['added_videos']) + len(result['added_images'])
        if added > 0:
            self.toast.show_message(f"已添加 {added} 个文件")
        else:
            self.toast.show_message("文件夹中没有支持的媒体文件")

    def _on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "",
            "媒体文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.png *.jpg *.jpeg)",
        )
        if not files:
            return
        result = self.library.add(files)
        added = len(result['added_videos']) + len(result['added_images'])
        self.toast.show_message(f"已添加 {added} 个文件")

    def _on_toggle_projection(self):
        if self.is_projecting:
            self.stop_projection()
        else:
            self.start_projection()

    def _sync_video_list_ui(self):
        snap = self.library.snapshot()
        self.video_list_widget.clear()
        for p in snap['videos']:
            self.video_list_widget.addItem(Path(p).name)

    def _sync_image_list_ui(self):
        snap = self.library.snapshot()
        self.image_list_widget.clear()
        for p in snap['images']:
            self.image_list_widget.addItem(Path(p).name)

    def runInMainThread(self, fn):
        fn()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MT-Player 多屏播控播放器')
    parser.add_argument('--api', action='store_true', help='启用 REST API 服务器')
    parser.add_argument('--port', type=int, default=5000, help='API 服务器端口 (默认: 5000)')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='API 服务器主机 (默认: 127.0.0.1)')
    parser.add_argument('--token', type=str, default=None, help='API 鉴权 Token（非 localhost 时必填）')
    parser.add_argument('--mcp', action='store_true', help='启用 MCP 服务器')
    parser.add_argument('--headless', action='store_true', help='无界面模式')
    args = parser.parse_args()

    if args.host != '127.0.0.1' and not args.token:
        print("错误: 监听非 localhost 时必须提供 --token 参数")
        print("示例: python dual_screen_player.py --host 0.0.0.0 --token YOUR_SECRET")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = VideoPlayerApp(headless=args.headless)

    if not args.headless:
        window.show()
    else:
        window.hide()
        logger.info("无界面模式启动")

    if args.api:
        try:
            from api_server import init_api
            init_api(window, host=args.host, port=args.port, token=args.token)
            logger.info(f"API 服务器已启用: http://{args.host}:{args.port}")
        except ImportError:
            logger.error("无法导入 Flask，请运行: pip install flask")

    if args.mcp:
        try:
            from mcp_server import start_mcp_server, MCP_AVAILABLE
            if MCP_AVAILABLE:
                start_mcp_server(window)
                logger.info("MCP 服务器已启用")
            else:
                logger.error("MCP 库未安装，请运行: pip install mcp")
        except ImportError:
            logger.error("无法导入 mcp_server，请运行: pip install mcp")

    sys.exit(app.exec())
