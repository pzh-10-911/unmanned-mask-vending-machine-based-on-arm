# Person B — 状态机 + 库存

## 产出文件

```
mask-vending-machine/
├── config.py                     # (与A协同，引脚号+价格常量)
├── logic/
│   ├── __init__.py
│   ├── state_machine.py          # 状态机核心逻辑
│   └── inventory.py              # 库存管理
```

## 状态机定义

### 状态常量

| 常量名 | 值 | 说明 |
|--------|-----|------|
| IDLE | 0 | 待机状态，可投币可选择 |
| SELECTED | 1 | 已选择品类，等待确认 |
| DISPENSE | 2 | 出货中（LED已亮起，等待取货） |

### 状态迁移图

```
IDLE ──select(ch)──▶ SELECTED ──confirm()──▶ DISPENSE ──complete()──▶ IDLE
 │                     │  │                       │
 │◀──cancel()──────────┘  │                       │
 │◀───────────────────────┴───────────────────────┘
 └──add_coin()── (余额增加，状态不变)
```

### logic/state_machine.py

```python
class StateMachine:
    """
    贩卖机状态机 — 管理交易全生命周期。
    """

    def __init__(self, inventory: Inventory):
        """
        初始化状态机。
        - state = IDLE
        - balance = 0
        - selected_channel = None
        - 接收 Inventory 实例用于库存检查
        """

    def add_coin(self) -> int:
        """
        投币操作。
        在任何状态下都可调用，balance += 1
        返回: 当前余额 balance (int)
        """

    def select(self, channel: int) -> dict:
        """
        选择口罩品类。
        要求: state 必须为 IDLE
        检查: balance < price → {"success": False, "msg": "余额不足"}
              stock <= 0    → {"success": False, "msg": "库存不足"}
        通过 → state → SELECTED, selected_channel = channel
        返回: {"success": True, "channel": channel, "price": price, "name": name}
        """

    def confirm(self, on_dispense: callable) -> dict:
        """
        确认购买。
        要求: state 必须为 SELECTED，balance >= price，stock > 0
        流程:
        1. balance -= price
        2. state = DISPENSE
        3. 执行回调 dispense_callback(selected_channel)
        4. 返回 {"success": True, "msg": "出货中，请取货", "channel": channel}
        """

    def cancel(self) -> dict:
        """
        取消交易。
        要求: state 为 SELECTED 或 DISPENSE
        流程: balance = 0, state = IDLE, selected_channel = None
        返回: {"success": True, "balance": 0}
        """

    def complete(self) -> dict:
        """
        取货完成（由 Person C 在红外检测到后调用）。
        要求: state 为 DISPENSE
        流程: 扣库存 → 记日志 → state = IDLE
        返回: {"success": True, "msg": "购买完成", "transaction_id": str}
        """

    def get_state(self) -> dict:
        """
        获取完整状态。
        返回:
        {
            "state": self.state,
            "state_name": "IDLE",
            "balance": self.balance,
            "selected_channel": self.selected_channel,
            "channels": [...]
        }
        """
```

### StateMachine 接口汇总

| 方法 | 入参 | 返回值 | 前置状态 | 行为 |
|------|------|--------|---------|------|
| `__init__` | `inventory: Inventory` | `StateMachine` | — | state=IDLE, balance=0, selected=None |
| `add_coin()` | 无 | `int` (balance) | 任意 | balance += 1 |
| `select(channel)` | `channel: int` | `dict` | IDLE | 检查余额/库存→设为 SELECTED |
| `confirm(on_dispense)` | `on_dispense: callable` | `dict` | SELECTED | 扣款→DISPENSE→回调 |
| `cancel()` | 无 | `dict` | SELECTED / DISPENSE | balance=0→IDLE |
| `complete()` | 无 | `dict` | DISPENSE | 扣库存→记日志→IDLE |
| `get_state()` | 无 | `dict` | 任意 | 返回完整状态对象 |

### select() 响应

| 场景 | 响应 |
|------|------|
| 成功 | `{"success": true, "channel": int, "price": float, "name": str}` |
| 余额不足 | `{"success": false, "msg": "余额不足"}` |
| 库存不足 | `{"success": false, "msg": "库存不足"}` |
| 状态错误 | `{"success": false, "msg": "状态错误"}` |
| 非法channel | `{"success": false, "msg": "无效货道"}` |

### confirm() 响应

| 场景 | 响应 |
|------|------|
| 成功 | `{"success": true, "msg": "出货中，请取货", "channel": int}` |
| 状态错误 | `{"success": false, "msg": "状态错误"}` |
| 系统异常 | `{"success": false, "msg": "系统错误"}` |

### cancel() / complete() 响应

| 方法 | 响应 |
|------|------|
| `cancel()` | `{"success": true, "balance": 0}` |
| `complete()` | `{"success": true, "msg": "购买完成", "transaction_id": str}` |

### get_state() 返回结构

```
{
  "state": 0,                    # int 状态码
  "state_name": "IDLE",          # str 状态名
  "balance": 3,                  # int 余额
  "selected_channel": null,      # int|null 已选货道
  "channels": [...]              # list 来自 inventory.get_status()
}
```

### C 如何调用 B

| C 的 API | 调用的 B 方法 | 说明 |
|----------|-------------|------|
| POST `/api/coin` | `sm.add_coin()` | 投币 |
| POST `/api/select/<id>` | `sm.select(ch)` | 选品类 |
| POST `/api/confirm` | `sm.confirm(on_dispense)` | 确认，传入出货回调 |
| POST `/api/cancel` | `sm.cancel()` | 取消 |
| 红外检测到口罩 | `sm.complete()` | 完成交易 |
| GET `/api/status` | `sm.get_state()` | 获取状态 |

## 库存管理

### Inventory 接口汇总

| 方法 | 入参 | 返回值 | 说明 |
|------|------|--------|------|
| `__init__` | `data_path: str` | `Inventory` | 文件存在则 load()，否则创建默认库存 |
| `load()` | 无 | `None` | 从 JSON 读取到内存 |
| `save()` | 无 | `None` | 内存写回 JSON |
| `deduct(channel)` | `channel: int` | `bool` | 扣库存，True=成功，False=库存不足 |
| `get_status()` | 无 | `list` | 所有货道信息 + available 状态 |
| `add_transaction(channel, amount, status)` | `channel, amount, status` | `dict` | 记录交易，返回记录对象 |
| `get_transactions(limit)` | `limit: int=50` | `list` | 最近 limit 条记录 |

```python
class Inventory:
    def __init__(self, data_path: str = "data/inventory.json"): ...
    def load(self) -> None: ...
    def save(self) -> None: ...
    def deduct(self, channel: int) -> bool: ...      # True=成功，False=库存不足
    def get_status(self) -> list: ...                 # 含 available 字段
    def add_transaction(self, ch: int, amt: float, status: str) -> dict: ...
    def get_transactions(self, limit: int = 50) -> list: ...
```

### JSON 格式

```json
{
    "channels": [
        {"id": 0, "name": "成人口罩", "price": 2.0, "stock": 10},
        {"id": 1, "name": "儿童口罩", "price": 2.0, "stock": 10},
        {"id": 2, "name": "N95口罩",  "price": 5.0, "stock": 5}
    ],
    "transactions": [
        {
            "time": "2026-06-22 10:30:00",
            "item": "成人口罩",
            "amount": 2.0,
            "status": "success"
        }
    ]
}
```

## config.py 常量

```python
# GPIO 引脚
RGB_R_PIN = 17     # RGB-LED 红色通道
RGB_G_PIN = 18     # RGB-LED 绿色通道
RGB_B_PIN = 19     # RGB-LED 蓝色通道
RGB_PINS = [RGB_R_PIN, RGB_G_PIN, RGB_B_PIN]
IR_SENSOR_PIN = 23
BUZZER_PIN = 26
COIN_BUTTON_PIN = 27

# RGB-LED 颜色映射（按货道）
CHANNEL_COLORS = {
    0: (1, 0, 0),  # 红 → 货道A 成人口罩
    1: (0, 1, 0),  # 绿 → 货道B 儿童口罩
    2: (0, 0, 1),  # 蓝 → 货道C N95口罩
}

# 价格和库存
CHANNEL_CONFIG = [
    {"id": 0, "name": "成人口罩", "price": 2.0, "init_stock": 10},
    {"id": 1, "name": "儿童口罩", "price": 2.0, "init_stock": 10},
    {"id": 2, "name": "N95口罩",  "price": 5.0, "init_stock": 5},
]

# 时间参数
DISPENSE_TIMEOUT = 30      # 出货等待超时（秒）
IR_DETECT_INTERVAL = 0.5   # 红外轮询间隔（秒）
IR_RETRY_COUNT = 60        # 超时前的检测次数
```

## 开发顺序

1. 写 inventory.py（测试：读/写 JSON、扣减库存、记录交易）
2. 写 state_machine.py（测试：完整购买流程、余额不足、取消交易）
3. 写 config.py（常量定义）
4. 不需要硬件，纯 Python 即可测试

## 依赖关系

- 无硬件依赖，可独立开发
- 需要与 A 协同确定 config.py 中的引脚号
- 输出给 Person C 集成
