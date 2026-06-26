# 库存与状态机接口文档
---

## 1. `Inventory` 类（库存管理）

```python
class Inventory:
    def __init__(self, filepath: str)
    def get_status(self) -> list[dict]
    def deduct(self, channel_id: int) -> bool
    def add_transaction(self, channel_id: int, amount: float, status: str) -> dict
    def get_transactions(self) -> list[dict]
```

### 方法说明

| 方法               | 参数                                                | 返回值                                                 | 说明                                             |
| ------------------ | --------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------ |
| `__init__`         | `filepath`: JSON文件路径                            | 无                                                     | 从文件加载库存数据（包含channels和transactions） |
| `get_status`       | 无                                                  | 列表，每个元素为 `{id, name, price, stock, available}` | 返回所有货道的当前状态                           |
| `deduct`           | `channel_id`: 货道编号(整数)                        | `True` 成功扣减，`False` 库存不足或货道不存在          | 扣减指定货道库存1件                              |
| `add_transaction`  | `channel_id`, `amount`, `status` ("success"/"fail") | 字典 `{item, amount, status, timestamp}`               | 记录一笔交易                                     |
| `get_transactions` | 无                                                  | 列表，每个元素为交易记录字典                           | 返回所有交易记录                                 |

### 使用示例

```python
inv = Inventory("data/inventory.json")
status = inv.get_status()        # 查看库存
inv.deduct(0)                    # 扣减货道0的库存
tx = inv.add_transaction(0, 2.0, "success")  # 记录成功交易
```

---

## 2. `StateMachine` 类（自动售货机状态机）

```python
class StateMachine:
    def __init__(self, inventory: Inventory)
    def get_state(self) -> dict
    def add_coin(self) -> int
    def select(self, channel_id: int) -> dict
    def confirm(self, on_dispense: callable) -> dict
    def cancel_select(self) -> dict   # 取消选择（保留余额） 
    def cancel(self) -> dict
    def complete(self) -> dict
```

### 状态说明

状态机有3个主要状态：

| 状态名称   | 状态值 | 描述                       |
| ---------- | ------ | -------------------------- |
| `IDLE`     | 0      | 空闲，等待投币             |
| `SELECTED` | 1      | 已选择商品，等待确认或取消 |
| `DISPENSE` | 2      | 确认购买，等待取货         |

### 方法说明

| 方法        | 参数                                      | 返回值                                                       | 说明                                                 |
| ----------- | ----------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------- |
| `__init__`  | `inventory`: Inventory实例                | 无                                                           | 创建状态机，初始状态为IDLE，余额0                    |
| `get_state` | 无                                        | 字典：`{"state": int, "balance": float, "state_name": str, ...}` | 返回当前状态和余额                                   |
| `add_coin`  | 无                                        | `int` 当前余额                                               | 投一枚硬币（金额1），只能在IDLE状态使用              |
| `select`    | `channel_id`: 货道编号                    | 字典：`{"success": True/False, "msg": str}`                  | 选择商品，需在IDLE状态且余额足够、库存充足           |
| `confirm`   | `on_dispense`: 回调函数，参数为channel_id | 字典：`{"success": True/False, "msg": str}`                  | 确认购买，触发出货回调，余额扣减，进入DISPENSE状态   |
|`cancel_select`	|无	| 字典：{"success": True/False, "msg": str}|	取消选择：保留余额，回到IDLE。仅适用于SELECTED状态
| `cancel`    | 无                                        | 字典：`{"success": True/False, "msg": str}`                  | 取消交易，余额退回到0，返回IDLE状态                  |
| `complete`  | 无                                        | 字典：`{"success": True/False, "msg": str}`                  | 取货完成，状态恢复到IDLE（余额不退，可继续投币使用） |

### 使用示例（完整购买流程）

```python
inv = Inventory("data/inventory.json")
sm = StateMachine(inv)

sm.add_coin()          # 投3次，余额=3
sm.add_coin()
sm.add_coin()

result = sm.select(0)  # 选择货道0（成人口罩¥2）
# result: {"success": True, "msg": "选择成功"}

dispensed = []
sm.confirm(on_dispense=lambda ch: dispensed.append(ch))
# 余额变为1，dispensed = [0]，状态变为DISPENSE

sm.complete()          # 取货完成，状态回到IDLE，余额仍为1
```

---

## 3. 错误处理说明

所有 `select`、`confirm`、`cancel`、`complete` 方法在非法状态下调用均会返回 `{"success": False, "msg": "错误原因"}`，不会抛出异常，请调用者检查返回值。

常见错误消息：

- `"余额不足"`
- `"库存不足"`
- `"非法货道"`
- `"当前状态不允许此操作"`

---

## 4. 数据文件格式（示例）

```json
{
  "channels": [
    {"id": 0, "name": "成人口罩", "price": 2.0, "stock": 3},
    {"id": 1, "name": "儿童口罩", "price": 2.0, "stock": 10}
  ],
  "transactions": []
}
```

- `channels` 列表：每个货道包含 `id`, `name`, `price`, `stock`。
- `transactions` 列表：记录历史交易（可由程序自动添加）。
