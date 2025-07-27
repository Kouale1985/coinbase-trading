# 🧠 AI-Powered Crypto Trading Bot

A Coinbase Advanced Trade bot that runs on Render using RSI, MACD, and ATR to simulate crypto trading signals.

---

## 🚀 Features

- Multi-asset support: XLM, XRP, LINK, OP, ARB
- RSI + MACD + ATR strategy
- Take-profit / stop-loss execution logic
- Simulation mode for safe testing
- Logs trades to `trades.csv`
- Render-ready as a **Background Worker**

---

## 🧱 File Structure

- `bot.py` — Main trading logic
- `config.py` — Per-coin strategy thresholds
- `.env.example` — Environment variable template
- `requirements.txt` — Dependencies
- `trades.csv` — Auto-generated trade log

---

## 🔧 Setup Instructions

### 1. Create GitHub Repo & Add Files

- Use GitHub or Codespaces to create the repo
- Add the 5 files: `bot.py`, `config.py`, `.env.example`, `requirements.txt`, `README.md`
- Commit and push to GitHub

---

### 2. Set Up Render Background Worker

- Go to [Render.com](https://dashboard.render.com/)
- Click **New → Background Worker**
- Connect your GitHub repo
- Use the following build & start commands:

**Build Command**:
```bash
pip install -r requirements.txt
