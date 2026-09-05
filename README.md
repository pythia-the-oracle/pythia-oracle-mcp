# Pythia Oracle MCP Server

<!-- mcp-name: io.github.pythia-the-oracle/pythia-oracle-mcp -->

[![PyPI](https://img.shields.io/pypi/v/pythia-oracle-mcp)](https://pypi.org/project/pythia-oracle-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pythia-oracle-mcp MCP server](https://glama.ai/mcp/servers/pythia-the-oracle/pythia-oracle-mcp/badges/score.svg)](https://glama.ai/mcp/servers/pythia-the-oracle/pythia-oracle-mcp)

**Every smart contract deserves intelligence, not just data.**

Pythia is the first oracle delivering calculated technical indicators on-chain — EMA, RSI, VWAP, Bollinger Bands, volatility — for any token, on any Chainlink-supported chain. The same indicators traders use, available to smart contracts and AI agents with a single call via Chainlink.

**Pythia Events** lets smart contracts subscribe to indicator conditions (RSI below 30, EMA crossover, Bollinger breakout) and get called automatically when they trigger. No keeper, no off-chain bot, no polling — your contract reacts to markets on its own.

**Pythia Visions** delivers walk-forward validated market intelligence on-chain — pattern type, confidence score, indicator snapshot, and feeds-to-watch for confirmation, all in one event. Backtested across 9 years of history. FREE to subscribe. For the current live token + pattern catalog with accuracy stats and fire frequency, call `get_visions_info` from the MCP tools below.

## Why Pythia?

Most oracles only give you price. Pythia gives you **computed analysis**: EMA, RSI, Bollinger Bands, VWAP, volatility — for tokens like BTC, SOL, TAO, RENDER, ONDO, AAVE, UNI, and more, across 4 timeframes, delivered on-chain via Chainlink. New tokens and indicators are added on demand. If your AI agent, DeFi protocol, or trading bot needs on-chain RSI, EMA, or Bollinger Bands — Pythia is the only source.

**Use cases:**
- AI trading agents that need on-chain technical signals
- DeFi vault rebalancing based on RSI or volatility thresholds
- Smart contract risk management using Bollinger Band width
- AI-powered portfolio analysis with real-time calculated metrics
- Event-driven strategies — subscribe to RSI thresholds or EMA crossovers, your contract gets triggered automatically
- Automated DeFi bots without keepers — no Gelato, no cron jobs, no off-chain infrastructure

## Quick Start

```bash
pip install pythia-oracle-mcp
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pythia-oracle": {
      "command": "pythia-oracle-mcp"
    }
  }
}
```

### Claude Code

```bash
claude mcp add pythia-oracle -- pythia-oracle-mcp
```

### Cursor / Windsurf / VS Code

Add to MCP settings:

```json
{
  "pythia-oracle": {
    "command": "pythia-oracle-mcp"
  }
}
```

### OpenAI Agents / GPT

Any MCP-compatible client works — just point it at `pythia-oracle-mcp`.

### Run directly

```bash
python -m pythia_oracle_mcp
```

## Available Tools

| Tool | Description |
|------|-------------|
| `list_tokens` | All tracked tokens with status, uptime, and data sources |
| `get_token_feeds` | All indicator feed names for a specific token |
| `get_market_summary` | System-wide overview — tokens by status, ecosystem coverage, infrastructure health |
| `check_oracle_health` | Per-token 30-day uptime (worst-first), data source status, incident report |
| `get_contracts` | All contract addresses (operator, consumers, faucet, LINK) |
| `get_pricing` | Pricing tiers and when to use each one |
| `get_integration_guide` | Ready-to-deploy Solidity code for any tier |
| `get_events_info` | How Pythia Events work — subscribe to indicator conditions, get triggered on-chain |
| `get_events_guide` | Solidity code and deployment steps for event subscriptions |
| `subscribe_info` | Subscription details — conditions, pricing, refund mechanics |
| `get_visions_info` | Pythia Visions overview — walk-forward validated patterns, fire-frequency disclosure, contract address |
| `get_visions_guide` | Solidity code to subscribe to Visions and listen for VisionFired events |
| `get_vision_history` | Recent Visions fired for a token with pattern breakdown and confidence stats |
| `get_vision_payload` | Full enriched object for a fired Vision — failure profile, cooldown context, concurrent fires |
| `lookup_event_feed` | Reverse-lookup an Event feedId (bytes32) to its human-readable feed name |
| `list_subscriptions` | Enumerate active Pythia Event subscriptions for an owner address |
| `get_feed_value` | Latest computed value for any Pythia indicator feed (off-chain cache) |

## Example Prompts

Ask your AI agent:

> "What indicators does Pythia have for Bitcoin?"

Calls `get_token_feeds("bitcoin")` — returns all indicator feeds for Bitcoin, grouped by type.

> "Is Pythia reliable enough to integrate?"

Calls `check_oracle_health()` — returns per-token uptime, data source health, and active incidents.

> "Give me a Solidity contract to consume Pythia's speed bundle"

Calls `get_integration_guide("speed")` — returns a complete, deployable contract with correct addresses and job IDs.

> "What tokens does Pythia cover and are they all working?"

Calls `get_market_summary()` — returns ecosystem coverage, status breakdown, and infrastructure health.

> "How do Pythia Events work? I want my contract to react when BTC RSI drops below 30."

Calls `get_events_info()` — returns how subscriptions work, supported conditions, and pricing.

> "Give me the Solidity code to subscribe to an EMA crossover event."

Calls `get_events_guide()` — returns a deployable EventSubscriber contract with subscribe/receive pattern.

> "What are Pythia Visions? What patterns does it detect?"

Calls `get_visions_info()` — returns walk-forward validated patterns with accuracy range, fire frequency, contract address, and how it works.

> "Show me recent BTC Visions that fired"

Calls `get_vision_history("BTC")` — returns recent pattern detections with confidence and price.

> "Give me Solidity code to subscribe to Pythia Visions"

Calls `get_visions_guide()` — returns a contract that subscribes to VisionFired events.

## What Pythia Provides

- **Any token, any Chainlink-supported chain** — currently serving BTC, SOL, TAO, RENDER, ONDO, AAVE, UNI, MORPHO, and more, with new tokens added on demand
- **6 indicator types:** EMA, RSI, Bollinger Bands (upper/lower), VWAP, Volatility, USD Price
- **4 timeframes:** 5-minute, 1-hour, 1-day, 1-week
- **4 pricing tiers:** Discovery / Analysis / Speed / Complete — for current LINK fees call `get_pricing`
- **Free trial:** PythiaFaucet contract — no LINK needed
- **Pythia Events:** Subscribe to indicator conditions (ABOVE/BELOW thresholds) — your contract gets called when they trigger. Prepaid in LINK, unused time refunded on cancel or fire. No keeper infrastructure needed.
- **Pythia Visions:** Walk-forward validated market intelligence on-chain — pattern type + confidence + indicator snapshot + feeds-to-watch, delivered via Chainlink. FREE to subscribe. For the live list of patterns + tokens, call `get_visions_info`.
- **Public indicator history:** free, immutable JSON archive of every published indicator value — one file per feed per closed UTC day at `https://pythia.c3x-solutions.com/history/{chain}/{feed_name}/{YYYY-MM-DD}.json` (start from `history/manifest.json`). Re-derive or audit any indicator condition over a date range without an oracle call; files never change once published.

## Data Freshness

This MCP server is a thin client over `https://pythia.c3x-solutions.com/feed-status.json`, the live status feed updated every 15 minutes by the data engine. New tokens, new patterns, contract addresses, and pricing changes appear in MCP tools within seconds of the next data-engine cycle — no package update required.

If the live feed is unreachable, MCP tools raise a clear error rather than serve stale baked-in data. Retry shortly or check status. (As of v0.9.0, fail-loud — earlier versions had baked-in fallbacks that drifted from production state and have been removed.)

## Integration Examples

See [pythia-oracle-examples](https://github.com/pythia-the-oracle/pythia-oracle-examples) for Solidity contracts with Hardhat setup — ready to deploy on any Chainlink-supported network.

## Links

- [Website & Live Feed Explorer](https://pythia.c3x-solutions.com)
- [Integration Examples (Solidity + Hardhat)](https://github.com/pythia-the-oracle/pythia-oracle-examples)
- [PyPI Package](https://pypi.org/project/pythia-oracle-mcp/)
- [Telegram](https://t.me/pythia_the_oracle)
- [Twitter/X](https://x.com/pythia_oracle)

## License

MIT
