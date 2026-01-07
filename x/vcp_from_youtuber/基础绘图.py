prices_of_stocks = ffn.get('fb,aapl,amzn,nflx,goog', start='2015-10-10')

prices_of_stocks.rebase().plot()

stats = prices_of_stocks.calc_stats()
stats.display()

stats.plot_drawdown()

returns = prices_of_stocks.to_returns().dropna()

returns.plot_corr_heatmap()