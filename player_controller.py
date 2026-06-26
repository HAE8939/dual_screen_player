import logging
import threading
from PyQt6.QtCore import QObject, pyqtSlot, QMetaObject, Qt

logger = logging.getLogger(__name__)


class PlayerController(QObject):
    """控制器 —— 所有跨线程请求通过 invoke_on_main 编组回主线程"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def invoke_on_main(self, callable_fn, *args, timeout: float = 10.0):
        """在主线程执行 callable 并同步等待结果（供 API/MCP 线程调用）"""
        event = threading.Event()
        result_box = [None, None]

        def _wrapper():
            try:
                result_box[0] = callable_fn(*args)
            except Exception as e:
                result_box[1] = e
            finally:
                event.set()

        QMetaObject.invokeMethod(
            self, "_execOnMain", Qt.ConnectionType.BlockingQueuedConnection,
            Qt.Q_ARG(object, _wrapper),
        )
        if not event.wait(timeout):
            logger.warning("invoke_on_main 超时，主线程可能阻塞")
        if result_box[1] is not None:
            raise result_box[1]
        return result_box[0]

    @pyqtSlot(object)
    def _execOnMain(self, fn):
        fn()
