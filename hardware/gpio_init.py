"""
GPIO 初始化与清理。

Windows 开发时自动使用 MagicMock 代替 RPi.GPIO。
"""

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from unittest.mock import MagicMock
    GPIO = MagicMock()
    print("[MOCK] Using mock GPIO for Windows development")


def init_gpio():
    """
    初始化所有 GPIO 引脚。
    - 设置 GPIO 模式为 BCM
    - 配置 RGB-LED 三引脚/BUZZER 引脚为 OUTPUT，初始 LOW
    - 配置按键/红外引脚为 INPUT，PUD_UP
    异常：如果初始化失败则抛出 RuntimeError
    """
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.OUT, initial=GPIO.LOW)   # RGB-R
    GPIO.setup(18, GPIO.OUT, initial=GPIO.LOW)   # RGB-G
    GPIO.setup(19, GPIO.OUT, initial=GPIO.LOW)   # RGB-B
    GPIO.setup(26, GPIO.OUT, initial=GPIO.LOW)   # 蜂鸣器
    GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # 红外传感器
    GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # 投币按键
    print("[GPIO] init_gpio() called")


def cleanup_gpio():
    """
    清理 GPIO 资源。
    - 所有输出引脚置 LOW
    - 调用 GPIO.cleanup()
    """
    GPIO.output(17, GPIO.LOW)
    GPIO.output(18, GPIO.LOW)
    GPIO.output(19, GPIO.LOW)
    GPIO.output(26, GPIO.LOW)
    GPIO.cleanup()
    print("[GPIO] cleanup_gpio() called")
