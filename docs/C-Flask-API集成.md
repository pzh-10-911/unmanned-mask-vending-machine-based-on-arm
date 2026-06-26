# Person C — Flask API 集成

## 产出文件

```
mask-vending-machine/
├── app.py                         # Flask 应用 + 路由
├── requirements.txt               # 依赖清单
└── run.sh                         # 启动脚本（可选）
```

## 系统集成点

Person C 负责把所有模块组装起来。

### 初始化代码

```python
from flask import Flask, jsonify, request, send_from_directory
from config import *
from hardware.gpio_init import init_gpio, cleanup_gpio
from hardware.led import RGBLED
from hardware.buzzer import Buzzer
from hardware.ir_sensor import IRSensor
from hardware.button import CoinButton
from logic.state_machine import StateMachine
from logic.inventory import Inventory

app = Flask(__name__, static_folder='static')

inv = Inventory('data/inventory.json')
sm = StateMachine(inv)
rgb = RGBLED(RGB_R_PIN, RGB_G_PIN, RGB_B_PIN)
buzzer = Buzzer(BUZZER_PIN)
ir = IRSensor(IR_SENSOR_PIN)
```

---

## API 端点一览（7个）

| # | 方法 | 路由 | 功能 | 请求体 | 响应格式 |
|---|------|------|------|--------|---------|
| 1 | GET | `/` | 返回前端主页 | — | `text/html` |
| 2 | GET | `/api/status` | 获取贩卖机全状态 | — | `application/json` |
| 3 | POST | `/api/coin` | 投币（余额+1） | — | `{"balance": int}` |
| 4 | POST | `/api/select/<id>` | 选择口罩品类 | — | `{"success": bool, ...}` |
| 5 | POST | `/api/confirm` | 确认购买 | — | `{"success": bool, ...}` |
| 6 | POST | `/api/cancel` | 取消交易 | — | `{"success": bool, "balance": 0}` |
| 7 | GET | `/api/logs` | 交易记录列表 | — | `application/json` |

---

### 端点 1 — 主页

| 字段 | 值 |
|------|-----|
| 方法 | `GET /` |
| 返回 | `static/index.html` |
| Content-Type | `text/html` |

```python
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')
```

---

### 端点 2 — 状态查询

| 字段 | 值 |
|------|-----|
| 方法 | `GET /api/status` |
| Content-Type | `application/json` |

**响应 JSON 字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `state` | int | 状态码（0=IDLE, 1=SELECTED, 2=DISPENSE） |
| `state_name` | string | 状态名称 |
| `balance` | int | 当前余额 |
| `selected_channel` | int/null | 已选货道ID |
| `channels` | array | 货道列表 |

**channels 内每个对象的字段：**

| 字段 | 类型 | 示例 |
|------|------|------|
| `id` | int | 0 |
| `name` | string | "成人口罩" |
| `price` | float | 2.0 |
| `stock` | int | 10 |
| `available` | bool | true |

**示例响应：**
```json
{
  "state": 0,
  "state_name": "IDLE",
  "balance": 3,
  "selected_channel": null,
  "channels": [
    {"id": 0, "name": "成人口罩", "price": 2.0, "stock": 10, "available": true},
    {"id": 1, "name": "儿童口罩", "price": 2.0, "stock": 10, "available": true},
    {"id": 2, "name": "N95口罩", "price": 5.0, "stock": 5, "available": true}
  ]
}
```

```python
@app.route('/api/status')
def api_status():
    return jsonify(sm.get_state())
```

---

### 端点 3 — 投币

| 字段 | 值 |
|------|-----|
| 方法 | `POST /api/coin` |
| 请求体 | 无 |
| 响应 | `{"balance": int}` |

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `balance` | int | 投币后余额 |

**示例：** 连续投币3次 → `{"balance": 1}` → `{"balance": 2}` → `{"balance": 3}`

```python
@app.route('/api/coin', methods=['POST'])
def api_coin():
    balance = sm.add_coin()
    return jsonify({"balance": balance})
```

---

### 端点 4 — 选择品类

| 字段 | 值 |
|------|-----|
| 方法 | `POST /api/select/<channel_id>` |
| 参数 | `channel_id`: int (0, 1, 2) |
| 请求体 | 无 |

**成功响应：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | true |
| `channel` | int | 选择的货道ID |
| `price` | float | 商品价格 |
| `name` | string | 商品名称 |

**失败响应：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | false |
| `msg` | string | 失败原因 |

**失败原因取值：** `"余额不足"` / `"库存不足"` / `"状态错误"`

```python
@app.route('/api/select/<int:channel_id>', methods=['POST'])
def api_select(channel_id):
    result = sm.select(channel_id)
    return jsonify(result)
```

---

### 端点 5 — 确认购买

| 字段 | 值 |
|------|-----|
| 方法 | `POST /api/confirm` |
| 请求体 | 无 |

**成功响应：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | true |
| `msg` | string | "出货中，请取货" |
| `channel` | int | 出货货道ID |

**失败响应：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | false |
| `msg` | string | 失败原因 |

```python
@app.route('/api/confirm', methods=['POST'])
def api_confirm():
    result = sm.confirm(on_dispense=on_dispense)
    return jsonify(result)
```

---

### 端点 6 — 取消交易

| 字段 | 值 |
|------|-----|
| 方法 | `POST /api/cancel` |
| 请求体 | 无 |

**响应：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | true |
| `balance` | int | 0（余额归零） |

```python
@app.route('/api/cancel', methods=['POST'])
def api_cancel():
    result = sm.cancel()
    return jsonify(result)
```

---

### 端点 7 — 交易记录

| 字段 | 值 |
|------|-----|
| 方法 | `GET /api/logs` |
| Content-Type | `application/json` |

**响应（数组）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `time` | string | 交易时间 "2026-06-22 10:30:00" |
| `item` | string | 商品名称 |
| `amount` | float | 交易金额 |
| `status` | string | "success" / "failed" / "cancelled" |

```python
@app.route('/api/logs')
def api_logs():
    return jsonify(inv.get_transactions())
```

---

## 核心业务流程

### confirm() 完整流程

```
POST /api/confirm
    │
    ├── sm.confirm(on_dispense)    ← 调用 B 的状态机
    │       │
    │       └── on_dispense(ch)    ← 回调 C 实现的函数
    │               │
    │               ├── rgb.set_channel(ch)    ← 调用 A 按货道设RGB颜色
    │               ├── buzzer.beep()           ← 蜂鸣器响200ms（PWM 1000Hz）
    │               └── 启动后台线程:
    │                       ┌─────────────────────────────┐
    │                       │ wait_for_pickup(ch)          │
    │                       │  每0.5s: ir.is_blocked()     │
    │                       │  ├── True → sm.complete()    │
    │                       │  │         → rgb.off()       │
    │                       │  └── 超时30s → sm.cancel()   │
    │                       │              → rgb.off()    │
    │                       └─────────────────────────────┘
    │
    └── 返回 {"success": true, "msg": "出货中"}
```

### 三个必须实现的辅助函数

```python
def on_dispense(channel: int):
    """出货回调 — 由 sm.confirm(on_dispense) 调用"""
    rgb.set_channel(channel)
    buzzer.beep(freq=1000, duration=0.2)  # PWM 驱动无源蜂鸣器
    threading.Thread(target=wait_for_pickup, args=(channel,), daemon=True).start()

def wait_for_pickup(channel: int):
    """后台红外检测线程"""
    for _ in range(IR_RETRY_COUNT):
        time.sleep(IR_DETECT_INTERVAL)
        if ir.is_blocked():
            sm.complete()
            rgb.off()
            return
    sm.cancel()
    rgb.off()

def on_coin_pressed():
    """投币按键回调"""
    sm.add_coin()
```

---

## main 入口

```python
if __name__ == '__main__':
    try:
        init_gpio()
        btn = CoinButton(COIN_BUTTON_PIN, on_coin_pressed)
        btn.start()
        app.run(host='0.0.0.0', port=80, debug=False, threaded=True)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_gpio()
```

---

## 依赖关系

| 依赖 | 来源 | 接口文件 | 备注 |
|------|------|---------|------|
| GPIO 初始化 | A | `hardware/gpio_init.py` | Windows 自动 mock |
| RGB-LED 控制 | A | `hardware/led.py` | `RGBLED(r,g,b).set_channel(ch)/.off()` |
| 蜂鸣器 | A | `hardware/buzzer.py` | `Buzzer(pin).beep(freq, dur)` |
| 红外检测 | A | `hardware/ir_sensor.py` | `IRSensor(pin).is_blocked()` |
| 按键监听 | A | `hardware/button.py` | `CoinButton(pin, callback)` |
| 状态机 | B | `logic/state_machine.py` | `StateMachine(inv)` |
| 库存管理 | B | `logic/inventory.py` | `Inventory(path)` |

## 开发顺序

1. API 骨架，所有路由返回 mock 数据
2. 接入 B 的 state_machine、inventory
3. 接入 A 的 led、ir_sensor
4. 集成投币按键回调 + 红外检测线程
5. 测试：curl / Postman / `test_api.py`

## 启动命令

```bash
# 开发（Windows）
pip install flask
python app.py
# → http://localhost:5000

# 生产（树莓派）
pip install flask RPi.GPIO
sudo python app.py
# → http://本机IP:5000
```
