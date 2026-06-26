import logging
from PyQt6.QtCore import QObject, pyqtSlot, QMetaObject, Qt

logger = logging.getLogger(__name__)


class PlayerController(QObject):
    """控制器 —— 所有跨线程请求通过 invoke_on_main 编组回主线程"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def invoke_on_main(self, callable_fn, *args, timeout: float = 10.0):
        """在主线程执行 callable 并同步等待结果（供 API/MCP 线程调用）

        使用 BlockingQueuedConnection，调用线程会阻塞直到主线程执行完毕。
        注意：主线程必须不被长时间阻塞（耗时 I/O 已移至 worker 线程）。
        """
        result_box = [None, None]

        def _wrapper():
            try:
                result_box[0] = callable_fn(*args)
            except Exception as e:
                result_box[1] = e

        QMetaObject.invokeMethod(
            self, "_execOnMain", Qt.ConnectionType.BlockingQueuedConnection,
            Qt.Q_ARG(object, _wrapper),
        )
        if result_box[1] is not None:
            raise result_box[1]
        return result_box[0]

    @pyqtSlot(object)
    def _execOnMain(self, fn):
        fn()
