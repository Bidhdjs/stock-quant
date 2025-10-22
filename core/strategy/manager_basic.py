from datetime import datetime


class Strategy:
    def __init__(self, strategy_name: str, strategy_body: str):
        self.strategy_name = strategy_name
        self.strategy_body = strategy_body
        self.version = '1'

class StrategyManager:
    def __init__(self, strategy: Strategy):
        self.strategy = strategy
        self.create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update_time = None

    def update(self):
        self.update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == '__main__':
    manage_basic = StrategyManager(Strategy("test-name", "test-body"))
