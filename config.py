"""
全局配置：引脚号、价格、库存初始值、超时参数。
"""

# ===== GPIO 引脚 =====
RGB_R_PIN = 17          # RGB-LED 红色通道（货道A 成人口罩）
RGB_G_PIN = 18          # RGB-LED 绿色通道（货道B 儿童口罩）
RGB_B_PIN = 19          # RGB-LED 蓝色通道（货道C N95）
RGB_PINS = [RGB_R_PIN, RGB_G_PIN, RGB_B_PIN]
IR_SENSOR_PIN = 23      # 红外传感器 — 取货口检测
BUZZER_PIN = 26         # 蜂鸣器
COIN_BUTTON_PIN = 27    # 投币按键
# GPIO22 空闲备用（原系统状态LED已取消，功能由RGB LED替代）

# RGB-LED 颜色映射（按货道）
CHANNEL_COLORS = {
    0: (1, 0, 0),       # 红 — 成人口罩
    1: (0, 1, 0),       # 绿 — 儿童口罩
    2: (0, 0, 1),       # 蓝 — N95口罩
}

# ===== 价格和库存 =====
CHANNEL_CONFIG = [
    {"id": 0, "name": "成人口罩", "price": 2.0, "init_stock": 10},
    {"id": 1, "name": "儿童口罩", "price": 2.0, "init_stock": 10},
    {"id": 2, "name": "N95口罩",  "price": 5.0, "init_stock": 5},
]

# ===== 时间参数 =====
DISPENSE_TIMEOUT = 30       # 出货等待超时（秒）
IR_DETECT_INTERVAL = 0.5    # 红外轮询间隔（秒）
IR_RETRY_COUNT = 56         # 超时前的检测次数 (30-2)/0.5=56
