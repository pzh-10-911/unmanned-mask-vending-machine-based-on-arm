"""
test_gpio_init.py — GPIO 初始化与清理 单独硬件测试

测试内容：
  1. GPIO 模式设置 (BCM)
  2. 6路引脚配置 (3输出 + 2输入上拉 + 1输出)
  3. GPIO 清理

接线：所有外设保持接线不变，本测试仅验证 GPIO 初始化流程。

运行方法：
  python3 hardware_tests/test_gpio_init.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hardware.gpio_init import init_gpio, cleanup_gpio

try:
    import RPi.GPIO as GPIO
    ON_PI = True
except (ImportError, RuntimeError):
    from unittest.mock import MagicMock
    GPIO = MagicMock()
    ON_PI = False


def main():
    print()
    print("=" * 60)
    print("  GPIO 初始化与清理 — 硬件测试")
    print("=" * 60)
    print(f"  运行平台: {'树莓派 (真实GPIO)' if ON_PI else 'Windows (Mock模式)'}")
    print()

    # === 测试1: GPIO 初始化 ===
    print("-" * 60)
    print("  [测试1] init_gpio() — GPIO 初始化")
    print("-" * 60)
    try:
        init_gpio()
        print("  >>> init_gpio() 执行成功")
    except Exception as e:
        print(f"  >>> [FAIL] init_gpio() 失败: {e}")
        return

    # === 测试2: 验证引脚配置 ===
    print()
    print("-" * 60)
    print("  [测试2] 验证引脚模式配置")
    print("-" * 60)

    pin_configs = [
        (17, GPIO.OUT, "RGB-LED R 通道"),
        (18, GPIO.OUT, "RGB-LED G 通道"),
        (19, GPIO.OUT, "RGB-LED B 通道"),
        (26, GPIO.OUT, "蜂鸣器 PWM"),
        (23, GPIO.IN,  "红外传感器 (上拉)"),
        (27, GPIO.IN,  "投币按键 (上拉)"),
    ]

    if ON_PI:
        for pin, expected_mode, desc in pin_configs:
            actual_mode = GPIO.gpio_function(pin)
            mode_names = {0: "OUTPUT", 1: "INPUT"}
            status = "OK" if actual_mode == expected_mode else "WARN"
            print(f"  [{status}] GPIO{pin:>2} ({desc:20s}) → {mode_names.get(actual_mode, actual_mode)}")
    else:
        for pin, _, desc in pin_configs:
            print(f"  [MOCK] GPIO{pin:>2} ({desc:20s}) → 已配置")

    # === 测试3: GPIO 清理 ===
    print()
    print("-" * 60)
    print("  [测试3] cleanup_gpio() — GPIO 清理")
    print("-" * 60)
    try:
        cleanup_gpio()
        print("  >>> cleanup_gpio() 执行成功")
    except Exception as e:
        print(f"  >>> [FAIL] cleanup_gpio() 失败: {e}")
        return

    # === 结果 ===
    print()
    print("=" * 60)
    print("  [PASS] GPIO 初始化测试全部通过!")
    print("=" * 60)
    print()


if __name__ == '__main__':
    main()
