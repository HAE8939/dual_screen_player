import logging
import threading
from pathlib import Path
from functools import wraps
from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)

app = Flask(__name__)
player_app = None
_api_token = None


def init_api(app_instance, host='127.0.0.1', port=5000, token=None):
    global player_app, _api_token
    player_app = app_instance
    _api_token = token

    def run_server():
        try:
            from waitress import serve
            logger.info(f"API 服务器启动于 http://{host}:{port} (waitress)")
            serve(app, host=host, port=port, threads=4)
        except ImportError:
            logger.warning("waitress 未安装，使用 Flask 开发服务器（不推荐生产使用）")
            app.run(host=host, port=port, threaded=True, use_reloader=False)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread


def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if _api_token is None:
            return f(*args, **kwargs)
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer ') or auth[7:] != _api_token:
            return jsonify({'success': False, 'error': '未授权，请提供有效的 Bearer Token'}), 401
        return f(*args, **kwargs)
    return decorated


def _get_json():
    data = request.get_json(silent=True)
    if data is None:
        return None, jsonify({'success': False, 'error': '请求体必须是 JSON 格式'}), 415
    return data, None, None


def _validate_int(value, name, min_val=0, max_val=None):
    if value is None or not isinstance(value, int):
        return None, jsonify({'success': False, 'error': f'{name} 必须是整数'}), 400
    if value < min_val:
        return None, jsonify({'success': False, 'error': f'{name} 不能小于 {min_val}'}), 400
    if max_val is not None and value > max_val:
        return None, jsonify({'success': False, 'error': f'{name} 不能大于 {max_val}'}), 400
    return value, None, None


def _get_controller():
    return player_app.controller if player_app else None


# ==================== 投放控制 ====================

@app.route('/api/projection/start', methods=['POST'])
@require_token
def start_projection():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    if player_app.is_projecting:
        return jsonify({'success': False, 'error': '已在投放中'}), 400

    data, err, code = _get_json()
    if err:
        return err, code

    ctrl = _get_controller()
    if data and 'screen_index' in data:
        idx, err_resp, err_code = _validate_int(data['screen_index'], 'screen_index')
        if err_resp:
            return err_resp, err_code
        ctrl.invoke_on_main(player_app.screen_combo.setCurrentIndex, idx)

    ctrl.invoke_on_main(player_app.start_projection)

    if player_app.is_projecting:
        return jsonify({'success': True, 'message': '投放已开始'})
    return jsonify({'success': False, 'error': '投放失败，请检查屏幕选择和文件列表'}), 400


@app.route('/api/projection/stop', methods=['POST'])
@require_token
def stop_projection():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    ctrl = _get_controller()
    ctrl.invoke_on_main(player_app.stop_projection)
    return jsonify({'success': True, 'message': '投放已停止'})


@app.route('/api/projection/status', methods=['GET'])
@require_token
def get_projection_status():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    return jsonify({
        'success': True,
        'is_projecting': player_app.is_projecting,
        'current_mode': player_app.current_mode,
    })


# ==================== 播放控制 ====================

@app.route('/api/player/play', methods=['POST'])
@require_token
def play():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    if not player_app.is_projecting:
        return jsonify({'success': False, 'error': '请先开始投放'}), 400
    ctrl = _get_controller()
    ctrl.invoke_on_main(player_app.player_window.media_player.play)
    return jsonify({'success': True, 'message': '已开始播放'})


@app.route('/api/player/pause', methods=['POST'])
@require_token
def pause():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    if not player_app.is_projecting:
        return jsonify({'success': False, 'error': '请先开始投放'}), 400
    ctrl = _get_controller()
    ctrl.invoke_on_main(player_app.player_window.media_player.pause)
    return jsonify({'success': True, 'message': '已暂停'})


@app.route('/api/player/prev', methods=['POST'])
@require_token
def prev_media():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    if not player_app.is_projecting or not player_app.player_window:
        return jsonify({'success': False, 'error': '请先开始投放'}), 400
    ctrl = _get_controller()
    ctrl.invoke_on_main(player_app.player_window.prev_video)
    return jsonify({'success': True, 'message': '已切换到上一个'})


@app.route('/api/player/next', methods=['POST'])
@require_token
def next_media():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    if not player_app.is_projecting or not player_app.player_window:
        return jsonify({'success': False, 'error': '请先开始投放'}), 400
    ctrl = _get_controller()
    ctrl.invoke_on_main(player_app.player_window.next_video)
    return jsonify({'success': True, 'message': '已切换到下一个'})


@app.route('/api/player/mute', methods=['POST'])
@require_token
def mute():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    if not player_app.is_projecting or not player_app.player_window:
        return jsonify({'success': False, 'error': '请先开始投放'}), 400
    if player_app.player_window.is_image_mode:
        return jsonify({'success': False, 'error': '图片模式无需静音控制'}), 400
    def _mute():
        player_app.player_window.audio_output.setMuted(True)
        player_app._update_mute_ui(True)
    ctrl = _get_controller()
    ctrl.invoke_on_main(_mute)
    return jsonify({'success': True, 'message': '已静音'})


@app.route('/api/player/unmute', methods=['POST'])
@require_token
def unmute():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    if not player_app.is_projecting or not player_app.player_window:
        return jsonify({'success': False, 'error': '请先开始投放'}), 400
    if player_app.player_window.is_image_mode:
        return jsonify({'success': False, 'error': '图片模式无需静音控制'}), 400
    def _unmute():
        player_app.player_window.audio_output.setMuted(False)
        player_app._update_mute_ui(False)
    ctrl = _get_controller()
    ctrl.invoke_on_main(_unmute)
    return jsonify({'success': True, 'message': '已取消静音'})


@app.route('/api/player/status', methods=['GET'])
@require_token
def get_player_status():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500

    status = {
        'success': True,
        'is_projecting': player_app.is_projecting,
        'current_mode': player_app.current_mode,
        'is_muted': player_app.is_muted,
        'current_index': -1,
        'total_count': 0,
        'current_file': None,
        'playback_state': 'stopped',
    }

    if player_app.is_projecting and player_app.player_window:
        pw = player_app.player_window
        status['current_index'] = pw.current_index
        status['is_image_mode'] = pw.is_image_mode
        snap = player_app.library.snapshot()
        files = snap['images'] if pw.is_image_mode else snap['videos']
        status['total_count'] = len(files)
        if 0 <= pw.current_index < len(files):
            status['current_file'] = Path(files[pw.current_index]).name
        if not pw.is_image_mode:
            ps = pw.media_player.playbackState()
            status['playback_state'] = 'playing' if ps == 1 else ('paused' if ps == 2 else 'stopped')

    return jsonify(status)


# ==================== 文件管理 ====================

@app.route('/api/files/videos', methods=['GET'])
@require_token
def get_video_list():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    snap = player_app.library.snapshot()
    videos = [{'index': i, 'path': p, 'name': Path(p).name} for i, p in enumerate(snap['videos'])]
    return jsonify({'success': True, 'videos': videos, 'count': len(videos)})


@app.route('/api/files/images', methods=['GET'])
@require_token
def get_image_list():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    snap = player_app.library.snapshot()
    images = [{'index': i, 'path': p, 'name': Path(p).name} for i, p in enumerate(snap['images'])]
    return jsonify({'success': True, 'images': images, 'count': len(images)})


@app.route('/api/files/add', methods=['POST'])
@require_token
def add_files():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500

    data, err, code = _get_json()
    if err:
        return err, code
    if 'files' not in data or not isinstance(data['files'], list):
        return jsonify({'success': False, 'error': '请提供 files 字段（文件路径数组）'}), 400

    valid_paths = []
    for fp in data['files']:
        if not isinstance(fp, str):
            continue
        p = Path(fp)
        if p.exists() and p.is_file():
            valid_paths.append(str(p.resolve()))

    result = player_app.library.add(valid_paths)
    added = len(result['added_videos']) + len(result['added_images'])
    skipped = len(data['files']) - added
    return jsonify({
        'success': True,
        'added_videos': len(result['added_videos']),
        'added_images': len(result['added_images']),
        'skipped': skipped,
    })


@app.route('/api/files/video/<int:index>', methods=['DELETE'])
@require_token
def delete_video(index):
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    ctrl = _get_controller()
    removed = ctrl.invoke_on_main(player_app.library.remove, 'video', index)
    if removed:
        return jsonify({'success': True, 'deleted': removed})
    return jsonify({'success': False, 'error': '索引超出范围'}), 400


@app.route('/api/files/image/<int:index>', methods=['DELETE'])
@require_token
def delete_image(index):
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    ctrl = _get_controller()
    removed = ctrl.invoke_on_main(player_app.library.remove, 'image', index)
    if removed:
        return jsonify({'success': True, 'deleted': removed})
    return jsonify({'success': False, 'error': '索引超出范围'}), 400


@app.route('/api/files/clear', methods=['POST'])
@require_token
def clear_files():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500

    data, err, code = _get_json()
    if err:
        return err, code

    clear_type = (data or {}).get('type', 'all')
    if clear_type not in ('all', 'video', 'image'):
        return jsonify({'success': False, 'error': 'type 必须是 all/video/image'}), 400

    ctrl = _get_controller()
    cleared = ctrl.invoke_on_main(player_app.library.clear, clear_type)
    return jsonify({'success': True, 'cleared': cleared})


# ==================== 屏幕管理 ====================

@app.route('/api/screens', methods=['GET'])
@require_token
def get_screens():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    from PyQt6.QtWidgets import QApplication
    qapp = QApplication.instance()
    screens = []
    for i, screen in enumerate(qapp.screens()):
        geo = screen.geometry()
        screens.append({
            'index': i,
            'name': f"屏幕 {i+1}",
            'width': geo.width(),
            'height': geo.height(),
            'x': geo.x(),
            'y': geo.y(),
            'is_primary': screen == qapp.primaryScreen(),
        })
    return jsonify({'success': True, 'screens': screens, 'count': len(screens)})


@app.route('/api/screens/select', methods=['POST'])
@require_token
def select_screen():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500

    data, err, code = _get_json()
    if err:
        return err, code

    idx, err_resp, err_code = _validate_int(data.get('index'), 'index')
    if err_resp:
        return err_resp, err_code

    if idx >= player_app.screen_combo.count():
        return jsonify({'success': False, 'error': '屏幕索引超出范围'}), 400

    ctrl = _get_controller()
    ctrl.invoke_on_main(player_app.screen_combo.setCurrentIndex, idx)
    return jsonify({'success': True, 'selected_index': idx})


# ==================== 状态查询 ====================

@app.route('/api/status', methods=['GET'])
@require_token
def get_full_status():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500

    from PyQt6.QtWidgets import QApplication
    qapp = QApplication.instance()
    snap = player_app.library.snapshot()

    status = {
        'success': True,
        'projection': {
            'is_projecting': player_app.is_projecting,
            'current_mode': player_app.current_mode,
        },
        'player': {
            'is_muted': player_app.is_muted,
            'current_index': -1,
            'total_count': 0,
            'current_file': None,
            'playback_state': 'stopped',
        },
        'files': {
            'video_count': len(snap['videos']),
            'image_count': len(snap['images']),
        },
        'screen': {
            'selected_index': player_app.screen_combo.currentIndex(),
            'total_screens': len(qapp.screens()),
        },
    }

    if player_app.is_projecting and player_app.player_window:
        pw = player_app.player_window
        status['player']['current_index'] = pw.current_index
        files = snap['images'] if pw.is_image_mode else snap['videos']
        status['player']['total_count'] = len(files)
        if 0 <= pw.current_index < len(files):
            status['player']['current_file'] = Path(files[pw.current_index]).name
        if not pw.is_image_mode:
            ps = pw.media_player.playbackState()
            status['player']['playback_state'] = 'playing' if ps == 1 else ('paused' if ps == 2 else 'stopped')

    return jsonify(status)


# ==================== 应用控制 ====================

@app.route('/api/app/shutdown', methods=['POST'])
@require_token
def shutdown_app():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500
    ctrl = _get_controller()
    ctrl.invoke_on_main(player_app._quit_app)
    return jsonify({'success': True, 'message': '应用正在关闭'})


@app.route('/api/app/info', methods=['GET'])
@require_token
def get_app_info():
    from media_library import __version__
    return jsonify({
        'success': True,
        'name': 'MT-Player',
        'version': __version__,
        'author': 'HAE',
        'api_version': '1.0.0',
    })


# ==================== 模式切换 ====================

@app.route('/api/mode/switch', methods=['POST'])
@require_token
def switch_mode():
    if not player_app:
        return jsonify({'success': False, 'error': '播放器未初始化'}), 500

    data, err, code = _get_json()
    if err:
        return err, code

    mode = data.get('mode')
    if mode not in ('video', 'image'):
        return jsonify({'success': False, 'error': 'mode 必须是 video 或 image'}), 400

    target_index = 0 if mode == 'video' else 1
    ctrl = _get_controller()
    ctrl.invoke_on_main(player_app.tab_widget.setCurrentIndex, target_index)
    return jsonify({'success': True, 'current_mode': mode})
