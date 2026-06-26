"""
test_mock_api.py — 模拟 API 接口调用硬件（全流程演示）

模拟 Flask 层调用硬件驱动的完整交易流程，验证各硬件模块接口是否正常工作。

模拟流程:
  场景A: 正常购买流程（投币→选品→确认→出货→取货检测→完成）
  场景B: 取消交易流程（投币→选品→取消）
  场景C: 取货超时流程（投币→选品→确认→超时未取货→取消）

运行方法:
  python3 hardware_tests/test_mock_api.py
"""

import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hardware.led import RGBLED
from hardware.buzzer import Buzzer
from hardware.ir_sensor import IRSensor
from hardware.gpio_init import init_gpio, cleanup_gpio
from config import (
    RGB_R_PIN, RGB_G_PIN, RGB_B_PIN,
    BUZZER_PIN, IR_SENSOR_PIN
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


def print_step(step_num, total, description):
    """打印步骤标题"""
    print(f"\n  [{step_num}/{total}] {description}")
    print(f"  {'─' * 50}")


def wait_for_pickup(ir, timeout=10, invert=True):
    """
    模拟红外轮询: 等待用户将口罩放到取货口。
    invert=True 适配常闭型传感器(遮挡=LOW)。
    """
    print(f"  >>> 红外轮询启动 (超时={timeout}秒, 间隔=1秒)")
    for i in range(timeout):
        raw = ir.is_blocked()
        blocked = not raw if invert else raw
        remaining = timeout - i - 1
        if blocked:
            print(f"      第{i+1}秒: ● 检测到遮挡! → 取货成功")
            return True
        else:
            print(f"      第{i+1}秒: ○ 无遮挡 (剩余{remaining}秒)")
        time.sleep(1)
    print(f"  >>> 超时! 未检测到取货")
    return False


def scenario_a_normal_purchase(rgb, buzzer, ir):
    """场景A: 正常购买流程"""
    print(f"\n{SEP}")
    print(f"  场景A: 正常购买流程 (投币→选品→确认→出货→取货→完成)")
    print(f"{SEP}")

    # Step 1: 投币
    print_step(1, 6, "用户投币 (模拟 POST /api/coin)")
    print("  >>> 投币按键触发 → sm.add_coin() → 余额+1元")
    time.sleep(0.5)

    # Step 2: 选品
    print_step(2, 6, "用户选择口罩品类 (模拟 POST /api/select/0)")
    print("  >>> 选择: Channel 0 = 成人口罩 (¥2.0)")
    rgb.set_channel(0)
    print("  >>> RGB-LED → 红色 (货道A指示)")
    time.sleep(1.5)

    # Step 3: 确认购买
    print_step(3, 6, "用户确认购买 (模拟 POST /api/confirm)")
    print("  >>> sm.confirm(on_dispense=on_dispense)")
    print("  >>> on_dispense 回调: RGB-LED 红色 + 蜂鸣器 1000Hz/0.2s")
    rgb.set_channel(0)
    buzzer.beep(freq=1000, duration=0.2)
    time.sleep(0.5)

    # Step 4: 等待取货
    print_step(4, 6, "等待用户取货 (红外轮询线程)")
    print("  >>> 请将口罩放到取货口上方的红外传感器处...")
    success = wait_for_pickup(ir, timeout=10)

    # Step 5: 完成
    if success:
        print_step(5, 6, "取货检测成功 → 交易完成")
        print("  >>> sm.complete() → 扣减库存 + 记录交易")
        rgb.off()
        buzzer.beep(freq=1000, duration=0.2)
        print("  >>> RGB-LED 熄灭, 蜂鸣器提示音")
    else:
        print_step(5, 6, "取货超时 → 交易取消")
        print("  >>> sm.cancel() → 退回余额")
        rgb.off()

    # Step 6: 回到待机
    print_step(6, 6, "系统回到待机状态")
    print("  >>> 状态: IDLE, LED: 灭")
    print(f"\n  >>> 场景A 结束!")
    time.sleep(1)


def scenario_b_cancel(rgb, buzzer):
    """场景B: 取消交易"""
    print(f"\n{SEP}")
    print(f"  场景B: 取消交易流程 (投币→选品→取消)")
    print(f"{SEP}")

    print_step(1, 4, "用户投币")
    print("  >>> 余额+1元")
    time.sleep(0.3)

    print_step(2, 4, "用户选择口罩品类")
    print("  >>> 选择: Channel 1 = 儿童口罩")
    rgb.set_channel(1)
    print("  >>> RGB-LED → 绿色")
    time.sleep(1)

    print_step(3, 4, "用户取消交易 (模拟 POST /api/cancel)")
    print("  >>> sm.cancel() → 余额退回, 状态回到 IDLE")
    rgb.off()
    print("  >>> RGB-LED 熄灭")
    time.sleep(0.5)

    print_step(4, 4, "系统回到待机状态")
    print(f"\n  >>> 场景B 结束!")
    time.sleep(1)


def scenario_c_timeout(rgb, buzzer, ir):
    """场景C: 取货超时"""
    print(f"\n{SEP}")
    print(f"  场景C: 取货超时流程 (投币→选品→确认→超时→取消)")
    print(f"{SEP}")

    print_step(1, 5, "用户投币 + 选品")
    print("  >>> 选择: Channel 2 = N95口罩 (¥5.0)")
    time.sleep(0.3)

    print_step(2, 5, "确认购买")
    rgb.set_channel(2)
    buzzer.beep(freq=1000, duration=0.2)
    print("  >>> RGB-LED → 蓝色, 蜂鸣器提示")
    time.sleep(0.5)

    print_step(3, 5, "等待取货 — 超时 (模拟30秒超时缩短为5秒)")
    print("  >>> 请勿遮挡传感器，等待超时...")
    success = wait_for_pickup(ir, timeout=5)

    if not success:
        print_step(4, 5, "取货超时 → 自动取消")
        print("  >>> sm.cancel() → 状态复位")
        rgb.off()
        buzzer.beep(freq=2000, duration=0.5)
        print("  >>> RGB-LED 熄灭, 蜂鸣器高频告警 2000Hz/0.5s")
    else:
        print_step(4, 5, "意外检测到遮挡 (请重试本场景)")

    print_step(5, 5, "系统回到待机状态")
    print(f"\n  >>> 场景C 结束!")
    time.sleep(1)


def main():
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + "  模拟 API 接口调用 — 硬件全流程测试".center(52) + "║")
    print("║" + "  验证 Flask→Hardware 接口是否正确".center(52) + "║")
    print("║" + f"  平台: {'树莓派 (真实GPIO)' if ON_PI else 'Windows (Mock)'}".ljust(52) + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    print("  本测试模拟 Flask API 层调用硬件驱动的 3 个场景:")
    print("    A. 正常购买: 投币 → 选品 → 确认 → 取货 → 完成")
    print("    B. 取消交易: 投币 → 选品 → 取消")
    print("    C. 取货超时: 投币 → 选品 → 确认 → 超时 → 取消")
    print()
    print("  涉及硬件接口:")
    print("    rgb.set_channel() / rgb.off()")
    print("    buzzer.beep(freq, duration)")
    print("    ir.is_blocked()")
    print()

    input("  按 Enter 开始测试...")

    init_gpio()
    rgb = RGBLED(RGB_R_PIN, RGB_G_PIN, RGB_B_PIN)
    buzzer = Buzzer(BUZZER_PIN)
    ir = IRSensor(IR_SENSOR_PIN)

    try:
        # 场景A: 正常购买
        scenario_a_normal_purchase(rgb, buzzer, ir)

        # 场景B: 取消
        scenario_b_cancel(rgb, buzzer)

        # 场景C: 超时
        scenario_c_timeout(rgb, buzzer, ir)

        # 结果
        print(f"\n{SEP}")
        print(f"  全部场景测试完成!")
        print(f"{SEP}")
        print()

    except KeyboardInterrupt:
        print("\n\n  [中断] 用户终止")
    except Exception as e:
        print(f"\n  [ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        rgb.off()
        buzzer.off()
        cleanup_gpio()
        print("  GPIO 已清理.")
        print()


if __name__ == '__main__':
    main()
