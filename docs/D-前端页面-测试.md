# Person D — 前端页面测试

## 自测方法（mock 数据）

在 `script.js` 开头加入以下 mock，可脱离后端独立测试 UI：

```javascript
// script.js (开发阶段)
// 当后端未就绪时，用以下 mock 数据调试 UI

function useMockData() {
    const mockState = {
        state: 0,
        state_name: "IDLE",
        balance: 3,
        selected_channel: null,
        channels: [
            {id: 0, name: "成人口罩", price: 2.0, stock: 5, available: true},
            {id: 1, name: "儿童口罩", price: 2.0, stock: 0, available: false},
            {id: 2, name: "N95口罩", price: 5.0, stock: 3, available: true},
        ]
    };

    // 用 mockState 渲染页面
    state = mockState;
    renderUI();
}

// 开发时取消注释即可脱离后端跑 UI
// useMockData();
```

## 测试 checklist（浏览器开发者工具验证）

```
打开浏览器控制台 (F12)：

1. 布局测试:
   □ iPhone SE 375×667  → 卡片3列变1列，可滚动
   □ iPhone 12 390×844  → 布局正常
   □ iPad 768×1024      → 卡片居中，留白合适

2. 元素检查:
   □ 余额显示在顶部，数字随 state.balance 变化
   □ 投币按钮绿色醒目，可点击
   □ 商品卡片：名称/价格/库存/购买按钮完整
   □ 库存=0时卡片 gray out + "缺货"文字
   □ 取消按钮默认隐藏，有余额后显示

3. 交互测试（手动修改 state 后调 renderUI()）:
   // 在控制台中执行:
   state.balance = 0; renderUI();
     □ "购买"按钮文字"余额不足"，灰色不可点
   state.balance = 3; renderUI();
     □ "购买"按钮蓝色可点
   state.channels[0].stock = 0; renderUI();
     □ 成人口罩卡片显示"缺货"，灰色不可点

4. 弹窗测试:
   // 控制台执行:
   $('#confirm-name').textContent = '成人口罩';
   $('#confirm-price').textContent = '2.0';
   $('#confirm-balance').textContent = '3.0';
   showPage('page-confirm');
     □ 遮罩层出现，信息正确
     □ 确认/取消按钮可点击

5. 动画测试:
   // 控制台执行:
   showPage('page-result');
   $('#result-icon').textContent = '✅';
   $('#result-message').textContent = '购买成功！请取走口罩';
     □ ✅ 图标显示
     □ 进度条动画 2 秒播放
     □ 3秒后自动返回主界面
```

## 测试表单

| # | 测试项 | 操作方式 | 预期 | 结果 |
|---|-------|---------|------|------|
| 1 | 移动端布局 | F12 切 iPhone SE 尺寸 | 卡片单列，可上下滑 | □ |
| 2 | 商品卡片 | 直接打开页面 | 3个卡片显示名称/价格/库存 | □ |
| 3 | 余额显示 | mock: balance=3 → renderUI | 顶部显示 ¥3 | □ |
| 4 | 缺货状态 | mock: stock=0 → renderUI | 卡片灰色 + "缺货" | □ |
| 5 | 余额不足 | mock: 余额<价格 → renderUI | 按钮灰色 + "余额不足" | □ |
| 6 | 余额充足 | mock: 余额≥价格 → renderUI | 按钮蓝色可点 | □ |
| 7 | 确认弹窗 | mock: showPage('page-confirm') | 遮罩层 + 商品信息正确 | □ |
| 8 | 出货动画 | mock: showPage('page-result') ✅ | 进度条动画 2 秒 | □ |
| 9 | 失败结果 | mock: 显示 ❌ + 原因 | 错误图标 + 提示文字 | □ |
| 10 | 返回主界面 | 结果页等待 3 秒 | 自动回到主界面 | □ |
