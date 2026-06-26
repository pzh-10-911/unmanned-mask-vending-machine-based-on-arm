# logic/state_machine.py
from .inventory import Inventory

# 状态常量
IDLE = 0
SELECTED = 1
DISPENSE = 2

class StateMachine:
    """
    贩卖机状态机 — 管理交易全生命周期。
    """
    def __init__(self, inventory: Inventory):
        """
        初始化状态机。
        - state = IDLE
        - balance = 0
        - selected_channel = None
        - 接收 Inventory 实例用于库存检查
        """
        self.inventory = inventory
        self.state = IDLE
        self.balance = 0
        self.selected_channel = None

    def cancel_select(self) -> dict:
        """
        取消当前选择（仅在 SELECTED 状态下有效）。
        不改变余额，将状态重置为 IDLE，selected_channel 清空。
        返回: {"success": True, "msg": "已取消选择"}
        """
        if self.state != SELECTED:
            return {"success": False, "msg": "当前状态不允许取消选择"}
        self.state = IDLE
        self.selected_channel = None
        return {"success": True, "msg": "已取消选择"}
    
    def add_coin(self) -> int:
        """
        投币操作。
        在任何状态下都可调用，balance += 1
        返回: 当前余额 balance (int)
        """
        self.balance += 1
        return self.balance

    def select(self, channel: int) -> dict:
        """
        选择口罩品类。
        要求: state 必须为 IDLE
        检查: balance < price → {"success": False, "msg": "余额不足"}
              stock <= 0    → {"success": False, "msg": "库存不足"}
        通过 → state → SELECTED, selected_channel = channel
        返回: {"success": True, "channel": channel, "price": price, "name": name}
        """
        if self.state != IDLE:
            return {"success": False, "msg": "状态错误"}

        # 查找货道
        channels = self.inventory.get_status()
        selected = None
        for ch in channels:
            if ch["id"] == channel:
                selected = ch
                break
        if selected is None:
            return {"success": False, "msg": "无效货道"}

        # 检查余额
        if self.balance < selected["price"]:
            return {"success": False, "msg": "余额不足"}

        # 检查库存
        if selected["stock"] <= 0:
            return {"success": False, "msg": "库存不足"}

        # 状态迁移
        self.state = SELECTED
        self.selected_channel = channel
        return {
            "success": True,
            "channel": channel,
            "price": selected["price"],
            "name": selected["name"]
        }

    def confirm(self, on_dispense: callable) -> dict:
        """
        确认购买。
        要求: state 必须为 SELECTED，balance >= price，stock > 0
        流程:
        1. balance -= price
        2. state = DISPENSE
        3. 执行回调 dispense_callback(selected_channel)
        4. 返回 {"success": True, "msg": "出货中，请取货", "channel": channel}
        """
        if self.state != SELECTED:
            return {"success": False, "msg": "状态错误"}

        # 再次检查余额和库存（防止期间发生变化）
        channels = self.inventory.get_status()
        selected = None
        for ch in channels:
            if ch["id"] == self.selected_channel:
                selected = ch
                break
        if selected is None:
            self.state = IDLE
            self.selected_channel = None
            return {"success": False, "msg": "系统错误"}

        if self.balance < selected["price"]:
            return {"success": False, "msg": "余额不足"}

        if selected["stock"] <= 0:
            # 库存不足时回退状态
            self.state = IDLE
            self.selected_channel = None
            return {"success": False, "msg": "库存不足"}

        # 扣款
        self.balance -= selected["price"]
        self.state = DISPENSE

        # 执行出货回调
        try:
            on_dispense(self.selected_channel)
        except Exception:
            # 回调异常处理，但不应影响状态机状态
            pass

        return {
            "success": True,
            "msg": "出货中，请取货",
            "channel": self.selected_channel,
            "balance": self.balance
        }

    def cancel(self) -> dict:
        """
        取消交易/退币。
        允许在 IDLE、SELECTED、DISPENSE 任意状态下调用。
        流程: balance = 0, state = IDLE, selected_channel = None
        返回: {"success": True, "balance": 0}
        """
        self.balance = 0
        self.state = IDLE
        self.selected_channel = None
        return {"success": True, "balance": 0}

    def complete(self) -> dict:
        """
        取货完成（由 Person C 在红外检测到后调用）。
        要求: state 为 DISPENSE
        流程: 扣库存 → 记日志 → state = IDLE
        返回: {"success": True, "msg": "购买完成", "transaction_id": str}
        """
        if self.state != DISPENSE:
            return {"success": False, "msg": "状态错误"}

        channel = self.selected_channel
        # 查找价格和名称
        channels = self.inventory.get_status()
        price = 0
        for ch in channels:
            if ch["id"] == channel:
                price = ch["price"]
                break

        # 扣库存
        if not self.inventory.deduct(channel):
            # 理论上这里不应该失败，因为之前已经检查过库存
            # 但为了防止并发或文件错误，返回错误
            self.state = IDLE
            self.selected_channel = None
            return {"success": False, "msg": "扣库存失败"}

        # 记录交易
        transaction = self.inventory.add_transaction(channel, price, "success")

        # 持久化
        self.inventory.save()

        # 状态机恢复 IDLE
        self.state = IDLE
        self.selected_channel = None

        return {
            "success": True,
            "msg": "购买完成",
            "transaction_id": transaction["time"]  # 使用时间戳作为简单ID
        }

    def get_state(self) -> dict:
        """
        获取完整状态。
        返回:
        {
            "state": self.state,
            "state_name": "IDLE",
            "balance": self.balance,
            "selected_channel": self.selected_channel,
            "channels": [...]
        }
        """
        state_names = {IDLE: "IDLE", SELECTED: "SELECTED", DISPENSE: "DISPENSE"}
        return {
            "state": self.state,
            "state_name": state_names.get(self.state, "UNKNOWN"),
            "balance": self.balance,
            "selected_channel": self.selected_channel,
            "channels": self.inventory.get_status()
        }
