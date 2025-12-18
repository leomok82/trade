import numpy as np
from collections import defaultdict
from enum import Enum

class TrendDirection(Enum):
    DOWN = "down"
    FLAT = "flat"
    UP = "up"

class TrendDetector:
    """
    Trend detector using:
    1) Linear regression slope (price level)
    2) Time-series momentum (sum/mean of returns over lookback)
    3) Autocorrelation (returns autocorr, lag-1 by default)
    """

    def __init__(
        self,
        lookback: int = 60,             
        slope_threshold: float = 0.001,     # normalized slope threshold
        mom_threshold: float = 0.0,          # require > 0 by default (or set small >0)
        ac_lag: int = 10,                     # lag for autocorr
        ac_threshold: float = 0.10,          # autocorr strength threshold
    ):
        self.slope_threshold = slope_threshold

        self.mom_threshold = mom_threshold

        self.lookback = lookback
        self.ac_lag = ac_lag
        self.ac_threshold = ac_threshold

        self.min_bars = lookback

        self.current_trend = defaultdict(lambda: TrendDirection.FLAT)
        self.trend_strength = defaultdict(float)

        # optional: store raw stats for debugging
        self.last_lr_slope = defaultdict(float)
        self.last_mom = defaultdict(float)
        self.last_ac = defaultdict(float)

    def calculate(self, symbol: str, price_history: list) -> TrendDirection:
        if len(price_history) < self.min_bars:
            self.current_trend[symbol] = TrendDirection.FLAT
            self.trend_strength[symbol] = 0.0
            return TrendDirection.FLAT

        prices = np.asarray(price_history, dtype=np.float64)
        if np.any(prices <= 0):
            # if your asset can be <=0 (rare), switch to simple returns
            returns = np.diff(prices) / np.maximum(prices[:-1], 1e-12)
        else:
            returns = np.diff(np.log(prices))

        # 1) Linear regression slope (existing idea)
        trend_lr, lr_strength = self._detect_lr_trend(prices)

        # 2) Time-series momentum (TSMOM)
        trend_mom, mom_strength = self._detect_tsmom_trend(returns)

        # 3) Autocorrelation (returns)
        trend_ac, ac_strength = self._detect_autocorr_trend(returns)
    
        score = 0.0

        score += self._dir_to_score(trend_lr) * 1.0
        score += self._dir_to_score(trend_mom) * 1.0

        # Autocorr: if positive and strong -> reinforces direction; if negative -> pushes toward FLAT (mean reversion regime)
        if trend_ac == TrendDirection.UP:
            score *= 1.25
        elif trend_ac == TrendDirection.DOWN:
            score *= 0.60

        # Final classification
        if score >= 1.0:
            trend = TrendDirection.UP
        elif score <= -1.0:
            trend = TrendDirection.DOWN
        else:
            trend = TrendDirection.FLAT

        # Strength: combine magnitudes (clipped to 0..1)
        # interpret as "confidence" not probability
        raw_strength = 0.45 * lr_strength + 0.45 * mom_strength + 0.10 * ac_strength
        strength = float(np.clip(raw_strength, 0.0, 1.0))

        self.current_trend[symbol] = trend
        self.trend_strength[symbol] = strength
        return trend

    def _dir_to_score(self, d: TrendDirection) -> float:
        if d == TrendDirection.UP:
            return 1.0
        if d == TrendDirection.DOWN:
            return -1.0
        return 0.0

    # -------- 1) Linear regression slope --------
    def _detect_lr_trend(self, prices: np.ndarray):
        lb = min(self.lookback, len(prices))
        y = prices[-lb:]
        x = np.arange(lb, dtype=np.float64)

        slope, intercept = np.polyfit(x, y, 1)
        avg_price = float(np.mean(y))
        norm_slope = float(slope / avg_price) if avg_price > 0 else 0.0

        self.last_lr_slope["_"] = norm_slope  # optional; overwritten if you keep symbol here

        if norm_slope > self.slope_threshold:
            direction = TrendDirection.UP
        elif norm_slope < -self.slope_threshold:
            direction = TrendDirection.DOWN
        else:
            direction = TrendDirection.FLAT

        # strength: scale slope relative to threshold
        strength = abs(norm_slope) / (abs(self.slope_threshold) + 1e-12)
        strength = float(np.clip(strength, 0.0, 1.0))
        return direction, strength

    # -------- 2) Time-series momentum --------
    def _detect_tsmom_trend(self, returns: np.ndarray):
        # returns length is len(prices)-1
        lb = min(self.lookback, len(returns))
        if lb < 5:
            return TrendDirection.FLAT, 0.0

        r = returns[-lb:]
        mom = float(np.mean(r))  # could also use sum(r) or cumulative return

        # normalize by return volatility to get a z-ish score
        vol = float(np.std(r, ddof=1)) if lb > 2 else 0.0
        mom_z = mom / (vol + 1e-12)

        # direction decision
        if mom > self.mom_threshold:
            direction = TrendDirection.UP
        elif mom < -self.mom_threshold:
            direction = TrendDirection.DOWN
        else:
            direction = TrendDirection.FLAT

        strength = float(np.tanh(abs(mom_z) / 2.0))  #
        return direction, strength

    # -------- 3) Autocorrelation --------
    def _detect_autocorr_trend(self, returns: np.ndarray):
        lb = min(self.lookback, len(returns))
        lag = self.ac_lag

        if lb <= lag + 5:
            return TrendDirection.FLAT, 0.0

        r = returns[-lb:]
        r0 = r[:-lag]
        r1 = r[lag:]

        # Pearson correlation
        r0c = r0 - np.mean(r0)
        r1c = r1 - np.mean(r1)
        denom = (np.sqrt(np.sum(r0c**2)) * np.sqrt(np.sum(r1c**2)) + 1e-12)
        ac = float(np.sum(r0c * r1c) / denom)

        # Interpret:
        # + autocorr -> trend-friendly
        # - autocorr -> mean-reverting
        if ac > self.ac_threshold:
            direction = TrendDirection.UP        # "trend regime"
        elif ac < -self.ac_threshold:
            direction = TrendDirection.DOWN      # "mean reversion regime"
        else:
            direction = TrendDirection.FLAT

        strength = float(np.clip(abs(ac) / (abs(self.ac_threshold) + 1e-12), 0.0, 1.0))
        return direction, strength

    # ------- getters -------
    def get_trend(self, symbol: str) -> TrendDirection:
        return self.current_trend[symbol]

    def get_trend_strength(self, symbol: str) -> float:
        return self.trend_strength[symbol]

    def get_trend_stats(self, symbol: str) -> dict:
        return {
            "trend": self.current_trend[symbol].value,
            "strength": self.trend_strength[symbol],
        }
