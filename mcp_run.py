#!/usr/bin/env python3
"""
MT-Player MCP 服务器

此脚本作为 MCP 服务器运行，允许 AI 助手（如 CoPaw）通过 MCP 协议控制播放器。

CoPaw 配置示例 (claude_desktop_config.json 或类似配置文件):
{
    "mcpServers": {
        "mt-player": {
            "command": "python",
            "args": ["<项目路径>/mcp_run.py"]
        }
    }
}

或使用 Python 绝对路径:
{
    "mcpServers": {
        "mt-player": {
            "command": "python",
            "args": ["<项目路径>/mcp_run.py"]
        }
    }
}
"""

import sys
import os
import asyncio
import logging
import signal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_dependencies():
    """检查依赖"""
    missing = []
    
    try:
        import PyQt6
    except ImportError:
        missing.append("PyQt6")
    
    try:
        import mcp
    except ImportError:
        missing.append("mcp")
    
    if missing:
        print(f"错误: 缺少依赖库: {', '.join(missing)}", file=sys.stderr)
        print(f"请运行: pip install {' '.join(missing)}", file=sys.stderr)
        sys.exit(1)


check_dependencies()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, QCoreApplication

try:
    from mcp_server import run_mcp_server, set_player_app, MCP_AVAILABLE
except ImportError as e:
    print(f"错误: 无法导入 mcp_server: {e}", file=sys.stderr)
    sys.exit(1)

if not MCP_AVAILABLE:
    print("错误: MCP 库未安装，请运行: pip install mcp", file=sys.stderr)
    sys.exit(1)


class MCPServerThread(QThread):
    """在 Qt 线程中运行 MCP 服务器"""
    
    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
    
    def run(self):
        """运行 MCP 服务器"""
        try:
            asyncio.run(run_mcp_server(self.app_instance))
        except Exception as e:
            logger.error(f"MCP 服务器异常: {e}")


def main():
    """主函数"""
    logger.info("MT-Player MCP 服务器启动中...")
    
    from dual_screen_player import VideoPlayerApp
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    window = VideoPlayerApp(headless=True)
    window.hide()
    
    set_player_app(window)
    
    mcp_thread = MCPServerThread(window)
    mcp_thread.finished.connect(app.quit)
    mcp_thread.start()
    
    def signal_handler(signum, frame):
        logger.info("收到退出信号")
        app.quit()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("MT-Player MCP 服务器已就绪，等待连接...")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
