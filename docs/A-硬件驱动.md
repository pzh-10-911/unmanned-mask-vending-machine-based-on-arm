# Person A — 硬件驱动 + 接线

## 产出文件

```
mask-vending-machine/
├── config.py                     # 引脚号常量 + 价格常量
├── hardware/
│   ├── __init__.py
│   ├── gpio_init.py              # GPIO.setmode/setup
│   ├── led.py                    # RGBLED 三色LED
│   ├── buzzer.py                  # Buzzer 无源蜂鸣器（PWM）
│   ├── ir_sensor.py              # IRSensor 红外检测
│   └── button.py                 # CoinButton 投币按键
```

## 接口规范（提供给 C）

### 接口一览

| 文件 | 类/函数 | 入参 | 返回值 | 说明 |
|------|---------|------|--------|------|
| `gpio_init.py` | `init_gpio()` | 无 | `None` / `raise RuntimeError` | 初始化所有 GPIO 引脚 |
| `gpio_init.py` | `cleanup_gpio()` | 无 | `None` | 清理 GPIO 资源 |
| `led.py` | `RGBLED(r_pin, g_pin, b_pin)` | `r_pin, g_pin, b_pin: int` | 实例 | 三色LED控制 |
| `led.py` | `.set_color(r, g, b)` | `r/g/b: bool` | `None` | 设置RGB颜色 |
| `led.py` | `.set_channel(channel)` | `channel: int` | `None` | 按货道设颜色 |
| `led.py` | `.off()` | 无 | `None` | 全部熄灭 |
| `buzzer.py` | `Buzzer(pin)` | `pin: int` | 实例 | 无源蜂鸣器（PWM驱动） |
| `buzzer.py` | `.beep(freq, duration)` | `freq:int, duration:float` | `None` | 发出指定频率/时长声音 |
| `buzzer.py` | `.off()` | 无 | `None` | 停止发声 |
| `button.py` | `CoinButton(pin, callback)` | `pin, callback` | 实例 | 投币按键检测 |
| `ir_sensor.py` | `IRSensor(pin)` | `pin: int` | 实例 | 红外传感器 |
| `ir_sensor.py` | `.is_blocked()` | 无 | `bool` | True=有口罩遮挡 |
| `button.py` | `.start()` | 无 | `None` | 启用按键监听 |
| `button.py` | `.stop()` | 无 | `None` | 停用按键监听 |

### 详细定义

#### gpio_init.py — 初始化/清理

| 函数 | 说明 |
|------|------|
| `init_gpio()` | 设置 GPIO 为 BCM 模式；RGB-LED三引脚/蜂鸣器引脚→OUTPUT初始LOW；按键/红外→INPUT(PUD_UP)；失败抛 `RuntimeError` |
| `cleanup_gpio()` | 所有输出置 LOW，调用 `GPIO.cleanup()` |

```python
def init_gpio(): ...
def cleanup_gpio(): ...
```

#### led.py — RGB 三色LED

| 方法 | 参数 | 返回值 | 行为 |
|------|------|--------|------|
| `__init__` | `r_pin: int, g_pin: int, b_pin: int` | `RGBLED` | 绑定 R/G/B 三个 GPIO 引脚 |
| `set_color(r, g, b)` | `r/g/b: bool` | `None` | 设置颜色，True=点亮，False=熄灭 |
| `off()` | 无 | `None` | 全部熄灭（等价于 `set_color(0,0,0)`） |
| `set_channel(channel)` | `channel: int` | `None` | 根据货道 ID 设置对应颜色（0=红,1=绿,2=蓝） |

```python
class RGBLED:
    def __init__(self, r_pin: int, g_pin: int, b_pin: int): ...
    def set_color(self, r: bool, g: bool, b: bool) -> None: ...
    def off(self) -> None: ...
    def set_channel(self, channel: int) -> None: ...
```

#### buzzer.py — 无源蜂鸣器

| 方法 | 参数 | 返回值 | 行为 |
|------|------|--------|------|
| `__init__` | `pin: int` | `Buzzer` | 绑定 GPIO 引脚，创建 PWM 对象 |
| `beep(freq, duration)` | `freq:int, duration:float` | `None` | 发出指定频率(Hz)和时长(秒)的声音 |
| `off()` | 无 | `None` | 停止发声 |

```python
class Buzzer:
    def __init__(self, pin: int): ...
    def beep(self, freq: int = 1000, duration: float = 0.2) -> None: ...
    def off(self) -> None: ...
```

#### ir_sensor.py — 红外传感器

| 方法 | 参数 | 返回值 | 行为 |
|------|------|--------|------|
| `__init__` | `pin: int` | `IRSensor` | 绑定 GPIO 引脚（INPUT） |
| `is_blocked()` | 无 | `bool` | 读取GPIO电平，True=遮挡(有口罩)，False=无遮挡 |

```python
class IRSensor:
    def __init__(self, pin: int): ...
    def is_blocked(self) -> bool: ...
```

#### button.py — 投币按键

| 方法 | 参数 | 返回值 | 行为 |
|------|------|--------|------|
| `__init__` | `pin: int, callback: callable` | `CoinButton` | 绑定引脚，注册下降沿中断回调，200ms 防抖 |
| `start()` | 无 | `None` | 启用 GPIO 中断事件检测 |
| `stop()` | 无 | `None` | 移除 GPIO 中断事件检测 |

```python
class CoinButton:
    def __init__(self, pin: int, callback: callable): ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

## 树莓派 GPIO 引脚对照

树莓派 40pin 排针布局（从上方看，SD卡槽朝向自己）：

```
                    SD卡槽
┌─────────────────────────────────────┐
│  (1) 3.3V    ▓   (2) 5V            │
│  (3) GPIO2   ▓   (4) 5V            │
│  (5) GPIO3   ▓   (6) GND           │
│  (7) GPIO4   ▓   (8) GPIO14        │
│  (9) GND     ▓   (10) GPIO15       │
│  (11)GPIO17──▓───(12)GPIO18        │  ← RGB-R(红) | RGB-G(绿)
│  (13)GPIO27──▓───(14)GND           │  ← 投币按键
│  (15)GPIO22──▓───(16)GPIO23────────┤  ← 空闲(备用) | 红外传感器
│  (17)3.3V    ▓   (18)GPIO24        │
│  (19)GPIO10  ▓   (20)GND           │
│  (21)GPIO9   ▓   (22)GPIO25        │
│  (23)GPIO11  ▓   (24)GPIO8         │
│  (25)GND     ▓   (26)GPIO7         │
│  (27)GPIO0   ▓   (28)GPIO1         │
│  (29)GPIO5   ▓   (30)GND           │
│  (31)GPIO6   ▓   (32)GPIO12        │
│  (33)GPIO13  ▓   (34)GND           │
│  (35)GPIO19  ▓   (36)GPIO16        │  ← RGB-B(蓝)
│  (37)GPIO26──▓───(38)GPIO20        │  ← 蜂鸣器
│  (39)GND     ▓   (40)GPIO21        │
└─────────────────────────────────────┘
```

**本项目使用的引脚标注（BCM 编号）：** GPIO17(RGB-R), 18(RGB-G), 19(RGB-B), 23, 26, 27 (GPIO22空闲备用)

## 硬件接线清单

### 完整接线表

| 树莓派引脚 | 连接对象 | 导线颜色建议 | 方向 | 说明 |
|-----------|---------|-------------|------|------|
| GPIO 17 (pin11) | RGB-LED R脚 → 220Ω → GND | 红 | OUT | RGB红通道（货道A出货指示） |
| GPIO 18 (pin12) | RGB-LED G脚 → 220Ω → GND | 绿 | OUT | RGB绿通道（货道B出货指示） |
| GPIO 19 (pin35) | RGB-LED B脚 → 220Ω → GND | 蓝 | OUT | RGB蓝通道（货道C出货指示） |
| GPIO 22 (pin15) | 空闲（备用） | — | — | 原系统状态LED已取消，功能由RGB LED替代 |
| GPIO 26 (pin37) | 蜂鸣器模块 IO 脚 | 灰 | OUT(PWM) | 无源蜂鸣器，PWM驱动 |
| 3.3V (pin1/pin17) | 蜂鸣器模块 VCC | 红 | 电源 | 必须接3.3V供电 |
| GPIO 23 (pin16) | 红外传感器 OUT 脚 | 绿 | IN | 取货口检测 |
| GPIO 27 (pin13) | 投币按键 一脚 | 白 | IN(PUD_UP) | 另一脚接 GND |
| 3.3V (pin1) | 红外传感器 VCC | 红 | 电源 | 注意用3.3V，非5V |
| GND (任一) | 红外GND + 按键GND + RGB-LED公共脚 + 蜂鸣器模块GND | 黑 | 共地 | pin6/9/14/20/25/30/34/39 |

### 逐元件接线步骤

#### 1. RGB-LED — 三色指示灯（替代4个单色LED）

**元器件：** 5mm RGB-LED（共阴极）×1 + 220Ω 电阻 ×3 + 杜邦线

**区分共阴极 vs 共阳极：**
- **共阴极**（推荐/最常见）：公共脚接GND，GPIO输出HIGH点亮对应颜色
- **共阳极：** 公共脚接3.3V，GPIO输出LOW点亮对应颜色（驱动代码中逻辑取反）
- 不确定时查阅LED数据手册或用万用表测量：公共脚与GND之间电阻最小的为共阴极

**步骤：**
1. RGB-LED有4个引脚：R(红)、G(绿)、B(蓝)、GND(公共)
2. 每路颜色分别串220Ω电阻后再接GPIO（三路各一个电阻，不可共用）
3. 以共阴极为例：

```
树莓派 GPIO17 ──┬── 220Ω ──┬── RGB-LED R 脚
树莓派 GPIO18 ──┬── 220Ω ──┬── RGB-LED G 脚
树莓派 GPIO19 ──┬── 220Ω ──┬── RGB-LED B 脚
树莓派 GND  ────┴──────────── RGB-LED 公共脚(GND)
```

**颜色-状态映射：**

| 状态 | R | G | B | 颜色 | 说明 |
|------|---|---|---|------|------|
| 待机(IDLE) | 0 | 1 | 0 | 🟢 绿 | 常亮，系统运行正常 |
| 已选(SELECTED) | 1 | 1 | 0 | 🟡 黄 | 等待确认 |
| 货道A出货中 | 1 | 0 | 0 | 🔴 红 | 成人口罩 |
| 货道B出货中 | 0 | 1 | 0 | 🟢 绿 | 儿童口罩 |
| 货道C出货中 | 0 | 0 | 1 | 🔵 蓝 | N95口罩 |
| 缺货/错误 | 1 | 0 | 1 | 🟣 紫 | 闪烁提示 |

**测试：** 分别使GPIO17/18/19输出HIGH，观察对应颜色点亮

#### 2. 蜂鸣器（3脚无源蜂鸣器模块）

**元器件：** 3脚无源蜂鸣器模块（VCC / IO / GND）

**引脚定义：**

```
蜂鸣器模块          树莓派
┌─────────┐
│ VCC  ───── 3.3V (pin1 或 pin17)    ← 供电
│ IO   ───── GPIO26 (pin37)          ← PWM 信号
│ GND  ───── GND (任意)               ← 共地
└─────────┘
```

**说明：**
- 无源蜂鸣器需要 PWM 方波驱动，通过 `Buzzer.beep(freq, duration)` 调节频率
- 不同频率发出不同音调：500Hz(低沉) / 1000Hz(默认) / 2000Hz(尖锐)
- **VCC 必须接电源**（3.3V 即可），否则不响
- 模块自带驱动电路，无需串联电阻

#### 3. 红外传感器（取货口检测）

**元器件：** 红外避障传感器（通常为3线制，如 HC-SR501 或类似模块）

**引脚定义：**

```
传感器模块         树莓派
┌─────────┐
│ VCC  ───── 3.3V (pin1)    ← 红/棕线
│ GND  ───── GND (任意)       ← 黑线
│ OUT  ───── GPIO23 (pin16)  ← 绿/黄线
└─────────┘
```

**说明：**
- 传感器模块通常有电位器可调节检测距离（建议调至 5-10cm）
- 有/无物体遮挡时 OUT 引脚电平会变化
- 如果传感器是**常开型**（遮挡时输出 HIGH）：`is_blocked()` 返回 `gpio_value == HIGH`
- 如果传感器是**常闭型**（遮挡时输出 LOW）：`is_blocked()` 返回 `gpio_value == LOW`
- **代码中做适配：** 实际测试后若行为相反，在 `ir_sensor.py` 的 `is_blocked()` 内部取反即可
- 安装位置：**固定在取货口上方**，红外发射头和接收头指向取货口中心

#### 4. 投币按键

**元器件：** 轻触按键（4脚或2脚）

**4脚按键辨别方向：** 同一排的两脚在内部是连通的，按下时两排连通

```
树莓派 GPIO27 (pin13) ────┬─── 按键一脚
树莓派 GND (pin14) ────────┴─── 按键另一脚

（无需外接电阻，内部上拉已启用）
```

**接线说明：**
- 按键任意一脚接 GPIO27
- 按键另一脚接 GND
- 代码设置 `GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)`
- 默认 GPIO27 为 HIGH，按下时变为 LOW（下降沿触发）

```
GPIO27 电平: ━━━━━━━━┓        ┏━━━━━━━━
                      ┃ 按下   ┃
                      ┗━━━━━━━━┛
                      ↑ 下降沿触发中断
```

### 面包板布局参考

```
           面包板（上半部分为电源/地排）
   ┌────────────────────────────────────────┐
   │ (+) ── 3.3V  ──────────────────────   │  ← 红排
   │ (-) ── GND    ──────────────────────   │  ← 黑排
   └────────────────────────────────────────┘
   ┌────────────────────────────────────────┐
   │ 17 ─┬── 220Ω ─┬── RGB-R 脚              │  ← RGB-LED红
   │ 18 ─┬── 220Ω ─┬── RGB-G 脚              │  ← RGB-LED绿
   │ 19 ─┬── 220Ω ─┬── RGB-B 脚              │  ← RGB-LED蓝
   │     │    GND  ─┴── RGB-公共脚            │  ← 共阴极
   │ 26 ←── 蜂鸣器 IO 脚                     │
   │ 3.3V ── 蜂鸣器 VCC                       │
   │ GND  ←── 蜂鸣器 GND                     │
   │ 23 ←── 红外 OUT                           │
   │ 3.3V ── 红外 VCC                          │
   │ GND  ←── 红外 GND                        │
   │ 27 ←── 按键 → 按键另一脚 → GND            │
   └────────────────────────────────────────┘
```

### 接线要点

1. **RGB-LED 每路必须单独串电阻**：R/G/B 各串一个 220Ω，不可只在公共脚串一个
2. **区分共阴极/共阳极**：共阴极公共脚接 GND；共阳极公共脚接 3.3V（代码逻辑需取反）
3. **红外传感器用 3.3V 而非 5V**：树莓派 GPIO 是 3.3V 逻辑，接 5V 会烧引脚
4. **共地**：所有元件的 GND 都要连在一起接到树莓派的 GND 引脚
5. **上电前检查**：VCC/GND 是否接反？RGB-LED 公共脚是否正确？有无短路？
6. **杜邦线颜色约定**：自行统一颜色方便排查，建议红色=电源，黑色=GND，其他颜色=信号

### 上电自检流程

硬件接好后，不跑代码，先做简单测试：

1. **电源检查**：树莓派上电后各元件有无冒烟、发热？（正常应不发热）
2. **RGB-LED 测试**：分别将 GPIO17/18/19 用杜邦线短接到 3.3V（注意安全），观察 R/G/B 是否依次点亮
3. **按键测试**：万用表测 GPIO27 到 GND 间电阻，按下时接近 0Ω，松开时无穷大
4. **红外传感器**：用手遮挡时，传感器上指示灯变化（大部分模块自带指示灯）

---

## 结构制作

- 纸板裁切3个格子，每个格子上方写上对应口罩品类和价格
- 每个格子旁固定一个 LED（用热熔胶或胶带）
- 投币按钮固定于机身正面下方
- 红外传感器固定于取货口处
- 蜂鸣器安装于机箱背面

## 开发顺序

1. 先在树莓派上接线（面包板）
2. 写 gpio_init.py（设置引脚模式、测试每个引脚输出正常）
3. 写 led.py（测试 RGB 三路亮灭及 set_channel 颜色切换）
4. 写 buzzer.py（测试 PWM 不同频率发声）
5. 写 ir_sensor.py（用手遮挡/移开测试读取值变化）
6. 写 button.py（按下按键测试回调正常）
7. 将 5 个文件放到 hardware/ 目录

## Mock 支持（Windows 开发用）

```python
# hardware/gpio_init.py
try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from unittest.mock import MagicMock
    GPIO = MagicMock()
    print("[MOCK] Using mock GPIO for Windows development")
```

## 依赖关系

- 无依赖，可独立开发
- 输出给 Person C 集成
