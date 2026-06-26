# 基于树莓派的无人口罩贩卖机 — 协作开发设计文档

## 0. 项目概述

嵌入式课程设计项目。使用树莓派作为主控 + Flask 提供 Web 服务，用户通过手机浏览器操作完成口罩自助购买。

### 核心流程

```
用户通过手机浏览器打开贩卖机网页
  → 按物理投币按键模拟投币（每次+1元）
  → 选择口罩品类 → 确认购买
  → 对应货道颜色（RGB-LED）亮起 + 蜂鸣器提示
  → 用户从对应格子取口罩放到取货口
  → 红外传感器检测到口罩 → 扣库存 → 完成
```

### 技术栈

| 层 | 技术 | 版本要求 |
|----|------|---------|
| 后端语言 | Python 3 | >= 3.7 |
| Web 框架 | Flask | >= 2.0 |
| GPIO | RPi.GPIO | 0.7.0 (树莓派) / mock (Windows) |
| 前端 | 纯 HTML + CSS + JS | 无依赖 |

---

## 技术说明

### 硬件技术参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 主控 | Raspberry Pi 3B+/4B | ARM Cortex-A53/A72, 1.2-1.5GHz |
| GPIO 电平 | 3.3V TTL | 所有 GPIO 引脚输入/输出均为 3.3V 逻辑电平 |
| GPIO 输出电流 | ~16mA/引脚 | 单个 GPIO 最大拉/灌电流，LED 串 220Ω 限流 |
| LED 工作电流 | ~10mA | 通过 220Ω 限流，满足 GPIO 驱动能力 |
| 红外传感器 | 3.3V 供电 | VCC→3.3V(pin1)，不得接 5V 以免损坏 GPIO |
| 按键 | 内部上拉 50kΩ | `PUD_UP` 启用内部上拉，按下→低电平 |
| 蜂鸣器 | 3脚无源蜂鸣器模块 | PWM驱动，`Buzzer.beep(freq, dur)`，VCC接3.3V |
| 系统电压 | 5V USB-C | 树莓派供电，各传感器从 3.3V/5V 取电 |

### GPIO 电气特性

```
                      内部上拉 ~50kΩ
        ┌───────────┬──── GPIO 引脚 (3.3V TTL)
        │           │
      3.3V        按键
        │           │
        └───────────┘
                   GND

  LED 驱动电路：
  GPIO →║ LED 长脚 → LED 短脚 → 220Ω → GND
         ║
    正向压降 ~2V, 电流 = (3.3-2)/220 ≈ 6mA
```

### 软件架构要点

#### Flask 线程模型

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `threaded` | True | Flask 开启多线程处理请求 |
| `host` | `0.0.0.0` | 监听所有网络接口，允许手机访问 |
| `port` | 80 | 生产环境用 80 端口，开发可用 5000 |
| `debug` | False | 生产关闭 debug，避免双进程 |

**线程安全问题：**
- GPIO 操作在单一线程中顺序执行（GIL + 无并发 GPIO 调用）
- `StateMachine` 所有方法由 Flask 线程串行调用，无需额外锁
- `threading.Thread` 用于红外轮询，与主线程通过 `sm.complete()` / `sm.cancel()` 交互

#### GPIO 中断 vs 轮询

| 方式 | 本项目选用 | 原因 |
|------|-----------|------|
| 投币按键 | **下降沿中断** (`GPIO.add_event_detect`) | 即时响应，不占 CPU，防抖 200ms |
| 红外检测 | **轮询** (`time.sleep(0.5)`) | 传感器可能短暂抖动，轮询可做滤波；无紧急实时要求 |

#### 状态机设计模式

```
状态机采用"控制反转"风格：
  - StateMachine 不直接操作硬件
  - 硬件操作通过回调函数 (on_dispense) 注入
  - 优点：状态机可脱离硬件独立测试

回调注入流程：
  sm.confirm(on_dispense=on_dispense)
                │
                └── StateMachine 内部执行:
                    1. balance -= price
                    2. state = DISPENSE
                    3. on_dispense(selected_channel)  ← 回调
                       ├── rgb.set_channel(ch)  (Person A)
                       ├── buzzer.beep()       (Person A)
                       └── thread: wait_for_pickup()  (Person C)
```

### 通信协议

#### HTTP API 约定

| 规则 | 说明 |
|------|------|
| 请求格式 | 全部 POST/GET，无请求体（`/api/select/<id>` 通过路径参数） |
| 响应格式 | 全部 JSON，`Content-Type: application/json` |
| 状态码 | 业务逻辑错误也返回 `200`，通过 JSON 内的 `success` 字段区分 |
| 字符编码 | UTF-8 |

#### 前端轮询策略

| 参数 | 值 | 说明 |
|------|-----|------|
| 轮询间隔 | 1 秒 | `setInterval(fetchStatus, 1000)` |
| 首次调用 | 立即 | `fetchStatus()` 在页面加载时马上执行 |
| 超时处理 | 无 | 纯 LAN 环境，不设超时重试 |

#### 红外检测策略

| 参数 | 值 | 说明 |
|------|-----|------|
| 轮询间隔 | 0.5 秒 | `IR_DETECT_INTERVAL = 0.5` |
| 超时时间 | 30 秒 | `DISPENSE_TIMEOUT = 30` |
| 最大检测次数 | 60 次 | `IR_RETRY_COUNT = 60` |

### 数据流分层

```
用户操作 (浏览器)
    │
    ├── 物理按键 ──→ GPIO 中断 ──→ CoinButton.callback ──→ sm.add_coin()
    │
    └── 页面点击 ──→ fetch API ──→ Flask 路由 ──→ sm.method()
                                                        │
                                         ┌──────────────┴──────────────┐
                                         ▼                             ▼
                                   sm 状态变更                  Inventory 读写
                                    │                          data/inventory.json
                                    ▼
                               on_dispense 回调
                                    │
                          ┌─────────┴──────────┐
                          ▼                    ▼
                     rgb.set_channel(ch)  thread: ir.is_blocked()
                     buzzer 200ms              │
                                              ├── True → sm.complete()
                                              └── 超时 → sm.cancel()
    ┌─────────────────────────────────────────────────────────────┐
    │           前端轮询 GET /api/status → sm.get_state()         │
    └─────────────────────────────────────────────────────────────┘
```

### 错误处理架构

| 错误类型 | 检测层 | 处理方式 | 用户可见 |
|---------|--------|---------|---------|
| GPIO 初始化失败 | `hardware/gpio_init` | 抛 `RuntimeError`，程序退出 | 无法启动 |
| JSON 文件损坏 | `logic/inventory` | 备份损坏文件，重建默认库存 | 无感恢复 |
| 按键抖动 | `hardware/button` | 200ms 防抖（软件去抖） | 无感 |
| 非法状态操作 | `logic/state_machine` | 返回 `{"success": false, "msg":"..."}` | 前端弹窗提示 |
| 传感器误检测 | `hardware/ir_sensor` | 轮询滤波（连续 2 次命中才算有效） | 无感 |
| 前端网络异常 | `static/script.js` | `try/catch` 包裹 fetch | "连接失败，请刷新" |
| 按钮重复点击 | `static/script.js` | 确认/投币后按钮立即 disabled | 按钮灰色 |

### 开发环境隔离

```
Windows (开发)                        树莓派 (生产)
───────────────                      ───────────────
app.py 直接运行                       app.py 执行
    │                                     │
    ├── RPi.GPIO → MagicMock              ├── RPi.GPIO → 真实硬件
    ├── inventory.json 可读写              ├── inventory.json 可读写
    └── Flask 监听 5000                   └── Flask 监听 80
         │                                     │
         └── 浏览器访问 localhost:5000           └── 手机访问 树莓派IP
```

---

## 1. 硬件设计

### 1.1 GPIO 引脚定义（config.py 中定义）

```python
# ========== 引脚号 ==========
# RGB-LED（三色，替代原4个单色LED）
RGB_R_PIN = 17    # 红色通道 — 货道A 成人口罩
RGB_G_PIN = 18    # 绿色通道 — 货道B 儿童口罩
RGB_B_PIN = 19    # 蓝色通道 — 货道C N95

# 传感器和输入
IR_SENSOR_PIN = 23         # 红外传感器 — 取货口检测
COIN_BUTTON_PIN = 27       # 投币模拟按键 — 按下=投入1元

# 输出指示
BUZZER_PIN = 26            # 蜂鸣器
# GPIO22 空闲备用（原系统状态LED已取消，由RGB-LED状态颜色替代）

# ========== GPIO 模式 ==========
# RGB-LED三引脚、蜂鸣器 → GPIO.OUT
# 按键、红外 → GPIO.IN, pull_up_down=GPIO.PUD_UP
```

### 1.2 硬件接线表

| 树莓派引脚 | 连接对象 | 方向 | 说明 |
|-----------|---------|------|------|
| GPIO 17 | RGB-LED R脚 → 220Ω → GND | OUT | 红色通道（货道A 成人口罩） |
| GPIO 18 | RGB-LED G脚 → 220Ω → GND | OUT | 绿色通道（货道B 儿童口罩） |
| GPIO 19 | RGB-LED B脚 → 220Ω → GND | OUT | 蓝色通道（货道C N95） |
| GPIO 22 | 空闲（备用） | — | 原系统状态LED已取消，功能由RGB-LED颜色状态替代 |
| GPIO 23 | 红外传感器 (Signal) | IN(PUD_UP) | 高电平=被遮挡(有口罩) |
| GPIO 26 | 蜂鸣器模块 IO → PWM | OUT | 无源蜂鸣器，PWM驱动 |
| 3.3V | 蜂鸣器模块 VCC | 电源 | 必须接3.3V供电 |
| GPIO 27 | 投币按键 (一端GPIO，一端GND) | IN(PUD_UP) | 下降沿触发 |
| 3.3V | 红外传感器 VCC | 电源 | 注意用3.3V，非5V |
| GND | 红外GND + 按键GND + 蜂鸣器GND + LED负极(电阻后) | 共地 | |

**接线注意事项：**
- RGB-LED共阴极：公共脚接GND，R/G/B分别经220Ω电阻接GPIO
- GPIO 输出 HIGH=点亮对应颜色通道
- 投币按键使用内部上拉，另一端接 GND，按下=GPIO 变 LOW
- 红外传感器若为 3 线制：VCC→3.3V，GND→GND，OUT→GPIO23

### 1.3 出货流程说明

本方案无机械出货结构，采用 **LED 指示 + 人工取货**：

```
用户确认购买 → 对应货道 LED 亮起 → 蜂鸣器响 200ms
  → 用户看到 LED 亮起 → 从对应格子取出一个口罩
  → 将口罩放至取货口（红外传感器处）→ 红外检测到遮挡
  → 系统确认取货成功 → LED 熄灭 → 页面显示"购买成功"
```

---

## 2. 软件架构

### 2.1 项目文件结构

```
mask-vending-machine/
├── app.py                    # ——— 入口文件，负责启动 Flask 和 GPIO 初始化
├── requirements.txt          # 依赖列表
├── config.py                 # ——— 全局配置：引脚号、价格、库存初始值
├── hardware/                 # ——— Person A 负责
│   ├── __init__.py
│   ├── gpio_init.py          # GPIO.setmode/setup，硬件初始化
│   ├── led.py                # DispenserLED 类：出货指示灯控制
│   ├── ir_sensor.py          # IRSensor 类：红外传感器读取
│   └── button.py             # CoinButton 类：投币按键检测
├── logic/                    # ——— Person B 负责
│   ├── __init__.py
│   ├── state_machine.py      # StateMachine 类：业务状态机
│   └── inventory.py          # Inventory 类：库存管理 + 持久化
├── static/                   # ——— Person D 负责
│   ├── index.html            # 手机端主页面（单页应用）
│   ├── style.css             # 响应式样式
│   └── script.js             # 前端交互逻辑
└── data/
    └── inventory.json        # 库存数据文件（自动生成）
```

### 2.2 架构分层

```
┌───────────────────────────────────────────┐
│  手机浏览器 (用户操作界面)                   │
│  └── 静态页面: index.html + style.css      │
│  └── 交互逻辑: script.js (fetch API)       │
└───────────────┬───────────────────────────┘
                │ HTTP JSON API (7 个端点)
┌───────────────▼───────────────────────────┐
│  app.py (Flask Web Server)                │
│  └── 路由处理 → 转发到 StateMachine        │
│  └── 调用 hardware/ 控制 GPIO             │
├───────────────────────────────────────────┤
│  logic/ (业务逻辑层)                       │
│  ├── state_machine.py ← 状态机调度         │
│  └── inventory.py     ← 库存管理           │
├───────────────────────────────────────────┤
│  hardware/ (硬件控制层)                    │
│  ├── gpio_init.py     ← 引脚初始化         │
│  ├── led.py           ← LED 亮/灭          │
│  ├── ir_sensor.py     ← 红外读取           │
│  └── button.py        ← 按键检测           │
├───────────────────────────────────────────┤
│  data/inventory.json (数据持久化)          │
└───────────────────────────────────────────┘
```

- **app.py 是唯一的集成点**，负责初始化所有模块并组装在一起
- **logic/ 不直接调用 hardware/**，由 app.py 在需要时传递调用
- **static/ 不关心后端实现**，只按 API 接口约定调 fetch

---

## 3. 各模块接口规范（核心协作约定）

### 3.1 Person A — hardware/ 各模块

**严格遵循以下类和函数签名，Person C 将按此签名调用。**

#### hardware/gpio_init.py

```python
def init_gpio():
    """
    初始化所有 GPIO 引脚。
    - 设置 GPIO 模式为 BCM
    - 配置 RGB-LED 三引脚/BUZZER 引脚为 OUTPUT，初始 LOW
    - 配置按键/红外引脚为 INPUT，PUD_UP
    无返回值。
    异常：如果初始化失败则抛出 RuntimeError
    """

def cleanup_gpio():
    """
    清理 GPIO 资源。
    - 所有输出引脚置 LOW
    - 调用 GPIO.cleanup()
    无返回值。
    """
```

#### hardware/led.py

```python
class RGBLED:
    """
    RGB 三色LED控制。

    Constructor:
        __init__(self, r_pin: int, g_pin: int, b_pin: int)
        - r_pin: 红色通道 GPIO 引脚号
        - g_pin: 绿色通道 GPIO 引脚号
        - b_pin: 蓝色通道 GPIO 引脚号

    Methods:
        def set_color(self, r: bool, g: bool, b: bool) -> None
            - 设置 RGB 颜色（True=点亮对应通道）

        def off(self) -> None
            - 全部熄灭

        def set_channel(self, channel: int) -> None
            - 按货道显示颜色：0=红(成人口罩), 1=绿(儿童口罩), 2=蓝(N95)

    Usage:
        rgb = RGBLED(17, 18, 19)
        rgb.set_channel(0)  # GPIO 17 输出 HIGH，显示红色
        rgb.off()           # 全部熄灭
    """
```

#### hardware/ir_sensor.py

```python
class IRSensor:
    """
    红外传感器 — 检测取货口是否有口罩。

    Constructor:
        __init__(self, pin: int)
        - pin: GPIO 引脚号

    Methods:
        def is_blocked(self) -> bool:
            - 读取 GPIO 电平
            - 返回 True=被遮挡（有口罩放置），False=未被遮挡
            - 注意：取决于传感器模块类型（常开/常闭），
              如果行为相反就在此方法内部做逻辑取反

    Usage:
        ir = IRSensor(23)
        if ir.is_blocked():
            print("口罩已放置")
    """
```

#### hardware/button.py

```python
class CoinButton:
    """
    投币模拟按键检测。

    Constructor:
        __init__(self, pin: int, callback: callable)
        - pin: GPIO 引脚号
        - callback: 按键按下时的回调函数（无参数）
        - 内部注册 GPIO 下降沿中断，带 200ms 防抖

    Methods:
        def start(self) -> None:
            - 启用按键监听
            - 添加 GPIO 中断事件检测

        def stop(self) -> None:
            - 停用按键监听
            - 移除 GPIO 中断事件检测

    Usage:
        def on_coin():
            print("收到1元")

        btn = CoinButton(27, on_coin)
        btn.start()
    """
```

### 3.2 Person B — logic/ 各模块

#### logic/state_machine.py

```python
class StateMachine:
    """
    贩卖机状态机 — 管理交易全生命周期。

    ===== 状态常量 =====
    IDLE      = 0   # 待机状态，可投币可选择
    SELECTED  = 1   # 已选择品类，等待确认
    DISPENSE  = 2   # 出货中（LED已亮起，等待取货）

    ===== 状态迁移图 =====
    IDLE ──select(ch)──▶ SELECTED ──confirm()──▶ DISPENSE ──complete()──▶ IDLE
     │                     │  │                       │
     │◀──cancel()──────────┘  │                       │
     │◀───────────────────────┴───────────────────────┘
     └──add_coin()── (余额增加，状态不变)
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
        - 在任何状态下都可调用
        - balance += 1
        返回: 当前余额 balance (int)
        """

    def select(self, channel: int) -> dict:
        """
        选择口罩品类。
        要求: state 必须为 IDLE
        检查:
            - balance < channels[channel].price → 返回 {"success": False, "msg": "余额不足"}
            - channels[channel].stock <= 0    → 返回 {"success": False, "msg": "库存不足"}
            通过 → state → SELECTED, selected_channel = channel
        返回: {"success": True, "channel": channel, "price": price, "name": name}
             或 {"success": False, "msg": "错误原因"}
        """

    def confirm(self, on_dispense: callable) -> dict:
        """
        确认购买。
        要求: state 必须为 SELECTED，balance >= price，stock > 0
        流程:
        1. balance -= price
        2. state = DISPENSE
        3. 执行回调 dispense_callback(selected_channel) — 通知 Person C 点亮LED+蜂鸣器
        4. 返回 {"success": True, "msg": "出货中，请取货", "channel": channel}
        错误:
            - 状态不对 → 返回 {"success": False, "msg": "状态错误"}
            - 其他异常 → 返回 {"success": False, "msg": "系统错误"}
        """

    def cancel(self) -> dict:
        """
        取消交易。
        要求: state 为 SELECTED 或 DISPENSE
        流程:
        1. balance = 0（不退还到余额）
        2. state = IDLE
        3. selected_channel = None
        返回: {"success": True, "balance": 0}
        """

    def complete(self) -> dict:
        """
        取货完成（由 Person C 在红外检测到后调用）。
        要求: state 为 DISPENSE
        流程:
        1. 扣减库存 inventory.deduct(selected_channel)
        2. 记录交易日志
        3. state = IDLE, selected_channel = None
        返回: {"success": True, "msg": "购买完成", "transaction_id": str}
        """

    def get_state(self) -> dict:
        """
        获取完整状态（用于 API /api/status 返回）。
        返回:
        {
            "state": self.state,          # int 状态码
            "state_name": "IDLE",         # 状态名
            "balance": self.balance,
            "selected_channel": self.selected_channel,  # None 或 int
            "channels": [...]             # 来自 inventory.get_status()
        }
        """
```

**C 调用 B 的接口汇总：**

| 函数调用 | 何时调用 |
|---------|---------|
| `sm.add_coin()` | POST /api/coin |
| `sm.select(ch)` | POST /api/select/<id> |
| `sm.confirm(on_dispense)` | POST /api/confirm |
| `sm.cancel()` | POST /api/cancel |
| `sm.complete()` | 红外检测到口罩时 |
| `sm.get_state()` | GET /api/status |

#### logic/inventory.py

```python
class Inventory:
    """
    库存管理。
    - 数据存储在 data/inventory.json
    - 程序启动时读取，每次变更后立即写回
    """

    def __init__(self, data_path: str = "data/inventory.json"):
        """
        初始化库存。
        - 如果文件存在则 load()
        - 如果文件不存在则创建默认库存并 save()
        """

    def load(self) -> None:
        """从 JSON 文件读取到内存。"""

    def save(self) -> None:
        """将内存数据写回 JSON 文件。"""

    def deduct(self, channel: int) -> bool:
        """
        扣减库存。
        - 检查 stock > 0
        - 扣减后立即 save()
        返回: True=成功，False=库存不足
        """

    def get_status(self) -> list:
        """
        返回所有货道信息。
        返回:
        [
            {
                "id": 0,
                "name": "成人口罩",
                "price": 2.0,
                "stock": 10,
                "available": True    # stock > 0
            },
            ...
        ]
        """

    def add_transaction(self, channel: int, amount: float, status: str) -> dict:
        """
        记录一笔交易。
        - channel: 货道ID
        - amount: 交易金额
        - status: "success" | "failed" | "cancelled"
        返回: {"time": "2026-06-22 10:30:00", "item": "成人口罩", "amount": 2.0, "status": "success"}
        """

    def get_transactions(self, limit: int = 50) -> list:
        """返回最近 limit 条交易记录。"""
    """
```

**inventory.json 格式：**

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

#### config.py

```python
# ===== GPIO 引脚 =====
LED_CHANNEL_0 = 17
LED_CHANNEL_1 = 18
LED_CHANNEL_2 = 19
LED_CHANNEL_ALL = [LED_CHANNEL_0, LED_CHANNEL_1, LED_CHANNEL_2]
IR_SENSOR_PIN = 23
STATUS_LED_PIN = 22
BUZZER_PIN = 26
COIN_BUTTON_PIN = 27

# ===== 价格和库存 =====
CHANNEL_CONFIG = [
    {"id": 0, "name": "成人口罩", "price": 2.0, "init_stock": 10},
    {"id": 1, "name": "儿童口罩", "price": 2.0, "init_stock": 10},
    {"id": 2, "name": "N95口罩",  "price": 5.0, "init_stock": 5},
]

# ===== 时间参数 =====
DISPENSE_TIMEOUT = 30      # 出货等待超时（秒）
IR_DETECT_INTERVAL = 0.5   # 红外轮询间隔（秒）
IR_RETRY_COUNT = 60        # 超时前的检测次数 = DISPENSE_TIMEOUT / IR_DETECT_INTERVAL
```

---

### 3.3 Person C — app.py (Flask API)

**这是整个系统集成点。Person C 负责把所有模块组装起来。**

#### 启动入口结构

```python
# app.py — 完整骨架

from flask import Flask, jsonify, request, send_from_directory
from config import *
from hardware.gpio_init import init_gpio, cleanup_gpio
from hardware.led import RGBLED
from hardware.ir_sensor import IRSensor
from hardware.button import CoinButton
from logic.state_machine import StateMachine
from logic.inventory import Inventory

app = Flask(__name__, static_folder='static')

# ---- 初始化模块 ----
inv = Inventory('data/inventory.json')
sm = StateMachine(inv)
rgb = RGBLED(RGB_R_PIN, RGB_G_PIN, RGB_B_PIN)
ir = IRSensor(IR_SENSOR_PIN)
```

**Person C 需要实现的 3 个额外函数：**

```python
# ===== 由状态机回调的出货函数 =====
def on_dispense(channel: int):
    """
    出货回调 — 由 sm.confirm(on_dispense) 调用。
    1. 按货道设置RGB颜色: rgb.set_channel(channel)
    2. 蜂鸣器响 200ms: buzzer.beep(freq=1000, duration=0.2)
    3. 启动后台线程轮询红外传感器
    """

# ===== 红外轮询线程 =====
def wait_for_pickup(channel: int):
    """
    后台线程执行，不阻塞 API 返回。
    1. 每 0.5 秒读一次 ir.is_blocked()
    2. 检测到被遮挡 → 调用 sm.complete() → rgb.off() → 记录完成
    3. 超时 30 秒 → 调用 sm.cancel() → rgb.off()
    """

# ===== 投币按键回调 =====
def on_coin_pressed():
    """由 CoinButton 回调。调用 sm.add_coin()，无需其他操作。"""
```

#### API 端点详细定义（7个）

```python
# ---- 1. 主页 ----
# GET /
# 返回: static/index.html 内容
# Content-Type: text/html
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


# ---- 2. 状态查询 ----
# GET /api/status
# 返回: JSON 状态对象
# 示例响应:
# {
#   "state": 0,
#   "state_name": "IDLE",
#   "balance": 3,
#   "selected_channel": null,
#   "channels": [
#     {"id": 0, "name": "成人口罩", "price": 2.0, "stock": 10, "available": true},
#     {"id": 1, "name": "儿童口罩", "price": 2.0, "stock": 10, "available": true},
#     {"id": 2, "name": "N95口罩", "price": 5.0, "stock": 5, "available": true}
#   ]
# }
@app.route('/api/status')
def api_status():
    return jsonify(sm.get_state())


# ---- 3. 投币 ----
# POST /api/coin
# 请求体: 无
# 示例响应: {"balance": 4}
@app.route('/api/coin', methods=['POST'])
def api_coin():
    balance = sm.add_coin()
    return jsonify({"balance": balance})


# ---- 4. 选择品类 ----
# POST /api/select/<channel_id>
# 示例: POST /api/select/0
# 成功响应: {"success": true, "channel": 0, "price": 2.0, "name": "成人口罩"}
# 失败响应: {"success": false, "msg": "余额不足"} 或 {"success": false, "msg": "库存不足"}
@app.route('/api/select/<int:channel_id>', methods=['POST'])
def api_select(channel_id):
    result = sm.select(channel_id)
    return jsonify(result)


# ---- 5. 确认购买 ----
# POST /api/confirm
# 请求体: 无
# 成功响应: {"success": true, "msg": "出货中，请取货", "channel": 0}
# 失败响应: {"success": false, "msg": "状态错误"}
@app.route('/api/confirm', methods=['POST'])
def api_confirm():
    result = sm.confirm(on_dispense=on_dispense)
    return jsonify(result)


# ---- 6. 取消交易 ----
# POST /api/cancel
# 请求体: 无
# 响应: {"success": true, "balance": 0}
@app.route('/api/cancel', methods=['POST'])
def api_cancel():
    result = sm.cancel()
    return jsonify(result)


# ---- 7. 交易记录 ----
# GET /api/logs
# 示例响应:
# [
#   {"time": "2026-06-22 10:30:00", "item": "成人口罩", "amount": 2.0, "status": "success"}
# ]
@app.route('/api/logs')
def api_logs():
    return jsonify(inv.get_transactions())
```

#### main 入口

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

### 3.4 Person D — static/ 前端页面

**与后端唯一的沟通方式是通过 7 个 API 端点，所有数据格式已在 3.3 节定义。**

#### 页面要求

**index.html** — 单页应用，一个 HTML 包含 3 个视图：

```html
<!-- 视图1: 主界面 -->
<div id="page-main">
  <div class="header">余额: ¥<span id="balance">0</span></div>
  <button id="btn-coin" class="coin-btn">投币 +1元</button>
  <div id="product-list">
    <!-- JS 动态渲染，每个卡片包含: 名称、价格、库存、购买按钮 -->
  </div>
  <button id="btn-cancel" class="cancel-btn" style="display:none">取消交易</button>
</div>

<!-- 视图2: 确认弹窗（遮罩层） -->
<div id="page-confirm" class="modal" style="display:none">
  <div class="modal-content">
    <p>商品: <span id="confirm-name"></span></p>
    <p>金额: ¥<span id="confirm-price"></span></p>
    <p>余额: ¥<span id="confirm-balance"></span></p>
    <button id="btn-confirm-yes">确认购买</button>
    <button id="btn-confirm-no">取消</button>
  </div>
</div>

<!-- 视图3: 结果页 -->
<div id="page-result" style="display:none">
  <div id="result-icon"></div>      <!-- ✅ 或 ❌ -->
  <div id="result-message"></div>   <!-- 成功/失败原因 -->
  <div id="result-timer">3秒后返回</div>
</div>
```

**核心 JS 函数：**

```javascript
// ===== API 基地址 =====
const API_BASE = window.location.origin;

// ===== 页面状态 =====
let state = {
    state: 0,
    state_name: 'IDLE',
    balance: 0,
    selected_channel: null,
    channels: []
};

// ===== 1. 轮询状态 =====
async function fetchStatus() {
    /** 每 1 秒调用 /api/status，更新全局 state 和 UI */
    const res = await fetch(`${API_BASE}/api/status`);
    state = await res.json();
    renderUI();
}

// ===== 2. 投币 =====
async function onCoinClick() {
    /** POST /api/coin → 更新余额显示 */
}

// ===== 3. 选择商品 =====
async function onBuyClick(channelId) {
    /** POST /api/select/{id} → 成功则弹出确认页 */
}

// ===== 4. 确认购买 =====
async function onConfirmClick() {
    /** POST /api/confirm → 成功则切换到结果页(出货动画) */
}

// ===== 5. 取消 =====
async function onCancelClick() {
    /** POST /api/cancel → 余额归零，回到主界面 */
}

// ===== 6. UI 渲染 =====
function renderUI() {
    /**
     * 根据 state 刷新:
     * - 余额文本
     * - 商品卡片的购买按钮状态（余额不足/库存不足时 disabled）
     * - 取消按钮显隐
     */
}

// ===== 7. 视图切换 =====
function showPage(pageId) {
    /** 显示指定视图，隐藏其他视图 */
}

// ===== 初始化 =====
setInterval(fetchStatus, 1000);   // 每秒轮询
fetchStatus();                     // 首次立即获取
```

**style.css 要求：**

```css
/* ===== 布局 ===== */
/* 移动端优先设计，最大宽度 480px，居中 */
body 背景色 #1a1a2e (暗色主题)
.card 白色卡片, 圆角12px, 阴影
/* 每个商品卡片的购买按钮 */
.btn-buy: 蓝色背景, 白色文字
.btn-buy:disabled 灰色背景, 文字"缺货" 或 "余额不足"
/* 投币按钮 */
.coin-btn: 大尺寸, 绿色背景, 明显突出
/* 余额显示 */
.header: 大字号, 显眼位置
/* 出货动画 */
@keyframes progress { from { width: 0% } to { width: 100% } }
.progress-bar { height: 20px; background: linear-gradient(...); animation: progress 2s }
/* 结果页 */
.result-success { color: #4caf50; font-size: 48px }  /* ✅ */
.result-fail { color: #f44336; font-size: 48px }     /* ❌ */
```

---

## 4. 完整数据流（核心场景）

### 场景1：正常购买

```
用户动作                  HTTP/API                     后端逻辑
─────────────────    ──────────────────    ─────────────────────────
1.打开手机浏览器 →      GET /               → 返回 index.html
2.看到页面，投币         ← 余额显示 ¥0
3.按物理投币按键         → (GPIO中断自动触发)
                                               sm.add_coin() → balance=1
4.页面轮询状态           GET /api/status      → sm.get_state() → {balance:1}
5.选择"成人口罩"         POST /api/select/0   → sm.select(0) → 状态变 SELECTED
                        ← {success:true, price:2.0}
6.点"确认购买"           POST /api/confirm    → sm.confirm(on_dispense)
                                                → rgb.set_channel(0) → 蜂鸣器200ms
                                                → 状态变 DISPENSE
                                                → 启动红外轮询线程
                        ← {success:true, msg:"出货中"}
7.页面显示进度条         ← 出货动画
8.LED亮起，用户取口罩     → 手动操作
9.放口罩至取货口          → 红外检测到遮挡
                                               → sm.complete() → 扣库存
                                               → rgb.off()
10.页面轮询              GET /api/status      → {state:IDLE, stock:9}
                        ← 页面回到主界面，库存更新为9
```

### 场景2：余额不足

```
POST /api/select/0  →  sm.select(0) 检查 balance(1) < price(2)
                      ←  {"success": false, "msg": "余额不足"}
页面弹窗提示"余额不足，请继续投币"
```

### 场景3：库存不足

```
POST /api/select/0  →  sm.select(0) 检查 stock(0) <= 0
                      ←  {"success": false, "msg": "库存不足"}
页面按钮显示 "缺货" 并灰色不可点
```

### 场景4：取消交易

```
用户在 SELECTED 状态 → 点击"取消"按钮
POST /api/cancel    →  sm.cancel() → balance=0, state=IDLE
                      ←  {"success": true, "balance": 0}
页面余额归零，回到主界面
```

### 场景5：取货超时

```
用户确认购买后 → 30秒内红外未检测到口罩
红外轮询线程超时
  → sm.cancel()(不做退款，但释放库存锁定)
  → rgb.off()
  → 前端下次轮询状态变回 IDLE
页面显示"取货超时，交易已取消"
```

---

## 5. 错误处理边界

| 场景 | 后端处理 | 前端显示 |
|------|---------|---------|
| GPIO 初始化失败 | 启动时抛 RuntimeError，程序退出 | — |
| inventory.json 损坏 | 备份后重建默认库存 | — |
| 同时收到多次请求 | Flask threaded=True，但 StateMachine 保证单线程状态安全 | 防止按钮重复点击 |
| 用户刷新页面 | 前端重新 fetchStatus() 获取最新状态 | 初始化时立即调用 fetchStatus() |
| 状态非法操作 | sm.confirm() 在 IDLE 状态被调 → 返回 {"success":false} | 显示"操作无效" |
| 网络断开 | API 超时或 404 | JS try/catch，显示"连接失败" |
| 多用户同时操作 | 课设仅为单用户场景，不做并发控制 | — |
| 出货中途断电 | 未持久化的余额丢失（可接受） | — |

---

## 6. 开发环境与 Mock 支持

```python
# hardware/gpio_init.py
try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from unittest.mock import MagicMock
    GPIO = MagicMock()
    print("[MOCK] Using mock GPIO for Windows development")
```

Windows 开发时，所有 GPIO 调用变为无操作（MagicMock 自动处理），Flask 可以正常启动和调试。

### 启动命令

```bash
# 开发（Windows）
pip install flask
python app.py
# → 浏览器访问 http://localhost:5000

# 生产（树莓派）
pip install flask RPi.GPIO
sudo python app.py
# → 本机IP:5000 访问
```

---

## 7. 各人开发顺序

### Person A — hardware/ + 接线

1. 先在树莓派上接线（面包板）
2. 写 gpio_init.py（设置引脚模式、测试每个引脚输出正常）
3. 写 led.py（测试RGB-LED各颜色通道及set_channel切换）
4. 写 ir_sensor.py（用手遮挡/移开测试读取值变化）
5. 写 button.py（按下按键测试回调正常）
6. 将 4 个文件放到 hardware/ 目录

### Person B — logic/

1. 写 inventory.py（测试：读/写 JSON、扣减库存、记录交易）
2. 写 state_machine.py（测试：完整购买流程、余额不足、取消交易）
3. 写 config.py（常量定义）
4. 不需要硬件，纯 Python 即可测试

### Person C — app.py

1. 先写 API 骨架，所有路由返回 mock 数据
2. 依次接入 B 的 state_machine、inventory
3. 依次接入 A 的 led、ir_sensor
4. 最后集成投币按键回调 + 红外检测线程
5. 测试工具：用 curl 或 Postman 手动测每个 API

### Person D — static/

1. 先做 HTML 结构 + CSS 样式
2. 用硬编码的 JS 数据调通 UI 渲染
3. 接入真实 API 调用（在 PC 上连 C 的 Flask 开发服务器）
4. 调试全流程交互体验

---

---

## 8. 各人自测

### 8.1 Person A — hardware/ 驱动测试

#### 测试代码（可另存为 `test_hardware.py`）

```python
# test_hardware.py
# Person A 在树莓派上跑，验证所有硬件工作正常
# 运行方法: sudo python test_hardware.py

import time
from config import *
from hardware.gpio_init import init_gpio, cleanup_gpio
from hardware.led import RGBLED
from hardware.ir_sensor import IRSensor
from hardware.button import CoinButton

def test_leds():
    """测试 RGB-LED 三色显示"""
    print("[TEST] 测试 RGB-LED ...")
    rgb = RGBLED(RGB_R_PIN, RGB_G_PIN, RGB_B_PIN)
    print("  红 (R) 亮")
    rgb.set_color(1, 0, 0)
    time.sleep(1)
    print("  绿 (G) 亮")
    rgb.set_color(0, 1, 0)
    time.sleep(1)
    print("  蓝 (B) 亮")
    rgb.set_color(0, 0, 1)
    time.sleep(1)
    print("  黄 (R+G) 亮")
    rgb.set_color(1, 1, 0)
    time.sleep(1)
    rgb.off()
    print("  OK")

def test_buzzer():
    """无源蜂鸣器 PWM 发声测试"""
    print("[TEST] 测试 蜂鸣器 ...")
    from hardware.buzzer import Buzzer
    buzzer = Buzzer(BUZZER_PIN)
    buzzer.beep(freq=1000, duration=0.5)
    print("  OK")

def test_ir_sensor():
    """检测红外传感器读数，用手遮挡观察输出变化"""
    print("[TEST] 测试 红外传感器 ...")
    ir = IRSensor(IR_SENSOR_PIN)
    print("  ※ 请用手遮挡/移开传感器，观察输出变化")
    print("  ※ 5 秒后退出")
    for _ in range(10):
        status = ir.is_blocked()
        print(f"  {'█ 遮挡' if status else '○ 无遮挡'}")
        time.sleep(0.5)
    print("  OK")

def test_coin_button():
    """按按键后看是否打印 '收到1元'"""
    print("[TEST] 测试 投币按键 ...")
    print("  ※ 请按按键 3 次，观察输出")
    count = 0

    def on_coin():
        nonlocal count
        count += 1
        print(f"  收到1元 (累计: {count})")

    btn = CoinButton(COIN_BUTTON_PIN, on_coin)
    btn.start()
    time.sleep(10)  # 等待按键
    btn.stop()
    if count >= 3:
        print("  OK")
    else:
        print(f"  ⚠ 只检测到 {count} 次，请检查接线")

if __name__ == '__main__':
    try:
        init_gpio()
        test_leds()
        test_buzzer()
        test_ir_sensor()
        test_coin_button()
    finally:
        cleanup_gpio()
```

**预期结果：**
```
[TEST] 测试 RGB-LED ...
  红 (R) 亮
  绿 (G) 亮
  蓝 (B) 亮
  黄 (R+G) 亮
  OK
[TEST] 测试 蜂鸣器 ... OK
[TEST] 测试 红外传感器 ...
  ○ 无遮挡
  ○ 无遮挡
  █ 遮挡       ← 用手挡住时
  █ 遮挡
  ○ 无遮挡     ← 松手后
  OK
[TEST] 测试 投币按键 ...
  ※ 请按按键 3 次
  收到1元 (累计: 1)
  收到1元 (累计: 2)
  收到1元 (累计: 3)
  OK
```

#### 测试表单

| # | 测试项 | 操作 | 预期 | 结果 | 备注 |
|---|-------|------|------|------|------|
| 1 | RGB-LED 颜色测试 | 运行 test_hardware.py | 红→绿→蓝→黄各亮1秒，最后熄灭 | □ | |
| 2 | 蜂鸣器 | 同上 | 蜂鸣器响 0.5 秒 | □ | |
| 3 | 红外遮挡 | 同上后用手遮挡 | 显示 █ 遮挡 | □ | 不遮挡显示 ○ |
| 4 | 投币按键 | 同上后按按键3次 | 显示"收到1元"×3 | □ | |

---

### 8.2 Person B — logic/ 逻辑测试

#### 测试代码（可另存为 `test_logic.py`）

```python
# test_logic.py
# Person B 在任意机器上跑（不需要树莓派）
# 运行方法: python test_logic.py

import os
import json
import tempfile
from logic.inventory import Inventory
from logic.state_machine import StateMachine

def test_inventory():
    """库存管理测试"""
    print("[TEST] Inventory ...")

    # 使用临时文件
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    tmp.write(json.dumps({
        "channels": [
            {"id": 0, "name": "成人口罩", "price": 2.0, "stock": 3},
            {"id": 1, "name": "儿童口罩", "price": 2.0, "stock": 0},
        ],
        "transactions": []
    }))
    tmp.close()

    inv = Inventory(tmp.name)

    # 测试1: 读取库存
    status = inv.get_status()
    assert status[0]["name"] == "成人口罩"
    assert status[0]["stock"] == 3
    assert status[0]["available"] == True
    assert status[1]["available"] == False   # stock=0
    print("  [PASS] 库存读取正确")

    # 测试2: 扣减库存
    assert inv.deduct(0) == True
    assert inv.deduct(0) == True
    assert inv.deduct(0) == True
    assert inv.deduct(0) == False  # 库存不足
    print("  [PASS] 库存扣减+库存不足检测正确")

    # 测试3: 库存扣减后 available 更新
    status = inv.get_status()
    assert status[0]["available"] == False
    print("  [PASS] available 状态正确")

    # 测试4: 交易记录
    tx = inv.add_transaction(0, 2.0, "success")
    assert tx["item"] == "成人口罩"
    assert tx["amount"] == 2.0
    assert len(inv.get_transactions()) == 1
    print("  [PASS] 交易记录正确")

    # 清理
    os.unlink(tmp.name)
    print("  OK")

def test_state_machine():
    """状态机全流程测试"""
    print("\n[TEST] StateMachine ...")

    inv = Inventory("data/inventory.json")
    sm = StateMachine(inv)

    # 初始状态
    s = sm.get_state()
    assert s["state"] == 0        # IDLE
    assert s["balance"] == 0
    assert s["state_name"] == "IDLE"
    print("  [PASS] 初始状态正确")

    # 测试1: 投币
    bal = sm.add_coin()
    bal = sm.add_coin()
    bal = sm.add_coin()
    assert bal == 3
    print("  [PASS] 投币累加正确 (¥3)")

    # 测试2: 选择商品
    result = sm.select(0)   # 成人口罩 ¥2
    assert result["success"] == True
    assert sm.get_state()["state_name"] == "SELECTED"
    print("  [PASS] 选择商品正确")

    # 测试3: 取消交易
    sm.cancel()
    assert sm.get_state()["balance"] == 0
    assert sm.get_state()["state_name"] == "IDLE"
    print("  [PASS] 取消交易正确")

    # 测试4: 余额不足
    sm.add_coin()  # balance = 1
    result = sm.select(0)  # 需要 ¥2
    assert result["success"] == False
    assert result["msg"] == "余额不足"
    print("  [PASS] 余额不足检测正确")

    # 测试5: 库存不足
    sm.add_coin()  # balance = 2
    result = sm.select(1)  # 儿童口罩 stock=0
    assert result["success"] == False
    assert result["msg"] == "库存不足"
    print("  [PASS] 库存不足检测正确")

    # 测试6: 完整购买流程
    sm.add_coin()  # balance = 3
    sm.add_coin()
    assert sm.get_state()["balance"] == 3

    result = sm.select(0)  # 成人口罩 ¥2
    assert result["success"] == True

    dispensed = []
    def fake_dispense(ch):
        dispensed.append(ch)

    result = sm.confirm(on_dispense=fake_dispense)
    assert result["success"] == True
    assert sm.get_state()["state_name"] == "DISPENSE"
    assert sm.get_state()["balance"] == 1  # 3-2=1
    assert dispensed == [0]   # 确认回调被调用
    print("  [PASS] 确认购买后余额扣减正确")

    # 完成取货
    result = sm.complete()
    assert result["success"] == True
    assert sm.get_state()["state_name"] == "IDLE"
    print("  [PASS] 完成取货后状态恢复正确")

    print("  OK")

def test_error_cases():
    """边界情况测试"""
    print("\n[TEST] ErrorCases ...")

    inv = Inventory("data/inventory.json")
    sm = StateMachine(inv)

    # IDLE 状态不能 confirm
    result = sm.confirm(on_dispense=lambda ch: None)
    assert result["success"] == False
    print("  [PASS] IDLE态拒绝 confirm 正确")

    # SELECTED 状态不能 select
    sm.add_coin()
    sm.add_coin()
    sm.select(0)
    result = sm.select(1)
    assert result["success"] == False
    print("  [PASS] SELECTED态拒绝二次 select 正确")

    # DISPENSE 状态不能 select
    sm.confirm(on_dispense=lambda ch: None)
    result = sm.select(0)
    assert result["success"] == False
    print("  [PASS] DISPENSE态拒绝 select 正确")

    # 非法 channel_id
    sm.cancel()
    sm.add_coin()
    sm.add_coin()
    result = sm.select(99)
    assert result["success"] == False
    print("  [PASS] 非法 channel_id 拒绝正确")

    print("  OK")

if __name__ == '__main__':
    test_inventory()
    test_state_machine()
    test_error_cases()
    print("\n✅ All logic tests passed!")
```

**预期输出：**
```
[TEST] Inventory ...
  [PASS] 库存读取正确
  [PASS] 库存扣减+库存不足检测正确
  [PASS] available 状态正确
  [PASS] 交易记录正确
  OK

[TEST] StateMachine ...
  [PASS] 初始状态正确
  [PASS] 投币累加正确 (¥3)
  [PASS] 选择商品正确
  [PASS] 取消交易正确
  [PASS] 余额不足检测正确
  [PASS] 库存不足检测正确
  [PASS] 确认购买后余额扣减正确
  [PASS] 完成取货后状态恢复正确
  OK

[TEST] ErrorCases ...
  [PASS] IDLE态拒绝 confirm 正确
  [PASS] SELECTED态拒绝二次 select 正确
  [PASS] DISPENSE态拒绝 select 正确
  [PASS] 非法 channel_id 拒绝正确
  OK

✅ All logic tests passed!
```

#### 测试表单

| # | 测试项 | 操作 | 预期 | 结果 | 备注 |
|---|-------|------|------|------|------|
| 1 | 库存读写 | 运行 test_logic.py | [PASS] 库存读取正确 | □ | |
| 2 | 库存扣减 | 同上 | 三次扣减后第四返回 False | □ | |
| 3 | 交易记录 | 同上 | 记录生成，item/amount 正确 | □ | |
| 4 | 初始状态 | 同上 | state=IDLE, balance=0 | □ | |
| 5 | 投币累加 | 同上 | 3次投币后 balance=3 | □ | |
| 6 | 余额不足 | 同上 | select 返回 success=False | □ | |
| 7 | 库存不足 | 同上 | select 返回 success=False | □ | |
| 8 | 完整购买 | 同上 | IDLE→SELECTED→DISPENSE→IDLE | □ | |
| 9 | 取消交易 | 同上 | balance=0, state=IDLE | □ | |
| 10 | 状态锁 | 同上 | IDLE不确认、SELECTED不再选 | □ | |

---

### 8.3 Person C — app.py API 测试

#### 测试代码（可另存为 `test_api.py`）

```python
# test_api.py
# Person C 测试所有 API 端点
# 运行前提: app.py 已在本地启动（Windows 上 mock GPIO）
# 运行方法: python test_api.py

import requests
import json
import time

BASE = "http://localhost:5000"

def test_homepage():
    """主页返回 HTML"""
    r = requests.get(f"{BASE}/")
    assert r.status_code == 200
    assert "text/html" in r.headers["Content-Type"]
    print("[PASS] GET / → 200, HTML")

def test_api_status():
    """状态接口返回完整信息"""
    r = requests.get(f"{BASE}/api/status")
    assert r.status_code == 200
    data = r.json()
    assert "state" in data
    assert "balance" in data
    assert "channels" in data
    assert len(data["channels"]) == 3
    print("[PASS] GET /api/status → 完整状态对象")

def test_coin():
    """投币接口"""
    r = requests.post(f"{BASE}/api/coin")
    assert r.status_code == 200
    data = r.json()
    assert "balance" in data
    print(f"[PASS] POST /api/coin → balance={data['balance']}")

def test_select():
    """选择商品"""
    # 先确保有余额
    requests.post(f"{BASE}/api/coin")
    requests.post(f"{BASE}/api/coin")

    r = requests.post(f"{BASE}/api/select/0")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] == True
    print(f"[PASS] POST /api/select/0 → 选择成功")

def test_select_insufficient():
    """余额不足选商品"""
    # 先取消回到 IDLE
    requests.post(f"{BASE}/api/cancel")

    # 余额不足
    requests.post(f"{BASE}/api/coin")  # balance=1
    r = requests.post(f"{BASE}/api/select/0")  # need ¥2
    data = r.json()
    assert data["success"] == False
    assert "余额不足" in data["msg"]
    print(f"[PASS] POST /api/select/0 余额不足 → 拒绝")

def test_confirm():
    """确认购买"""
    # 准备: 投币3元 → 选择
    requests.post(f"{BASE}/api/cancel")
    for _ in range(3):
        requests.post(f"{BASE}/api/coin")
    requests.post(f"{BASE}/api/select/0")

    r = requests.post(f"{BASE}/api/confirm")
    data = r.json()
    assert data["success"] == True
    print(f"[PASS] POST /api/confirm → 出货中")

def test_cancel():
    """取消交易"""
    # 准备: 投币 → 选择
    requests.post(f"{BASE}/api/cancel")
    for _ in range(3):
        requests.post(f"{BASE}/api/coin")
    requests.post(f"{BASE}/api/select/0")

    r = requests.post(f"{BASE}/api/cancel")
    data = r.json()
    assert data["success"] == True
    assert data["balance"] == 0
    print(f"[PASS] POST /api/cancel → 余额归零")

def test_complete_flow():
    """完整购买流程"""
    # 重置
    requests.post(f"{BASE}/api/reset") if has_reset() else None

    # 投币 → 选择 → 确认 → 完成
    for _ in range(3):
        requests.post(f"{BASE}/api/coin")
    requests.post(f"{BASE}/api/select/0")
    requests.post(f"{BASE}/api/confirm")

    # 等待红外检测（测试时直接检查状态变化）
    time.sleep(2)
    r = requests.get(f"{BASE}/api/status")
    data = r.json()
    print(f"[INFO] 购买后状态: {data['state_name']}, 余额: {data['balance']}")

def test_logs():
    """交易记录"""
    r = requests.get(f"{BASE}/api/logs")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    print(f"[PASS] GET /api/logs → {len(data)} 条记录")

def has_reset():
    """检查是否有 reset API"""
    try:
        r = requests.post(f"{BASE}/api/reset")
        return r.status_code == 200
    except:
        return False

if __name__ == '__main__':
    print("测试 API (确保 app.py 已在 localhost:5000 运行)")
    print("-" * 40)

    # 顺序执行
    try:
        test_homepage()
        test_api_status()
        test_coin()
        test_select()
        test_select_insufficient()
        test_cancel()
        test_confirm()
        test_logs()
        print("\n✅ All API tests passed!")
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到 localhost:5000，请先启动 app.py")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
```

**测试方式：**
```bash
# 终端1: 启动服务器
python app.py

# 终端2: 运行测试
python test_api.py
```

#### 测试表单

| # | 测试项 | 操作 | 预期 | 结果 | 备注 |
|---|-------|------|------|------|------|
| 1 | 主页 | `GET /` | 200 + text/html | □ | |
| 2 | 状态接口 | `GET /api/status` | 含 state, balance, channels 字段 | □ | |
| 3 | 投币 | `POST /api/coin` | balance +1 | □ | 连续3次 |
| 4 | 选择(有余额) | 投币后 `POST /api/select/0` | success: true | □ | |
| 5 | 选择(余额不足) | balance<price 时 select | success: false + msg | □ | |
| 6 | 确认购买 | 余额充足 select 后 confirm | success: true + "出货中" | □ | |
| 7 | 取消交易 | select 后 `POST /api/cancel` | balance=0, state=IDLE | □ | |
| 8 | 交易记录 | `GET /api/logs` | 返回数组 | □ | |
| 9 | 完整流程 | 投币→选品→确认→检测→完成 | 状态流转正确 | □ | |
| 10 | 非法参数 | select 不存在的 channel_id | 拒绝请求 | □ | |

---

### 8.4 Person D — 前端自测（浏览器）

#### 自测方法（不需要后端，用 mock 数据独立测试）

在 `script.js` 开头加入以下 mock：

```javascript
// script.js (开发阶段)
// 当后端未就绪时，用以下 mock 数据调试 UI

function useMockData() {
    // 模拟 fetch，返回假数据供页面渲染
    const mockState = {
        state: 0,
        state_name: "IDLE",
        balance: 3,
        selected_channel: null,
        channels: [
            {id: 0, name: "成人口罩", price: 2.0, stock: 5, available: true},
            {id: 1, name: "儿童口罩", price: 2.0, stock: 0, available: false},
            {id: 2, name: "N95口罩", price: 5.0, stock: 3, available: true},
        ]
    };

    // 用 mockState 渲染页面
    state = mockState;
    renderUI();
}

// 开发时取消注释即可脱离后端跑 UI
// useMockData();
```

#### 测试 checklist（在浏览器开发者工具中逐项验证）

```
打开浏览器控制台 (F12)：

1. 布局测试:
   □ iPhone SE 375×667  → 卡片3列变1列，可滚动
   □ iPhone 12 390×844  → 布局正常
   □ iPad 768×1024      → 卡片居中，留白合适

2. 元素检查:
   □ 余额显示在顶部，数字随 state.balance 变化
   □ 投币按钮绿色醒目，可点击
   □ 商品卡片：名称/价格/库存/购买按钮完整
   □ 库存=0时卡片 gray out + "缺货"文字
   □ 取消按钮默认隐藏，有余额后显示

3. 交互测试（手动修改 state 后调 renderUI()）:
   // 在控制台中执行:
   state.balance = 0; renderUI();
     □ "购买"按钮文字"余额不足"，灰色不可点
   state.balance = 3; renderUI();
     □ "购买"按钮蓝色可点
   state.channels[0].stock = 0; renderUI();
     □ 成人口罩卡片显示"缺货"，灰色不可点

4. 弹窗测试:
   // 控制台执行:
   $('#confirm-name').textContent = '成人口罩';
   $('#confirm-price').textContent = '2.0';
   $('#confirm-balance').textContent = '3.0';
   showPage('page-confirm');
     □ 遮罩层出现，信息正确
     □ 确认/取消按钮可点击

5. 动画测试:
   // 控制台执行:
   showPage('page-result');
   $('#result-icon').textContent = '✅';
   $('#result-message').textContent = '购买成功！请取走口罩';
     □ ✅ 图标显示
     □ 进度条动画 2 秒播放
     □ 3秒后自动返回主界面
```

#### 测试表单

| # | 测试项 | 操作方式 | 预期 | 结果 |
|---|-------|---------|------|------|
| 1 | 移动端布局 | F12 切 iPhone SE 尺寸 | 卡片单列，可上下滑 | □ |
| 2 | 商品卡片 | 直接打开页面 | 3个卡片显示名称/价格/库存 | □ |
| 3 | 余额显示 | mock: balance=3 → renderUI | 顶部显示 ¥3 | □ |
| 4 | 缺货状态 | mock: stock=0 → renderUI | 卡片灰色 + "缺货" | □ |
| 5 | 余额不足 | mock: 余额<价格 → renderUI | 按钮灰色 + "余额不足" | □ |
| 6 | 余额充足 | mock: 余额≥价格 → renderUI | 按钮蓝色可点 | □ |
| 7 | 确认弹窗 | mock: showPage('page-confirm') | 遮罩层 + 商品信息正确 | □ |
| 8 | 出货动画 | mock: showPage('page-result') ✅ | 进度条动画 2 秒 | □ |
| 9 | 失败结果 | mock: 显示 ❌ + 原因 | 错误图标 + 提示文字 | □ |
| 10 | 返回主界面 | 结果页等待 3 秒 | 自动回到主界面 | □ |

---

## 9. 联调清单（Day 2 检查用）

### 9.1 分模块检查

```
Person A:
  □ RGB-LED 各颜色通道独立亮灭（红/绿/蓝/黄）
  □ 按投币按键，回调正确触发
  □ 红外遮挡/不遮挡返回值正确

Person B:
  □ 投币 → balance 正确增加
  □ 选择商品 → 余额不足时拒绝
  □ 选择商品 → 库存不足时拒绝
  □ 确认购买 → 状态变 DISPENSE
  □ 完成取货 → 库存扣减、交易记录生成
  □ 取消交易 → 余额归零
  □ inventory.json 读写正确

Person C:
  □ 7个 API 返回正确状态码和格式
  □ POST /api/confirm 后 LED 亮起、蜂鸣器响
  □ 红外检测到后状态自动完成
  □ 按键投币后 /api/status 余额变化

Person D:
  □ 页面布局适配手机屏幕
  □ 余额实时显示
  □ 余额不足/库存不足时按钮禁用
  □ 确认弹窗显示正确商品信息
  □ 出货动画正常播放
  □ 结果页显示正确提示
```

### 8.2 全流程测试

```
□ 开机 → 系统状态LED亮
□ 打开浏览器 → 页面显示3种口罩，余额 ¥0
□ 按投币按键3次 → 页面余额显示 ¥3
□ 选择成人口罩(¥2) → 弹出确认页
□ 确认 → LED1亮起 + 蜂鸣器响 + 页面显示"出货中"
□ 放口罩到取货口 → 红外检测 → LED熄灭 → 页面显示"成功"
□ 页面余额显示 ¥1，库存从10变为9
□ 再投1元 → 余额¥2 → 选N95(¥5) → 提示余额不足
□ 再投3次 → 余额¥5 → 选N95 → 确认 → LED3亮起 → 放口罩 → 完成
□ N95库存从5变4
□ 取消交易测试：投币 → 选择 → 取消 → 余额归零
□ 缺货测试：将某个货道库存手动改为0 → 页面显示灰色"缺货"
□ 查看 /api/logs → 有所有交易记录
```
