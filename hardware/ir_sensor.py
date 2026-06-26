"""
红外传感器 — 检测取货口是否有口罩放置。

使用 RPi.GPIO 读取传感器电平。
Windows 开发时自动使用 MagicMock 代替 RPi.GPIO。

接线说明：
  传感器 VCC  → 树莓派 3.3V (pin1)
  传感器 GND  → 树莓派 GND (任意)
  传感器 OUT  → GPIO23 (pin16)
"""

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from unittest.mock import MagicMock
    GPIO = MagicMock()


class IRSensor:
    """
    红外传感器 — 检测取货口是否有口罩。

    Usage:
        ir = IRSensor(23)
        if ir.is_blocked():
            print("口罩已放置")
    """

    def __init__(self, pin: int):
        """
        pin: GPIO 引脚号（BCM编码）
        """
        self.pin = pin
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def is_blocked(self) -> bool:
        """
        读取 GPIO 电平判断是否有遮挡。

        返回 True = 被遮挡（有口罩放置），False = 未被遮挡。

        注意：取决于传感器模块类型（常开/常闭）：
        - 常开型（遮挡输出 HIGH）：返回 GPIO.input(pin) == HIGH
        - 常闭型（遮挡输出 LOW）： 返回 GPIO.input(pin) == LOW
        如果实际行为与预期相反，在此方法内部做逻辑取反即可。
        """
        # 常闭型传感器：遮挡时输出 LOW → 返回 True
        return GPIO.input(self.pin) == GPIO.LOW
