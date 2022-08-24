from typing import TYPE_CHECKING

from vnpy.trader.object import TickData, TradeData, OrderData
from vnpy.trader.constant import Direction, Offset

if TYPE_CHECKING:       # 只在编辑代码时导入
    from .engine import StrategyEngine


class StrategyTemplate:
    """策略开发模板"""

    def __init__(
        self,
        strategy_engine: "StrategyEngine",
        vt_symbol: str
    ) -> None:
        """"""
        self.strategy_engine: "StrategyEngine" = strategy_engine
        self.trading_symbol: str = vt_symbol

    def on_tick(self, tick: TickData) -> None:
        """行情推送"""
        pass

    def on_order(self, order: OrderData) -> None:
        """委托推送"""
        pass

    def on_trade(self, trade: TradeData) -> None:
        """成交推送"""
        pass

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

    def short(self, price: float, volume: int) -> None:
        """卖出开仓"""
        self.strategy_engine.send_order(
            self.trading_symbol,
            price,
            volume,
            Direction.SHORT,
            Offset.OPEN
        )

    def cover(self, price: float, volume: int) -> None:
        """买入平仓"""
        self.strategy_engine.send_order(
            self.trading_symbol,
            price,
            volume,
            Direction.LONG,
            Offset.CLOSE
        )

    def write_log(self, msg: str) -> None:
        """输出日志"""
        self.strategy_engine.write_log(msg)

    def put_event(self, data: dict) -> None:
        """推送事件"""
        self.strategy_engine.put_event(data)
