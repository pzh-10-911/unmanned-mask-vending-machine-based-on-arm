# Person C — Flask API 集成测试

## 测试代码

保存为 `test_api.py`。**前提：** app.py 已在本地启动（Windows 上 mock GPIO）。

```bash
# 终端1: 启动服务器
python app.py

# 终端2: 运行测试
python test_api.py
```

```python
# test_api.py
# Person C 测试所有 API 端点
# 运行前提: app.py 已在本地启动（Windows 上 mock GPIO）

import requests
import json
import time

BASE = "http://localhost:5000"

def test_homepage():
    """主页返回 HTML"""
    r = requests.get(f"{BASE}/")
    assert r.status_code == 200
    assert "text/html" in r.headers["Content-Type"]
    print("[PASS] GET / → 200, HTML")

def test_api_status():
    """状态接口返回完整信息"""
    r = requests.get(f"{BASE}/api/status")
    assert r.status_code == 200
    data = r.json()
    assert "state" in data
    assert "balance" in data
    assert "channels" in data
    assert len(data["channels"]) == 3
    print("[PASS] GET /api/status → 完整状态对象")

def test_coin():
    """投币接口"""
    r = requests.post(f"{BASE}/api/coin")
    assert r.status_code == 200
    data = r.json()
    assert "balance" in data
    print(f"[PASS] POST /api/coin → balance={data['balance']}")

def test_select():
    """选择商品"""
    # 先确保有余额
    requests.post(f"{BASE}/api/coin")
    requests.post(f"{BASE}/api/coin")

    r = requests.post(f"{BASE}/api/select/0")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] == True
    print(f"[PASS] POST /api/select/0 → 选择成功")

def test_select_insufficient():
    """余额不足选商品"""
    # 先取消回到 IDLE
    requests.post(f"{BASE}/api/cancel")

    # 余额不足
    requests.post(f"{BASE}/api/coin")  # balance=1
    r = requests.post(f"{BASE}/api/select/0")  # need ¥2
    data = r.json()
    assert data["success"] == False
    assert "余额不足" in data["msg"]
    print(f"[PASS] POST /api/select/0 余额不足 → 拒绝")

def test_confirm():
    """确认购买"""
    # 准备: 投币3元 → 选择
    requests.post(f"{BASE}/api/cancel")
    for _ in range(3):
        requests.post(f"{BASE}/api/coin")
    requests.post(f"{BASE}/api/select/0")

    r = requests.post(f"{BASE}/api/confirm")
    data = r.json()
    assert data["success"] == True
    print(f"[PASS] POST /api/confirm → 出货中")

def test_cancel():
    """取消交易"""
    # 准备: 投币 → 选择
    requests.post(f"{BASE}/api/cancel")
    for _ in range(3):
        requests.post(f"{BASE}/api/coin")
    requests.post(f"{BASE}/api/select/0")

    r = requests.post(f"{BASE}/api/cancel")
    data = r.json()
    assert data["success"] == True
    assert data["balance"] == 0
    print(f"[PASS] POST /api/cancel → 余额归零")

def test_complete_flow():
    """完整购买流程"""
    # 重置
    requests.post(f"{BASE}/api/reset") if has_reset() else None

    # 投币 → 选择 → 确认 → 完成
    for _ in range(3):
        requests.post(f"{BASE}/api/coin")
    requests.post(f"{BASE}/api/select/0")
    requests.post(f"{BASE}/api/confirm")

    # 等待红外检测（测试时直接检查状态变化）
    time.sleep(2)
    r = requests.get(f"{BASE}/api/status")
    data = r.json()
    print(f"[INFO] 购买后状态: {data['state_name']}, 余额: {data['balance']}")

def test_logs():
    """交易记录"""
    r = requests.get(f"{BASE}/api/logs")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    print(f"[PASS] GET /api/logs → {len(data)} 条记录")

def has_reset():
    """检查是否有 reset API"""
    try:
        r = requests.post(f"{BASE}/api/reset")
        return r.status_code == 200
    except:
        return False

if __name__ == '__main__':
    print("测试 API (确保 app.py 已在 localhost:5000 运行)")
    print("-" * 40)

    try:
        test_homepage()
        test_api_status()
        test_coin()
        test_select()
        test_select_insufficient()
        test_cancel()
        test_confirm()
        test_logs()
        print("\n✅ All API tests passed!")
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到 localhost:5000，请先启动 app.py")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
```

## 测试表单

| # | 测试项 | 操作 | 预期 | 结果 | 备注 |
|---|-------|------|------|------|------|
| 1 | 主页 | `GET /` | 200 + text/html | □ | |
| 2 | 状态接口 | `GET /api/status` | 含 state, balance, channels 字段 | □ | |
| 3 | 投币 | `POST /api/coin` | balance +1 | □ | 连续3次 |
| 4 | 选择(有余额) | 投币后 `POST /api/select/0` | success: true | □ | |
| 5 | 选择(余额不足) | balance<price 时 select | success: false + msg | □ | |
| 6 | 确认购买 | 余额充足 select 后 confirm | success: true + "出货中" | □ | |
| 7 | 取消交易 | select 后 `POST /api/cancel` | balance=0, state=IDLE | □ | |
| 8 | 交易记录 | `GET /api/logs` | 返回数组 | □ | |
| 9 | 完整流程 | 投币→选品→确认→检测→完成 | 状态流转正确 | □ | |
| 10 | 非法参数 | select 不存在的 channel_id | 拒绝请求 | □ | |
