"""
Streamlit dashboard for the stochastic trade engine.

Wraps equity-curve, vectorized backtest, GBM Monte Carlo, Taylor pricing,
and an optional options scanner — without changing the CLI strategy scripts.
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _secret(name: str) -> str | None:
    """Resolve a credential from Streamlit secrets, then environment."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name) or None


def get_credentials() -> tuple[str | None, str | None]:
    return _secret("ALPACA_API_KEY"), _secret("ALPACA_SECRET_KEY")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_daily_bars(symbol: str, days: int, api_key: str, secret_key: str) -> pd.DataFrame:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    client = StockHistoricalDataClient(api_key, secret_key)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date,
    )
    bars = client.get_stock_bars(request).df
    return bars.xs(symbol, level="symbol")


def run_zscore_equity(
    close: pd.Series, window: int = 15, threshold: float = 1.5
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Mean-reversion equity curves matching plot_equity.py."""
    log_returns = np.log(close / close.shift(1)).fillna(0)
    rolling_mean = log_returns.rolling(window=window).mean()
    rolling_vol = log_returns.rolling(window=window).std()
    z_scores = (log_returns - rolling_mean) / rolling_vol
    positions = pd.Series(
        np.select([z_scores < -threshold, z_scores > threshold], [1, -1], default=0),
        index=close.index,
    )
    strategy_log = positions.shift(1) * log_returns
    strategy_log = strategy_log.fillna(0)
    buy_hold = np.exp(log_returns.cumsum())
    algo = np.exp(strategy_log.cumsum())
    return buy_hold, algo, z_scores


def run_slippage_backtest(
    close: pd.Series,
    volume: pd.Series,
    window: int = 15,
    threshold: float = 1.5,
    starting_capital: float = 100_000.0,
    gamma: float = 0.1,
) -> dict:
    """Vectorized backtest with square-root market impact (backtest.py)."""
    log_returns = np.log(close / close.shift(1)).fillna(0)
    rolling_mean = log_returns.rolling(window=window).mean()
    daily_vol = log_returns.rolling(window=window).std()
    z_scores = (log_returns - rolling_mean) / daily_vol
    positions = pd.Series(
        np.select([z_scores < -threshold, z_scores > threshold], [1, 0], default=0),
        index=close.index,
    )
    target_shares = (positions.shift(1) * starting_capital) / close
    target_shares = target_shares.fillna(0)
    trade_qty = np.abs(target_shares.diff().fillna(0))
    adv = volume.rolling(window=20).mean().replace(0, np.nan)
    slippage_cost = gamma * daily_vol * np.sqrt(trade_qty / adv) * close * trade_qty
    slippage_cost = slippage_cost.fillna(0)
    commission_cost = trade_qty * 0.005
    price_change = close.diff().fillna(0)
    gross_pnl = target_shares.shift(1).fillna(0) * price_change
    net_pnl = gross_pnl - slippage_cost - commission_cost
    equity = starting_capital + net_pnl.cumsum()
    return {
        "equity": equity,
        "gross_final": starting_capital + gross_pnl.cumsum().iloc[-1],
        "net_final": float(equity.iloc[-1]),
        "friction": float(slippage_cost.sum() + commission_cost.sum()),
        "starting": starting_capital,
    }


def run_gbm_monte_carlo(
    close: pd.Series,
    days: int = 30,
    iterations: int = 1000,
    strike: float | None = None,
    risk_free_rate: float = 0.045,
) -> dict:
    """GBM paths + Monte Carlo call fair value (simulate_gbm.py)."""
    log_returns = np.log(close / close.shift(1)).dropna()
    u = log_returns.mean()
    var = log_returns.var()
    drift = u - (0.5 * var)
    stdev = log_returns.std()
    current_price = float(close.iloc[-1])
    if strike is None:
        strike = round(current_price, 2)
    rng = np.random.default_rng(42)
    z = rng.normal(size=(days, iterations))
    daily_step = np.exp(drift + stdev * z)
    price_paths = current_price * np.cumprod(daily_step, axis=0)
    terminal = price_paths[-1]
    time_in_years = days / 252.0
    call_payoffs = np.maximum(terminal - strike, 0)
    fair_value = float(np.mean(call_payoffs) * np.exp(-risk_free_rate * time_in_years))
    return {
        "paths": price_paths,
        "terminal": terminal,
        "current_price": current_price,
        "strike": strike,
        "fair_value": fair_value,
        "drift": float(drift),
        "stdev": float(stdev),
    }


def taylor_demo() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Offline Taylor pricing approximation (taylor_approx.py) — no API required."""

    def true_function(x):
        return np.exp(x)

    def taylor_1st(x, a=0):
        return np.exp(a) + np.exp(a) * (x - a)

    def taylor_2nd(x, a=0):
        return taylor_1st(x, a) + (np.exp(a) / math.factorial(2)) * (x - a) ** 2

    market_moves = np.linspace(-3, 3, 100)
    y_true = true_function(market_moves)
    y_delta = taylor_1st(market_moves)
    y_gamma = taylor_2nd(market_moves)
    err_delta = np.abs(y_true - y_delta)
    err_gamma = np.abs(y_true - y_gamma)
    return market_moves, y_true, y_delta, y_gamma, err_delta, err_gamma


def run_options_scanner(
    symbols: list[str], api_key: str, secret_key: str
) -> tuple[pd.DataFrame, float]:
    """Cheap OTM options scan (scanner.py)."""
    from alpaca.data.historical.option import OptionHistoricalDataClient
    from alpaca.data.historical.stock import StockHistoricalDataClient
    from alpaca.data.requests import OptionChainRequest, StockLatestQuoteRequest

    options_client = OptionHistoricalDataClient(api_key, secret_key)
    stock_client = StockHistoricalDataClient(api_key, secret_key)
    today = datetime.now()
    rows = []

    for symbol in symbols:
        try:
            latest_quote = stock_client.get_stock_latest_quote(
                StockLatestQuoteRequest(symbol_or_symbols=symbol)
            )
            current_price = latest_quote[symbol].ask_price
            chain = options_client.get_option_chain(
                OptionChainRequest(underlying_symbol=symbol)
            )
            valid = []
            for contract_symbol, snapshot in chain.items():
                if not snapshot.latest_quote:
                    continue
                ask_price = snapshot.latest_quote.ask_price
                date_str = contract_symbol[-15:-9]
                expiration_date = datetime.strptime(date_str, "%y%m%d")
                dte = (expiration_date - today).days
                option_type = contract_symbol[-9]
                strike_price = float(contract_symbol[-8:]) / 1000
                is_valid_put = option_type == "P" and (
                    current_price * 0.50 <= strike_price <= current_price * 0.80
                )
                is_valid_call = option_type == "C" and (
                    current_price * 1.20 <= strike_price <= current_price * 1.50
                )
                if (
                    30 <= dte <= 90
                    and 0.00 < ask_price <= 0.05
                    and (is_valid_put or is_valid_call)
                ):
                    valid.append(
                        {
                            "ticker": symbol,
                            "spot": current_price,
                            "contract": contract_symbol,
                            "ask": ask_price,
                            "dte": dte,
                            "type": option_type,
                            "strike": strike_price,
                            "distance": abs(current_price - strike_price),
                        }
                    )
            if valid:
                valid.sort(key=lambda x: (x["ask"], x["distance"]))
                rows.append(valid[0])
        except Exception as exc:  # noqa: BLE001 — surface per-symbol failures in UI
            rows.append({"ticker": symbol, "error": str(exc)})

    df = pd.DataFrame(rows)
    total = 0.0
    if "ask" in df.columns:
        total = float(df["ask"].dropna().sum() * 100)
    return df, total


def main() -> None:
    st.set_page_config(
        page_title="Stochastic Trade Engine",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.title("Stochastic Trade Engine")
    st.sidebar.caption("Python backtests, Monte Carlo, and options tooling via Alpaca.")

    api_key, secret_key = get_credentials()
    has_creds = bool(api_key and secret_key)

    if has_creds:
        st.sidebar.success("Alpaca credentials detected")
    else:
        st.sidebar.warning(
            "Add `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` in Streamlit Secrets "
            "or a local `.env` file. Taylor demo works without keys."
        )

    symbol = st.sidebar.text_input("Symbol", value="SPY").strip().upper() or "SPY"
    lookback_days = st.sidebar.slider("Lookback (days)", 90, 730, 365, step=30)
    z_window = st.sidebar.slider("Z-score window", 5, 40, 15)
    z_threshold = st.sidebar.slider("Z-score threshold", 0.5, 3.0, 1.5, step=0.1)

    st.title("Stochastic Trade Engine")
    st.markdown(
        "Interactive dashboard for mean-reversion equity curves, friction-aware "
        "backtests, GBM Monte Carlo options pricing, and Taylor Greeks intuition."
    )

    tab_overview, tab_equity, tab_backtest, tab_gbm, tab_taylor, tab_scanner = st.tabs(
        [
            "Overview",
            "Equity curve",
            "Backtest + slippage",
            "GBM Monte Carlo",
            "Taylor approx",
            "Options scanner",
        ]
    )

    with tab_overview:
        st.subheader("What this repo does")
        st.markdown(
            """
            | Module | Role |
            | --- | --- |
            | `plot_equity.py` / **Equity curve** | Z-score mean reversion vs buy & hold |
            | `backtest.py` / **Backtest** | Vectorized P&L with square-root impact + commissions |
            | `simulate_gbm.py` / **GBM** | Monte Carlo paths and call fair value |
            | `taylor_approx.py` / **Taylor** | Delta/gamma pricing approximation (offline) |
            | `scanner.py` / **Scanner** | Cheap OTM options filter |
            | `stream.py` | Live Alpaca WebSocket VWAP (CLI only) |
            | `main.py` | Paper trading cycle (CLI only — not run from this UI) |

            **Hosting:** Streamlit Community Cloud — set the main file to `streamlit_app.py`.
            Live order bots stay CLI-only so a public demo cannot submit trades.
            """
        )
        if not has_creds:
            st.info(
                "Configure secrets before running market-data tabs. "
                "See README → Streamlit Cloud secrets."
            )

    with tab_equity:
        st.subheader("Equity curve — Z-score vs buy & hold")
        if not has_creds:
            st.warning("Alpaca credentials required.")
        elif st.button("Run equity curve", key="btn_equity"):
            with st.spinner(f"Fetching {symbol} bars…"):
                try:
                    bars = fetch_daily_bars(symbol, lookback_days, api_key, secret_key)
                    buy_hold, algo, z_scores = run_zscore_equity(
                        bars["close"], window=z_window, threshold=z_threshold
                    )
                    fig, ax = plt.subplots(figsize=(11, 5))
                    ax.plot(
                        buy_hold,
                        label=f"Buy & Hold ({symbol})",
                        color="steelblue",
                        alpha=0.6,
                    )
                    ax.plot(
                        algo, label="Z-Score Algorithm", color="darkorange", linewidth=2
                    )
                    ax.set_title(
                        f"Equity Curve: Mean Reversion vs Buy & Hold ({symbol})"
                    )
                    ax.set_xlabel("Date")
                    ax.set_ylabel("Cumulative Return (1.0 = start)")
                    ax.legend(loc="upper left")
                    ax.grid(True, linestyle="--", alpha=0.5)
                    fig.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Buy & Hold final", f"{buy_hold.iloc[-1]:.3f}×")
                    c2.metric("Algo final", f"{algo.iloc[-1]:.3f}×")
                    c3.metric("Latest Z-score", f"{z_scores.dropna().iloc[-1]:.2f}")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Failed to run equity curve: {exc}")

    with tab_backtest:
        st.subheader("Vectorized backtest with market impact")
        capital = st.number_input(
            "Starting capital ($)", min_value=10_000, value=100_000, step=10_000
        )
        gamma = st.slider("Impact gamma", 0.01, 0.5, 0.1, step=0.01)
        if not has_creds:
            st.warning("Alpaca credentials required.")
        elif st.button("Run backtest", key="btn_bt"):
            with st.spinner("Running friction-aware backtest…"):
                try:
                    bars = fetch_daily_bars(symbol, lookback_days, api_key, secret_key)
                    result = run_slippage_backtest(
                        bars["close"],
                        bars["volume"],
                        window=z_window,
                        threshold=z_threshold,
                        starting_capital=float(capital),
                        gamma=float(gamma),
                    )
                    fig, ax = plt.subplots(figsize=(11, 5))
                    ax.plot(result["equity"], color="teal", linewidth=2)
                    ax.set_title(f"Net Equity after Slippage & Commissions ({symbol})")
                    ax.set_xlabel("Date")
                    ax.set_ylabel("Equity ($)")
                    ax.grid(True, linestyle="--", alpha=0.5)
                    fig.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Gross final", f"${result['gross_final']:,.0f}")
                    c2.metric("Net final", f"${result['net_final']:,.0f}")
                    c3.metric("Lost to friction", f"${result['friction']:,.0f}")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Backtest failed: {exc}")

    with tab_gbm:
        st.subheader("Geometric Brownian Motion — Monte Carlo")
        gbm_symbol = st.text_input("GBM symbol", value="AAPL").strip().upper() or "AAPL"
        sim_days = st.slider("Days to simulate", 5, 90, 30)
        iterations = st.slider("Paths", 100, 5000, 1000, step=100)
        rfr = st.number_input(
            "Risk-free rate", min_value=0.0, max_value=0.2, value=0.045, step=0.005
        )
        strike_override = st.number_input(
            "Call strike (0 = use last close)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            help="Leave at 0 to strike at the latest close price.",
        )
        if not has_creds:
            st.warning("Alpaca credentials required.")
        elif st.button("Run Monte Carlo", key="btn_gbm"):
            with st.spinner("Simulating paths…"):
                try:
                    bars = fetch_daily_bars(
                        gbm_symbol, lookback_days, api_key, secret_key
                    )
                    strike_arg = float(strike_override) if strike_override > 0 else None
                    result = run_gbm_monte_carlo(
                        bars["close"],
                        days=sim_days,
                        iterations=iterations,
                        strike=strike_arg,
                        risk_free_rate=float(rfr),
                    )
                    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
                    sample = min(80, result["paths"].shape[1])
                    axes[0].plot(result["paths"][:, :sample], alpha=0.25, linewidth=0.8)
                    axes[0].set_title(f"{gbm_symbol} GBM paths (sample of {sample})")
                    axes[0].set_xlabel("Day")
                    axes[0].set_ylabel("Price")
                    axes[1].hist(
                        result["terminal"], bins=40, color="slategray", edgecolor="white"
                    )
                    axes[1].axvline(
                        result["strike"], color="crimson", linestyle="--", label="Strike"
                    )
                    axes[1].set_title("Terminal price distribution")
                    axes[1].legend()
                    fig.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Spot", f"${result['current_price']:.2f}")
                    c2.metric("Strike", f"${result['strike']:.2f}")
                    c3.metric("MC call fair value", f"${result['fair_value']:.2f}")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Monte Carlo failed: {exc}")

    with tab_taylor:
        st.subheader("Taylor approximation — delta vs gamma")
        st.caption("Offline demo from `taylor_approx.py`. No API keys needed.")
        moves, y_true, y_delta, y_gamma, err_delta, err_gamma = taylor_demo()
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
        axes[0].plot(moves, y_true, label="True price (eˣ)", linewidth=2, color="steelblue")
        axes[0].plot(
            moves, y_delta, label="Delta (1st order)", linestyle="--", color="darkorange"
        )
        axes[0].plot(
            moves, y_gamma, label="Gamma (2nd order)", linestyle="-.", color="seagreen"
        )
        axes[0].set_title("Pricing models")
        axes[0].set_xlabel("Market move from anchor")
        axes[0].set_ylabel("Value")
        axes[0].set_ylim(-1, 10)
        axes[0].legend()
        axes[0].grid(True, alpha=0.4)
        axes[1].plot(moves, err_delta, label="Delta error", color="darkorange")
        axes[1].plot(moves, err_gamma, label="Gamma error", color="seagreen")
        axes[1].set_title("Approximation error")
        axes[1].set_xlabel("Market move")
        axes[1].legend()
        axes[1].grid(True, alpha=0.4)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    with tab_scanner:
        st.subheader("Black-swan options scanner")
        st.caption(
            "Filters for 30–90 DTE contracts priced ≤ $0.05 with strikes 20–50% OTM. "
            "Requires Alpaca options market-data access."
        )
        default_syms = "AAPL,JNJ,XOM,JPM,WMT"
        scan_input = st.text_input("Symbols (comma-separated)", value=default_syms)
        if not has_creds:
            st.warning("Alpaca credentials required.")
        elif st.button("Scan options", key="btn_scan"):
            symbols = [s.strip().upper() for s in scan_input.split(",") if s.strip()]
            with st.spinner("Scanning option chains…"):
                try:
                    df, total = run_options_scanner(symbols, api_key, secret_key)
                    st.dataframe(df, use_container_width=True)
                    if total:
                        st.metric(
                            "Capital for 1 contract each (×100 multiplier)",
                            f"${total:,.2f}",
                        )
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Scanner failed: {exc}")

    st.divider()
    st.caption(
        "CLI scripts (`main.py`, `stream.py`, `execute_option.py`, …) are unchanged. "
        "This UI is read-only analytics — it never submits orders."
    )


if __name__ == "__main__":
    main()
