# 项目分工

## 项目信息
- 项目名：基于ARM(树莓派)的无人口罩贩卖机
- 周期：2天
- 人数：4人
- 联调时间：Day 2 全天

## 任务总览

| 角色 | 人名 | 产出 | 代码量 | 依赖 | 独立 |
|------|------|------|--------|------|------|
| A | | hardware/ 驱动层 + 硬件接线 | ~60 行 | 无 | ✅ |
| B | | logic/ 状态机 + 库存 | ~100 行 | 无 | ✅ |
| C | | app.py Flask 入口 + API | ~80 行 | A硬件接口 + B状态机 | 可用mock占位 |
| D | | static/ 前端页面 | ~150 行 | C的API接口 | 接口已定，mock开发 |

---

## Person A — 硬件驱动

### 产出文件
```
mask-vending-machine/
├── config.py                     # 引脚号常量 + 价格常量
├── hardware/
│   ├── __init__.py
│   ├── gpio_init.py              # GPIO.setmode/setup
│   ├── led.py                    # LED 出货指示
│   ├── ir_sensor.py              # IRSensor 红外检测
│   └── button.py                 # CoinButton 投币按键
```

### 接口规范（提供给 C）

```python
# led.py
class RGBLED:
    def __init__(self, r_pin: int, g_pin: int, b_pin: int)
    def set_channel(self, channel: int) -> None  # 按货道设颜色
    def off(self) -> None          # 全部熄灭

# ir_sensor.py
class IRSensor:
    def __init__(self, pin: int)
    def is_blocked(self) -> bool   # True=口罩已到出货口

# button.py
class CoinButton:
    def __init__(self, pin: int, callback: callable)  # 按下时回调
```

### 硬件接线清单

| 树莓派引脚 | 连接设备 |
|-----------|---------|
| GPIO 17 | RGB-LED R脚 + 220Ω → GND — 红色通道（货道A 成人口罩） |
| GPIO 18 | RGB-LED G脚 + 220Ω → GND — 绿色通道（货道B 儿童口罩） |
| GPIO 19 | RGB-LED B脚 + 220Ω → GND — 蓝色通道（货道C N95） |
| GPIO 23 | 红外传感器 (Signal) — 取货口检测 |
| GPIO 27 | 投币按键 (一端接GPIO，一端接GND) |
| GPIO 22 | 空闲（备用） |
| GPIO 26 | 蜂鸣器模块 IO |
| 3.3V | 红外传感器 VCC |
| GND | 红外GND + 按键GND + RGB-LED公共脚 + 蜂鸣器GND |

**接线要点：** LED 长脚(Anode)接 GPIO，短脚接电阻再接 GND。GPIO 输出 HIGH 时灯亮。

### 结构制作
- 纸板裁切3个格子，每个格子上方写上对应口罩品类和价格
- 每个格子旁固定一个 LED（用热熔胶或胶带）
- 投币按钮固定于机身正面下方
- 红外传感器固定于取货口处
- 蜂鸣器安装于机箱背面

---

## Person B — 状态机 + 库存

### 产出文件
```
mask-vending-machine/
├── config.py                     # (与A协同，引脚号+价格常量)
├── logic/
│   ├── __init__.py
│   ├── state_machine.py          # 状态机核心逻辑
│   └── inventory.py              # 库存管理
```

### 状态机定义

```python
class StateMachine:
    # 状态常量
    IDLE = 0      # 待机
    COIN_IN = 1   # 投币中
    SELECT = 2    # 已选择品类
    CONFIRM = 3   # 等待确认
    DISPENSE = 4  # 出货中

    def add_coin(self) -> bool        # 余额+1，返回是否成功
    def select(self, channel) -> bool # 选择货道，检查余额是否足够
    def confirm(self) -> dict         # 执行购买，返回 {success, msg}
    def cancel(self) -> None          # 取消交易，余额归零
    def get_state(self) -> dict       # 返回当前状态+余额+库存
```

### 库存管理

```python
class Inventory:
    def load(self) -> None            # 从 data/inventory.json 读取
    def save(self) -> None            # 持久化到文件
    def deduct(self, channel) -> bool # 扣减库存，False=库存不足
    def get_status(self) -> list      # 返回所有货道库存信息
```

### JSON 格式

```json
{
    "channels": [
        {"id": 0, "name": "成人口罩", "price": 2.0, "stock": 10},
        {"id": 1, "name": "儿童口罩", "price": 2.0, "stock": 10},
        {"id": 2, "name": "N95口罩", "price": 5.0, "stock": 5}
    ],
    "transactions": [],
    "balance": 0
}
```

---

## Person C — Flask 入口 + API

### 产出文件
```
mask-vending-machine/
├── app.py                         # Flask 应用 + 路由
├── requirements.txt               # 依赖清单
└── run.sh                         # 启动脚本（可选）
```

### 启动入口

```python
# app.py
app = Flask(__name__, static_folder='static')
sm = StateMachine()        # from logic.state_machine
inv = Inventory()          # from logic.inventory
rgb = RGBLED(17, 18, 19)  # from hardware.led
ir = IRSensor(23)          # from hardware.ir_sensor
btn = CoinButton(27, cb)   # from hardware.button
```

### 7个 API 路由 (响应 JSON)

```python
@app.route('/api/status')      # GET → 返回 {state, balance, channels:[{id,name,price,stock,available}]}
@app.route('/api/coin')        # POST → sm.add_coin() → 返回 {balance}
@app.route('/api/select/<id>') # POST → sm.select(id) → 返回 {success, channel}
@app.route('/api/confirm')     # POST → sm.confirm() → 调用舵机+红外 → 返回 {success, msg}
@app.route('/api/cancel')      # POST → sm.cancel() → 返回 {balance}
@app.route('/api/reset')       # POST → 恢复初始库存 → 返回 {success}
@app.route('/api/logs')        # GET → 返回 [{time, item, amount, status}]
```

### 调度逻辑（confirm 中的核心业务流程）

```
confirm():
  1. 检查库存 → 不足则返回失败
  2. 对应货道颜色（RGB-LED）亮起 + 蜂鸣器响 200ms
  3. 等待用户取货（红外检测，最长30秒）
  4. 红外检测到口罩被取走 → 扣库存 → 记录交易 → rgb.off() → 返回 success=True
  5. 超时未取 → 取消交易 → rgb.off() → 返回 success=False
```

---

## Person D — 前端页面

### 产出文件
```
mask-vending-machine/
├── static/
│   ├── index.html    # 单页应用HTML
│   ├── style.css     # 移动端响应式样式
│   └── script.js     # 前端交互逻辑
```

### 页面结构

**index.html** — 3个页面容器，通过 JS 控制显示/隐藏：
```html
<div id="page-main">   <!-- 主界面：余额+商品卡片+投币/退款按钮 --></div>
<div id="page-confirm"><!-- 确认弹窗：遮罩+商品信息+确认/取消 --></div>
<div id="page-result"> <!-- 出货结果：动画+成功/失败提示 --></div>
```

### script.js 接口约定

```javascript
// 调用的 API 端点（与 C 约定）
const API = {
    status:  '/api/status',    // GET
    coin:    '/api/coin',      // POST
    select:  '/api/select/',   // POST + id
    confirm: '/api/confirm',   // POST
    cancel:  '/api/cancel',    // POST
    logs:    '/api/logs',      // GET
};

// 核心函数
function fetchStatus()     // 定期轮询，更新UI
function onCoinClick()     // 调用 /api/coin，更新余额
function onBuy(id)         // 调用 /api/select，弹出确认页
function onConfirm()       // 调用 /api/confirm，显示出货动画
function onCancel()        // 调用 /api/cancel，退回主界面
```

### 样式要求
- 移动端自适应 (max-width: 480px)
- 卡片布局，显示口罩图标(emoji) + 名称 + 价格 + 库存
- 余额不足/库存不足时按钮灰色不可点
- 出货进度条动画（CSS transition）
- 暗色主题基调

---

## Day 2 联调计划

### 上午 — 分步联调

| 时间段 | 参与 | 内容 |
|--------|------|------|
| 9:00-10:00 | A+B | 按键触发 → 状态机变化 → LED亮起 → 红外检测 |
| 10:00-11:00 | C+D | 前端页面调Flask真实API，全流程数据通 |
| 11:00-12:00 | A+B+C | 硬件+后端集成 (按键→API→LED→红外) |

### 下午 — 全系统合体

| 时间段 | 内容 |
|--------|------|
| 13:00-14:30 | 四人：按键投币→手机页面更新→选品→出货→红外检测→页面反馈 |
| 14:30-15:30 | 修bug，反复跑完整流程 |
| 15:30-16:00 | 拍演示视频/准备答辩 |

### 关键检查点

- [ ] 按键按一下，余额+1，页面更新
- [ ] 余额不足时"购买"按钮灰色不可点
- [ ] 选择品类后弹出确认弹窗
- [ ] 确认后对应货道颜色亮起，蜂鸣器响
- [ ] 口罩放入取货口，红外检测到，页面显示成功
- [ ] 库存扣减，页面实时更新
- [ ] 缺货时按钮置灰，API 拒绝购买
- [ ] 取消交易后余额归零
- [ ] 联调计划中的时间线调整
