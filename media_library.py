import threading
import logging
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg'}

__version__ = '3.1.0'


class MediaLibrary(QObject):
    """媒体库 —— 唯一数据源，线程安全"""

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
        return {'added_videos': added_videos, 'added_images': added_images}

    def remove(self, kind: str, index: int) -> str | None:
        with self._lock:
            if kind == 'video':
                if 0 <= index < len(self._videos):
                    removed = self._videos.pop(index)
                    self.videosChanged.emit()
                    return removed
            elif kind == 'image':
                if 0 <= index < len(self._images):
                    removed = self._images.pop(index)
                    self.imagesChanged.emit()
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
        return cleared

    def snapshot(self) -> dict:
        with self._lock:
            return {
                'videos': list(self._videos),
                'images': list(self._images),
            }

    @property
    def video_count(self) -> int:
        with self._lock:
            return len(self._videos)

    @property
    def image_count(self) -> int:
        with self._lock:
            return len(self._images)
