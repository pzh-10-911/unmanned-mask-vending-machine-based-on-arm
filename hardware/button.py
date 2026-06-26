"""
投币按键检测。

使用 GPIO 下降沿中断检测按键。
带 200ms 软件防抖。
Windows 开发时自动使用 MagicMock 代替 RPi.GPIO。

接线说明：
  按键一脚 → GPIO27 (pin13)
  按键另一脚 → GND (pin14)
  （使用内部上拉，无需外接电阻）
"""

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from unittest.mock import MagicMock
    GPIO = MagicMock()


class CoinButton:
    """
    投币按键检测。

    按下时触发注册的 callback 函数。
    内部使用 GPIO 下降沿中断检测，带 200ms 防抖。

    Usage:
        def on_coin():
            print("收到1元")

        btn = CoinButton(27, on_coin)
        btn.start()
        # ...
        btn.stop()
    """

    def __init__(self, pin: int, callback: callable):
        """
        pin: GPIO 引脚号（BCM编码）
        callback: 按键按下时的回调函数（无参数）
        """
        self.pin = pin
        self.callback = callback
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def start(self) -> None:
        """
        启用按键监听。
        注册 GPIO 下降沿中断事件，防抖时间 200ms。
        RPi.GPIO 回调会传入 channel 参数，用 lambda 忽略。
        """
        GPIO.add_event_detect(
            self.pin, GPIO.FALLING,
            callback=lambda ch: self.callback(),
            bouncetime=200
        )
        print(f"[BTN] GPIO{self.pin} listening started")

    def stop(self) -> None:
        """
        停用按键监听。
        移除 GPIO 中断事件检测。
        """
        GPIO.remove_event_detect(self.pin)
        print(f"[BTN] GPIO{self.pin} listening stopped")
