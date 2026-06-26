"""
test_button.py — 投币按键中断检测 单独硬件测试

测试内容：
  1. 按键按下中断触发检测
  2. 200ms防抖验证
  3. 10秒内按5次即通过

接线（轻触按键）：
  按键一脚 → GPIO27 (pin13)
  按键另一脚 → GND (pin14)
  （使用 GPIO 内部上拉电阻 PUD_UP，无需外接电阻）

运行方法：
  python3 hardware_tests/test_button.py
"""

import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hardware.button import CoinButton
from hardware.gpio_init import init_gpio, cleanup_gpio
from config import COIN_BUTTON_PIN

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
    print("  投币按键中断检测 — 硬件测试")
    print("=" * 60)
    print(f"  运行平台: {'树莓派 (真实GPIO)' if ON_PI else 'Windows (Mock模式)'}")
    print(f"  引脚: GPIO{COIN_BUTTON_PIN} (pin13), INPUT + 内部上拉")
    print(f"  触发方式: 下降沿中断 (FALLING), 防抖200ms")
    print()
    print("  测试说明:")
    print("    请在 15 秒内按按键 5 次")
    print("    每次按下时终端会打印投币记录")
    print("    快速连按验证防抖: 不应出现重复计数")
    print("    长按不放验证边沿触发: 只应计数1次")
    print()

    count = [0]  # 用list包装以便在闭包中修改

    def on_coin():
        count[0] += 1
        ts = time.strftime("%H:%M:%S")
        print(f"  💰 [{ts}] 投币!  计数: {count[0]}/5")

    print("-" * 60)
    print("  [测试] 按键中断检测 — 15秒测试窗口")
    print("-" * 60)

    btn = CoinButton(COIN_BUTTON_PIN, on_coin)
    btn.start()
    print(f"  >>> 中断监听已启动 (GPIO{COIN_BUTTON_PIN}, 下降沿, 200ms防抖)")
    print(f"  >>> 请开始按按键...")
    print()

    try:
        for remaining in range(15, 0, -1):
            if count[0] >= 5:
                print(f"  >>> 已达到5次，提前结束!")
                break
            bar = "█" * (15 - remaining) + "░" * (remaining - 1)
            print(f"  [{remaining:>2}s剩余] {bar}  已按下: {count[0]}/5")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  [中断] 用户取消测试")

    btn.stop()
    print(f"  >>> 中断监听已停止")

    print()
    print("-" * 60)
    if count[0] >= 5:
        print(f"  [PASS] 按键测试通过! (检测到 {count[0]} 次按下)")
    elif count[0] > 0:
        print(f"  [WARN] 仅检测到 {count[0]}/5 次按下")
        print(f"  请检查: 按键是否接在 GPIO27↔GND 不同排")
    else:
        print(f"  [FAIL] 未检测到任何按键!")
        print(f"  请检查: 1)按键是否接在GPIO27(pin13)和GND(pin14)")
        print(f"         2)两脚是否接在不同排")
        print(f"         3)万用表通断档验证按键是否正常")
    print("-" * 60)

    print()
    print("=" * 60)
    print(f"  按键测试结束 (共按下 {count[0]} 次)")
    print("=" * 60)
    print()


def main_wrapper():
    init_gpio()
    try:
        main()
    finally:
        cleanup_gpio()


if __name__ == '__main__':
    main_wrapper()
