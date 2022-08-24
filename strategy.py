from typing import TYPE_CHECKING

from vnpy.trader.object import TickData
from vnpy.trader.constant import Direction, Offset

if TYPE_CHECKING:       # 只在编辑代码时导入
    from engine import StrategyEngine


class SimpleStrategy:
    """简单策略"""

    def __init__(self, strategy_engine: "StrategyEngine", vt_symbol: str) -> None:
        """"""
        self.strategy_engine: "StrategyEngine" = strategy_engine
        self.trading_symbol: str = vt_symbol

        self.tick_history: list[TickData] = []
        self.trading_target: int = 0

    def on_tick(self, tick: TickData) -> None:
        """行情推送"""
        # 检查至少要3个Tick
        history = self.tick_history
        if len(history) < 3:
            return

        # 提取行情和合约
        tick1 = history[-1]
        tick2 = history[-2]
        tick3 = history[-3]

        # 多头检查
        if tick1.last_price > tick2.last_price > tick3.last_price:
            if not self.trading_targets:
                self.buy(tick1.last_price + 10, 1)
                self.trading_target = 1
                self.write_log(f"{self.vt_symbol}买入开仓1手 {tick1.datetime}")

        # 空头检查
        if tick1.last_price < tick2.last_price < tick3.last_price:
            if self.trading_target > 0:
                self.sell(tick1.last_price - 10, 1)
                self.trading_target = 0
                self.write_log(f"{self.vt_symbol}卖出平仓1手 {tick1.datetime}")

        # 推送事件
        data = {
            "vt_symbol": self.vt_symbol,
            "datetime": tick1.datetime,
            "last_price": tick1.last_price,
            "trading_target": self.trading_target
        }
        self.put_event(data)

    def buy(self, price: float, volume: int) -> None:
        """买入开仓"""
        self.strategy_engine.send_order(
            self.trading_symbol,
            price,
            volume,
            Direction.LONG,
            Offset.OPEN
        )

    def sell(self, price: float, volume: int) -> None:
        """卖出平仓"""
        self.strategy_engine.send_order(
            self.trading_symbol,
            price,
            volume,
            Direction.SHORT,
            Offset.CLOSE
        )

    def write_log(self, msg: str) -> None:
        """输出日志"""
        self.strategy_engine.write_log(msg)

    def put_event(self, data: dict) -> None:
        """推送事件"""
        self.strategy_engine.put_event(data)
