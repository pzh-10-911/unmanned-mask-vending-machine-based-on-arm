# Person A — 硬件驱动测试

## 测试文件

```
mask-vending-machine/
├── hardware_tests/                 # 分项硬件测试（单独运行）
│   ├── test_rgb_led.py             # 三色LED测试
│   ├── test_buzzer.py              # 无源蜂鸣器测试
│   └── test_button.py              # 投币按键测试
└── tests/
    └── test_hardware.py            # 综合测试（所有硬件）
```

## 测试方法

在**树莓派**上运行：

```bash
cd ~/911

# 方式1：单项测试
python3 hardware_tests/test_rgb_led.py
python3 hardware_tests/test_buzzer.py
python3 hardware_tests/test_button.py

# 方式2：综合测试（注意需手动按键）
python3 -m tests.test_hardware
```

---

## 测试 1 — RGB-LED

运行 `python3 hardware_tests/test_rgb_led.py`

### 预期输出

```
===========================================
  RGB-LED Hardware Test
===========================================
  R=GPIO17, G=GPIO18, B=GPIO19
  Each color displays for 1.5 seconds

--- Single Colors ---
  1. Red   (R)
  2. Green (G)
  3. Blue  (B)

--- Mixed Colors ---
  4. Yellow (R+G)
  5. Purple (R+B)
  6. Cyan   (G+B)
  7. White  (R+G+B)

--- OFF ---
  8. All OFF

--- Channel Colors ---
  9.0 Channel 0 - Red   (Adult Mask)
  9.1 Channel 1 - Green (Child Mask)
  9.2 Channel 2 - Blue  (N95 Mask)
  All OFF

===========================================
  [PASS] RGB-LED test completed!
===========================================
```

### 测试表单

| # | 测试项 | 操作 | 预期 | 结果 | 备注 |
|---|-------|------|------|------|------|
| 1 | 单色显示 | 运行 test_rgb_led.py | 红→绿→蓝各亮1.5秒 | □ | |
| 2 | 混色显示 | 同上 | 黄→紫→青→白各亮1.5秒 | □ | |
| 3 | 熄灭 | 同上 | 灯全灭 | □ | |
| 4 | 货道颜色 | 同上 | ch0红→ch1绿→ch2蓝各亮1.5秒 | □ | |

---

## 测试 2 — 蜂鸣器

运行 `python3 hardware_tests/test_buzzer.py`

### 预期输出

```
===========================================
  Passive Buzzer Hardware Test
===========================================
  Buzzer: GPIO26 (PWM)

  1. Default beep (1000Hz, 0.2s)
  2. Low tone (500Hz, 0.5s)
  3. Mid tone (1500Hz, 0.5s)
  4. High tone (2000Hz, 0.5s)
  5. Continuous tone (1000Hz, 2s)
  6. Silent (off)
-------------------------------------------
  [PASS] Buzzer test completed!
===========================================
```

### 测试表单

| # | 测试项 | 操作 | 预期 | 结果 | 备注 |
|---|-------|------|------|------|------|
| 1 | 默认蜂鸣 | 运行 test_buzzer.py | 1000Hz 响0.2秒 | □ | |
| 2 | 低频 | 同上 | 500Hz 低沉声 | □ | |
| 3 | 中频 | 同上 | 1500Hz 中等音调 | □ | |
| 4 | 高频 | 同上 | 2000Hz 尖锐声 | □ | |
| 5 | 长鸣 | 同上 | 1000Hz 持续2秒 | □ | |
| 6 | 静音 | 同上 | 停止后无声 | □ | |

---

## 测试 3 — 投币按键

运行 `python3 hardware_tests/test_button.py`

### 预期输出

```
===========================================
  Coin Button Hardware Test
===========================================
  Button: GPIO27 (with pull-up)
  Please press the button 3 times within 10 seconds
-------------------------------------------
[BTN] GPIO27 listening started
  [10s left] Press count: 0
  [9s left] Press count: 0
  Coin! (press #1)
  Coin! (press #2)
  [7s left] Press count: 2
  Coin! (press #3)
[BTN] GPIO27 listening stopped
-------------------------------------------
  [PASS] Button OK (detected 3 presses)
===========================================
  [PASS] Coin button test completed!
===========================================
```

### 测试表单

| # | 测试项 | 操作 | 预期 | 结果 | 备注 |
|---|-------|------|------|------|------|
| 1 | 按键检测 | 运行 test_button.py，10秒内按3次 | 显示"Coin! (press #1/2/3)" | □ | |
| 2 | 未按键 | 运行 test_button.py，不按键 | 10秒后显示0次，WARN | □ | 仅在验证防抖时做 |

---

## 测试 4 — 红外传感器

手动测试（未单独测试文件，在综合测试或直接读引脚验证）：

```bash
cd ~/911 && python3 -m tests.test_hardware
```

或用 Python 直接读引脚：

```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)
print(GPIO.input(23))  # 遮挡=1, 无遮挡=0
GPIO.cleanup()
```

### 测试表单

| # | 测试项 | 操作 | 预期 | 结果 | 备注 |
|---|-------|------|------|------|------|
| 1 | 无遮挡 | 移开遮挡物 | GPIO23 读取 0 | □ | |
| 2 | 有遮挡 | 用手挡住传感器 | GPIO23 读取 1 | □ | |

---

## 综合测试

运行 `python3 -m tests.test_hardware`

### 预期输出

```
[GPIO] init_gpio() called
[TEST] RGB-LED ...
  Red (R) / Green (G) / Blue (B) / Yellow / Purple / Cyan / White / All OFF
  [PASS] RGB-LED all colors OK
[TEST] Buzzer ...
  [PASS] Buzzer OK
[TEST] IR Sensor ...
  [clear] / [BLOCKED] / [clear] / ...
  [PASS] IR Sensor OK
[TEST] Coin Button ...
  Press the button 3 times within 10s
  Coin! (total: 1/2/3)
  [PASS] Button OK
[*] All hardware tests passed!
```

### 测试表单

| # | 测试项 | 操作 | 预期 | 结果 | 备注 |
|---|-------|------|------|------|------|
| 1 | RGB-LED 颜色 | 运行综合测试 | 七色全部正常显示 | □ | |
| 2 | 蜂鸣器 | 同上 | 1000Hz 响0.5秒 | □ | |
| 3 | 红外传感器 | 同上后遮挡/移开 | clear/BLOCKED 交替 | □ | |
| 4 | 投币按键 | 同上后按键3次 | 显示"收到1元"×3 | □ | |
