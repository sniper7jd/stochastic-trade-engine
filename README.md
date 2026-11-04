# Stochastic Trade Engine

Python toolkit for **statistical mean-reversion trading**, friction-aware backtests, GBM Monte Carlo options pricing, and cheap OTM options scanning — powered by [Alpaca](https://alpaca.markets/) market data.

Primary host: **[Streamlit Community Cloud](https://streamlit.io/cloud)** via **`streamlit_app.py`** (repo root). GitHub Pages is not the primary host (interactive Python + live API calls).

> **Looking for `streamlit_app.py`?** It lives on branch [`cursor/streamlit-hosting-50d4`](https://github.com/sniper7jd/stochastic-trade-engine/tree/cursor/streamlit-hosting-50d4) ([PR #1](https://github.com/sniper7jd/stochastic-trade-engine/pull/1)). It is **not** on `main` until that PR is merged. On Streamlit Cloud, set **Branch** to `cursor/streamlit-hosting-50d4` (or merge first, then use `main`).

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
# Use Python 3.11.x locally to match Cloud
python3.11 -m venv .venv
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

1. Open [share.streamlit.io](https://share.streamlit.io) → **New app**.
2. Connect repo `sniper7jd/stochastic-trade-engine`.
3. Fill in:

   | Setting | Value |
   | --- | --- |
   | **Repository** | `sniper7jd/stochastic-trade-engine` |
   | **Branch** | `cursor/streamlit-hosting-50d4` until PR #1 merges; then `main` |
   | **Main file path** | `streamlit_app.py` |
   | **Python version** | **3.11** (Advanced settings — required; Cloud ignores `runtime.txt`) |

4. Under **Advanced settings → Secrets**, paste:

   ```toml
   ALPACA_API_KEY = "your_key"
   ALPACA_SECRET_KEY = "your_secret"
   ```

5. **Deploy**. After the app URL is live, set the GitHub repo homepage to that URL (About → Website), e.g. `https://YOUR_APP.streamlit.app`.

### Why Python 3.11

Pinned deps (`streamlit==1.41.1`, `pandas==2.2.3`, `numpy==2.1.3`, `alpaca-py==0.40.1`) are validated for **Python 3.11**. Community Cloud defaults can be newer (e.g. 3.12+); pick **3.11** in Advanced settings so installs stay compatible. Cloud does **not** read `runtime.txt` / `.python-version` for the runtime — the UI dropdown is the source of truth. `.python-version` in this repo is for local tooling only.

### Secrets / env the Cloud app needs

| Name | Required for | Notes |
| --- | --- | --- |
| `ALPACA_API_KEY` | Equity, backtest, GBM, scanner | Paper or live data key |
| `ALPACA_SECRET_KEY` | Same | Never commit; use Streamlit Secrets or `.env` |

- **Taylor approx** tab works with no secrets.
- Options scanner needs Alpaca options market-data access on the key.
- Prefer a paper/data-only key for a public Cloud app.

## Project layout

```
streamlit_app.py      # ← Streamlit Cloud main file (repo root)
requirements.txt      # Pinned deps for Streamlit Cloud
.python-version       # Local hint: 3.11 (Cloud: set in Advanced settings)
.streamlit/config.toml
.env.example          # Template only — real keys stay local/Secrets
*.py                  # CLI research & trading scripts
```

## License

Use and modify at your own risk. This is research / educational software, not investment advice. Paper-trade before considering live capital.
