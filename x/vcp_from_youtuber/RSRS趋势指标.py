class RSRS_Indicator:
    def __init__(self, N=18, M=600, threshold_buy=0.7, threshold_sell=-0.7):
        """
        初始化RSRS指标计算器。

        参数:
            N (int): 线性回归计算窗口 (默认18)
            M (int): Z-Score标准化窗口 (默认600)
            threshold_buy (float): 买入阈值 (默认0.7)
            threshold_sell (float): 卖出阈值 (默认-0.7)
        """
        self.N = N
        self.M = M
        self.threshold_buy = threshold_buy
        self.threshold_sell = threshold_sell

    def calculate(self, df):
        """
        核心计算函数。

        参数:
            df (pd.DataFrame): 必须包含 'High', 'Low', 'Close' 列

        返回:
            pd.DataFrame: 包含所有RSRS中间变量和信号的DataFrame
        """
        # 数据完整性检查
        required_cols = ['High', 'Low', 'Close']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"DataFrame必须包含列: {required_cols}")

        df = df.copy()

        # 1. 计算基础斜率 Beta 和 R2 (使用向量化方法)
        beta, r2 = self._calculate_beta_r2_vectorized(df['High'].values, df['Low'].values, self.N)
        df = beta
        df = r2

        # 2. 计算标准化分 Z-Score
        # 注意：前M个数据将为NaN，因为需要足够的历史数据来计算均值和标准差
        df = df.rolling(window=self.M).mean()
        df = df.rolling(window=self.M).std()
        df = (df - df) / df

        # 3. 计算修正指标 (右偏修正)
        # RSRS_RightSkew = Zscore * Beta * R2 (一种常见的组合变体)
        # 这里演示标准修正：Zscore * R2
        df = df * df

        # 4. 生成交易信号 (基于基础Z-Score)
        # 1 = 买入/持有, 0 = 空仓/卖出
        df = 0

        # 逻辑：
        # 如果 Zscore > Buy_Threshold -> 持有 (1)
        # 如果 Zscore < Sell_Threshold -> 空仓 (0)
        # 中间区域 -> 维持前一状态

        signal = np.zeros(len(df))
        current_position = 0

        z_scores = df.values

        for i in range(self.M, len(df)):
            z = z_scores[i]

            if np.isnan(z):
                continue

            if z > self.threshold_buy:
                current_position = 1
            elif z < self.threshold_sell:
                current_position = 0

            signal[i] = current_position

        df['Position'] = signal

        return df

    def _calculate_beta_r2_vectorized(self, high, low, N):
        """内部私有方法：向量化计算"""
        # 预分配内存
        size = len(high)
        beta = np.full(size, np.nan)
        r2 = np.full(size, np.nan)

        if size < N:
            return beta, r2

        # 构造strides
        strides_low = low.strides + (low.strides[-1],)
        strides_high = high.strides + (high.strides[-1],)

        low_wins = np.lib.stride_tricks.as_strided(
            low, shape=(size - N + 1, N), strides=strides_low
        )
        high_wins = np.lib.stride_tricks.as_strided(
            high, shape=(size - N + 1, N), strides=strides_high
        )

        # 计算统计量
        mean_low = np.mean(low_wins, axis=1, keepdims=True)
        mean_high = np.mean(high_wins, axis=1, keepdims=True)

        low_diff = low_wins - mean_low
        high_diff = high_wins - mean_high

        cov = np.sum(low_diff * high_diff, axis=1)
        var_low = np.sum(low_diff ** 2, axis=1)
        var_high = np.sum(high_diff ** 2, axis=1)

        # 计算Beta
        valid_mask = var_low != 0
        # 临时数组用于存储有效计算结果
        beta_valid = np.divide(cov[valid_mask], var_low[valid_mask])

        # 计算R2
        # Corr = Cov / sqrt(Var_X * Var_Y)
        denom = np.sqrt(var_low * var_high)
        valid_mask_r2 = denom != 0
        corr = np.divide(cov[valid_mask_r2], denom[valid_mask_r2])
        r2_valid = corr ** 2

        # 填充结果
        # 注意切片位置：从第 N-1 个位置开始才有值
        beta[N - 1:][valid_mask] = beta_valid
        r2[N - 1:][valid_mask_r2] = r2_valid

        return beta, r2