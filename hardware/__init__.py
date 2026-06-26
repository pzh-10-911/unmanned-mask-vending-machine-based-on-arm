"""
hardware package - 硬件驱动层

为 Person C 提供统一的硬件控制接口：
- RGBLED: 三色LED控制
- IRSensor: 红外传感器读取
- CoinButton: 投币按键检测
- init_gpio / cleanup_gpio: GPIO 初始化与清理
"""
