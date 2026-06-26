"""
无源蜂鸣器控制。

无源蜂鸣器需要 PWM 方波驱动，通过调节频率发出不同音调。
Windows 开发时自动使用 MagicMock 代替 RPi.GPIO。

接线说明（3脚无源蜂鸣器模块）：
  模块 VCC → 树莓派 3.3V (pin1/pin17)
  模块 IO  → GPIO26 (pin37)
  模块 GND → 树莓派 GND (任意)
"""

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from unittest.mock import MagicMock
    GPIO = MagicMock()


class Buzzer:
    """
    无源蜂鸣器控制。

    使用 PWM 驱动，支持频率调节和时长控制。
    PWM 对象在 __init__ 时创建，后续只修改频率，不重复创建。

    Usage:
        buzzer = Buzzer(26)
        buzzer.beep()                      # 默认 1000Hz, 0.2 秒
        buzzer.beep(freq=2000)             # 2kHz
        buzzer.beep(freq=500, duration=1)  # 500Hz, 1 秒
        buzzer.off()                       # 停止
    """

    def __init__(self, pin: int):
        """
        pin: GPIO 引脚号（BCM编码）
        """
        self.pin = pin
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)
        self.pwm = GPIO.PWM(self.pin, 1000)  # 初始 1000Hz
        self.pwm.start(0)                     # 占空比 0 = 静音

    def beep(self, freq: int = 1000, duration: float = 0.2):
        """
        发出指定频率和时长的声音。

        freq: 频率 Hz（默认 1000）
        duration: 持续时间 秒（默认 0.2）
        """
        import time
        self.pwm.ChangeFrequency(freq)
        self.pwm.ChangeDutyCycle(50)  # 50% 占空比
        time.sleep(duration)
        self.pwm.ChangeDutyCycle(0)   # 停止发声

    def off(self):
        """停止发声。"""
        self.pwm.ChangeDutyCycle(0)
