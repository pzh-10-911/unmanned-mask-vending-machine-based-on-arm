"""
RGB 三色LED控制。
替代原 DispenserLED（单色LED），使用一颗RGB-LED通过颜色区分货道和系统状态。
"""

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from unittest.mock import MagicMock
    GPIO = MagicMock()


class RGBLED:
    """
    RGB 三色LED控制。

    Usage:
        rgb = RGBLED(17, 18, 19)   # R, G, B 引脚
        rgb.set_color(1, 0, 0)     # 红色
        rgb.set_channel(0)         # 货道A颜色（红色）
        rgb.off()                  # 全部熄灭
    """

    def __init__(self, r_pin: int, g_pin: int, b_pin: int):
        """
        r_pin: 红色通道 GPIO 引脚号
        g_pin: 绿色通道 GPIO 引脚号
        b_pin: 蓝色通道 GPIO 引脚号
        """
        self.pins = (r_pin, g_pin, b_pin)
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

    def set_color(self, r: bool, g: bool, b: bool) -> None:
        """
        设置 RGB 颜色。
        True = 点亮对应颜色通道，False = 熄灭。
        """
        r_val, g_val, b_val = self.pins
        GPIO.output(r_val, GPIO.HIGH if r else GPIO.LOW)
        GPIO.output(g_val, GPIO.HIGH if g else GPIO.LOW)
        GPIO.output(b_val, GPIO.HIGH if b else GPIO.LOW)

    def off(self) -> None:
        """全部熄灭。"""
        self.set_color(False, False, False)

    def set_channel(self, channel: int) -> None:
        """
        按货道显示对应颜色。
        0→红(成人口罩), 1→绿(儿童口罩), 2→蓝(N95口罩)
        """
        colors = {0: (1, 0, 0), 1: (0, 1, 0), 2: (0, 0, 1)}
        r, g, b = colors.get(channel, (0, 0, 0))
        self.set_color(bool(r), bool(g), bool(b))
