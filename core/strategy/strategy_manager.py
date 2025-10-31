import backtrader as bt


class StrategyManager:

    def __init__(self):
        self.strategy_list = []

    def register_strategy(self, strategy: bt.Strategy):
        self.strategy_list.append(strategy)

    def get_strategy(self, strategy_class: bt.Strategy):
        for strategy in self.strategy_list:
            if strategy.__class__ == strategy_class:
                return strategy
        return None

if __name__ == '__main__':
    pass