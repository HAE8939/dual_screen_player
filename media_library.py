import threading
import json
import logging
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg'}

__version__ = '3.2.0'

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
        self._lock = threading.Lock()

    @staticmethod
    def classify(path: str) -> str | None:
        ext = Path(path).suffix.lower()
        if ext in SUPPORTED_VIDEO_EXTS:
            return 'video'
        if ext in SUPPORTED_IMAGE_EXTS:
            return 'image'
        return None

    def add(self, paths: list[str]) -> dict:
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
        if added_videos or added_images:
            if added_videos:
                self.videosChanged.emit()
            if added_images:
                self.imagesChanged.emit()
            self._persist()
        return {'added_videos': added_videos, 'added_images': added_images}

    def remove(self, kind: str, index: int) -> str | None:
        with self._lock:
            if kind == 'video':
                if 0 <= index < len(self._videos):
                    removed = self._videos.pop(index)
                    self.videosChanged.emit()
                    self._persist()
                    return removed
            elif kind == 'image':
                if 0 <= index < len(self._images):
                    removed = self._images.pop(index)
                    self.imagesChanged.emit()
                    self._persist()
                    return removed
        return None

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
        """保存当前列表到磁盘"""
        try:
            _STATE_DIR.mkdir(parents=True, exist_ok=True)
            snap = self.snapshot()
            data = {
                'videos': snap['videos'],
                'images': snap['images'],
            }
            _STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            logger.warning(f"保存媒体列表失败: {e}")

    def load_from_disk(self) -> dict:
        """从磁盘加载上次的列表，校验文件是否存在"""
        if not _STATE_FILE.exists():
            return {'videos': 0, 'images': 0, 'missing': 0}

        try:
            data = json.loads(_STATE_FILE.read_text(encoding='utf-8'))
        except Exception as e:
            logger.warning(f"读取媒体列表失败: {e}")
            return {'videos': 0, 'images': 0, 'missing': 0}

        valid_videos = [p for p in data.get('videos', []) if Path(p).is_file()]
        valid_images = [p for p in data.get('images', []) if Path(p).is_file()]
        missing = (len(data.get('videos', [])) - len(valid_videos) +
                   len(data.get('images', [])) - len(valid_images))

        with self._lock:
            self._videos = valid_videos
            self._images = valid_images

        if valid_videos:
            self.videosChanged.emit()
        if valid_images:
            self.imagesChanged.emit()

        loaded = len(valid_videos) + len(valid_images)
        if missing > 0:
            logger.info(f"已恢复 {loaded} 个文件，{missing} 个文件已丢失跳过")
        else:
            logger.info(f"已恢复 {loaded} 个文件")
        return {'videos': len(valid_videos), 'images': len(valid_images), 'missing': missing}

    @property
    def video_count(self) -> int:
        with self._lock:
            return len(self._videos)

    @property
    def image_count(self) -> int:
        with self._lock:
            return len(self._images)
