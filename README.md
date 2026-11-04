# Stochastic Trade Engine

Python toolkit for **statistical mean-reversion trading**, friction-aware backtests, GBM Monte Carlo options pricing, and cheap OTM options scanning — powered by [Alpaca](https://alpaca.markets/) market data.

Primary host: **[Streamlit Community Cloud](https://streamlit.io/cloud)** via **`streamlit_app.py`** (repo root). GitHub Pages is not the primary host (interactive Python + live API calls).

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
   | **Branch** | `main` |
   | **Main file path** | `streamlit_app.py` |
   | **Python version** | **3.11** (Advanced settings — required; Cloud ignores `runtime.txt`) |

4. Under **Advanced settings → Secrets**, paste:

   ```toml
   ALPACA_API_KEY = "your_key"
   ALPACA_SECRET_KEY = "your_secret"
   # Optional — defaults to iex (free). Only set sip if your Alpaca plan includes SIP.
   # ALPACA_DATA_FEED = "iex"
   ```

5. **Deploy**. After the app URL is live, set the GitHub repo homepage to that URL (About → Website), e.g. `https://YOUR_APP.streamlit.app`.

### Why Python 3.11

Pinned deps (`streamlit==1.41.1`, `pandas==2.2.3`, `numpy==2.1.3`, `alpaca-py==0.40.1`) are validated for **Python 3.11**. Community Cloud defaults can be newer (e.g. 3.12+); pick **3.11** in Advanced settings so installs stay compatible. Cloud does **not** read `runtime.txt` / `.python-version` for the runtime — the UI dropdown is the source of truth. `.python-version` in this repo is for local tooling only.

### Data feed (IEX vs SIP)

Equity bars and underlying quotes in `streamlit_app.py` request **`feed=iex` by default**. Free/basic Alpaca keys cannot query recent SIP (`subscription does not permit querying recent SIP data`). No extra secret is required for the free plan.

| `ALPACA_DATA_FEED` | When to use |
| --- | --- |
| `iex` (default) | Free / basic Alpaca — use this |
| `delayed_sip` | If your plan allows delayed SIP |
| `sip` | Paid real-time SIP subscription only |

### Secrets / env the Cloud app needs

| Name | Required for | Notes |
| --- | --- | --- |
| `ALPACA_API_KEY` | Equity, backtest, GBM, scanner | Paper or live data key |
| `ALPACA_SECRET_KEY` | Same | Never commit; use Streamlit Secrets or `.env` |
| `ALPACA_DATA_FEED` | Optional | Defaults to `iex`. Set `sip` / `delayed_sip` only with a matching subscription |

- **Taylor approx** tab works with no secrets.
- Options scanner needs Alpaca options market-data access on the key (separate from SIP).
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

## Contributing

Commit with your own GitHub name and email (`git config user.name` / `user.email`) so the repository contributors list reflects the people who own the project.

## License

Use and modify at your own risk. This is research / educational software, not investment advice. Paper-trade before considering live capital.
