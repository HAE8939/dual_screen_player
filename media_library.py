import threading
import json
import logging
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg'}

__version__ = '3.3.1'

# 持久化文件路径：用户目录下
_STATE_DIR = Path.home() / ".mt-player"
_STATE_FILE = _STATE_DIR / "media_state.json"


class MediaLibrary(QObject):
    """媒体库 —— 唯一数据源，线程安全，支持持久化"""

    videosChanged = pyqtSignal()
    imagesChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._videos = []
        self._images = []
        self._watched_folders = []  # 已导入的文件夹路径
        self._standalone_files = []  # 单独添加的文件（非文件夹导入）
        self._lock = threading.Lock()

    @staticmethod
    def classify(path: str) -> str | None:
        ext = Path(path).suffix.lower()
        if ext in SUPPORTED_VIDEO_EXTS:
            return 'video'
        if ext in SUPPORTED_IMAGE_EXTS:
            return 'image'
        return None

    def add(self, paths: list[str], track_standalone: bool = True) -> dict:
        added_videos, added_images = [], []
        with self._lock:
            existing_v = set(self._videos)
            existing_i = set(self._images)
            for p in paths:
                resolved = str(Path(p).resolve())
                kind = self.classify(resolved)
                if kind == 'video' and resolved not in existing_v:
                    self._videos.append(resolved)
                    existing_v.add(resolved)
                    added_videos.append(resolved)
                elif kind == 'image' and resolved not in existing_i:
                    self._images.append(resolved)
                    existing_i.add(resolved)
                    added_images.append(resolved)
            if track_standalone:
                all_added = added_videos + added_images
                if all_added:
                    existing_standalone = set(self._standalone_files)
                    for f in all_added:
                        if f not in existing_standalone:
                            self._standalone_files.append(f)
                            existing_standalone.add(f)
        if added_videos or added_images:
            if added_videos:
                self.videosChanged.emit()
            if added_images:
                self.imagesChanged.emit()
            self._persist()
        return {'added_videos': added_videos, 'added_images': added_images}

    def add_from_folder(self, folder_path: str) -> dict:
        """从文件夹导入，记录文件夹路径以便启动时自动扫描"""
        folder = str(Path(folder_path).resolve())
        new_paths = []
        try:
            for file in Path(folder).iterdir():
                if file.is_file():
                    new_paths.append(str(file.resolve()))
        except Exception as e:
            logger.error(f"读取文件夹出错: {e}")
            return {'added_videos': [], 'added_images': []}

        with self._lock:
            if folder not in self._watched_folders:
                self._watched_folders.append(folder)

        return self.add(new_paths, track_standalone=False)

    def remove(self, kind: str, index: int) -> str | None:
        removed, sig = None, None
        with self._lock:
            lst = self._videos if kind == 'video' else self._images if kind == 'image' else None
            if lst is not None and 0 <= index < len(lst):
                removed = lst.pop(index)
                sig = 'video' if kind == 'video' else 'image'
        if removed is not None:
            (self.videosChanged if sig == 'video' else self.imagesChanged).emit()
            self._persist()
        return removed

    def clear(self, kind: str = 'all') -> dict:
        cleared = {'videos': 0, 'images': 0}
        with self._lock:
            if kind in ('all', 'video'):
                cleared['videos'] = len(self._videos)
                self._videos.clear()
            if kind in ('all', 'image'):
                cleared['images'] = len(self._images)
                self._images.clear()
        if kind in ('all', 'video'):
            self.videosChanged.emit()
        if kind in ('all', 'image'):
            self.imagesChanged.emit()
        self._persist()
        return cleared

    def snapshot(self) -> dict:
        with self._lock:
            return {
                'videos': list(self._videos),
                'images': list(self._images),
            }

    # ==================== 持久化 ====================

    def _persist(self):
        """保存文件夹列表和单独文件到磁盘"""
        try:
            _STATE_DIR.mkdir(parents=True, exist_ok=True)
            with self._lock:
                data = {
                    'watched_folders': list(self._watched_folders),
                    'standalone_files': list(self._standalone_files),
                }
            _STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            logger.warning(f"保存媒体列表失败: {e}")

    def load_from_disk(self) -> dict:
        """从磁盘加载：扫描已记录的文件夹 + 恢复单独文件"""
        if not _STATE_FILE.exists():
            return {'videos': 0, 'images': 0, 'missing': 0}

        try:
            data = json.loads(_STATE_FILE.read_text(encoding='utf-8'))
        except Exception as e:
            logger.warning(f"读取媒体列表失败: {e}")
            return {'videos': 0, 'images': 0, 'missing': 0}

        # 兼容旧格式（直接保存文件列表）
        if 'videos' in data and 'images' in data:
            all_paths = data.get('videos', []) + data.get('images', [])
            with self._lock:
                self._standalone_files = list(all_paths)
            self._persist()  # 转换为新格式
            return self.load_from_disk()

        all_new = []

        # 扫描已记录的文件夹
        valid_folders = []
        for folder in data.get('watched_folders', []):
            if Path(folder).is_dir():
                valid_folders.append(folder)
                try:
                    for file in Path(folder).iterdir():
                        if file.is_file():
                            all_new.append(str(file.resolve()))
                except Exception:
                    pass

        # 恢复单独文件
        missing = 0
        for f in data.get('standalone_files', []):
            if Path(f).is_file():
                all_new.append(f)
            else:
                missing += 1

        result = self.add(all_new, track_standalone=False)

        # 更新已记录的文件夹（移除不存在的）
        self._watched_folders = valid_folders
        self._persist()

        loaded = len(result['added_videos']) + len(result['added_images'])
        logger.info(f"已恢复 {loaded} 个文件（来自 {len(valid_folders)} 个文件夹），{missing} 个已丢失")
        return {'videos': len(result['added_videos']), 'images': len(result['added_images']), 'missing': missing}

    @property
    def video_count(self) -> int:
        with self._lock:
            return len(self._videos)

    @property
    def image_count(self) -> int:
        with self._lock:
            return len(self._images)
