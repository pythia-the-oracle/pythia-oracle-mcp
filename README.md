# Pythia Oracle MCP Server

<!-- mcp-name: io.github.pythia-the-oracle/pythia-oracle-mcp -->

[![PyPI](https://img.shields.io/pypi/v/pythia-oracle-mcp)](https://pypi.org/project/pythia-oracle-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pythia-oracle-mcp MCP server](https://glama.ai/mcp/servers/pythia-the-oracle/pythia-oracle-mcp/badges/score.svg)](https://glama.ai/mcp/servers/pythia-the-oracle/pythia-oracle-mcp)

**On-chain calculated crypto indicators for AI agents and smart contracts.**

Pythia is the first oracle delivering calculated technical indicators on-chain — EMA, RSI, VWAP, Bollinger Bands, volatility — for 22 tokens across crypto. Not just prices. The same indicators traders use, available to smart contracts and AI agents with a single call via Chainlink.

## Why Pythia?

Most oracles only give you price. Pythia gives you **computed analysis**: 484 indicator feeds across 22 tokens (BTC, SOL, TAO, RENDER, ONDO, AAVE, UNI, and more), 4 timeframes, delivered on Polygon via Chainlink. If your AI agent, DeFi protocol, or trading bot needs on-chain RSI, EMA, or Bollinger Bands — Pythia is the only source.

**Use cases:**
- AI trading agents that need on-chain technical signals
- DeFi vault rebalancing based on RSI or volatility thresholds
- Smart contract risk management using Bollinger Band width
- AI-powered portfolio analysis with real-time calculated metrics

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
| `list_tokens` | All 22 tracked tokens with status, uptime, and data sources |
| `get_token_feeds` | All indicator feed names for a specific token |
| `get_market_summary` | System-wide overview — tokens by status, ecosystem coverage, infrastructure health |
| `check_oracle_health` | Per-token 30-day uptime (worst-first), data source status, incident report |
| `get_contracts` | All contract addresses (operator, consumers, faucet, LINK) |
| `get_pricing` | Pricing tiers and when to use each one |
| `get_integration_guide` | Ready-to-deploy Solidity code for any tier |

## Example Prompts

Ask your AI agent:

> "What indicators does Pythia have for Bitcoin?"

Calls `get_token_feeds("bitcoin")` — returns all 22 indicator feeds grouped by type.

> "Is Pythia reliable enough to integrate?"

Calls `check_oracle_health()` — returns per-token uptime, data source health, and active incidents.

> "Give me a Solidity contract to consume Pythia's speed bundle"

Calls `get_integration_guide("speed")` — returns a complete, deployable contract with correct addresses and job IDs.

> "What tokens does Pythia cover and are they all working?"

Calls `get_market_summary()` — returns ecosystem coverage, status breakdown, and infrastructure health.

## What Pythia Provides

- **484 indicator feeds** across 22 tokens (cross-chain: BTC, SOL, TAO, RENDER, ONDO and more)
- **5 indicator types:** EMA, RSI, Bollinger (upper/lower), Volatility, USD Price
- **4 timeframes:** 5-minute, 1-hour, 1-day, 1-week
- **4 pricing tiers:** Discovery (0.01 LINK), Analysis (0.03), Speed (0.05), Complete (0.10)
- **Free trial:** PythiaFaucet contract — no LINK needed, 5 requests/day

## Integration Examples

See [pythia-oracle-examples](https://github.com/pythia-the-oracle/pythia-oracle-examples) for Solidity contracts with Hardhat setup — ready to deploy on Polygon.

## Links

- [Website & Live Feed Explorer](https://pythia.c3x-solutions.com)
- [Integration Examples (Solidity + Hardhat)](https://github.com/pythia-the-oracle/pythia-oracle-examples)
- [PyPI Package](https://pypi.org/project/pythia-oracle-mcp/)
- [Telegram](https://t.me/pythia_the_oracle)
- [Twitter/X](https://x.com/pythia_oracle)

## License

MIT
