# Pythia Oracle MCP Server

On-chain calculated technical indicators for AI agents. EMA, RSI, Bollinger Bands, Volatility — delivered to smart contracts via Chainlink.

**Pythia is the first oracle providing computed metrics on-chain.** Unlike price-only oracles, Pythia calculates the same indicators traders use and makes them available to smart contracts with a single call.

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

### Cursor / VS Code

Add to MCP settings:

```json
{
  "pythia-oracle": {
    "command": "pythia-oracle-mcp"
  }
}
```

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

## Example Usage (in Claude)

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

## Links

- [Website & Feed Explorer](https://pythia.c3x-solutions.com)
- [Telegram](https://t.me/pythia_the_oracle)
- [Twitter/X](https://x.com/pythia_oracle)

## License

MIT
