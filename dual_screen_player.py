import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QListWidget, QToolButton, QFileDialog,
    QSystemTrayIcon, QMenu, QMessageBox, QTabWidget, QListWidgetItem,
    QStackedWidget
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QAction, QColor, QPainter
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


def resource_path(relative_path):
    """获取资源绝对路径，始终相对于本 .py 文件所在目录"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class PlayerWindow(QMainWindow):
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, screen_geometry):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )
        self.setGeometry(screen_geometry)
        self.setStyleSheet("background-color: black;")

        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        self.video_widget.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)  # 确保不透明

        # 创建绘制容器而不是QVideoWidget用于图片
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        
        # 使用栈窗口来切换视频和图片显示
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.video_widget)
        self.stacked_widget.addWidget(self.image_label)
        self.setCentralWidget(self.stacked_widget)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)

        self.video_list = []
        self.image_list = []
        self.current_index = -1
        self.is_image_mode = False
        self.current_image_pixmap = None  # 存储当前图片

        print("PlayerWindow 初始化完成")

    def set_video_list(self, video_list):
        self.video_list = video_list
        self.is_image_mode = False
        if video_list:
            self.play_video(0)

    def set_image_list(self, image_list):
        self.image_list = image_list
        self.is_image_mode = True
        self.media_player.stop()  # 停止视频播放
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
            self.currentIndexChanged.emit(index)

    def play_image(self, index):
        if 0 <= index < len(self.image_list):
            self.current_index = index
            self.is_image_mode = True
            self.stacked_widget.setCurrentWidget(self.image_label)
            image_path = self.image_list[index]
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # 缩放图片以适应屏幕
                scaled_pixmap = pixmap.scaledToWidth(
                    self.image_label.width() if self.image_label.width() > 0 else 1920,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
            self.currentIndexChanged.emit(index)

    def on_media_status_changed(self, status):
        # 仅在视频模式下处理自动播放
        if not self.is_image_mode and status == QMediaPlayer.MediaStatus.EndOfMedia:
            next_index = (self.current_index + 1) % len(self.video_list) if self.video_list else 0
            self.play_video(next_index)

    def pause_play(self):
        if self.is_image_mode:
            # 图片模式下暂停无意义，返回True表示"继续"
            return True
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            return False
        else:
            self.media_player.play()
            return True

    def toggle_mute(self):
        try:
            print("调用 PlayerWindow.toggle_mute 方法")
            print(f"audio_output 状态: {self.audio_output}")
            if not self.audio_output:
                print("错误: audio_output 未初始化！")
                return
            current_state = self.audio_output.isMuted()
            print(f"当前静音状态: {current_state}")
            self.audio_output.setMuted(not current_state)
            print(f"设置静音后: {self.audio_output.isMuted()}")
            return self.audio_output.isMuted()
        except Exception as e:
            print(f"toggle_mute 异常: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    def prev_video(self):
        if self.is_image_mode:
            if not self.image_list:
                return
            idx = (self.current_index - 1) % len(self.image_list)
            self.play_image(idx)
        else:
            if not self.video_list:
                return
            idx = (self.current_index - 1) % len(self.video_list)
            self.play_video(idx)

    def next_video(self):
        if self.is_image_mode:
            if not self.image_list:
                return
            idx = (self.current_index + 1) % len(self.image_list)
            self.play_image(idx)
        else:
            if not self.video_list:
                return
            idx = (self.current_index + 1) % len(self.video_list)
            self.play_video(idx)


class VideoPlayerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("MT-Player")
        self.setFixedSize(478, 420)
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                font-family: "Microsoft YaHei", sans-serif;
            }
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
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
                color: white;
                padding: 5px 15px;
                border: 1px solid #555;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === 标题栏 ===
        title_bar = QWidget()
        title_bar.setFixedHeight(56)
        title_bar.setStyleSheet("background-color: #000000;")
        title_label = QLabel()
        title_label.setText("<span style='font-size: 18px;'>MT-Player</span>&nbsp;&nbsp;<span style='font-size: 9px;'>BY:HAE</span>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: white; font-weight: bold;")
        title_layout = QHBoxLayout()
        title_layout.addWidget(title_label)
        title_bar.setLayout(title_layout)
        main_layout.addWidget(title_bar)

        # === 屏幕选择区域（高对比度）===
        screen_layout = QHBoxLayout()
        screen_layout.setContentsMargins(10, 5, 10, 5)
        screen_label = QLabel("屏幕选择：")
        screen_label.setStyleSheet("color: white; font-size: 12px;")
        self.screen_combo = QComboBox()
        self.screen_combo.setFixedHeight(20)
        self.screen_combo.setStyleSheet("""
            QComboBox {
                background-color: #353535;
                color: white;
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
                border-right: 2px solid white;
                border-bottom: 2px solid white;
                margin: -2px -8px 0 0;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: white;
                selection-background-color: #0078d4;
                selection-color: white;
                font-size: 12px;
                border: 1px solid #444;
            }
        """)
        screen_layout.addWidget(screen_label)
        screen_layout.addWidget(self.screen_combo)
        screen_widget = QWidget()
        screen_widget.setFixedHeight(30)
        screen_widget.setLayout(screen_layout)
        main_layout.addWidget(screen_widget)

        # === 选项卡（视频/图片列表）===
        self.tab_widget = QTabWidget()
        self.tab_widget.setFixedHeight(210)
        
        self.video_list_widget = QListWidget()
        self.video_list_widget.setStyleSheet("""
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
        """)
        
        self.image_list_widget = QListWidget()
        self.image_list_widget.setStyleSheet("""
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
        """)
        
        self.tab_widget.addTab(self.video_list_widget, "视频列表")
        self.tab_widget.addTab(self.image_list_widget, "图片列表")
        main_layout.addWidget(self.tab_widget)

        # === 按钮栏 ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.setContentsMargins(10, 5, 10, 5)

        self.btn_folder = self.create_tool_button("img/从文件夹导入.png", "folder")
        self.btn_add_file = self.create_tool_button("img/添加视频.png", "add_file")
        self.btn_play_pause = self.create_tool_button("img/播放.png", "play_pause")
        self.btn_prev = self.create_tool_button("img/上一个.png", "prev")
        self.btn_next = self.create_tool_button("img/下一个.png", "next")
        self.btn_mute = self.create_tool_button("img/取消静音.png", "mute")
        self.btn_projection = self.create_tool_button("img/继续投放.png", "projection")

        for btn in [self.btn_folder, self.btn_add_file, self.btn_play_pause,
                    self.btn_prev, self.btn_next, self.btn_mute, self.btn_projection]:
            button_layout.addWidget(btn)

        button_widget = QWidget()
        button_widget.setFixedHeight(38)
        button_widget.setStyleSheet("background-color: #2d2d2d;")
        button_widget.setLayout(button_layout)
        main_layout.addWidget(button_widget)

        central_widget.setLayout(main_layout)

        # 初始化
        self.video_paths = []
        self.image_paths = []
        self.player_window = None
        self.is_muted = False
        self.current_mode = "video"  # 当前模式：video 或 image
        self.is_projecting = False  # 投放状态标志

        self.init_screens()

        # 连接信号
        self.btn_folder.clicked.connect(self.add_folder)
        self.btn_add_file.clicked.connect(self.add_files)
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)
        self.btn_prev.clicked.connect(self.prev_video)
        self.btn_next.clicked.connect(self.next_video)
        self.btn_mute.clicked.connect(self.toggle_mute)
        self.btn_projection.clicked.connect(self.toggle_projection)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # 系统托盘
        self.setup_tray_icon()

    def create_tool_button(self, icon_rel_path, name):
        btn = QToolButton()
        btn.setObjectName(name)
        icon_path = resource_path(icon_rel_path)
        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            print(f"⚠️ 图标未加载：{icon_path}")
            btn.setText(name[:2].upper())
        else:
            pixmap = pixmap.scaled(
                32, 32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            btn.setIcon(QIcon(pixmap))
        return btn

    def init_screens(self):
        app = QApplication.instance()
        screens = app.screens()
        self.screen_combo.clear()
        for i, screen in enumerate(screens):
            geo = screen.geometry()
            is_primary = screen == app.primaryScreen()
            label = f"屏幕 {i+1} ({geo.width()}x{geo.height()})" + (" [主屏]" if is_primary else "")
            self.screen_combo.addItem(label, geo)

    def on_tab_changed(self, index):
        """选项卡切换时的处理"""
        if index == 0:
            self.current_mode = "video"
        else:
            self.current_mode = "image"
        
        # 投放状态下同步内容到全屏窗口
        if self.is_projecting and self.player_window and self.player_window.isVisible():
            self.sync_projection_content()

    def sync_projection_content(self):
        """同步当前选项卡内容到全屏窗口"""
        if not self.player_window or not self.player_window.isVisible():
            return
        
        # 断开旧的信号连接
        try:
            self.player_window.currentIndexChanged.disconnect()
        except:
            pass
        
        # 根据当前模式加载内容
        if self.current_mode == "video":
            if self.video_paths:
                self.player_window.set_video_list(self.video_paths)
                self.player_window.currentIndexChanged.connect(self.sync_video_list_selection)
            else:
                QMessageBox.warning(self, "提示", "视频列表为空！")
                return
        else:
            if self.image_paths:
                self.player_window.set_image_list(self.image_paths)
                self.player_window.currentIndexChanged.connect(self.sync_image_list_selection)
            else:
                QMessageBox.warning(self, "提示", "图片列表为空！")
                return

    def start_projection(self):
        """开始投放"""
        if self.current_mode == "video":
            if not self.video_paths:
                QMessageBox.warning(self, "提示", "请先添加视频！")
                return
            content_list = self.video_paths
        else:
            if not self.image_paths:
                QMessageBox.warning(self, "提示", "请先添加图片！")
                return
            content_list = self.image_paths
        
        screen_geo = self.screen_combo.currentData()
        if not screen_geo:
            print("错误: 无法获取屏幕几何数据！")
            return
        
        # 检查投放屏幕是否与主窗口所在屏幕相同
        if not self.check_different_screen(screen_geo):
            QMessageBox.warning(self, "提示", "投放屏幕不能与应用程序所在屏幕相同，请选择其他屏幕！")
            return
        
        self.player_window = PlayerWindow(screen_geo)
        
        if self.current_mode == "video":
            self.player_window.set_video_list(content_list)
            self.player_window.currentIndexChanged.connect(self.sync_video_list_selection)
        else:
            self.player_window.set_image_list(content_list)
            self.player_window.currentIndexChanged.connect(self.sync_image_list_selection)
        
        self.player_window.showFullScreen()
        self.is_projecting = True
        self.update_projection_button()

    def check_different_screen(self, target_geo):
        """检查目标屏幕是否与主窗口所在屏幕不同"""
        app = QApplication.instance()
        main_window_screen = app.screenAt(self.geometry().center())
        
        # 遍历所有屏幕，找到与target_geo匹配的屏幕
        for screen in app.screens():
            if screen.geometry() == target_geo:
                # 如果找到的屏幕与主窗口所在屏幕相同，返回False
                if screen == main_window_screen:
                    return False
                return True
        
        return True

    def stop_projection(self):
        """停止投放"""
        if self.player_window:
            # 断开信号连接
            try:
                self.player_window.currentIndexChanged.disconnect()
            except:
                pass
            self.player_window.close()
            self.player_window = None
        self.is_projecting = False
        self.update_projection_button()

    def pause_play(self):
        if self.is_image_mode:
            # 图片模式下暂停无意义，返回True表示"继续"
            return True
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            return False
        else:
            self.media_player.play()
            return True

    def toggle_mute(self):
        try:
            print("调用 PlayerWindow.toggle_mute 方法")
            print(f"audio_output 状态: {self.audio_output}")
            if not self.audio_output:
                print("错误: audio_output 未初始化！")
                return
            current_state = self.audio_output.isMuted()
            print(f"当前静音状态: {current_state}")
            self.audio_output.setMuted(not current_state)
            print(f"设置静音后: {self.audio_output.isMuted()}")
            return self.audio_output.isMuted()
        except Exception as e:
            print(f"toggle_mute 异常: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    def prev_video(self):
        if self.is_image_mode:
            if not self.image_list:
                return
            idx = (self.current_index - 1) % len(self.image_list)
            self.play_image(idx)
        else:
            if not self.video_list:
                return
            idx = (self.current_index - 1) % len(self.video_list)
            self.play_video(idx)

    def next_video(self):
        if self.is_image_mode:
            if not self.image_list:
                return
            idx = (self.current_index + 1) % len(self.image_list)
            self.play_image(idx)
        else:
            if not self.video_list:
                return
            idx = (self.current_index + 1) % len(self.video_list)
            self.play_video(idx)


class VideoPlayerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("MT-Player")
        self.setFixedSize(478, 420)
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                font-family: "Microsoft YaHei", sans-serif;
            }
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
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
                color: white;
                padding: 5px 15px;
                border: 1px solid #555;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === 标题栏 ===
        title_bar = QWidget()
        title_bar.setFixedHeight(56)
        title_bar.setStyleSheet("background-color: #000000;")
        title_label = QLabel()
        title_label.setText("<span style='font-size: 18px;'>MT-Player</span>&nbsp;&nbsp;<span style='font-size: 9px;'>BY:HAE</span>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: white; font-weight: bold;")
        title_layout = QHBoxLayout()
        title_layout.addWidget(title_label)
        title_bar.setLayout(title_layout)
        main_layout.addWidget(title_bar)

        # === 屏幕选择区域（高对比度）===
        screen_layout = QHBoxLayout()
        screen_layout.setContentsMargins(10, 5, 10, 5)
        screen_label = QLabel("屏幕选择：")
        screen_label.setStyleSheet("color: white; font-size: 12px;")
        self.screen_combo = QComboBox()
        self.screen_combo.setFixedHeight(20)
        self.screen_combo.setStyleSheet("""
            QComboBox {
                background-color: #353535;
                color: white;
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
                border-right: 2px solid white;
                border-bottom: 2px solid white;
                margin: -2px -8px 0 0;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: white;
                selection-background-color: #0078d4;
                selection-color: white;
                font-size: 12px;
                border: 1px solid #444;
            }
        """)
        screen_layout.addWidget(screen_label)
        screen_layout.addWidget(self.screen_combo)
        screen_widget = QWidget()
        screen_widget.setFixedHeight(30)
        screen_widget.setLayout(screen_layout)
        main_layout.addWidget(screen_widget)

        # === 选项卡（视频/图片列表）===
        self.tab_widget = QTabWidget()
        self.tab_widget.setFixedHeight(210)
        
        self.video_list_widget = QListWidget()
        self.video_list_widget.setStyleSheet("""
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
        """)
        
        self.image_list_widget = QListWidget()
        self.image_list_widget.setStyleSheet("""
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
        """)
        
        self.tab_widget.addTab(self.video_list_widget, "视频列表")
        self.tab_widget.addTab(self.image_list_widget, "图片列表")
        main_layout.addWidget(self.tab_widget)

        # === 按钮栏 ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.setContentsMargins(10, 5, 10, 5)

        self.btn_folder = self.create_tool_button("img/从文件夹导入.png", "folder")
        self.btn_add_file = self.create_tool_button("img/添加视频.png", "add_file")
        self.btn_play_pause = self.create_tool_button("img/播放.png", "play_pause")
        self.btn_prev = self.create_tool_button("img/上一个.png", "prev")
        self.btn_next = self.create_tool_button("img/下一个.png", "next")
        self.btn_mute = self.create_tool_button("img/取消静音.png", "mute")
        self.btn_projection = self.create_tool_button("img/继续投放.png", "projection")

        for btn in [self.btn_folder, self.btn_add_file, self.btn_play_pause,
                    self.btn_prev, self.btn_next, self.btn_mute, self.btn_projection]:
            button_layout.addWidget(btn)

        button_widget = QWidget()
        button_widget.setFixedHeight(38)
        button_widget.setStyleSheet("background-color: #2d2d2d;")
        button_widget.setLayout(button_layout)
        main_layout.addWidget(button_widget)

        central_widget.setLayout(main_layout)

        # 初始化
        self.video_paths = []
        self.image_paths = []
        self.player_window = None
        self.is_muted = False
        self.current_mode = "video"  # 当前模式：video 或 image
        self.is_projecting = False  # 投放状态标志

        self.init_screens()

        # 连接信号
        self.btn_folder.clicked.connect(self.add_folder)
        self.btn_add_file.clicked.connect(self.add_files)
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)
        self.btn_prev.clicked.connect(self.prev_video)
        self.btn_next.clicked.connect(self.next_video)
        self.btn_mute.clicked.connect(self.toggle_mute)
        self.btn_projection.clicked.connect(self.toggle_projection)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # 系统托盘
        self.setup_tray_icon()

    def create_tool_button(self, icon_rel_path, name):
        btn = QToolButton()
        btn.setObjectName(name)
        icon_path = resource_path(icon_rel_path)
        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            print(f"⚠️ 图标未加载：{icon_path}")
            btn.setText(name[:2].upper())
        else:
            pixmap = pixmap.scaled(
                32, 32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            btn.setIcon(QIcon(pixmap))
        return btn

    def init_screens(self):
        app = QApplication.instance()
        screens = app.screens()
        self.screen_combo.clear()
        for i, screen in enumerate(screens):
            geo = screen.geometry()
            is_primary = screen == app.primaryScreen()
            label = f"屏幕 {i+1} ({geo.width()}x{geo.height()})" + (" [主屏]" if is_primary else "")
            self.screen_combo.addItem(label, geo)

    def on_tab_changed(self, index):
        """选项卡切换时的处理"""
        if index == 0:
            self.current_mode = "video"
        else:
            self.current_mode = "image"
        
        # 投放状态下同步内容到全屏窗口
        if self.is_projecting and self.player_window and self.player_window.isVisible():
            self.sync_projection_content()

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
            image_exts = {'.png', '.jpg', '.jpeg'}
            new_video_paths = []
            new_image_paths = []
            
            for file in Path(folder).iterdir():
                if file.is_file():
                    if file.suffix.lower() in video_exts:
                        new_video_paths.append(str(file.resolve()))
                    elif file.suffix.lower() in image_exts:
                        new_image_paths.append(str(file.resolve()))
            
            if new_video_paths:
                self.add_videos_to_list(new_video_paths)
            if new_image_paths:
                self.add_images_to_list(new_image_paths)
            
            if not new_video_paths and not new_image_paths:
                QMessageBox.warning(self, "提示", "文件夹中没有支持的视频或图片文件！")

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文件",
            "", "视频文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm);;图片文件 (*.png *.jpg *.jpeg)"
        )
        if files:
            video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
            image_exts = {'.png', '.jpg', '.jpeg'}
            video_paths = []
            image_paths = []
            
            for f in files:
                path = str(Path(f).resolve())
                ext = Path(f).suffix.lower()
                if ext in video_exts:
                    video_paths.append(path)
                elif ext in image_exts:
                    image_paths.append(path)
            
            if video_paths:
                self.add_videos_to_list(video_paths)
            if image_paths:
                self.add_images_to_list(image_paths)

    def add_videos_to_list(self, new_paths):
        existing = set(self.video_paths)
        for path in new_paths:
            if path not in existing:
                self.video_paths.append(path)
                self.video_list_widget.addItem(Path(path).name)
                existing.add(path)

    def add_images_to_list(self, new_paths):
        existing = set(self.image_paths)
        for path in new_paths:
            if path not in existing:
                self.image_paths.append(path)
                self.image_list_widget.addItem(Path(path).name)
                existing.add(path)

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
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(restore_action)
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("MT-Player", "程序已最小化到系统托盘", QSystemTrayIcon.MessageIcon.Information, 2000)

    def sync_projection_content(self):
        """同步当前选项卡内容到全屏窗口"""
        if not self.player_window or not self.player_window.isVisible():
            return
        
        # 断开旧的信号连接
        try:
            self.player_window.currentIndexChanged.disconnect()
        except:
            pass
        
        # 根据当前模式加载内容
        if self.current_mode == "video":
            if self.video_paths:
                self.player_window.set_video_list(self.video_paths)
                self.player_window.currentIndexChanged.connect(self.sync_video_list_selection)
            else:
                QMessageBox.warning(self, "提示", "视频列表为空！")
                return
        else:
            if self.image_paths:
                self.player_window.set_image_list(self.image_paths)
                self.player_window.currentIndexChanged.connect(self.sync_image_list_selection)
            else:
                QMessageBox.warning(self, "提示", "图片列表为空！")
                return

    def toggle_projection(self):
        """切换投放/取消投放"""
        if self.is_projecting:
            self.stop_projection()
        else:
            self.start_projection()

    def start_projection(self):
        """开始投放"""
        if self.current_mode == "video":
            if not self.video_paths:
                QMessageBox.warning(self, "提示", "请先添加视频！")
                return
            content_list = self.video_paths
        else:
            if not self.image_paths:
                QMessageBox.warning(self, "提示", "请先添加图片！")
                return
            content_list = self.image_paths
        
        screen_geo = self.screen_combo.currentData()
        if not screen_geo:
            print("错误: 无法获取屏幕几何数据！")
            return
        
        # 检查投放屏幕是否与主窗口所在屏幕相同
        if not self.check_different_screen(screen_geo):
            QMessageBox.warning(self, "提示", "投放屏幕不能与应用程序所在屏幕相同，请选择其他屏幕！")
            return
        
        self.player_window = PlayerWindow(screen_geo)
        
        if self.current_mode == "video":
            self.player_window.set_video_list(content_list)
            self.player_window.currentIndexChanged.connect(self.sync_video_list_selection)
        else:
            self.player_window.set_image_list(content_list)
            self.player_window.currentIndexChanged.connect(self.sync_image_list_selection)
        
        self.player_window.showFullScreen()
        self.is_projecting = True
        self.update_projection_button()

    def check_different_screen(self, target_geo):
        """检查目标屏幕是否与主窗口所在屏幕不同"""
        app = QApplication.instance()
        main_window_screen = app.screenAt(self.geometry().center())
        
        # 遍历所有屏幕，找到与target_geo匹配的屏幕
        for screen in app.screens():
            if screen.geometry() == target_geo:
                # 如果找到的屏幕与主窗口所在屏幕相同，返回False
                if screen == main_window_screen:
                    return False
                return True
        
        return True

    def stop_projection(self):
        """停止投放"""
        if self.player_window:
            try:
                self.player_window.currentIndexChanged.disconnect()
            except:
                pass
            self.player_window.close()
            self.player_window = None
        self.is_projecting = False
        self.update_projection_button()

    def update_projection_button(self):
        """更新投放按钮的图标"""
        if self.is_projecting:
            icon_path = resource_path("img/取消投放.png")
        else:
            icon_path = resource_path("img/继续投放.png")
        
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                32, 32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.btn_projection.setIcon(QIcon(pixmap))

    def sync_video_list_selection(self, index):
        """同步视频列表选择"""
        for i in range(self.video_list_widget.count()):
            item = self.video_list_widget.item(i)
            if i == index:
                file_name = Path(self.video_paths[i]).name
                item.setText(f"▶ {file_name}")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor("#0078d4"))
            else:
                file_name = Path(self.video_paths[i]).name if i < len(self.video_paths) else ""
                if file_name:
                    item.setText(file_name)
                    font = item.font()
                    font.setBold(False)
                    item.setFont(font)
                    item.setForeground(QColor("#000000"))
        
        self.video_list_widget.setCurrentRow(index)

    def sync_image_list_selection(self, index):
        """同步图片列表选择"""
        for i in range(self.image_list_widget.count()):
            item = self.image_list_widget.item(i)
            if i == index:
                file_name = Path(self.image_paths[i]).name
                item.setText(f"▶ {file_name}")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor("#0078d4"))
            else:
                file_name = Path(self.image_paths[i]).name if i < len(self.image_paths) else ""
                if file_name:
                    item.setText(file_name)
                    font = item.font()
                    font.setBold(False)
                    item.setFont(font)
                    item.setForeground(QColor("#000000"))
        
        self.image_list_widget.setCurrentRow(index)

    def toggle_play_pause(self):
        """播放/暂停"""
        if not self.is_projecting:
            QMessageBox.warning(self, "提示", "请先点击投放按钮进行投放！")
            return
        
        player = self.player_window
        if player:
            is_playing = player.pause_play()
            if is_playing:
                icon_path = resource_path("img/暂停.png")
            else:
                icon_path = resource_path("img/播放.png")
            
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    32, 32,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.btn_play_pause.setIcon(QIcon(pixmap))

    def toggle_mute(self):
        """静音/取消静音"""
        try:
            if not self.is_projecting:
                QMessageBox.warning(self, "提示", "请先点击投放按钮进行投放！")
                return
            
            player = self.player_window
            if player:
                is_muted = player.toggle_mute()
                self.is_muted = is_muted
                if is_muted:
                    icon_path = resource_path("img/静音.png")
                else:
                    icon_path = resource_path("img/取消静音.png")
                
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(
                        32, 32,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.btn_mute.setIcon(QIcon(pixmap))
        except Exception as e:
            print(f"VideoPlayerApp.toggle_mute 异常: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    def prev_video(self):
        """上一个"""
        if not self.is_projecting:
            QMessageBox.warning(self, "提示", "请先点击投放按钮进行投放！")
            return
        
        player = self.player_window
        if player:
            player.prev_video()

    def next_video(self):
        """下一个"""
        if not self.is_projecting:
            QMessageBox.warning(self, "提示", "请先点击投放按钮进行投放！")
            return
        
        player = self.player_window
        if player:
            player.next_video()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = VideoPlayerApp()
    window.show()

    sys.exit(app.exec())