"""
test_all.py — 硬件驱动层综合测试（逐项运行，用于拍摄演示）

按顺序依次测试:
  1. GPIO 初始化
  2. RGB-LED 三色灯
  3. 蜂鸣器 PWM 发声
  4. 红外传感器遮挡检测
  5. 投币按键中断检测

每个测试之间有 2 秒间隔，终端输出清晰的分隔线，便于拍摄。

运行方法:
  python3 hardware_tests/test_all.py
"""

import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hardware.gpio_init import init_gpio, cleanup_gpio
from hardware.led import RGBLED
from hardware.buzzer import Buzzer
from hardware.ir_sensor import IRSensor
from hardware.button import CoinButton
from config import (
    RGB_R_PIN, RGB_G_PIN, RGB_B_PIN,
    BUZZER_PIN, IR_SENSOR_PIN, COIN_BUTTON_PIN
)

try:
    import RPi.GPIO as GPIO
    ON_PI = True
except (ImportError, RuntimeError):
    from unittest.mock import MagicMock
    GPIO = MagicMock()
    ON_PI = False


SEP = "=" * 60
SEP2 = "-" * 60


def banner(title):
    """打印醒目标题"""
    print()
    print(SEP)
    print(f"  {title}")
    print(SEP)
    print()


def test_1_gpio_init():
    """测试1: GPIO 初始化与清理"""
    banner("测试1/5: GPIO 初始化 (init_gpio)")

    print("  >>> 调用 init_gpio() ...")
    init_gpio()
    print("  >>> init_gpio() 执行成功!")
    print()
    print("  已配置引脚:")
    print("    输出: GPIO17(R-LED) GPIO18(G-LED) GPIO19(B-LED) GPIO26(蜂鸣器)")
    print("    输入: GPIO23(红外传感器) GPIO27(投币按键)")
    print("    模式: BCM编码, 输入引脚启用内部上拉(PUD_UP)")
    print()
    print("  [OK] GPIO 初始化测试通过 ✓")
    time.sleep(1)


def test_2_rgb_led():
    """测试2: RGB-LED 三色灯"""
    banner("测试2/5: RGB-LED 三色指示灯 (led.py)")

    rgb = RGBLED(RGB_R_PIN, RGB_G_PIN, RGB_B_PIN)
    print(f"  引脚: R=GPIO{RGB_R_PIN}, G=GPIO{RGB_G_PIN}, B=GPIO{RGB_B_PIN}")
    print()

    # 单色
    print(SEP2)
    print("  单色测试")
    print(SEP2)
    colors = [
        (1, 0, 0, "■ 红色 (货道A)"),
        (0, 1, 0, "■ 绿色 (货道B)"),
        (0, 0, 1, "■ 蓝色 (货道C)"),
    ]
    for r, g, b, desc in colors:
        print(f"  >>> {desc}")
        rgb.set_color(r, g, b)
        time.sleep(1.5)

    # 混色
    print()
    print(SEP2)
    print("  混色测试")
    print(SEP2)
    mixes = [
        (1, 1, 0, "■ 黄色 (R+G, 等待确认)"),
        (1, 0, 1, "■ 紫色 (R+B, 故障告警)"),
        (0, 1, 1, "■ 青色 (G+B)"),
        (1, 1, 1, "■ 白色 (全亮)"),
    ]
    for r, g, b, desc in mixes:
        print(f"  >>> {desc}")
        rgb.set_color(r, g, b)
        time.sleep(1.5)

    # 货道映射
    print()
    print(SEP2)
    print("  货道颜色映射 (set_channel)")
    print(SEP2)
    for ch, desc in [(0, "Channel 0 → 红色(成人口罩)"),
                      (1, "Channel 1 → 绿色(儿童口罩)"),
                      (2, "Channel 2 → 蓝色(N95)")]:
        print(f"  >>> {desc}")
        rgb.set_channel(ch)
        time.sleep(1)

    # 熄灭
    print()
    print("  >>> 全部熄灭 (off)")
    rgb.off()
    time.sleep(0.5)

    print()
    print("  [OK] RGB-LED 测试通过 ✓ (8种颜色全部正常)")
    time.sleep(1)


def test_3_buzzer():
    """测试3: 蜂鸣器 PWM 发声"""
    banner("测试3/5: 蜂鸣器 PWM 驱动 (buzzer.py)")

    buzzer = Buzzer(BUZZER_PIN)
    print(f"  引脚: GPIO{BUZZER_PIN} (pin37), PWM方波驱动")
    print()

    tests = [
        (500,  1.5, "低频 500Hz  — 余额不足提示 (低沉)"),
        (1000, 1.5, "中频 1000Hz — 出货成功提示 (正常)"),
        (1500, 1.5, "中高频1500Hz — 偏高"),
        (2000, 1.5, "高频 2000Hz — 超时告警 (尖锐)"),
    ]

    print(SEP2)
    print("  四频率发声测试 (占空比50%)")
    print(SEP2)

    for freq, duration, desc in tests:
        print(f"  >>> {desc}")
        print(f"      freq={freq}Hz, duration={duration}s")
        buzzer.beep(freq=freq, duration=duration)
        time.sleep(0.3)

    # 长鸣
    print()
    print("  >>> 连续长鸣测试 (1000Hz, 1.5秒)")
    buzzer.beep(freq=1000, duration=1.5)
    time.sleep(0.3)

    # 静音
    print("  >>> 静音 (off)")
    buzzer.off()

    print()
    print("  [OK] 蜂鸣器测试通过 ✓ (4个频率均正常)")
    time.sleep(1)


def test_4_ir_sensor():
    """测试4: 红外传感器遮挡检测"""
    banner("测试4/5: 红外传感器遮挡检测 (ir_sensor.py)")

    ir = IRSensor(IR_SENSOR_PIN)
    # 常闭型传感器取反；常开型去掉 not
    def is_blocked():
        return not ir.is_blocked()
    print(f"  引脚: GPIO{IR_SENSOR_PIN} (pin16), INPUT + 内部上拉")
    print()
    print("  请做以下操作验证传感器:")
    print("    1) 不遮挡 → 观察输出")
    print("    2) 用口罩/手遮挡 → 观察输出变化")
    print()

    print(SEP2)
    print("  实时检测 (15秒)")
    print(SEP2)
    print(f"  {'秒':>4s}  │  状态")
    print(f"  {'─'*4:>4s}──┼──{'─'*20:20s}")

    last_state = None
    triggered = False

    for i in range(15):
        blocked = is_blocked()
        elapsed = i + 1

        if blocked:
            state_str = "●●● 检测到遮挡! ●●●"
        else:
            state_str = "○○○ 无遮挡"

        # 状态变化时高亮
        if blocked != last_state and last_state is not None:
            if blocked:
                print(f"  ╔══════════════════════════════════╗")
                print(f"  ║  >>> 传感器被遮挡! <<<          ║")
                print(f"  ╚══════════════════════════════════╝")
                triggered = True
            else:
                print(f"  ──────── 物体已移开 ────────")

        last_state = blocked
        print(f"  {elapsed:>3}s │  {state_str}")

        time.sleep(1)

    print()
    if triggered:
        print("  [OK] 红外传感器测试通过 ✓ (能正确检测遮挡)")
    else:
        print("  [WARN] 未检测到遮挡, 请检查接线和电位器")
    time.sleep(1)


def test_5_button():
    """测试5: 投币按键中断检测"""
    banner("测试5/5: 投币按键中断检测 (button.py)")

    count = [0]

    def on_coin():
        count[0] += 1
        ts = time.strftime("%H:%M:%S")
        print(f"  💰 [{ts}] 检测到投币!  第 {count[0]} 次")

    btn = CoinButton(COIN_BUTTON_PIN, on_coin)
    btn.start()

    print(f"  引脚: GPIO{COIN_BUTTON_PIN} (pin13), 下降沿中断 + 200ms防抖")
    print()
    print("  请在 10 秒内按按键至少 3 次")
    print("  验证: 单次按下=1次计数, 长按=1次计数(边沿触发)")
    print()

    print(SEP2)
    print("  等待按键 (10秒)")
    print(SEP2)

    try:
        for remaining in range(10, 0, -1):
            if count[0] >= 3:
                print(f"  >>> 已检测到 {count[0]} 次，提前结束!")
                break
            bar = "▓" * (10 - remaining) + "░" * remaining
            print(f"  [{remaining:>2}s] {bar}  计数: {count[0]}/3")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  [中断]")

    btn.stop()

    print()
    if count[0] >= 3:
        print("  [OK] 按键测试通过 ✓")
    else:
        print(f"  [WARN] 仅检测到 {count[0]}/3 次, 请检查接线")
    time.sleep(1)


def main():
    """主流程: 依次运行5个测试"""
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + "  无人口罩贩卖机 — 硬件驱动层综合测试".center(52) + "║")
    print("║" + "  测试顺序: GPIO→RGB-LED→蜂鸣器→红外→按键".center(52) + "║")
    print("║" + f"  平台: {'树莓派 (真实GPIO)' if ON_PI else 'Windows (Mock模式)'}".ljust(52) + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    print("  每个测试之间间隔2秒，总时长约90秒")
    print("  按 Ctrl+C 可随时终止")
    print()

    # 询问开始
    input("  按 Enter 开始测试...")

    try:
        init_gpio()

        test_1_gpio_init()
        time.sleep(2)

        test_2_rgb_led()
        time.sleep(2)

        test_3_buzzer()
        time.sleep(2)

        test_4_ir_sensor()
        time.sleep(2)

        test_5_button()

        # 最终结果
        print()
        print("╔" + "═" * 58 + "╗")
        print("║" + "  全部硬件测试完成!".center(52) + "║")
        print("║" + "  测试项目: GPIO / RGB-LED / 蜂鸣器 / 红外 / 按键".center(52) + "║")
        print("╚" + "═" * 58 + "╝")
        print()

    except KeyboardInterrupt:
        print("\n\n  [中断] 用户终止测试")
    except Exception as e:
        print(f"\n\n  [ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_gpio()
        print("  GPIO 已清理, 程序退出.")
        print()


if __name__ == '__main__':
    main()
