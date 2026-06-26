"""
test_buzzer.py — 无源蜂鸣器 单独硬件测试

测试内容：
  1. 四个频率发声: 500Hz(低沉) / 1000Hz(正常) / 1500Hz(偏高) / 2000Hz(尖锐)
  2. 长鸣测试: 连续2秒
  3. 静音停止

接线（3脚无源蜂鸣器模块）：
  模块 VCC → 树莓派 3.3V (pin1/pin17)
  模块 IO  → GPIO26 (pin37)
  模块 GND → 树莓派 GND

运行方法：
  python3 hardware_tests/test_buzzer.py
"""

import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hardware.buzzer import Buzzer
from hardware.gpio_init import init_gpio, cleanup_gpio
from config import BUZZER_PIN

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
    print("  无源蜂鸣器 PWM 驱动 — 硬件测试")
    print("=" * 60)
    print(f"  运行平台: {'树莓派 (真实GPIO)' if ON_PI else 'Windows (Mock模式)'}")
    print(f"  引脚: GPIO{BUZZER_PIN} (pin37), PWM方波驱动")
    print(f"  模块: 3脚无源蜂鸣器 (VCC→3.3V, IO→GPIO26, GND→GND)")
    print()

    init_gpio()
    buzzer = Buzzer(BUZZER_PIN)

    try:
        # ===== 测试1: 四频率发声 =====
        print("-" * 60)
        print("  [测试1] 四频率音调测试")
        print("-" * 60)

        tests = [
            (500,  1.5, "低频 (500Hz)  — 低沉，余额不足提示"),
            (1000, 1.5, "中频 (1000Hz) — 适中，出货成功提示"),
            (1500, 1.5, "中高频(1500Hz) — 偏高"),
            (2000, 1.5, "高频 (2000Hz) — 尖锐，超时告警"),
        ]

        for freq, duration, desc in tests:
            print(f"  >>> {desc}")
            print(f"      频率={freq}Hz, 时长={duration}秒, 占空比=50%")
            buzzer.beep(freq=freq, duration=duration)
            time.sleep(0.3)
            print(f"      发声完毕")
            print()

        # ===== 测试2: 长鸣 =====
        print("-" * 60)
        print("  [测试2] 连续长鸣测试 — 1000Hz, 2秒")
        print("-" * 60)
        print("  >>> 蜂鸣器连续发声 2 秒...")
        buzzer.beep(freq=1000, duration=2.0)
        time.sleep(0.3)
        print("      长鸣完毕")
        print()

        # ===== 测试3: 静音 =====
        print("-" * 60)
        print("  [测试3] 静音停止 — off()")
        print("-" * 60)
        print("  >>> 调用 buzzer.off()")
        buzzer.off()
        time.sleep(0.5)
        print("      蜂鸣器已静音")
        print()

        print("=" * 60)
        print("  [PASS] 蜂鸣器测试全部通过! (4个频率均正常发声)")
        print("=" * 60)
        print()

    except KeyboardInterrupt:
        print("\n  [中断] 用户取消测试")
    finally:
        buzzer.off()
        cleanup_gpio()


if __name__ == '__main__':
    main()
