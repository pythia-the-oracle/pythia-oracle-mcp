# Pythia Oracle MCP Server

On-chain calculated technical indicators for AI agents. EMA, RSI, VWAP, Bollinger Bands, volatility, and liquidity — delivered to smart contracts via Chainlink.

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
| `list_tokens` | All 13 supported tokens with engine IDs and status |
| `list_indicators` | Available indicator types (EMA, RSI, VWAP, Bollinger, volatility, liquidity) |
| `get_token_feeds` | All indicator feeds for a specific token |
| `get_feed_value` | Current cached value for a specific feed |
| `get_contracts` | All contract addresses (operator, consumers, faucet, LINK) |
| `get_pricing` | Pricing tiers and when to use each one |
| `get_integration_guide` | Ready-to-deploy Solidity code for any tier |
| `get_system_status` | Live system status — uptime, feed count, chain info |

## Example Usage (in Claude)

> "What indicators does Pythia have for AAVE?"

The AI calls `get_token_feeds("aave")` and returns all 22 indicator feeds with pricing guidance.

> "Generate a Solidity contract to consume Pythia's speed bundle"

The AI calls `get_integration_guide("speed")` and returns a complete, deployable contract with the correct addresses and job IDs.

> "What's the current RSI for POL on the 1-hour timeframe?"

The AI calls `get_feed_value("pol_RSI_1H_14")` and returns the live value.

## What Pythia Provides

- **286 indicator instances** across 13 tokens on Polygon
- **8 indicator types:** EMA, RSI, VWAP, Bollinger (upper/mid/lower), volatility, liquidity
- **4 timeframes:** 5-minute, 1-hour, 1-day, 1-week
- **4 pricing tiers:** Discovery (0.01 LINK), Analysis (0.03), Speed (0.05), Complete (0.10)
- **Free trial:** PythiaFaucet contract — no LINK needed, 5 requests/day

## Links

- [Website & Feed Explorer](https://pythia.c3x-solutions.com)
- [Telegram](https://t.me/pythia_the_oracle)
- [Twitter/X](https://x.com/PythiaOracle)

## License

MIT
