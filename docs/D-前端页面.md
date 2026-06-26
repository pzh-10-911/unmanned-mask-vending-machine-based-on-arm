# Person D — 前端页面（纯 JS）

## 产出文件

```
mask-vending-machine/
├── static/
│   ├── index.html    # 单页应用HTML
│   ├── style.css     # 移动端响应式样式
│   └── script.js     # 前端交互逻辑
```

---

## API 接口约定（与 C 的协约）

| 函数调用 | API 端点 | 方法 | 用途 |
|---------|---------|------|------|
| `fetchStatus()` | `/api/status` | GET | 轮询状态，更新 UI |
| `onCoinClick()` | `/api/coin` | POST | 投币+1元 |
| `onBuyClick(id)` | `/api/select/{id}` | POST | 选择品类 |
| `onConfirmClick()` | `/api/confirm` | POST | 确认购买 |
| `onCancelClick()` | `/api/cancel` | POST | 取消交易 |

### API 基地址

```javascript
const API_BASE = window.location.origin;
```

### GET /api/status — 返回数据结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `state` | int | 0=IDLE, 1=SELECTED, 2=DISPENSE |
| `state_name` | string | "IDLE" / "SELECTED" / "DISPENSE" |
| `balance` | int | 当前余额（元） |
| `selected_channel` | int / null | 已选品类ID |
| `channels` | array | 3个货道信息 |

**channels[i] 字段：**

| 字段 | 类型 | 示例 |
|------|------|------|
| `id` | int | 0 |
| `name` | string | "成人口罩" |
| `price` | float | 2.0 |
| `stock` | int | 10 |
| `available` | bool | true |

### POST /api/coin — 响应

```json
{"balance": 3}
```

### POST /api/select/{id} — 响应

| 结果 | 响应 |
|------|------|
| 成功 | `{"success": true, "channel": 0, "price": 2.0, "name": "成人口罩"}` |
| 余额不足 | `{"success": false, "msg": "余额不足"}` |
| 库存不足 | `{"success": false, "msg": "库存不足"}` |
| 状态错误 | `{"success": false, "msg": "状态错误"}` |

### POST /api/confirm — 响应

| 结果 | 响应 |
|------|------|
| 成功 | `{"success": true, "msg": "出货中，请取货", "channel": 0}` |
| 失败 | `{"success": false, "msg": "状态错误"}` |

### POST /api/cancel — 响应

```json
{"success": true, "balance": 0}
```

---

## 页面结构

### 3个视图

| 视图 | id | 默认显示 | 用途 |
|------|-----|---------|------|
| 主界面 | `page-main` | ✅ | 余额 + 商品卡片 + 按钮 |
| 确认弹窗 | `page-confirm` | ❌ | 遮罩层 + 商品信息 + 确认/取消 |
| 结果页 | `page-result` | ❌ | 成功/失败图标 + 提示 + 自动返回 |

```html
<div id="page-main">
  <div class="header">余额: ¥<span id="balance">0</span></div>
  <button id="btn-coin" class="coin-btn">投币 +1元</button>
  <div id="product-list"><!-- JS 动态渲染 --></div>
  <button id="btn-cancel" class="cancel-btn" style="display:none">取消交易</button>
</div>

<div id="page-confirm" class="modal" style="display:none">
  <div class="modal-content">
    <p>商品: <span id="confirm-name"></span></p>
    <p>金额: ¥<span id="confirm-price"></span></p>
    <p>余额: ¥<span id="confirm-balance"></span></p>
    <button id="btn-confirm-yes">确认购买</button>
    <button id="btn-confirm-no">取消</button>
  </div>
</div>

<div id="page-result" style="display:none">
  <div id="result-icon"></div>       <!-- ✅ 或 ❌ -->
  <div id="result-message"></div>    <!-- 购买成功/失败原因 -->
  <div id="result-timer">3秒后返回</div>
</div>
```

---

## script.js 核心逻辑

### 全局状态

```javascript
let state = {
    state: 0,
    state_name: 'IDLE',
    balance: 0,
    selected_channel: null,
    channels: []
};
```

### 函数清单

| 函数 | 触发时机 | 调用API | 副作用 |
|------|---------|---------|--------|
| `fetchStatus()` | 每秒定时 + 初次加载 | GET `/api/status` | 更新 state + 刷新 UI |
| `onCoinClick()` | 点击投币按钮 | POST `/api/coin` | 更新余额显示 |
| `onBuyClick(id)` | 点击购买按钮 | POST `/api/select/{id}` | 成功→弹出确认页 |
| `onConfirmClick()` | 点击确认购买 | POST `/api/confirm` | 成功→结果页(出货动画) |
| `onCancelClick()` | 点击取消交易 | POST `/api/cancel` | 余额归零→主界面 |
| `renderUI()` | fetchStatus 后 | — | 刷新余额、按钮状态、取消键显隐 |
| `showPage(id)` | 视图切换 | — | 显示目标视图，隐藏其他 |

### 模板代码

```javascript
// ===== 初始化 =====
setInterval(fetchStatus, 1000);
fetchStatus();

// ===== 1. 轮询状态 =====
async function fetchStatus() {
    const res = await fetch(`${API_BASE}/api/status`);
    state = await res.json();
    renderUI();
}

// ===== 2. 投币 =====
async function onCoinClick() {
    const res = await fetch(`${API_BASE}/api/coin`, { method: 'POST' });
    const data = await res.json();
    state.balance = data.balance;
    renderUI();
}

// ===== 3. 选择商品 =====
async function onBuyClick(channelId) {
    const res = await fetch(`${API_BASE}/api/select/${channelId}`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
        // 记录选中商品，弹出确认页
        selected = data;
        showPage('page-confirm');
    } else {
        alert(data.msg);
    }
}

// ===== 4. 确认购买 =====
async function onConfirmClick() {
    const res = await fetch(`${API_BASE}/api/confirm`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
        showPage('page-result');
        // 显示 ✅ + 出货动画
    } else {
        alert(data.msg);
    }
}

// ===== 5. 取消 =====
async function onCancelClick() {
    await fetch(`${API_BASE}/api/cancel`, { method: 'POST' });
    showPage('page-main');
    fetchStatus();
}

// ===== 6. UI 渲染 =====
function renderUI() {
    document.getElementById('balance').textContent = state.balance;

    // 取消按钮显隐
    document.getElementById('btn-cancel').style.display =
        state.balance > 0 ? 'block' : 'none';

    // 渲染商品卡片
    const container = document.getElementById('product-list');
    container.innerHTML = '';
    state.channels.forEach(ch => {
        const btnDisabled = !ch.available || state.balance < ch.price;
        const btnText = !ch.available ? '缺货'
                      : state.balance < ch.price ? '余额不足'
                      : '购买';
        container.innerHTML += `
            <div class="card">
              <span>${ch.name}</span>
              <span>¥${ch.price}</span>
              <span>库存: ${ch.stock}</span>
              <button ${btnDisabled ? 'disabled' : ''}
                      onclick="onBuyClick(${ch.id})">${btnText}</button>
            </div>`;
    });
}

// ===== 7. 视图切换 =====
function showPage(pageId) {
    ['page-main', 'page-confirm', 'page-result'].forEach(id => {
        document.getElementById(id).style.display =
            id === pageId ? 'block' : 'none';
    });
}
```

---

## style.css 要求

| 规则 | 值 |
|------|-----|
| 移动端自适应 | `max-width: 480px`, 居中 |
| 背景色 | `#1a1a2e`（暗色主题） |
| 商品卡片 | 白色背景, `border-radius: 12px`, 阴影 |
| 投币按钮 | 大尺寸, 绿色背景 `#4caf50` |
| 购买按钮(可用) | 蓝色背景 `#2196f3` |
| 按钮(禁用) | 灰色背景, 显示"缺货"/"余额不足" |
| 取消按钮 | 红色背景, 余额>0时显示 |
| 余额 | 大字号, 顶部显眼 |
| 出货进度条 | `@keyframes progress` 动画 2s |
| 结果图标 | ✅ = `color: #4caf50`, ❌ = `color: #f44336` |

---

## 开发顺序

1. HTML 结构 + CSS 样式
2. 用 mock 数据调通 UI 渲染（取消 `useMockData()` 注释）
3. 接入真实 API（连 C 的 Flask 开发服务器）
4. 调试全流程交互体验

## Mock 数据（开发用）

```javascript
// script.js 开头 — 取消注释即可脱离后端跑 UI
function useMockData() {
    state = {
        state: 0, state_name: "IDLE", balance: 3, selected_channel: null,
        channels: [
            {id: 0, name: "成人口罩", price: 2.0, stock: 5, available: true},
            {id: 1, name: "儿童口罩", price: 2.0, stock: 0, available: false},
            {id: 2, name: "N95口罩", price: 5.0, stock: 3, available: true},
        ]
    };
    renderUI();
}
// useMockData();
```

## 依赖关系

- 只依赖 C 的 7 个 API 端点（接口已定，mock 可独立开发）
