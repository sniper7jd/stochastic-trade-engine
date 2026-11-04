# Stochastic Trade Engine

Python toolkit for **statistical mean-reversion trading**, friction-aware backtests, GBM Monte Carlo options pricing, and cheap OTM options scanning — powered by [Alpaca](https://alpaca.markets/) market data.

Primary host: **[Streamlit Community Cloud](https://streamlit.io/cloud)** via `streamlit_app.py`. GitHub Pages is not used as the main deploy path (this is an interactive Python app with live API calls, not a static site).

## Features

| Area | Scripts / UI |
| --- | --- |
| Z-score equity curve vs buy & hold | `plot_equity.py`, Equity curve tab |
| Vectorized backtest + square-root impact | `backtest.py`, Backtest tab |
| GBM Monte Carlo call pricing | `simulate_gbm.py`, GBM tab |
| Taylor delta/gamma intuition | `taylor_approx.py`, Taylor tab (offline) |
| Cheap OTM options scanner | `scanner.py` / `target_scanner.py`, Scanner tab |
| Live VWAP WebSocket | `stream.py` (CLI) |
| Paper trading cycle | `main.py` (CLI — not exposed in the UI) |

The Streamlit dashboard is **read-only analytics**. Order submission stays in CLI scripts so a public Cloud app cannot trade.

## Quick start (local)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then edit with your Alpaca keys
streamlit run streamlit_app.py
```

CLI examples (same credentials):

```bash
python plot_equity.py
python backtest.py
python simulate_gbm.py
python scanner.py
python stream.py            # live VWAP WebSocket
```

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub (already at `sniper7jd/stochastic-trade-engine`).
2. Open [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select the repo, branch `main` (or your deploy branch), and set:

   | Setting | Value |
   | --- | --- |
   | **Main file path** | `streamlit_app.py` |
   | Python version | 3.11+ (3.12 fine) |

4. Under **Advanced settings → Secrets**, add:

   ```toml
   ALPACA_API_KEY = "your_key"
   ALPACA_SECRET_KEY = "your_secret"
   ```

5. Deploy. After the app URL is live, set the GitHub repo homepage to that URL:

   ```bash
   gh repo edit sniper7jd/stochastic-trade-engine --homepage "https://YOUR_APP.streamlit.app"
   ```

### Secrets / env the Cloud app needs

| Name | Required for | Notes |
| --- | --- | --- |
| `ALPACA_API_KEY` | Equity, backtest, GBM, scanner | Paper or live data key |
| `ALPACA_SECRET_KEY` | Same | Never commit; use Streamlit Secrets or `.env` |

- **Taylor approx** tab works with no secrets.
- Options scanner needs Alpaca options market-data access on the key.
- Do **not** put trading keys into a public app if you also use those keys for live orders; prefer a paper/data-only key for Cloud.

## Project layout

```
streamlit_app.py      # Cloud / local dashboard entrypoint
requirements.txt      # Pinned deps for Streamlit Cloud
.streamlit/config.toml
.env.example          # Template only — real keys stay local/Secrets
*.py                  # CLI research & trading scripts
```

## License

Use and modify at your own risk. This is research / educational software, not investment advice. Paper-trade before considering live capital.
