#!/usr/bin/env python3
"""
Pythia Oracle MCP Server

Exposes Pythia's on-chain calculated indicators (EMA, RSI, VWAP, Bollinger,
volatility, liquidity) to AI agents via the Model Context Protocol.

Run: python server.py
Or via MCP: mcp run server.py
"""

import json
from datetime import datetime, timezone

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Pythia Oracle",
    instructions=(
        "On-chain calculated technical indicators — EMA, RSI, VWAP, "
        "Bollinger Bands, volatility, liquidity. The first oracle delivering "
        "computed metrics to smart contracts via Chainlink on Polygon."
    ),
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEED_STATUS_URL = "https://pythia.c3x-solutions.com/feed-status.json"
WEBSITE_URL = "https://pythia.c3x-solutions.com"

CONTRACTS = {
    "chain": "Polygon",
    "chain_id": 137,
    "link_token_erc677": "0xb0897686c545045aFc77CF20eC7A532E3120E0F1",
    "operator": "0xAA37710aF244514691629Aa15f4A5c271EaE6891",
    "faucet": "0x640fC3B9B607E324D7A3d89Fcb62C77Cc0Bd420A",
    "consumers": {
        "discovery": {
            "address": "0xeC2865d66ae6Af47926B02edd942A756b394F820",
            "fee": "0.01 LINK",
            "returns": "uint256 (single indicator)",
            "job_id": "0x8920841054eb4082b5910af84afa005e00000000000000000000000000000000",
        },
        "analysis": {
            "address": "0x3b3aC62d73E537E3EF84D97aB5B84B51aF8dB316",
            "fee": "0.03 LINK",
            "returns": "uint256[] (1H/1D/1W bundle)",
            "job_id": "0xa1ecae215cd9471a95095ab52e2f403600000000000000000000000000000000",
        },
        "speed": {
            "address": "0xC406e7d9AC385e7AB43cBD56C74ad487f085d47B",
            "fee": "0.05 LINK",
            "returns": "uint256[] (5M bundle)",
            "job_id": "0x8a50dfe4645f41a993a175b486d9840600000000000000000000000000000000",
        },
        "complete": {
            "address": "0x2dEC98fd7173802b351d1E28d0Cd5DdD20C24252",
            "fee": "0.10 LINK",
            "returns": "uint256[] (all indicators)",
            "job_id": "0x48d135697ade4c8faec5fe67bbc3f65b00000000000000000000000000000000",
        },
    },
}

INDICATORS = {
    "EMA": {
        "name": "Exponential Moving Average",
        "description": "20-period EMA. Smoothed trend indicator.",
        "feed_format": "{engine_id}_EMA_{timeframe}_20",
    },
    "RSI": {
        "name": "Relative Strength Index",
        "description": "14-period RSI. Momentum oscillator (0-100). >70 = overbought, <30 = oversold.",
        "feed_format": "{engine_id}_RSI_{timeframe}_14",
    },
    "VWAP": {
        "name": "Volume-Weighted Average Price",
        "description": "Price weighted by volume. Key institutional benchmark.",
        "feed_format": "{engine_id}_VWAP_{timeframe}",
    },
    "BOLLINGER_UPPER": {
        "name": "Bollinger Band (Upper)",
        "description": "Upper band = SMA(20) + 2*stddev. Price above = potential overbought.",
        "feed_format": "{engine_id}_BOLLINGER_UPPER_{timeframe}_20",
    },
    "BOLLINGER_MID": {
        "name": "Bollinger Band (Middle)",
        "description": "Middle band = SMA(20). The baseline moving average.",
        "feed_format": "{engine_id}_BOLLINGER_MID_{timeframe}_20",
    },
    "BOLLINGER_LOWER": {
        "name": "Bollinger Band (Lower)",
        "description": "Lower band = SMA(20) - 2*stddev. Price below = potential oversold.",
        "feed_format": "{engine_id}_BOLLINGER_LOWER_{timeframe}_20",
    },
    "VOLATILITY": {
        "name": "Volatility",
        "description": "Standard deviation-based volatility measure.",
        "feed_format": "{engine_id}_VOLATILITY_{timeframe}",
    },
    "LIQUIDITY": {
        "name": "Liquidity Depth",
        "description": "DEX liquidity depth metric.",
        "feed_format": "{engine_id}_LIQUIDITY_{timeframe}",
    },
}

TIMEFRAMES = {
    "5M": {"name": "5-minute", "tier": "speed"},
    "1H": {"name": "1-hour", "tier": "analysis"},
    "1D": {"name": "1-day", "tier": "analysis"},
    "1W": {"name": "1-week", "tier": "analysis"},
}

# Cache for feed data
_feed_cache: dict = {"data": None, "fetched_at": None}
CACHE_TTL_SECONDS = 300  # 5 minutes


async def _fetch_feed_status() -> dict:
    """Fetch feed status from the public website, with caching."""
    now = datetime.now(timezone.utc)
    if (
        _feed_cache["data"]
        and _feed_cache["fetched_at"]
        and (now - _feed_cache["fetched_at"]).total_seconds() < CACHE_TTL_SECONDS
    ):
        return _feed_cache["data"]

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(FEED_STATUS_URL)
        resp.raise_for_status()
        data = resp.json()

    _feed_cache["data"] = data
    _feed_cache["fetched_at"] = now
    return data


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_tokens() -> str:
    """List all tokens supported by Pythia Oracle with their engine IDs and current status."""
    data = await _fetch_feed_status()
    tokens = data.get("tokens", [])
    lines = [f"Pythia Oracle — {len(tokens)} supported tokens\n"]
    for t in tokens:
        lines.append(
            f"  {t['symbol']:6s}  engine_id={t['engine_id']:<35s}  "
            f"chain={t.get('chain', 'polygon')}  status={t.get('status', 'unknown')}"
        )
    lines.append(f"\nData source: {WEBSITE_URL}")
    return "\n".join(lines)


@mcp.tool()
async def list_indicators() -> str:
    """List all calculated indicator types available from Pythia (EMA, RSI, VWAP, Bollinger, volatility, liquidity)."""
    lines = ["Pythia Oracle — Available Indicators\n"]
    for key, info in INDICATORS.items():
        lines.append(f"  {key}")
        lines.append(f"    {info['name']}: {info['description']}")
        lines.append(f"    Feed format: {info['feed_format']}")
        lines.append("")
    lines.append("Timeframes:")
    for tf, info in TIMEFRAMES.items():
        lines.append(f"  {tf} ({info['name']}) — included in {info['tier']} tier")
    return "\n".join(lines)


@mcp.tool()
async def get_token_feeds(engine_id: str) -> str:
    """Get all available indicator feeds for a specific token.

    Args:
        engine_id: Token engine ID (e.g., 'aave', 'pol', 'uniswap', 'quickswap', 'morpho')
    """
    data = await _fetch_feed_status()
    tokens = {t["engine_id"]: t for t in data.get("tokens", [])}

    if engine_id not in tokens:
        available = ", ".join(sorted(tokens.keys()))
        return f"Token '{engine_id}' not found. Available: {available}"

    token = tokens[engine_id]
    feeds = token.get("feeds", [])

    lines = [f"{token['symbol']} ({engine_id}) — {len(feeds)} indicator feeds\n"]
    for feed in feeds:
        name = feed if isinstance(feed, str) else feed.get("name", str(feed))
        lines.append(f"  {name}")

    lines.append(f"\nTo request any single feed: use Discovery tier (0.01 LINK)")
    lines.append(f"For all 1H/1D/1W feeds: use Analysis bundle (0.03 LINK)")
    lines.append(f"For all 5M feeds: use Speed bundle (0.05 LINK)")
    lines.append(f"For everything: use Complete bundle (0.10 LINK)")
    lines.append(f"\nFree trial: call PythiaFaucet at {CONTRACTS['faucet']}")
    return "\n".join(lines)


@mcp.tool()
async def get_feed_value(feed_name: str) -> str:
    """Get the current cached value for a specific indicator feed.

    Args:
        feed_name: Feed identifier (e.g., 'aave_EMA_5M_20', 'pol_RSI_1H_14', 'uniswap_VWAP_1D')
    """
    data = await _fetch_feed_status()
    for token in data.get("tokens", []):
        feeds = token.get("feeds", [])
        for feed in feeds:
            if isinstance(feed, dict) and feed.get("name") == feed_name:
                return json.dumps(
                    {
                        "feed": feed_name,
                        "token": token["symbol"],
                        "value": feed.get("value"),
                        "updated_at": feed.get("updated_at"),
                        "status": feed.get("status", "unknown"),
                    },
                    indent=2,
                )

    # Feed not found — suggest closest matches
    all_feeds = []
    for token in data.get("tokens", []):
        for feed in token.get("feeds", []):
            name = feed if isinstance(feed, str) else feed.get("name", "")
            all_feeds.append(name)

    suggestions = [f for f in all_feeds if feed_name.split("_")[0] in f.lower()][:10]
    msg = f"Feed '{feed_name}' not found in cached data."
    if suggestions:
        msg += f"\n\nDid you mean one of: {', '.join(suggestions)}"
    return msg


@mcp.tool()
async def get_contracts() -> str:
    """Get all Pythia contract addresses on Polygon (operator, consumers, faucet, LINK token)."""
    lines = ["Pythia Oracle — Contract Addresses (Polygon Mainnet, Chain ID 137)\n"]
    lines.append(f"  Operator:           {CONTRACTS['operator']}")
    lines.append(f"  LINK Token (ERC-677): {CONTRACTS['link_token_erc677']}")
    lines.append(f"  Faucet (free trial): {CONTRACTS['faucet']}")
    lines.append("")
    lines.append("Consumer Contracts (by tier):")
    for tier, info in CONTRACTS["consumers"].items():
        lines.append(f"\n  {tier.upper()} — {info['fee']}")
        lines.append(f"    Address: {info['address']}")
        lines.append(f"    Returns: {info['returns']}")
        lines.append(f"    Job ID:  {info['job_id']}")

    lines.append("\n\nIMPORTANT: Use ERC-677 LINK only (0xb08976...).")
    lines.append("Bridged ERC-20 LINK (0x53e0bc...) does NOT work with Chainlink.")
    lines.append("Use PegSwap (pegswap.chain.link) to convert if needed.")
    return "\n".join(lines)


@mcp.tool()
async def get_pricing() -> str:
    """Get Pythia Oracle pricing tiers and when to use each one."""
    return """Pythia Oracle — Pricing Tiers

  DISCOVERY — 0.01 LINK
    Any single indicator (EMA, RSI, VWAP, Bollinger, volatility, liquidity)
    Returns: uint256
    Best for: one-off queries, specific signals

  ANALYSIS — 0.03 LINK
    All 1-hour, 1-day, and 1-week indicators bundled
    Returns: uint256[] (all analysis timeframe slots)
    Best for: protocols needing multi-timeframe view
    Saves vs Discovery: 3+ individual calls

  SPEED — 0.05 LINK
    All 5-minute indicators bundled
    Returns: uint256[] (all 5M slots)
    Best for: real-time trading, HFT agents, active rebalancing
    Saves vs Discovery: 5+ individual calls

  COMPLETE — 0.10 LINK
    Every indicator for a token (all timeframes)
    Returns: uint256[] (all slots)
    Best for: comprehensive analysis, dashboards
    Saves vs Discovery: 10+ individual calls

  FREE TRIAL — PythiaFaucet
    Address: 0x640fC3B9B607E324D7A3d89Fcb62C77Cc0Bd420A
    Call requestIndicator(feed) — no LINK needed
    Rate limit: 5 requests/day/address
    Returns real data — not mocks"""


@mcp.tool()
async def get_integration_guide(tier: str = "discovery") -> str:
    """Get Solidity code to integrate Pythia Oracle into a smart contract.

    Args:
        tier: Pricing tier — 'discovery' (single value), 'analysis', 'speed', or 'complete' (bundles). Default: discovery.
    """
    tier = tier.lower()
    if tier not in CONTRACTS["consumers"]:
        return f"Unknown tier '{tier}'. Choose: discovery, analysis, speed, complete"

    info = CONTRACTS["consumers"][tier]

    if tier == "discovery":
        return f"""Pythia Integration — Discovery Tier (Single Indicator)

Consumer: {info['address']}
Fee: {info['fee']}
Job ID: {info['job_id']}

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";

contract MyPythiaConsumer is ChainlinkClient, ConfirmedOwner {{
    using Chainlink for Chainlink.Request;

    uint256 public lastValue;
    bytes32 private jobId = {info['job_id']};
    uint256 private fee = 0.01 ether; // 0.01 LINK
    address private oracle = {CONTRACTS['operator']};

    constructor() ConfirmedOwner(msg.sender) {{
        _setChainlinkToken({CONTRACTS['link_token_erc677']});
        _setChainlinkOracle(oracle);
    }}

    /// @notice Request a single indicator value
    /// @param feed Feed name, e.g. "aave_EMA_5M_20" or "pol_RSI_1H_14"
    function requestIndicator(string memory feed) public onlyOwner returns (bytes32) {{
        Chainlink.Request memory req = _buildChainlinkRequest(
            jobId, address(this), this.fulfill.selector
        );
        req._add("feed", feed);
        return _sendChainlinkRequest(req, fee);
    }}

    function fulfill(bytes32 requestId, uint256 value) public recordChainlinkFulfillment(requestId) {{
        lastValue = value;
    }}

    function withdrawLink() public onlyOwner {{
        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.transfer(msg.sender, link.balanceOf(address(this))));
    }}
}}
```

Steps:
1. Deploy this contract on Polygon mainnet
2. Fund it with ERC-677 LINK (use PegSwap if you have bridged LINK)
3. Call requestIndicator("aave_EMA_5M_20") — result arrives in fulfill()
4. Read lastValue — it's the indicator × 1e18

Free trial: Use PythiaFaucet ({CONTRACTS['faucet']}) instead — no LINK needed."""

    else:
        return f"""Pythia Integration — {tier.upper()} Tier (Bundle)

Consumer: {info['address']}
Fee: {info['fee']}
Job ID: {info['job_id']}

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";

contract MyPythiaBundleConsumer is ChainlinkClient, ConfirmedOwner {{
    using Chainlink for Chainlink.Request;

    uint256[] public lastBundle;
    bytes32 private jobId = {info['job_id']};
    uint256 private fee = {info['fee'].replace(' LINK', '')} ether;
    address private oracle = {CONTRACTS['operator']};

    constructor() ConfirmedOwner(msg.sender) {{
        _setChainlinkToken({CONTRACTS['link_token_erc677']});
        _setChainlinkOracle(oracle);
    }}

    /// @notice Request a bundle of indicators for a token
    /// @param engineId Token engine ID, e.g. "aave", "pol", "uniswap"
    function requestBundle(string memory engineId) public onlyOwner returns (bytes32) {{
        Chainlink.Request memory req = _buildChainlinkRequest(
            jobId, address(this), this.fulfillBundle.selector
        );
        req._add("feed", engineId);
        req._add("bundle", "true");
        return _sendChainlinkRequest(req, fee);
    }}

    function fulfillBundle(bytes32 requestId, uint256[] memory values)
        public recordChainlinkFulfillment(requestId)
    {{
        lastBundle = values;
    }}

    function getBundleValue(uint256 index) public view returns (uint256) {{
        require(index < lastBundle.length, "Index out of bounds");
        return lastBundle[index];
    }}

    function withdrawLink() public onlyOwner {{
        LinkTokenInterface link = LinkTokenInterface(_chainlinkTokenAddress());
        require(link.transfer(msg.sender, link.balanceOf(address(this))));
    }}
}}
```

Steps:
1. Deploy on Polygon mainnet (gasLimit: 1,000,000 — bundles need more gas)
2. Fund with ERC-677 LINK
3. Call requestBundle("aave") — bundle arrives in fulfillBundle()
4. Read lastBundle[i] — each slot is an indicator × 1e18

Bundle contents vary by tier:
  Analysis = 1H + 1D + 1W indicators
  Speed = all 5M indicators
  Complete = everything

Docs: {WEBSITE_URL}"""


@mcp.tool()
async def get_system_status() -> str:
    """Get current Pythia Oracle system status — chains, token count, feed count, uptime."""
    data = await _fetch_feed_status()
    stats = data.get("stats", {})
    chains = data.get("chains", [])
    generated = data.get("generated_at", "unknown")

    lines = ["Pythia Oracle — System Status\n"]
    lines.append(f"  Data as of: {generated}")
    lines.append(f"  Tokens:     {stats.get('tokens', '?')}")
    lines.append(f"  Indicators: {stats.get('total_indicators', '?')}")
    lines.append(f"  Active feeds: {stats.get('active_feeds', '?')}")
    lines.append(f"  Uptime (30d): {stats.get('uptime_30d', '?')}%")
    lines.append(f"  Avg response: {stats.get('avg_response_ms', '?')}ms")
    lines.append(f"  Active incidents: {stats.get('active_incidents', 0)}")
    lines.append("")
    lines.append("Chains:")
    for chain in chains:
        lines.append(
            f"  {chain['name']}: {chain.get('status', '?')} "
            f"({chain.get('tokens', '?')} tokens, {chain.get('feeds', '?')} feeds)"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Entry point for the CLI script."""
    mcp.run()


if __name__ == "__main__":
    main()
