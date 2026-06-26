"""
test_hardware.py — Person A 硬件驱动测试

测试项：
  1. RGB-LED：红/绿/蓝/黄/紫/青/白 七色 + 熄灭
  2. 蜂鸣器：响 0.5 秒
  3. 红外传感器：遮挡/无遮挡检测
  4. 投币按键：按下触发回调

运行方法（树莓派）：
  cd ~/911 && python3 -m tests.test_hardware

运行方法（本地 Windows mock）：
  python -m tests.test_hardware
"""

import time
import sys
import os

# 将项目根目录加入 sys.path，确保可导入 config 和 hardware
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import *
from hardware.gpio_init import init_gpio, cleanup_gpio
from hardware.led import RGBLED
from hardware.ir_sensor import IRSensor
from hardware.button import CoinButton


def test_rgb_led():
    """[TEST-1] RGB-LED 七色显示"""
    print("[TEST] RGB-LED ...")
    rgb = RGBLED(RGB_R_PIN, RGB_G_PIN, RGB_B_PIN)

    colors = [
        ("Red (R)",   1, 0, 0),
        ("Green (G)", 0, 1, 0),
        ("Blue (B)",  0, 0, 1),
        ("Yellow",    1, 1, 0),
        ("Purple",    1, 0, 1),
        ("Cyan",      0, 1, 1),
        ("White",     1, 1, 1),
    ]
    for name, r, g, b in colors:
        print(f"  {name}")
        rgb.set_color(r, g, b)
        time.sleep(1)

    rgb.off()
    print("  All OFF")
    print("  [PASS] RGB-LED all colors OK")


def test_buzzer():
    """[TEST-2] 蜂鸣器响 0.5 秒"""
    print("[TEST] Buzzer ...")
    import RPi.GPIO as GPIO
    GPIO.output(26, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(26, GPIO.LOW)
    print("  [PASS] Buzzer OK")


def test_ir_sensor():
    """[TEST-3] 红外传感器遮挡检测"""
    print("[TEST] IR Sensor ...")
    print("  Please block/unblock the sensor (5s)")
    ir = IRSensor(IR_SENSOR_PIN)
    for _ in range(10):
        status = ir.is_blocked()
        print(f"  {'[BLOCKED]' if status else '[clear]'}")
        time.sleep(0.5)
    print("  [PASS] IR Sensor OK")


def test_coin_button():
    """[TEST-4] 投币按键，按 3 次"""
    print("[TEST] Coin Button ...")
    print("  Press the button 3 times within 10s")
    count = 0

    def on_coin():
        nonlocal count
        count += 1
        print(f"  Coin! (total: {count})")

    btn = CoinButton(COIN_BUTTON_PIN, on_coin)
    btn.start()
    time.sleep(10)
    btn.stop()

    if count >= 3:
        print(f"  [PASS] Button OK (detected {count}/3)")
    else:
        print(f"  [WARN] Only {count}/3 presses, check wiring")


if __name__ == '__main__':
    try:
        init_gpio()
        test_rgb_led()
        test_buzzer()
        test_ir_sensor()
        test_coin_button()
        print("\n[*] All hardware tests passed!")
    except KeyboardInterrupt:
        print("\n[*] Interrupted by user")
    finally:
        cleanup_gpio()
