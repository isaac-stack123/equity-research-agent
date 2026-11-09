# Autonomous Equity Research and Trading Agent

A multi-agent system built on Claude Code that researches US equities, writes an
investment thesis, stress-tests it against a written risk policy, and manages a small
dedicated live brokerage account through the Alpaca API.

The project is a test of research process and
risk discipline, not a claim of market-beating returns. Trade history is kept private.

## How a trading day works

1. **Research (cloud, pre-market).** Screens a liquid universe, reviews news and filings,
   and writes a brief.
2. **Decision (8:00am ET).** Reads the brief, checks open positions against their
   invalidation points, and places orders only if they pass the rulebook.
3. **Review (4:30pm ET).** Logs fills, updates the trade journal, and benchmarks results
   against QQQ and VOO.

## Research agents

Each agent in [`.claude/agents`](.claude/agents) covers one job:

| Agent | Role |
|---|---|
| `fundamentals-analyst` | Financial statements, margins, balance sheet, multiples |
| `sec-filings-analyst` | 10-K, 10-Q, 8-K and Form 4 primary-source review |
| `valuation-analyst` | Segment DCF, reverse DCF, and a one-page thesis |
| `technical-analyst` | Trend, momentum, volatility, and stop distances |
| `news-analyst` | Company news, macro backdrop, event odds |
| `sentiment-analyst` | Crowd sentiment, including when it is a warning sign |
| `bull-case` / `bear-case` | The strongest honest argument on each side |
| `risk-reviewer` | Checks a proposed trade line by line against the rulebook |

## Risk framework

[`STRATEGY.md`](STRATEGY.md) is binding on every run. Its main controls:

- Every position needs a written thesis and a specific, observable invalidation point
- Long-only, cash account: no margin, shorting, or options
- Resting broker stop orders, a -30% hard stop, and a trailing stop on winners
- Position limits and conviction-based sizing
- Account circuit breakers: sizing halves at -20%, all trading stops at -40%

## Tools

Python utilities in [`tools/`](tools): `dcf.py` (valuation), `edgar.py` (SEC filings),
`screen.py` (stock screen), `technicals.py` (indicators), `benchmark.py` (performance vs
index funds), `polymarket.py` (event probabilities), `stocktwits.py` (sentiment),
`alpaca.py` (broker access), and `alert.py` (failure alerts).

## How this was built

The system was developed with Claude Code, and the agents, prompts, rulebook, and much of
the code were written with AI assistance. The author sets the mandate and risk limits and
approved the rulebook and the move to live trading. Individual trades are decided by the
agent within those rules, without per-trade approval.

## Running it

Credentials are read from the environment or the macOS keychain and are never stored in
this repository. Scripts expect the project at `~/trading`, Alpaca keys in
`~/.alpaca-live.env`, and `TRADING_ALERT_TO` set for email alerts.

Not financial advice. This is a personal research project and it can lose money.
