"""
test_ir_sensor.py — 红外避障传感器 单独硬件测试

测试内容：
  1. 实时读取传感器状态，终端每秒打印一次
  2. 测试遮挡/无遮挡切换响应
  3. 持续30秒，期间用手或口罩遮挡传感器观察输出

接线（3线制红外避障传感器）：
  传感器 VCC → 树莓派 3.3V (pin1/pin17)  【必须3.3V，不可5V！】
  传感器 GND → 树莓派 GND
  传感器 OUT → GPIO23 (pin16)

运行方法：
  python3 hardware_tests/test_ir_sensor.py
"""

import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hardware.ir_sensor import IRSensor
from hardware.gpio_init import init_gpio, cleanup_gpio
from config import IR_SENSOR_PIN

# ===== 传感器适配 =====
# 如果传感器灯亮了但 is_blocked() 返回 False → True（反转）
# 如果传感器灯亮了且 is_blocked() 返回 True  → False（不反转）
_IR_SENSOR = None

def is_blocked():
    """包装 is_blocked()，适配常开/常闭传感器。修改下面一行即可切换。"""
    return not _IR_SENSOR.is_blocked()  # 常闭型：取反
    # return _IR_SENSOR.is_blocked()    # 常开型：直接返回
# =======================

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
    print("  红外避障传感器 — 硬件测试")
    print("=" * 60)
    print(f"  运行平台: {'树莓派 (真实GPIO)' if ON_PI else 'Windows (Mock模式)'}")
    print(f"  引脚: GPIO{IR_SENSOR_PIN} (pin16), INPUT + 内部上拉")
    print(f"  传感器: 3线制红外避障 (VCC→3.3V, OUT→GPIO23, GND→GND)")
    print()
    print("  测试说明:")
    print("    持续检测30秒，请在此期间做以下操作：")
    print("    1) 不遮挡传感器 — 观察终端输出 '○ 无遮挡'")
    print("    2) 用手/口罩靠近传感器 — 观察终端输出 '● 检测到遮挡!'")
    print("    3) 移开手/口罩 — 观察终端恢复 '○ 无遮挡'")
    print("    4) 快速划过 — 观察响应速度")
    print()

    init_gpio()
    global _IR_SENSOR
    _IR_SENSOR = IRSensor(IR_SENSOR_PIN)
    print(f"  适配模式: 常闭型 (取反 is_blocked)")

    try:
        print("-" * 60)
        print("  [测试] 实时遮挡检测 — 持续30秒, 每秒检测1次")
        print("-" * 60)
        print(f"  {'时间':>5s}  状态           GPIO电平")
        print(f"  {'─'*5:>5s}  {'─'*12:12s}  {'─'*8:8s}")

        block_count = 0
        unblock_count = 0
        last_state = None

        for i in range(30):
            blocked = is_blocked()

            if ON_PI:
                raw_level = GPIO.input(IR_SENSOR_PIN)
                level_str = f"HIGH({raw_level})" if raw_level else f"LOW({raw_level})"
            else:
                level_str = "MOCK"

            if blocked:
                state_str = "● 检测到遮挡!"
                block_count += 1
            else:
                state_str = "○ 无遮挡"
                unblock_count += 1

            # 状态切换时打印醒目提示
            if blocked != last_state and last_state is not None:
                if blocked:
                    print(f"  >>> ╔══════════════════════════════╗")
                    print(f"  >>> ║  传感器检测到物体遮挡!      ║")
                    print(f"  >>> ╚══════════════════════════════╝")
                else:
                    print(f"  >>> ───── 物体已移开 ─────")

            last_state = blocked
            remaining = 29 - i
            print(f"  {remaining:>4}s  {state_str:14s}  {level_str:>8s}")

            time.sleep(1)

        print()
        print("-" * 60)
        print(f"  统计: 检测到遮挡 {block_count} 次, 无遮挡 {unblock_count} 次")
        print("-" * 60)

        if block_count > 0:
            print()
            print("=" * 60)
            print("  [PASS] 红外传感器测试通过! (能正确检测遮挡)")
            print("=" * 60)
        else:
            print()
            print("=" * 60)
            print("  [WARN] 未检测到任何遮挡")
            print("  请检查: 1)传感器VCC是否接3.3V")
            print("         2)电位器是否调到合适距离(5-8cm)")
            print("         3)OUT→GPIO23接线是否正确")
            print("=" * 60)

        print()

    except KeyboardInterrupt:
        print("\n  [中断] 用户取消测试")
    finally:
        cleanup_gpio()


if __name__ == '__main__':
    main()
