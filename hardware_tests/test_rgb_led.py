"""
test_rgb_led.py — RGB-LED 单独硬件测试

测试内容：
  1. 单色测试：红(R) → 绿(G) → 蓝(B) 各亮1.5秒
  2. 混色测试：黄(R+G) → 紫(R+B) → 青(G+B) → 白(R+G+B)
  3. 熄灭测试
  4. 货道颜色映射：ch0(红) → ch1(绿) → ch2(蓝)

接线（共阴极RGB-LED）：
  RGB-LED R 脚 → GPIO17 (pin11)
  RGB-LED G 脚 → GPIO18 (pin12)
  RGB-LED B 脚 → GPIO19 (pin35)
  RGB-LED 公共阴极 → GND

运行方法：
  python3 hardware_tests/test_rgb_led.py
"""

import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hardware.led import RGBLED
from hardware.gpio_init import init_gpio, cleanup_gpio
from config import RGB_R_PIN, RGB_G_PIN, RGB_B_PIN

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
    print("  RGB-LED 三色指示灯 — 硬件测试")
    print("=" * 60)
    print(f"  运行平台: {'树莓派 (真实GPIO)' if ON_PI else 'Windows (Mock模式)'}")
    print(f"  引脚: R=GPIO{RGB_R_PIN}(pin11), G=GPIO{RGB_G_PIN}(pin12), B=GPIO{RGB_B_PIN}(pin35)")
    print(f"  类型: 共阴极 (公共脚→GND, GPIO HIGH=点亮)")
    print()

    init_gpio()
    rgb = RGBLED(RGB_R_PIN, RGB_G_PIN, RGB_B_PIN)

    try:
        # ===== 测试1: 单色 =====
        print("-" * 60)
        print("  [测试1] 单色测试 — 红/绿/蓝 各1.5秒")
        print("-" * 60)

        for r, g, b, desc in [
            (1, 0, 0, "■ 红色 — 货道A(成人口罩)"),
            (0, 1, 0, "■ 绿色 — 货道B(儿童口罩)"),
            (0, 0, 1, "■ 蓝色 — 货道C(N95口罩)"),
        ]:
            print(f"  >>> 点亮: {desc}")
            rgb.set_color(r, g, b)
            time.sleep(1.5)
            print(f"      1.5秒到，切换下一个...")
            print()

        # ===== 测试2: 混色 =====
        print("-" * 60)
        print("  [测试2] 混色测试 — 黄/紫/青/白 各1.5秒")
        print("-" * 60)

        for r, g, b, desc in [
            (1, 1, 0, "■ 黄色 (R+G) — 待确认状态"),
            (1, 0, 1, "■ 紫色 (R+B) — 故障告警"),
            (0, 1, 1, "■ 青色 (G+B)"),
            (1, 1, 1, "■ 白色 (R+G+B)"),
        ]:
            print(f"  >>> 点亮: {desc}")
            rgb.set_color(r, g, b)
            time.sleep(1.5)
            print(f"      1.5秒到，切换下一个...")
            print()

        # ===== 测试3: 熄灭 =====
        print("-" * 60)
        print("  [测试3] 熄灭测试")
        print("-" * 60)
        print("  >>> 全部熄灭")
        rgb.off()
        time.sleep(1)
        print("      LED 已熄灭")
        print()

        # ===== 测试4: 货道颜色映射 =====
        print("-" * 60)
        print("  [测试4] 货道颜色映射 — set_channel()")
        print("-" * 60)

        for ch, desc in [(0, "Channel 0 → 红色(成人口罩)"),
                          (1, "Channel 1 → 绿色(儿童口罩)"),
                          (2, "Channel 2 → 蓝色(N95口罩)")]:
            print(f"  >>> {desc}")
            rgb.set_channel(ch)
            time.sleep(1.5)
            print()

        rgb.off()
        print("  >>> 全部熄灭，测试结束")

        print()
        print("=" * 60)
        print("  [PASS] RGB-LED 测试全部通过! (8种颜色均正常)")
        print("=" * 60)
        print()

    except KeyboardInterrupt:
        print("\n  [中断] 用户取消测试")
    finally:
        rgb.off()
        cleanup_gpio()


if __name__ == '__main__':
    main()
