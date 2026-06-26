"""
Flask 入口 — 系统集成点。

组装 hardware/ + logic/ 模块，提供 7 个 API 端点。
"""

import time
import threading
import sys
from flask import Flask, jsonify

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from unittest.mock import MagicMock
    GPIO = MagicMock()

from config import *
from hardware.gpio_init import init_gpio, cleanup_gpio
from hardware.led import RGBLED
from hardware.buzzer import Buzzer
from hardware.ir_sensor import IRSensor
from hardware.button import CoinButton
from logic.state_machine import StateMachine
from logic.inventory import Inventory

app = Flask(__name__, static_folder='static', static_url_path='/static')

# 强制禁用浏览器缓存（开发调试用）
@app.after_request
def add_no_cache(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ---- 初始化模块 ----
init_gpio()
inv = Inventory('data/inventory.json')
sm = StateMachine(inv)
rgb = RGBLED(RGB_R_PIN, RGB_G_PIN, RGB_B_PIN)
buzzer = Buzzer(BUZZER_PIN)
ir = IRSensor(IR_SENSOR_PIN)


# ===== 辅助函数 =====

def on_dispense(channel: int):
    """出货回调 — 由 sm.confirm(on_dispense) 调用。"""
    try:
        rgb.set_channel(channel)
        print(f"[DISPENSE] LED channel {channel} ON"); sys.stdout.flush()
    except Exception as e:
        print(f"[DISPENSE] LED ERROR: {e}"); sys.stdout.flush()
    try:
        buzzer.beep(freq=1000, duration=0.2)
        print(f"[DISPENSE] Buzzer beep OK"); sys.stdout.flush()
    except Exception as e:
        print(f"[DISPENSE] Buzzer ERROR: {e}"); sys.stdout.flush()
    threading.Thread(target=wait_for_pickup, args=(channel,), daemon=True).start()
    print(f"[DISPENSE] IR thread started for channel {channel}"); sys.stdout.flush()


def wait_for_pickup(channel: int):
    """红外轮询线程，检测取货或超时。
    初始延迟2秒避免手快速划过误触，
    需连续3次遮挡才确认取货（1.5秒稳定检测）。
    取货成功蜂鸣两声，超时蜂鸣长响告警。
    """
    log(f"IR线程启动  等待2秒后开始检测")
    time.sleep(2)
    blocked_count = 0
    for i in range(IR_RETRY_COUNT):
        time.sleep(IR_DETECT_INTERVAL)
        blocked = ir.is_blocked()
        if blocked:
            blocked_count += 1
            log(f"IR检测到遮挡  count={blocked_count}/3  (第{i+1}次)")
            if blocked_count >= 3:
                log(f"取货成功  货道{channel}  交易完成")
                sm.complete()
                rgb.off()
                buzzer.beep(freq=1000, duration=0.1)
                time.sleep(0.15)
                buzzer.beep(freq=1000, duration=0.1)
                return
        else:
            if blocked_count > 0:
                log(f"IR遮挡消失  count重置  (第{i+1}次)")
            blocked_count = 0
    log(f"取货超时  货道{channel}  自动取消  (已等待{i+1}次)")
    sm.cancel()
    rgb.off()
    buzzer.beep(freq=2000, duration=0.5)


def on_coin_pressed():
    """投币按键回调。"""
    sm.add_coin()


# ===== 日志工具 =====
from datetime import datetime

def log(msg):
    """输出带时间戳的操作日志到终端"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

# ===== API 端点 =====

@app.route('/')
def index():
    with open('static/index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/api/status')
def api_status():
    return jsonify(sm.get_state())


@app.route('/api/coin', methods=['POST'])
def api_coin():
    balance = sm.add_coin()
    log(f"投币 +1  |  余额={balance}")
    return jsonify({"balance": balance})


@app.route('/api/select/<int:channel_id>', methods=['POST'])
def api_select(channel_id):
    result = sm.select(channel_id)
    if result["success"]:
        log(f"选品 {result['name']}  ¥{result['price']}  |  余额={sm.balance}")
    else:
        log(f"选品失败  |  {result['msg']}")
    return jsonify(result)


@app.route('/api/confirm', methods=['POST'])
def api_confirm():
    result = sm.confirm(on_dispense)
    if result["success"]:
        log(f"确认购买  货道{result['channel']}  |  余额={result['balance']}")
    else:
        log(f"确认失败  |  {result['msg']}")
    return jsonify(result)

@app.route('/api/cancel_select', methods=['POST'])
def api_cancel_select():
    result = sm.cancel_select()
    rgb.off()
    log(f"取消选择  |  余额保留={sm.balance}")
    return jsonify(result)

@app.route('/api/cancel', methods=['POST'])
def api_cancel():
    result = sm.cancel()
    rgb.off()
    buzzer.beep(freq=2000, duration=0.5)
    log(f"取消交易  |  余额清零  |  退币{sm.balance}元")
    return jsonify(result)


@app.route('/api/logs')
def api_logs():
    return jsonify(inv.get_transactions())


@app.route('/api/reset', methods=['POST'])
def api_reset():
    # 重置库存数据
    inv.channels = []
    for ch in CHANNEL_CONFIG:
        inv.channels.append({
            "id": ch["id"],
            "name": ch["name"],
            "price": ch["price"],
            "stock": ch["init_stock"]
        })
    inv.transactions = []
    inv.save()
    # 重置状态机
    sm.state = 0
    sm.balance = 0
    sm.selected_channel = None
    log("系统重置  |  库存恢复  余额归零")
    return jsonify({"success": True})


# ===== 入口 =====

if __name__ == '__main__':
    try:

        btn = CoinButton(COIN_BUTTON_PIN, on_coin_pressed)
        btn.start()
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_gpio()
