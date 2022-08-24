from pathlib import Path

from vnpy.trader.app import BaseApp

from .engine import StrategyEngine


__version__ = "0.0.1"


class SimpleStrategyApp(BaseApp):
    """"""

    app_name: str = "SimpleStrategy"
    app_module: str = __module__
    app_path: Path = Path(__file__).parent
    display_name: str = "简单策略"
    engine_class: StrategyEngine = StrategyEngine
    widget_name: str = "SimpleWidget"
    icon_name: str = str(app_path.joinpath("simple.ico"))