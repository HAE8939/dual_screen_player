import sys
import os
import logging
import argparse
import threading
import mss
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QListWidget, QToolButton, QFileDialog,
    QSystemTrayIcon, QMenu, QMessageBox, QTabWidget, QListWidgetItem,
    QStackedWidget, QDialog, QDialogButtonBox, QSizePolicy, QSplitter,
    QSizeGrip
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer, QSize, QThread
from PyQt6.QtGui import QIcon, QPixmap, QImage, QAction, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from media_library import MediaLibrary, SUPPORTED_VIDEO_EXTS, SUPPORTED_IMAGE_EXTS, __version__
from player_controller import PlayerController
from theme import build_stylesheet, CLAY_PRIMARY, TEXT_SECONDARY, DANGER
from icon_loader import load_icon
from widgets import GhostIconButton, PrimaryButton, StatusBadge, MediaListWidget

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MIN_WIDTH = 820
MIN_HEIGHT = 420
PREVIEW_PANEL_WIDTH = 260


def resource_path(relative_path):
    """资源路径：兼容 PyInstaller 打包（onefile/onedir）与源码运行。"""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class ToastLabel(QLabel):
    """非阻塞 Toast 提示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toastLabel")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
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


class PreviewWorker(QThread):
    """后台线程：抓取屏幕预览帧，避免阻塞主线程"""
    frame_ready = pyqtSignal(QImage)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._screen = None
        self._lock = threading.Lock()

    def set_screen(self, screen):
        with self._lock:
            self._screen = screen

    def run(self):
        self._running = True
        while self._running:
            screen = None
            with self._lock:
                screen = self._screen
            if screen:
                try:
                    geo = screen.geometry()
                    with mss.MSS() as sct:
                        monitor = {
                            "left": geo.x(), "top": geo.y(),
                            "width": geo.width(), "height": geo.height(),
                        }
                        shot = sct.grab(monitor)
                        img = QImage(
                            shot.rgb, shot.width, shot.height,
                            shot.width * 3, QImage.Format.Format_RGB888,
                        )
                        self.frame_ready.emit(img.copy())
                except Exception:
                    pass
            self.msleep(1500)

    def stop(self):
        self._running = False
        self.wait()


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
        self._tearing_down = False

    def teardown(self):
        self._tearing_down = True
        try:
            self.media_player.mediaStatusChanged.disconnect(self.on_media_status_changed)
        except (TypeError, RuntimeError):
            pass
        try:
            self.media_player.setSource(QUrl())
            self.media_player.stop()
        except Exception:
            pass

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
        if self.is_image_mode or getattr(self, "_tearing_down", False):
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
        layout.addWidget(label)

        btn_box = QDialogButtonBox()
        self.btn_minimize = btn_box.addButton("最小化到托盘", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_exit = btn_box.addButton("退出程序", QDialogButtonBox.ButtonRole.DestructiveRole)
        self.btn_cancel = btn_box.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        self.btn_exit.setObjectName("exitDialogBtn")
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

    def __init__(self, headless=False, theme="light"):
        super().__init__()

        self.setWindowTitle("MT-Player")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.resize(MIN_WIDTH, MIN_HEIGHT)
        self._drag_pos = None
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_rect = None

        # 全局样式
        QApplication.instance().setStyleSheet(build_stylesheet(theme))

        self.headless = headless
        self.library = MediaLibrary()
        self.controller = PlayerController(self)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        outer_layout = QHBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # === 左侧面板 ===
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # --- 标题栏（可拖动）---
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(50)
        title_bar.mousePressEvent = self._title_bar_mouse_press
        title_bar.mouseMoveEvent = self._title_bar_mouse_move
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(16, 0, 8, 0)

        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(6)
        brand_label = QLabel("MT-Player")
        brand_label.setObjectName("titleLabel")
        brand_label.setStyleSheet("background: transparent;")
        version_label = QLabel(f"v{__version__}")
        version_label.setObjectName("versionLabel")
        version_label.setStyleSheet("background: transparent;")
        brand_layout.addWidget(brand_label)
        brand_layout.addWidget(version_label)
        brand_layout.addStretch()
        title_layout.addLayout(brand_layout)

        self.btn_minimize = QToolButton()
        self.btn_minimize.setObjectName("minimizeBtn")
        self.btn_minimize.setText("─")
        self.btn_minimize.setFixedSize(32, 32)
        self.btn_minimize.setToolTip("最小化")
        self.btn_minimize.clicked.connect(self.showMinimized)
        title_layout.addWidget(self.btn_minimize)

        self.btn_exit_app = QToolButton()
        self.btn_exit_app.setObjectName("exitBtn")
        self.btn_exit_app.setText("✕")
        self.btn_exit_app.setFixedSize(32, 32)
        self.btn_exit_app.setToolTip("退出程序")
        self.btn_exit_app.clicked.connect(self._on_exit_clicked)
        title_layout.addWidget(self.btn_exit_app)

        title_bar.setLayout(title_layout)
        left_layout.addWidget(title_bar)

        # --- 屏幕选择行 ---
        screen_row = QWidget()
        screen_row.setFixedHeight(36)
        screen_layout = QHBoxLayout()
        screen_layout.setContentsMargins(16, 4, 16, 4)

        screen_label = QLabel("屏幕")
        screen_label.setObjectName("screenLabel")
        screen_layout.addWidget(screen_label)

        self.screen_combo = QComboBox()
        self.screen_combo.setFixedHeight(24)
        self.screen_combo.setMinimumWidth(180)
        screen_layout.addWidget(self.screen_combo)

        self.status_badge = StatusBadge()
        screen_layout.addWidget(self.status_badge)
        screen_layout.addStretch()

        screen_row.setLayout(screen_layout)
        left_layout.addWidget(screen_row)

        # --- 选项卡 ---
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumHeight(180)

        self.video_list_widget = MediaListWidget()
        self.image_list_widget = MediaListWidget()

        self.tab_widget.addTab(self.video_list_widget, "视频列表")
        self.tab_widget.addTab(self.image_list_widget, "图片列表")
        left_layout.addWidget(self.tab_widget, 1)

        # --- 按钮栏 ---
        button_bar = QWidget()
        button_bar.setObjectName("buttonBar")
        button_bar.setFixedHeight(72)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(16, 4, 16, 4)
        button_layout.setSpacing(4)

        self.btn_folder = GhostIconButton("folder", "导入", "从文件夹导入")
        self.btn_add_file = GhostIconButton("add", "添加", "添加文件")
        self.btn_play_pause = GhostIconButton("play", "播放", "播放/暂停")
        self.btn_prev = GhostIconButton("prev", "上一个", "上一个")
        self.btn_next = GhostIconButton("next", "下一个", "下一个")
        self.btn_mute = GhostIconButton("unmute", "静音", "静音/取消静音")

        for w in [self.btn_folder, self.btn_add_file, self.btn_play_pause,
                  self.btn_prev, self.btn_next, self.btn_mute]:
            button_layout.addWidget(w)

        button_layout.addStretch()

        self.btn_projection = PrimaryButton("投放", "projection", "投放/取消投放")
        button_layout.addWidget(self.btn_projection)

        button_bar.setLayout(button_layout)
        left_layout.addWidget(button_bar)

        left_panel.setLayout(left_layout)
        outer_layout.addWidget(left_panel, 1)

        # === 右侧预览面板 ===
        preview_container = QVBoxLayout()
        preview_container.setContentsMargins(0, 0, 0, 0)
        preview_container.setSpacing(0)

        preview_title = QLabel("目标屏幕预览")
        preview_title.setObjectName("previewTitle")
        preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_container.addWidget(preview_title)

        self.preview_label = QLabel("无信号")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setMinimumWidth(PREVIEW_PANEL_WIDTH)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_container.addWidget(self.preview_label, 1)

        preview_wrapper = QWidget()
        preview_wrapper.setLayout(preview_container)
        outer_layout.addWidget(preview_wrapper)

        main_layout.addLayout(outer_layout, 1)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 4, 4)
        grip_row.addStretch()
        size_grip = QSizeGrip(self)
        size_grip.setFixedSize(16, 16)
        grip_row.addWidget(size_grip)
        main_layout.addLayout(grip_row)

        central_widget.setLayout(main_layout)

        # 状态
        self.player_window = None
        self._projecting_screen = None
        self.is_muted = False
        self.current_mode = "video"
        self.is_projecting = False
        self._projection_debounce = False

        self.init_screens()

        self.toast = ToastLabel(self)

        self.screen_combo.currentIndexChanged.connect(self._on_screen_changed)

        # 预览 worker 线程（替代主线程 mss.grab）
        self._preview_worker = PreviewWorker(self)
        self._preview_worker.frame_ready.connect(self._on_preview_frame)
        self._preview_worker.set_screen(self.screen_combo.currentData())
        if not headless:
            self._preview_worker.start()

        # 屏幕热插拔信号（替代 3 秒轮询）
        qapp = QApplication.instance()
        qapp.screenAdded.connect(self._on_screens_changed)
        qapp.screenRemoved.connect(self._on_screens_changed)

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

        # 启动时恢复上次的媒体列表
        result = self.library.load_from_disk()
        total = result['videos'] + result['images']
        if total > 0:
            msg = f"已恢复 {total} 个文件"
            if result['missing'] > 0:
                msg += f"，{result['missing']} 个已丢失"
            self.toast.show_message(msg, 3000)

    def init_screens(self):
        app = QApplication.instance()
        screens = app.screens()
        self.screen_combo.clear()
        for i, screen in enumerate(screens):
            geo = screen.geometry()
            is_primary = screen == app.primaryScreen()
            label = f"屏幕 {i+1} ({geo.width()}×{geo.height()})" + (" [主屏]" if is_primary else "")
            self.screen_combo.addItem(label, screen)

    def _on_screen_changed(self, index):
        screen = self.screen_combo.currentData()
        if self._preview_worker and screen:
            self._preview_worker.set_screen(screen)
        if self.is_projecting:
            self.toast.show_message("切换屏幕需重新投放", 2000)

    def _on_screens_changed(self, screen=None):
        """Qt 原生热插拔信号回调 —— 重建下拉框，屏蔽信号避免误报"""
        self.screen_combo.blockSignals(True)
        self.init_screens()
        self.screen_combo.blockSignals(False)

        if self.is_projecting and self.player_window:
            app = QApplication.instance()
            if self._projecting_screen not in app.screens():
                self.toast.show_message("目标屏幕已断开，停止投放")
                self.stop_projection()

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
        content_list = snap['videos'] if self.current_mode == "video" else snap['images']

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

        name = target_screen.name()

        if self._projection_debounce:
            return
        self._projection_debounce = True
        QTimer.singleShot(500, lambda: setattr(self, '_projection_debounce', False))

        self.player_window = PlayerWindow(target_screen.geometry())
        self._projecting_screen = target_screen

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
        pw = self.player_window
        self.player_window = None
        self._projecting_screen = None
        self.is_projecting = False
        self._update_projection_ui()
        if pw:
            try:
                pw.currentIndexChanged.disconnect()
            except TypeError:
                pass
            pw.teardown()
            pw.hide()
            pw.deleteLater()

    def _update_projection_ui(self):
        if self.is_projecting:
            self.btn_projection.set_active(True)
            idx = self.screen_combo.currentIndex()
            self.status_badge.set_state("projecting", screen_index=idx + 1)
        else:
            self.btn_projection.set_active(False)
            self.status_badge.set_state("idle")

    def _on_preview_frame(self, img: QImage):
        """预览 worker 线程回调 —— 在主线程设置 pixmap"""
        pix = QPixmap.fromImage(img)
        if not pix.isNull():
            target_size = self.preview_label.size()
            scaled = pix.scaled(
                target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview_label.setPixmap(scaled)

    def _load_app_icon(self):
        """加载多分辨率应用图标：优先 ico（含 16/24/32/48/64/128/256），回退 png。"""
        ico_path = resource_path("img/app.ico")
        if Path(ico_path).exists():
            return QIcon(ico_path)
        png_path = resource_path("img/app.png")
        if Path(png_path).exists():
            return QIcon(png_path)
        return QIcon()

    def setup_tray_icon(self):
        icon = self._load_app_icon()
        self.setWindowIcon(icon)  # 任务栏 / Alt-Tab / 窗口标题图标

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

    def _quit_app(self):
        if self.player_window:
            self.player_window.teardown()
            self.player_window.hide()
            self.player_window.deleteLater()
        if getattr(self, "_preview_worker", None):
            self._preview_worker.stop()
        QApplication.quit()

    # === 窗口拖动 ===

    def _title_bar_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _title_bar_mouse_move(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    _EDGE_MARGIN = 6

    def _hit_test_edges(self, pos):
        rect = self.rect()
        x, y = pos.x(), pos.y()
        m = self._EDGE_MARGIN
        if x < m:
            if y < m:
                return "top-left"
            elif y > rect.height() - m:
                return "bottom-left"
            return "left"
        if x > rect.width() - m:
            if y < m:
                return "top-right"
            elif y > rect.height() - m:
                return "bottom-right"
            return "right"
        if y < m:
            return "top"
        if y > rect.height() - m:
            return "bottom"
        return None

    _EDGE_CURSORS = {
        "top-left": Qt.CursorShape.SizeFDiagCursor,
        "bottom-right": Qt.CursorShape.SizeFDiagCursor,
        "top-right": Qt.CursorShape.SizeBDiagCursor,
        "bottom-left": Qt.CursorShape.SizeBDiagCursor,
        "left": Qt.CursorShape.SizeHorCursor,
        "right": Qt.CursorShape.SizeHorCursor,
        "top": Qt.CursorShape.SizeVerCursor,
        "bottom": Qt.CursorShape.SizeVerCursor,
    }

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            edge = self._hit_test_edges(pos)
            if edge and not self.childAt(pos):
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_rect = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, '_resize_edge') and self._resize_edge and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            r = self._resize_start_rect
            new_rect = r.adjusted(0, 0, 0, 0)
            if "right" in self._resize_edge:
                new_rect.setRight(r.right() + delta.x())
            if "bottom" in self._resize_edge:
                new_rect.setBottom(r.bottom() + delta.y())
            if "left" in self._resize_edge:
                new_rect.setLeft(r.left() + delta.x())
            if "top" in self._resize_edge:
                new_rect.setTop(r.top() + delta.y())
            if new_rect.width() >= MIN_WIDTH and new_rect.height() >= MIN_HEIGHT:
                self.setGeometry(new_rect)
            event.accept()
            return
        edge = self._hit_test_edges(event.position().toPoint())
        if edge and not self.childAt(event.position().toPoint()):
            self.setCursor(self._EDGE_CURSORS.get(edge, Qt.CursorShape.ArrowCursor))
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resize_edge = None
        self._drag_pos = None
        self.unsetCursor()
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        self._ask_exit()
        event.ignore()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.headless and not self._preview_worker.isRunning():
            self._preview_worker.set_screen(self.screen_combo.currentData())
            self._preview_worker.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._preview_worker.stop()

    def _sync_video_list_selection(self, index):
        snap = self.library.snapshot()
        self._sync_list_selection(self.video_list_widget, snap['videos'], index)

    def _sync_image_list_selection(self, index):
        snap = self.library.snapshot()
        self._sync_list_selection(self.image_list_widget, snap['images'], index)

    def _sync_list_selection(self, list_widget, paths, index):
        for i in range(list_widget.count()):
            name = Path(paths[i]).name if i < len(paths) else ""
            list_widget.update_item(i, name, is_playing=(i == index))
        list_widget.setCurrentRow(index)

    def _on_toggle_play_pause(self):
        if not self.is_projecting:
            self.toast.show_message("请先点击投放按钮")
            return
        player = self.player_window
        if not player:
            return
        if player.is_image_mode:
            self.toast.show_message("图片模式无需播放控制", 1500)
            return
        # pause_play() 已切换播放器状态，这里只需同步 UI（避免重复 play/pause）
        is_playing = player.pause_play()
        self._update_play_pause_ui(is_playing)

    def _on_toggle_mute(self):
        if not self.is_projecting:
            self.toast.show_message("请先点击投放按钮")
            return
        player = self.player_window
        if not player:
            return
        if player.is_image_mode:
            self.toast.show_message("图片模式无需静音控制", 1500)
            return
        is_muted = player.toggle_mute()
        self._apply_mute(is_muted)
        self.toast.show_message("已静音" if is_muted else "已取消静音", 1500)

    def _update_mute_ui(self, is_muted: bool):
        self.is_muted = is_muted
        icon_name = "mute" if is_muted else "unmute"
        self.btn_mute.set_icon(icon_name)
        self.btn_mute.label.setText("静音" if is_muted else "取消静音")

    def _apply_mute(self, muted: bool):
        """远程控制统一入口 —— 同时更新播放器状态与 UI"""
        if self.player_window and not self.player_window.is_image_mode:
            self.player_window.audio_output.setMuted(muted)
        self._update_mute_ui(muted)

    def _update_play_pause_ui(self, play: bool):
        icon_name = "pause" if play else "play"
        self.btn_play_pause.set_icon(icon_name)
        self.btn_play_pause.label.setText("暂停" if play else "播放")

    def _apply_play_pause(self, play: bool):
        """远程控制统一入口 —— 同时更新播放器状态与 UI"""
        if self.player_window:
            if play:
                self.player_window.media_player.play()
            else:
                self.player_window.media_player.pause()
            self._update_play_pause_ui(play)

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

        result = self.library.add_from_folder(folder)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MT-Player 多屏播控播放器')
    parser.add_argument('--api', action='store_true', help='启用 REST API 服务器')
    parser.add_argument('--port', type=int, default=5000, help='API 服务器端口 (默认: 5000)')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='API 服务器主机 (默认: 127.0.0.1)')
    parser.add_argument('--token', type=str, default=None, help='API 鉴权 Token（非 localhost 时必填）')
    parser.add_argument('--mcp', action='store_true', help='启用 MCP 服务器')
    parser.add_argument('--headless', action='store_true', help='无界面模式')
    parser.add_argument('--theme', choices=['light', 'dark'], default='light', help='主题: light/dark')
    args = parser.parse_args()

    if args.host != '127.0.0.1' and not args.token:
        print("错误: 监听非 localhost 时必须提供 --token 参数")
        print("示例: python dual_screen_player.py --host 0.0.0.0 --token YOUR_SECRET")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = VideoPlayerApp(headless=args.headless, theme=args.theme)

    if not args.headless:
        window.show()
        window.raise_()
        window.activateWindow()
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
