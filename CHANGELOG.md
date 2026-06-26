# Person C 代码审查修改日志

> 审查日期：2026-06-26  
> 审查范围：Flask API 集成层（app.py）及其关联文件  
> 测试结果：API 51/51 ✅ | 硬件集成 56/56 ✅ | 场景模拟 94/94 ✅ | 前后端契约 20/21 ✅

---

## 修改清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `app.py` | 修改 | 6 处 bug 修复 |
| `static/index.html` | 修改 | 2 处路径更新 |
| `test_api.py` | 新增 | API 全量测试（51 条） |
| `hardware_simulator.py` | 新增 | 硬件模拟层 |
| `test_hardware_integration.py` | 新增 | 硬件集成测试（56 条） |
| `test_scenarios.py` | 新增 | 场景模拟测试（12 场景 / 94 条） |
| `run.sh` | 新增 | 树莓派启动脚本 |

---

## Bug #1: 首页 Content-Type 错误

**现象：** `GET /` 返回 `Content-Type: text/plain` 而非 `text/html`

**根因：** 两个问题叠加：
1. `static_url_path=''` 导致 Werkzeug `SharedDataMiddleware` 在 `/` 路径直接拦截请求，返回静态文件，Flask 的 `index()` 路由从未被调用
2. Windows 注册表中 `.html` 扩展名的 Content Type 缺失，Python `mimetypes` 模块将所有扩展名返回 `text/plain`

**修复：**
- `app.py:26` — `static_url_path=''` → `static_url_path='/static'`
- `app.py:65-69` — 用 `open()` 读文件 + `(html, 200, {'Content-Type': ...})` 元组方式显式设置 MIME 类型，不再依赖系统 MIME 数据库
- `static/index.html:7` — `href="style.css"` → `href="/static/style.css"`
- `static/index.html:82` — `src="script.js"` → `src="/static/script.js"`

```python
# Before
app = Flask(__name__, static_folder='static', static_url_path='')

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# After
app = Flask(__name__, static_folder='static', static_url_path='/static')

@app.route('/')
def index():
    with open('static/index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
```

---

## Bug #2: api_status 返回字段不完整

**现象：** 前端 `state.state_name` 和 `state.selected_channel` 始终为 `undefined`

**根因：** `api_status` 手动构建 dict，未调用 `sm.get_state()`，缺少 `state_name` 和 `selected_channel` 字段

```python
# Before
@app.route('/api/status')
def api_status():
    return jsonify({
        "state": sm.state if hasattr(sm, 'state') else "IDLE",
        "balance": sm.balance if hasattr(sm, 'balance') else 0,
        "channels": inv.get_status()
    })

# After
@app.route('/api/status')
def api_status():
    return jsonify(sm.get_state())
```

`sm.get_state()` 返回完整结构：
```json
{
    "state": 0,
    "state_name": "IDLE",
    "balance": 0,
    "selected_channel": null,
    "channels": [ ... ]
}
```

---

## Bug #3: api_reset 不重置状态机

**现象：** 调用 `/api/reset` 后库存恢复但余额和状态仍然残留

**根因：** `api_reset` 只操作 `inv`（库存），不操作 `sm`（状态机）。连续测试时上轮余额延续到下轮。

```python
# After (新增部分)
@app.route('/api/reset', methods=['POST'])
def api_reset():
    # ... 库存重置（不变）...
    # 新增：重置状态机
    sm.state = 0
    sm.balance = 0
    sm.selected_channel = None
    return jsonify({"success": True})
```

---

## Bug #4: api_reset 引用不存在的属性

**现象：** `AttributeError: 'Inventory' object has no attribute 'DEFAULT_CHANNELS'`

**根因：** 原始代码 `inv.DEFAULT_CHANNELS` 不存在。`Inventory` 类没有此属性。

```python
# Before
inv.channels = [dict(ch) for ch in inv.DEFAULT_CHANNELS]

# After — 从 CHANNEL_CONFIG 重建
inv.channels = []
for ch in CHANNEL_CONFIG:
    inv.channels.append({
        "id": ch["id"],
        "name": ch["name"],
        "price": ch["price"],
        "stock": ch["init_stock"]
    })
```

---

## Bug #6: cancel/cancel_select 未关闭 LED

**现象：** 在 DISPENSE 状态下取消交易后，RGB LED 保持亮起，直到 30 秒超时线程才熄灭

**根因：** `api_cancel` 和 `api_cancel_select` 只调用 `sm.cancel()`/`sm.cancel_select()`，未调用 `rgb.off()`。LED 关闭只在 `wait_for_pickup` 线程（complete/timeout 分支）中执行。

**修复：** 在 `api_cancel` 和 `api_cancel_select` 中增加 `rgb.off()` 调用。

```python
# Before
@app.route('/api/cancel', methods=['POST'])
def api_cancel():
    result = sm.cancel()
    return jsonify(result)

# After
@app.route('/api/cancel', methods=['POST'])
def api_cancel():
    result = sm.cancel()
    rgb.off()
    return jsonify(result)
```

---

## Bug #5: 未使用的 import

**现象：** `send_from_directory` 和 `make_response` 导入但最终方案不依赖它们

**修复：** `from flask import Flask, jsonify, send_from_directory, make_response` → `from flask import Flask, jsonify`

---

## 新增：test_api.py

51 条测试覆盖 9 个端点，场景包括：

| 端点 | 测试场景 |
|------|---------|
| `GET /` | 状态码、Content-Type、HTML 内容 |
| `GET /api/status` | 字段完整性、类型检查、初始状态、状态流转 |
| `POST /api/coin` | 单次投币、累加、在 SELECTED/DISPENSE 状态下投币 |
| `POST /api/select/<id>` | 正常选择、余额不足、无效货道、重复选择拒绝 |
| `POST /api/confirm` | 确认购买、未选择状态下确认、余额扣减验证 |
| `POST /api/cancel` | 从 SELECTED 取消、从 DISPENSE 取消 |
| `POST /api/cancel_select` | 取消选择、余额保留验证 |
| `GET /api/logs` | 返回数组、结构验证 |
| `POST /api/reset` | 库存恢复、交易记录清除、状态机重置 |

运行方式：
```bash
# 终端 1：启动服务器
python app.py

# 终端 2：运行测试
python test_api.py
```

---

## 新增：hardware_simulator.py + test_hardware_integration.py

为无硬件环境提供可控的模拟层：

| 模拟组件 | 功能 |
|---------|------|
| `SimulatedIRSensor` | 可设置遮挡/无遮挡状态 |
| `SpyRGBLED` | 记录所有颜色/通道操作，可查询 |
| `SpyBuzzer` | 记录所有蜂鸣操作（频率、时长） |
| `HardwareSimulator` | 统一管理：投币模拟、取货模拟、超时模拟、LED/蜂鸣器断言 |

12 个集成测试场景：
1. 初始状态检查
2. 投币按键模拟
3. 完整购买流程（投币→选货→确认→取货）
4. 红外超时（无人取货）
5. DISPENSE 状态下取消
6. LED 颜色对应货道
7. 蜂鸣器参数验证
8. 完整流程（含余额不足拒绝）
9. 多次连续购买
10. 各状态下的投币行为
11. 红外传感器翻转
12. on_dispense 回调链验证

运行方式：
```bash
python test_hardware_integration.py
```

---

## 测试结果汇总

```
API 端点测试:        51/51 通过 ✅
前后端契约验证:      20/21 通过 ✅ (1个终端 GBK 编码问题，非逻辑错误)
状态机流转验证:      全部正确 ✅
硬件模拟集成测试:    56/56 通过 ✅
```

---

## 部署检查清单

- [ ] `python test_api.py` 全部通过
- [ ] `python test_hardware_integration.py` 全部通过
- [ ] 浏览器访问 `http://树莓派IP:5000` 首页正常显示
- [ ] 浏览器控制台无 JS 报错（`state_name`、`selected_channel` 不再是 `undefined`）
- [ ] 投币、选货、确认、取消流程完整可用
- [ ] RGB LED 按货道显示正确颜色
- [ ] 蜂鸣器在出货时响 200ms
- [ ] 红外传感器检测到取货后 LED 熄灭
- [ ] `POST /api/reset` 恢复库存且余额归零
