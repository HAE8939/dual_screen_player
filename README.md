# MT-Player 多屏播控播放器

> 专为双屏/多屏场景设计的轻量级媒体播放工具，支持视频与图片的全屏投放，主窗口进行列表管理与控制。适用于展会、监控、广告轮播、图片展示等场景。

![MT-Player](cover.png)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 功能特性

### 多屏投放
- 自动识别所有连接的显示器
- 全屏投放到指定屏幕，支持多屏环境
- 投放屏幕与应用屏幕必须不同（防护机制）
- 实时屏幕预览，选择屏幕后即时更新

### 媒体管理
- **视频**：MP4、MKV、AVI、MOV、WMV、FLV、WebM
- **图片**：PNG、JPG、JPEG
- 从文件夹批量导入，自动分类视频/图片
- 手动添加单个或多个文件，自动去重
- **持久化存储**：自动记住上次加载的文件，重启后直接可用

### 播放控制
- 暂停/继续播放
- 上一个/下一个（循环切换）
- 静音/取消静音
- 视频播完自动续播下一个
- 损坏文件自动跳过，不卡死

### 远程控制
- **REST API**：HTTP 接口控制所有功能
- **MCP 协议**：AI 助手（如 CoPaw）通过 MCP 协议控制
- **无界面模式**：后台服务运行

### 主题系统
- **亮色主题**：Anthropic 品牌调性（陶土橙 + 象牙暖白）
- **暗色主题**：暖黑底 + 同一陶土橙强调色
- SVG 线性图标，hover 动态变色

---

## 安装与运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动程序

```bash
# 基础 GUI 模式（亮色主题）
python dual_screen_player.py

# 暗色主题
python dual_screen_player.py --theme dark

# 启用 REST API（仅监听 localhost）
python dual_screen_player.py --api --port 5000

# 局域网访问（强制鉴权）
python dual_screen_player.py --api --host 0.0.0.0 --token YOUR_SECRET

# 启用 MCP 服务器（AI 助手控制）
python dual_screen_player.py --mcp

# 无界面后台服务
python dual_screen_player.py --api --mcp --headless
```

---

## 启动参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--api` | 启用 REST API 服务器 | 关闭 |
| `--port` | API 端口 | 5000 |
| `--host` | API 监听地址 | `127.0.0.1` |
| `--token` | API 鉴权 Token（非 localhost 必填） | 无 |
| `--mcp` | 启用 MCP 服务器 | 关闭 |
| `--headless` | 无界面模式 | 关闭 |
| `--theme` | 主题：`light` / `dark` | `light` |

---

## REST API 接口

### 投放控制

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/projection/start` | POST | 开始投放 |
| `/api/projection/stop` | POST | 停止投放 |
| `/api/projection/status` | GET | 投放状态 |

### 播放控制

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/player/play` | POST | 播放 |
| `/api/player/pause` | POST | 暂停 |
| `/api/player/prev` | POST | 上一个 |
| `/api/player/next` | POST | 下一个 |
| `/api/player/mute` | POST | 静音 |
| `/api/player/unmute` | POST | 取消静音 |
| `/api/player/status` | GET | 播放状态 |

### 文件管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/files/videos` | GET | 视频列表 |
| `/api/files/images` | GET | 图片列表 |
| `/api/files/add` | POST | 添加文件 |
| `/api/files/video/<index>` | DELETE | 删除视频 |
| `/api/files/image/<index>` | DELETE | 删除图片 |
| `/api/files/clear` | POST | 清空列表 |

### 屏幕与状态

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/screens` | GET | 屏幕列表 |
| `/api/screens/select` | POST | 选择屏幕 |
| `/api/status` | GET | 完整状态 |
| `/api/app/info` | GET | 应用信息 |
| `/api/app/shutdown` | POST | 关闭应用 |
| `/api/mode/switch` | POST | 切换模式 |

### 调用示例

```python
import requests

BASE_URL = "http://localhost:5000"
HEADERS = {"Authorization": "Bearer YOUR_SECRET"}

# 添加文件并投放
requests.post(f"{BASE_URL}/api/files/add", json={"files": ["C:/Videos/demo.mp4"]}, headers=HEADERS)
requests.post(f"{BASE_URL}/api/projection/start", headers=HEADERS)

# 获取状态
status = requests.get(f"{BASE_URL}/api/status", headers=HEADERS).json()
```

---

## MCP 协议支持

### 配置 CoPaw / Claude Desktop

```json
{
    "mcpServers": {
        "mt-player": {
            "command": "python",
            "args": ["<项目路径>/mcp_run.py"]
        }
    }
}
```

### MCP 工具（22 个）

投放控制：`start_projection`、`stop_projection`、`get_projection_status`

播放控制：`play`、`pause`、`prev_media`、`next_media`、`mute`、`unmute`、`get_player_status`

文件管理：`get_video_list`、`get_image_list`、`add_files`、`delete_video`、`delete_image`、`clear_files`

屏幕与状态：`get_screens`、`select_screen`、`get_full_status`、`get_app_info`、`shutdown_app`、`switch_mode`

---

## 安全说明

- API 默认仅监听 `127.0.0.1`，外部无法访问
- 局域网访问必须通过 `--token` 设置鉴权令牌
- 所有写操作端点校验 `Authorization: Bearer <token>`
- 使用 `waitress` 替代 Flask 开发服务器

```bash
python dual_screen_player.py --api --host 0.0.0.0 --token my_secret_token
```

---

## 项目结构

```
Dual_screen_player/
├── dual_screen_player.py    # 主程序
├── media_library.py         # 媒体数据模型（线程安全 + 持久化）
├── player_controller.py     # 跨线程控制层
├── theme.py                 # 主题系统（light/dark）
├── icon_loader.py           # SVG 图标加载器
├── widgets.py               # 可复用 UI 组件
├── api_server.py            # REST API 服务器
├── mcp_server.py            # MCP 服务器
├── mcp_run.py               # MCP 独立启动脚本
├── requirements.txt         # 依赖锁定
├── .gitignore
└── img/
    ├── app.ico / app.png    # 应用图标
    └── icons/               # SVG 线性图标
```

---

## 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 运行环境 |
| PyQt6 | >=6.5.0 | GUI + 多媒体 |
| Flask | >=3.0.0 | REST API |
| waitress | >=2.1.0 | 生产级 WSGI |
| MCP | >=1.0.0 | AI 助手控制 |

---

## 版本历史

### v3.2.0 (2026-06-26)
- 架构重构：MediaLibrary 统一数据模型 + PlayerController 跨线程控制
- 品牌 UI：Anthropic 陶土橙主题 + SVG 图标 + hover 动态变色
- 安全加固：API 鉴权 + localhost 默认 + waitress
- 持久化：自动记住上次加载的媒体文件
- Bug 修复：图片缩放、空指针、损坏文件处理等

### v3.1.0 (2026-03-13)
- REST API + MCP 远程控制

### v3.0.0 (2026-01-15)
- 代码优化，消除重复

### v2.x (2026-01)
- 图片投放 + 屏幕预览

### v1.0.0 (2025-12-31)
- 初始版本

---

**作者**：HAE | **License**：MIT
