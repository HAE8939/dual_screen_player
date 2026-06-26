import logging
import threading
import json
from pathlib import Path

logger = logging.getLogger(__name__)

player_app = None

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP 库未安装，请运行: pip install mcp")


def get_player_app():
    return player_app


def set_player_app(app):
    global player_app
    player_app = app


def create_tools():
    return [
        Tool(name="start_projection", description="开始投放媒体到指定屏幕。", inputSchema={
            "type": "object", "properties": {
                "screen_index": {"type": "integer", "description": "目标屏幕索引（可选）"}
            }
        }),
        Tool(name="stop_projection", description="停止当前投放。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="get_projection_status", description="获取投放状态。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="play", description="播放视频（仅视频模式）。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="pause", description="暂停视频播放。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="prev_media", description="切换到上一个媒体。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="next_media", description="切换到下一个媒体。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="mute", description="静音。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="unmute", description="取消静音。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="get_player_status", description="获取播放器状态。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="get_video_list", description="获取视频列表。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="get_image_list", description="获取图片列表。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="add_files", description="添加媒体文件。", inputSchema={
            "type": "object", "properties": {
                "files": {"type": "array", "items": {"type": "string"}, "description": "文件路径列表"}
            }, "required": ["files"]
        }),
        Tool(name="delete_video", description="删除视频。", inputSchema={
            "type": "object", "properties": {
                "index": {"type": "integer", "description": "视频索引"}
            }, "required": ["index"]
        }),
        Tool(name="delete_image", description="删除图片。", inputSchema={
            "type": "object", "properties": {
                "index": {"type": "integer", "description": "图片索引"}
            }, "required": ["index"]
        }),
        Tool(name="clear_files", description="清空文件列表。", inputSchema={
            "type": "object", "properties": {
                "type": {"type": "string", "enum": ["all", "video", "image"], "description": "清空类型"}
            }
        }),
        Tool(name="get_screens", description="获取屏幕列表。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="select_screen", description="选择投放屏幕。", inputSchema={
            "type": "object", "properties": {
                "index": {"type": "integer", "description": "屏幕索引"}
            }, "required": ["index"]
        }),
        Tool(name="get_full_status", description="获取完整状态。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="get_app_info", description="获取应用信息。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="shutdown_app", description="关闭应用。", inputSchema={"type": "object", "properties": {}}),
        Tool(name="switch_mode", description="切换播放模式。", inputSchema={
            "type": "object", "properties": {
                "mode": {"type": "string", "enum": ["video", "image"], "description": "目标模式"}
            }, "required": ["mode"]
        }),
    ]


def handle_tool_call(name: str, arguments: dict):
    from PyQt6.QtWidgets import QApplication

    app = get_player_app()
    if not app:
        return "错误：播放器未初始化"

    ctrl = app.controller
    lib = app.library

    try:
        if name == "start_projection":
            if app.is_projecting:
                return "已在投放中"
            idx = arguments.get("screen_index")
            if idx is not None:
                if not isinstance(idx, int):
                    return "错误: screen_index 必须是整数"
                if 0 <= idx < app.screen_combo.count():
                    ctrl.invoke_on_main(app.screen_combo.setCurrentIndex, idx)
            ctrl.invoke_on_main(app.start_projection)
            return "投放已开始" if app.is_projecting else "投放失败"

        elif name == "stop_projection":
            ctrl.invoke_on_main(app.stop_projection)
            return "投放已停止"

        elif name == "get_projection_status":
            return json.dumps({"is_projecting": app.is_projecting, "current_mode": app.current_mode}, ensure_ascii=False)

        elif name == "play":
            if not app.is_projecting or not app.player_window:
                return "请先开始投放"
            if app.player_window.is_image_mode:
                return "图片模式无需播放控制"
            ctrl.invoke_on_main(app._apply_play_pause, True)
            return "已开始播放"

        elif name == "pause":
            if not app.is_projecting or not app.player_window:
                return "请先开始投放"
            if app.player_window.is_image_mode:
                return "图片模式无需暂停控制"
            ctrl.invoke_on_main(app._apply_play_pause, False)
            return "已暂停"

        elif name == "prev_media":
            if not app.is_projecting or not app.player_window:
                return "请先开始投放"
            ctrl.invoke_on_main(app.player_window.prev_video)
            return "已切换到上一个"

        elif name == "next_media":
            if not app.is_projecting or not app.player_window:
                return "请先开始投放"
            ctrl.invoke_on_main(app.player_window.next_video)
            return "已切换到下一个"

        elif name == "mute":
            if not app.is_projecting or not app.player_window:
                return "请先开始投放"
            if app.player_window.is_image_mode:
                return "图片模式无需静音控制"
            ctrl.invoke_on_main(app._apply_mute, True)
            return "已静音"

        elif name == "unmute":
            if not app.is_projecting or not app.player_window:
                return "请先开始投放"
            if app.player_window.is_image_mode:
                return "图片模式无需静音控制"
            ctrl.invoke_on_main(app._apply_mute, False)
            return "已取消静音"

        elif name == "get_player_status":
            status = {
                "is_projecting": app.is_projecting,
                "current_mode": app.current_mode,
                "is_muted": app.is_muted,
                "current_index": -1, "total_count": 0,
                "current_file": None, "playback_state": "stopped",
            }
            if app.is_projecting and app.player_window:
                pw = app.player_window
                status["current_index"] = ctrl.invoke_on_main(lambda: pw.current_index)
                is_image = ctrl.invoke_on_main(lambda: pw.is_image_mode)
                snap = lib.snapshot()
                files = snap['images'] if is_image else snap['videos']
                status["total_count"] = len(files)
                idx = status["current_index"]
                if 0 <= idx < len(files):
                    status["current_file"] = Path(files[idx]).name
                if not is_image:
                    ps = ctrl.invoke_on_main(pw.media_player.playbackState)
                    status["playback_state"] = "playing" if ps == 1 else ("paused" if ps == 2 else "stopped")
            return json.dumps(status, ensure_ascii=False)

        elif name == "get_video_list":
            snap = lib.snapshot()
            videos = [{"index": i, "path": p, "name": Path(p).name} for i, p in enumerate(snap['videos'])]
            return json.dumps({"count": len(videos), "videos": videos}, ensure_ascii=False)

        elif name == "get_image_list":
            snap = lib.snapshot()
            images = [{"index": i, "path": p, "name": Path(p).name} for i, p in enumerate(snap['images'])]
            return json.dumps({"count": len(images), "images": images}, ensure_ascii=False)

        elif name == "add_files":
            files = arguments.get("files", [])
            if not isinstance(files, list):
                return "错误: files 必须是数组"
            valid = []
            for fp in files:
                if isinstance(fp, str):
                    p = Path(fp)
                    if p.exists() and p.is_file():
                        valid.append(str(p.resolve()))
            result = ctrl.invoke_on_main(lib.add, valid)
            added = len(result['added_videos']) + len(result['added_images'])
            return json.dumps({"added": added, "videos": len(result['added_videos']), "images": len(result['added_images'])}, ensure_ascii=False)

        elif name == "delete_video":
            idx = arguments.get("index")
            if not isinstance(idx, int):
                return "错误: index 必须是整数"
            removed = ctrl.invoke_on_main(lib.remove, 'video', idx)
            return f"已删除: {Path(removed).name}" if removed else "索引超出范围"

        elif name == "delete_image":
            idx = arguments.get("index")
            if not isinstance(idx, int):
                return "错误: index 必须是整数"
            removed = ctrl.invoke_on_main(lib.remove, 'image', idx)
            return f"已删除: {Path(removed).name}" if removed else "索引超出范围"

        elif name == "clear_files":
            clear_type = arguments.get("type", "all")
            if clear_type not in ("all", "video", "image"):
                return "错误: type 必须是 all/video/image"
            cleared = ctrl.invoke_on_main(lib.clear, clear_type)
            return f"已清空: {cleared}"

        elif name == "get_screens":
            qapp = QApplication.instance()
            screens = []
            for i, screen in enumerate(qapp.screens()):
                geo = screen.geometry()
                screens.append({
                    "index": i, "name": f"屏幕 {i+1}",
                    "width": geo.width(), "height": geo.height(),
                    "is_primary": screen == qapp.primaryScreen(),
                })
            return json.dumps({"count": len(screens), "screens": screens}, ensure_ascii=False)

        elif name == "select_screen":
            idx = arguments.get("index")
            if not isinstance(idx, int):
                return "错误: index 必须是整数"
            if 0 <= idx < app.screen_combo.count():
                ctrl.invoke_on_main(app.screen_combo.setCurrentIndex, idx)
                return f"已选择屏幕 {idx}"
            return "屏幕索引超出范围"

        elif name == "get_full_status":
            qapp = QApplication.instance()
            snap = lib.snapshot()
            status = {
                "projection": {"is_projecting": app.is_projecting, "current_mode": app.current_mode},
                "player": {
                    "is_muted": app.is_muted, "current_index": -1, "total_count": 0,
                    "current_file": None, "playback_state": "stopped",
                },
                "files": {"video_count": len(snap['videos']), "image_count": len(snap['images'])},
                "screen": {"selected_index": app.screen_combo.currentIndex(), "total_screens": len(qapp.screens())},
            }
            if app.is_projecting and app.player_window:
                pw = app.player_window
                status["player"]["current_index"] = ctrl.invoke_on_main(lambda: pw.current_index)
                is_image = ctrl.invoke_on_main(lambda: pw.is_image_mode)
                files = snap['images'] if is_image else snap['videos']
                status["player"]["total_count"] = len(files)
                idx = status["player"]["current_index"]
                if 0 <= idx < len(files):
                    status["player"]["current_file"] = Path(files[idx]).name
                if not is_image:
                    ps = ctrl.invoke_on_main(pw.media_player.playbackState)
                    status["player"]["playback_state"] = "playing" if ps == 1 else ("paused" if ps == 2 else "stopped")
            return json.dumps(status, ensure_ascii=False, indent=2)

        elif name == "get_app_info":
            from media_library import __version__
            return json.dumps({"name": "MT-Player", "version": __version__, "author": "HAE", "mcp_version": "1.0.0"}, ensure_ascii=False)

        elif name == "shutdown_app":
            ctrl.invoke_on_main(app._quit_app)
            return "应用正在关闭"

        elif name == "switch_mode":
            mode = arguments.get("mode")
            if mode not in ("video", "image"):
                return "错误: mode 必须是 video 或 image"
            target_index = 0 if mode == "video" else 1
            ctrl.invoke_on_main(app.tab_widget.setCurrentIndex, target_index)
            return f"已切换到 {mode} 模式"

        else:
            return f"未知工具: {name}"

    except Exception as e:
        logger.error(f"MCP 工具调用异常: {e}")
        return f"错误: {str(e)}"


if MCP_AVAILABLE:
    server = Server("mt-player-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return create_tools()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        from mcp.types import TextContent
        result = handle_tool_call(name, arguments)
        return [TextContent(type="text", text=result)]

    async def run_mcp_server(app_instance):
        set_player_app(app_instance)
        logger.info("MCP 服务器启动")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    def start_mcp_server(app_instance):
        import asyncio
        def run_in_thread():
            asyncio.run(run_mcp_server(app_instance))
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        return thread

else:
    def start_mcp_server(app_instance):
        logger.error("MCP 库未安装，无法启动 MCP 服务器")
        return None
