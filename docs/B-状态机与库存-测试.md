# Person B — 状态机与库存测试

## 测试代码

保存为 `test_logic.py`，在**任意机器**上运行（不需要树莓派）：

```bash
python test_logic.py
```

```python
# test_logic.py
# Person B 在任意机器上跑（不需要树莓派）

import os
import json
import tempfile
from logic.inventory import Inventory
from logic.state_machine import StateMachine

def test_inventory():
    """库存管理测试"""
    print("[TEST] Inventory ...")

    # 使用临时文件
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    tmp.write(json.dumps({
        "channels": [
            {"id": 0, "name": "成人口罩", "price": 2.0, "stock": 3},
            {"id": 1, "name": "儿童口罩", "price": 2.0, "stock": 0},
        ],
        "transactions": []
    }))
    tmp.close()

    inv = Inventory(tmp.name)

    # 测试1: 读取库存
    status = inv.get_status()
    assert status[0]["name"] == "成人口罩"
    assert status[0]["stock"] == 3
    assert status[0]["available"] == True
    assert status[1]["available"] == False   # stock=0
    print("  [PASS] 库存读取正确")

    # 测试2: 扣减库存
    assert inv.deduct(0) == True
    assert inv.deduct(0) == True
    assert inv.deduct(0) == True
    assert inv.deduct(0) == False  # 库存不足
    print("  [PASS] 库存扣减+库存不足检测正确")

    # 测试3: 库存扣减后 available 更新
    status = inv.get_status()
    assert status[0]["available"] == False
    print("  [PASS] available 状态正确")

    # 测试4: 交易记录
    tx = inv.add_transaction(0, 2.0, "success")
    assert tx["item"] == "成人口罩"
    assert tx["amount"] == 2.0
    assert len(inv.get_transactions()) == 1
    print("  [PASS] 交易记录正确")

    # 清理
    os.unlink(tmp.name)
    print("  OK")

def test_state_machine():
    """状态机全流程测试"""
    print("\n[TEST] StateMachine ...")

    inv = Inventory("data/inventory.json")
    sm = StateMachine(inv)

    # 初始状态
    s = sm.get_state()
    assert s["state"] == 0        # IDLE
    assert s["balance"] == 0
    assert s["state_name"] == "IDLE"
    print("  [PASS] 初始状态正确")

    # 测试1: 投币
    bal = sm.add_coin()
    bal = sm.add_coin()
    bal = sm.add_coin()
    assert bal == 3
    print("  [PASS] 投币累加正确 (¥3)")

    # 测试2: 选择商品
    result = sm.select(0)   # 成人口罩 ¥2
    assert result["success"] == True
    assert sm.get_state()["state_name"] == "SELECTED"
    print("  [PASS] 选择商品正确")

    # 测试3: 取消交易
    sm.cancel()
    assert sm.get_state()["balance"] == 0
    assert sm.get_state()["state_name"] == "IDLE"
    print("  [PASS] 取消交易正确")

    # 测试4: 余额不足
    sm.add_coin()  # balance = 1
    result = sm.select(0)  # 需要 ¥2
    assert result["success"] == False
    assert result["msg"] == "余额不足"
    print("  [PASS] 余额不足检测正确")

    # 测试5: 库存不足
    sm.add_coin()  # balance = 2
    result = sm.select(1)  # 儿童口罩 stock=0
    assert result["success"] == False
    assert result["msg"] == "库存不足"
    print("  [PASS] 库存不足检测正确")

    # 测试6: 完整购买流程
    sm.add_coin()  # balance = 3
    sm.add_coin()
    assert sm.get_state()["balance"] == 3

    result = sm.select(0)  # 成人口罩 ¥2
    assert result["success"] == True

    dispensed = []
    def fake_dispense(ch):
        dispensed.append(ch)

    result = sm.confirm(on_dispense=fake_dispense)
    assert result["success"] == True
    assert sm.get_state()["state_name"] == "DISPENSE"
    assert sm.get_state()["balance"] == 1  # 3-2=1
    assert dispensed == [0]   # 确认回调被调用
    print("  [PASS] 确认购买后余额扣减正确")

    # 完成取货
    result = sm.complete()
    assert result["success"] == True
    assert sm.get_state()["state_name"] == "IDLE"
    print("  [PASS] 完成取货后状态恢复正确")

    print("  OK")

def test_error_cases():
    """边界情况测试"""
    print("\n[TEST] ErrorCases ...")

    inv = Inventory("data/inventory.json")
    sm = StateMachine(inv)

    # IDLE 状态不能 confirm
    result = sm.confirm(on_dispense=lambda ch: None)
    assert result["success"] == False
    print("  [PASS] IDLE态拒绝 confirm 正确")

    # SELECTED 状态不能 select
    sm.add_coin()
    sm.add_coin()
    sm.select(0)
    result = sm.select(1)
    assert result["success"] == False
    print("  [PASS] SELECTED态拒绝二次 select 正确")

    # DISPENSE 状态不能 select
    sm.confirm(on_dispense=lambda ch: None)
    result = sm.select(0)
    assert result["success"] == False
    print("  [PASS] DISPENSE态拒绝 select 正确")

    # 非法 channel_id
    sm.cancel()
    sm.add_coin()
    sm.add_coin()
    result = sm.select(99)
    assert result["success"] == False
    print("  [PASS] 非法 channel_id 拒绝正确")

    print("  OK")

if __name__ == '__main__':
    test_inventory()
    test_state_machine()
    test_error_cases()
    print("\n✅ All logic tests passed!")
```

## 预期输出

```
[TEST] Inventory ...
  [PASS] 库存读取正确
  [PASS] 库存扣减+库存不足检测正确
  [PASS] available 状态正确
  [PASS] 交易记录正确
  OK

[TEST] StateMachine ...
  [PASS] 初始状态正确
  [PASS] 投币累加正确 (¥3)
  [PASS] 选择商品正确
  [PASS] 取消交易正确
  [PASS] 余额不足检测正确
  [PASS] 库存不足检测正确
  [PASS] 确认购买后余额扣减正确
  [PASS] 完成取货后状态恢复正确
  OK

[TEST] ErrorCases ...
  [PASS] IDLE态拒绝 confirm 正确
  [PASS] SELECTED态拒绝二次 select 正确
  [PASS] DISPENSE态拒绝 select 正确
  [PASS] 非法 channel_id 拒绝正确
  OK

✅ All logic tests passed!
```

## 测试表单

| # | 测试项 | 操作 | 预期 | 结果 | 备注 |
|---|-------|------|------|------|------|
| 1 | 库存读写 | 运行 test_logic.py | [PASS] 库存读取正确 | □ | |
| 2 | 库存扣减 | 同上 | 三次扣减后第四次返回 False | □ | |
| 3 | 交易记录 | 同上 | 记录生成，item/amount 正确 | □ | |
| 4 | 初始状态 | 同上 | state=IDLE, balance=0 | □ | |
| 5 | 投币累加 | 同上 | 3次投币后 balance=3 | □ | |
| 6 | 余额不足 | 同上 | select 返回 success=False | □ | |
| 7 | 库存不足 | 同上 | select 返回 success=False | □ | |
| 8 | 完整购买 | 同上 | IDLE→SELECTED→DISPENSE→IDLE | □ | |
| 9 | 取消交易 | 同上 | balance=0, state=IDLE | □ | |
| 10 | 状态锁 | 同上 | IDLE不确认、SELECTED不再选 | □ | |
