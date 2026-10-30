# Read-only Solana Research Discord Bot

A starter Python Discord bot for researching **established Solana tokens**. It scans public market data, checks SPL mint authorities and the largest token accounts where supported by the configured RPC, produces a transparent heuristic assessment, and can monitor a watchlist.

**It does not connect to or control your Axiom account, hold private keys, sign transactions, trade, or guarantee token safety.** Axiom-specific integration is not included because this project does not assume an undocumented/private Axiom API. It uses public DexScreener market data and Solana JSON-RPC.

## Features

- `/scan <mint address>` — market snapshot + rule-based risk assessment.
- `/watch <mint address>` — add a token to a local SQLite watchlist.
- `/unwatch <mint address>` — remove a token.
- `/watchlist` — show watched tokens.
- `/setalertchannel <channel>` — choose the channel for important alerts (requires Manage Server permission).
- Periodic watchlist polling; sends alerts for risk flags, assessment changes, price moves >=15%, or liquidity moves >=20%.
- Optional OpenAI-generated explanation of the structured report. AI does not determine the score.

## Requirements

- Windows 10/11
- Python 3.10+
- A Discord application and bot token
- Optional OpenAI API key for AI explanations

## Setup (Windows)

1. Create a Discord application at https://discord.com/developers/applications.
2. Under **Bot**, create a bot and copy its token. Keep it secret.
3. Under **OAuth2 > URL Generator**, select `bot` and `applications.commands`; grant `Send Messages` and `Embed Links`. Use the generated URL to invite it to your own test server.
4. Extract this project folder.
5. Copy `.env.example` to `.env`.
6. Put your Discord bot token in `DISCORD_TOKEN`. Optionally add an OpenAI API key.
7. Double-click `run.bat`, or run:

```powershell
py -3 -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env, then:
python -m solana_bot
```

The bot syncs slash commands globally on startup. Global command propagation can take a little while.

## Important limitations

- DexScreener is a third-party market-data source; data can be delayed, incomplete, or wrong.
- The public Solana RPC endpoint is rate-limited. For reliable polling, use a reputable RPC provider and set `SOLANA_RPC_URL`.
- Top 10 *token accounts* are not necessarily top 10 beneficial owners. Exchange, pool, vesting, and associated accounts can distort concentration.
- LP lock/burn status, insider wallet clusters, wash trading, transfer restrictions, honeypot-like behaviour, and deployer history are not fully checked in this first version.
- SPL Token-2022 extensions may need additional parsing. The basic mint layout checks do not inspect every extension.
- A high score is not a buy signal or evidence a token is safe. The verdict is research triage only.
- Alerts are disabled until a server administrator runs `/setalertchannel`. This prevents the bot from posting in an unintended public channel.
- The project is read-only. Never add wallet seed phrases or private keys.

## Scoring

The initial score is a heuristic starting point, not a trained predictive model. It considers authority status, top token-account concentration, liquidity, volume/liquidity ratio, buy/sell transaction counts, and 24h price movement. Certain risk flags override the numeric score.

Before relying on any ranking, test it against historical data and record forward outcomes (1h, 6h, 24h, 7d) including fees/slippage assumptions. Do not tune weights to a handful of lucky examples.

## Next engineering steps

1. Add a per-guild alert-channel configuration command.
2. Add robust retries, provider rate-limit handling, and request caching.
3. Add Token-2022 extension parsing and pool/LP lock analysis.
4. Add wallet-cluster and deployer-history research using reputable indexed data providers.
5. Add a dashboard and historical score/outcome database.
6. Backtest the heuristic before considering any more assertive recommendation labels.
