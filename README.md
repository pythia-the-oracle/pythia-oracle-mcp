# Pythia Oracle MCP Server

<!-- mcp-name: io.github.pythia-the-oracle/pythia-oracle-mcp -->

[![PyPI](https://img.shields.io/pypi/v/pythia-oracle-mcp)](https://pypi.org/project/pythia-oracle-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pythia-oracle-mcp MCP server](https://glama.ai/mcp/servers/pythia-the-oracle/pythia-oracle-mcp/badges/score.svg)](https://glama.ai/mcp/servers/pythia-the-oracle/pythia-oracle-mcp)

**Every smart contract deserves intelligence, not just data.**

Pythia is the first oracle delivering calculated technical indicators on-chain — EMA, RSI, VWAP, Bollinger Bands, volatility — for any token, on any Chainlink-supported chain. The same indicators traders use, available to smart contracts and AI agents with a single call via Chainlink.

**Pythia Events** lets smart contracts subscribe to indicator conditions (RSI below 30, EMA crossover, Bollinger breakout) and get called automatically when they trigger. No keeper, no off-chain bot, no polling — your contract reacts to markets on its own.

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

## What Pythia Provides

- **Any token, any Chainlink-supported chain** — currently serving BTC, SOL, TAO, RENDER, ONDO, AAVE, UNI, MORPHO, and more, with new tokens added on demand
- **6 indicator types:** EMA, RSI, Bollinger Bands (upper/lower), VWAP, Volatility, USD Price
- **4 timeframes:** 5-minute, 1-hour, 1-day, 1-week
- **4 pricing tiers:** Discovery (0.01 LINK), Analysis (0.02), Speed (0.05), Complete (0.10)
- **Free trial:** PythiaFaucet contract — no LINK needed, 5 requests/day
- **Pythia Events:** Subscribe to indicator conditions (ABOVE/BELOW thresholds) — your contract gets called when they trigger. Prepaid in LINK, unused time refunded on cancel or fire. No keeper infrastructure needed.

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
