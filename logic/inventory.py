# logic/inventory.py
import json
import os
from datetime import datetime
from pathlib import Path

from config import CHANNEL_CONFIG

class Inventory:
    """
    贩卖机库存管理，包含货道信息和交易记录。
    数据存储在 JSON 文件中。
    """
    def __init__(self, data_path: str = "data/inventory.json"):
        self.data_path = data_path
        self.channels = []
        self.transactions = []
        # 如果文件存在则加载，否则创建默认库存
        if os.path.exists(self.data_path):
            self.load()
        else:
            self._create_default()

    def _create_default(self):
        """创建默认库存结构（基于 config.py 中的 CHANNEL_CONFIG）"""
        self.channels = []
        for ch in CHANNEL_CONFIG:
            self.channels.append({
                "id": ch["id"],
                "name": ch["name"],
                "price": ch["price"],
                "stock": ch["init_stock"]
            })
        self.transactions = []
        self.save()

    def load(self) -> None:
        """从 JSON 文件加载数据到内存"""
        with open(self.data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.channels = data["channels"]
        self.transactions = data.get("transactions", [])

    def save(self) -> None:
        """将内存数据写入 JSON 文件"""
        # 确保目录存在
        dir_path = os.path.dirname(self.data_path)
        if dir_path:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump({
                "channels": self.channels,
                "transactions": self.transactions
            }, f, ensure_ascii=False, indent=4)

    def deduct(self, channel: int) -> bool:
        """
        扣减指定货道的库存。
        返回 True 表示成功，False 表示库存不足或货道不存在。
        """
        for ch in self.channels:
            if ch["id"] == channel:
                if ch["stock"] > 0:
                    ch["stock"] -= 1
                    return True
                else:
                    return False
        return False   # 货道不存在

    def get_status(self) -> list:
        """
        返回所有货道信息，附加 available 字段。
        available 表示库存大于0。
        """
        status = []
        for ch in self.channels:
            status.append({
                "id": ch["id"],
                "name": ch["name"],
                "price": ch["price"],
                "stock": ch["stock"],
                "available": ch["stock"] > 0
            })
        return status

    def add_transaction(self, ch: int, amount: float, status: str) -> dict:
        """
        记录一笔交易。
        ch: 货道ID
        amount: 交易金额
        status: 交易状态（如 "success"）
        返回记录对象。
        """
        # 查找货道名称
        name = "未知"
        for c in self.channels:
            if c["id"] == ch:
                name = c["name"]
                break
        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "item": name,
            "amount": amount,
            "status": status
        }
        self.transactions.append(record)
        return record

    def get_transactions(self, limit: int = 50) -> list:
        """
        返回最近的 limit 条交易记录。
        """
        return self.transactions[-limit:]