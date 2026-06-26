# 基于树莓派的无人口罩贩卖机

攀枝花学院 2023 级计算机科学与技术专业 — 嵌入式课程设计

基于树莓派的无人口罩贩卖机系统。用户通过手机浏览器操作，配合物理按键模拟投币，完成口罩自助购买。

## 快速开始

```bash
pip install -r requirements.txt
python app.py
```

浏览器访问 `http://localhost:5000`

## 硬件清单

| 元件 | 数量 | 用途 |
|------|------|------|
| 树莓派 3B+/4B | 1 | 主控 |
| RGB-LED（共阴极） | 1 | 三色状态/出货指示 |
| 220Ω 电阻 | 3 | RGB-LED 限流（每路一个） |
| 红外避障传感器 | 1 | 取货口检测 |
| 轻触按键 | 1 | 投币模拟 |
| 3脚无源蜂鸣器模块 | 1 | 出货提示音（PWM驱动） |
| 面包板 + 杜邦线 | 若干 | 接线 |

## GPIO 引脚分配

| 引脚 | 连接 | 方向 |
|------|------|------|
| GPIO 17 | RGB-LED R（红色，货道A） | OUT |
| GPIO 18 | RGB-LED G（绿色，货道B） | OUT |
| GPIO 19 | RGB-LED B（蓝色，货道C） | OUT |
| GPIO 22 | 空闲（备用） | — |
| GPIO 23 | 红外传感器 OUT | IN |
| GPIO 26 | 蜂鸣器模块 IO（PWM） | OUT |
| GPIO 27 | 投币按键 | IN (PUD_UP) |

## 项目结构

```
├── app.py                    Flask 入口 + 8 个 API 路由
├── config.py                 全局配置（引脚号、价格、超时参数）
├── requirements.txt          依赖清单（Flask + RPi.GPIO）
├── run.sh                    树莓派启动脚本
├── hardware_simulator.py     硬件模拟层（无硬件环境测试用）
├── hardware/                 硬件驱动层（Person A）
│   ├── __init__.py
│   ├── gpio_init.py          GPIO 初始化与清理
│   ├── led.py                RGBLED 三色控制
│   ├── buzzer.py             无源蜂鸣器 PWM 驱动
│   ├── ir_sensor.py          红外传感器读取
│   └── button.py             投币按键中断检测
├── hardware_tests/           硬件分项测试（Person A，7个文件）
│   ├── test_all.py           一键全测
│   ├── test_rgb_led.py       三色LED测试（含set_channel）
│   ├── test_buzzer.py        蜂鸣器 PWM 测试
│   ├── test_button.py        按键中断测试
│   ├── test_ir_sensor.py     红外遮挡检测测试
│   ├── test_gpio_init.py     GPIO 初始化/清理测试
│   └── test_mock_api.py      模拟 API 调用测试
├── tests/                    综合测试
│   ├── __init__.py
│   └── test_hardware.py      全硬件综合测试
├── logic/                    业务逻辑层（Person B）
│   ├── __init__.py
│   ├── state_machine.py      状态机（IDLE→SELECTED→DISPENSE）
│   └── inventory.py          库存 JSON 持久化
├── static/                   前端页面（Person D）
│   ├── index.html            单页应用 + 弹窗式交互
│   ├── style.css             移动端响应式暗色主题
│   └── script.js             内嵌于 index.html（轮询 + API 调用）
├── data/                     运行时数据（自动生成）
│   └── inventory.json        库存与交易记录
├── test_api.py               API 全量测试（51条）
├── test_hardware_integration.py  硬件集成测试（56条）
├── test_scenarios.py         场景模拟测试（12场景/94条）
├── test_logic.py             逻辑层独立测试
└── docs/                     设计文档
    ├── A-硬件驱动.md
    ├── A-硬件驱动-测试.md
    ├── B-状态机与库存.md
    ├── B-状态机与库存-测试.md
    ├── C-Flask-API集成.md
    ├── C-Flask-API集成-测试.md
    ├── D-前端页面.md
    ├── D-前端页面-测试.md
    ├── design.md              完整设计文档
    ├── team-assignment.md      分工文档
    ├── logic接口文档.md        逻辑接口规范
    ├── Git提交指南.md          Git 协作指南
    └── 硬件接线总表.md         完整接线文档
```

## API 接口

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/` | 返回前端主页 |
| GET | `/api/status` | 获取贩卖机状态、余额、库存 |
| POST | `/api/coin` | 投币（余额 +1） |
| POST | `/api/select/<id>` | 选择口罩品类 |
| POST | `/api/confirm` | 确认购买 |
| POST | `/api/cancel_select` | 取消选择（保留余额） |
| POST | `/api/cancel` | 取消交易（余额清零 + 退币） |
| GET | `/api/logs` | 获取交易记录 |
| POST | `/api/reset` | 恢复初始库存 + 重置状态机 |

## 核心流程

```
物理按键投币（每次 +1 元）
  → 手机页面选择口罩品类
  → 弹出确认弹窗 → 确认购买
  → 对应货道颜色亮起（RGB-LED）+ 蜂鸣器响 200ms
  → 2 秒后开始红外检测（防手快速划过误触）
  → 用户从对应格子取口罩放至取货口
  → 红外传感器连续 3 次检测到遮挡（1.5 秒稳定确认）
  → 扣减库存 → RGB-LED 熄灭 → 蜂鸣器响两声确认
  → 前端检测到 DISPENSE→IDLE 自动关闭结果弹窗
```

## 蜂鸣器提示音设计

| 时机 | 频率 | 时长 | 含义 |
|------|------|------|------|
| 确认购买（出货开始） | 1000Hz | 0.2s 一声 | 提示用户准备取货 |
| 取货成功（红外检测） | 1000Hz | 0.1s 两声 | 交易完成确认 |
| 取货超时（30秒未取） | 2000Hz | 0.5s 长响 | 超时告警 |
| 取消交易（退币） | 2000Hz | 0.5s 长响 | 退币提示 |

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 后端 | Python 3 + Flask | Web 服务器，提供 REST API |
| GPIO | RPi.GPIO | 树莓派引脚控制，Windows 开发自动 Mock |
| 前端 | 纯 HTML + CSS + JS | 无框架，移动端自适应，弹窗式交互 |
| 持久化 | JSON 文件 | 库存与交易记录存储 |

## 测试

```bash
# 逻辑层测试（无需硬件）
python test_logic.py

# API 端点测试（需先启动 app.py）
python test_api.py

# 硬件集成测试（使用模拟层，无需硬件）
python test_hardware_integration.py

# 场景模拟测试（12 个场景）
python test_scenarios.py
```

## 部署

树莓派启动：

```bash
cd ~/911
python3 -u app.py
```

手机连接同一 WiFi 后浏览器访问 `http://树莓派IP:5000`（默认 `http://192.168.43.185:5000`）。

## 分工

| 角色 | 任务 | 产出文件 |
|------|------|---------|
| Person A | 硬件接线 + 驱动层 | `hardware/` 下 5 个模块 + `hardware_tests/` 下 7 个测试 |
| Person B | 状态机 + 库存逻辑 | `logic/` 下 2 个模块 + `config.py` |
| Person C | Flask API 集成 | `app.py` + 路由 + 红外轮询线程 + 测试脚本 |
| Person D | 前端页面 | `static/` 下 3 个文件 |
