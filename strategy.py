from typing import TYPE_CHECKING

from vnpy.trader.object import TickData

from template import StrategyTemplate

if TYPE_CHECKING:       # 只在编辑代码时导入
    from engine import StrategyEngine


class SimpleStrategy(StrategyTemplate):
    """简单策略"""

    def __init__(self, strategy_engine: "StrategyEngine", vt_symbol: str) -> None:
        """"""
        super().__init__(strategy_engine, vt_symbol)

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
