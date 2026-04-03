#!/usr/bin/env python3
"""
Pythia Oracle MCP Server

On-chain calculated technical indicators (EMA, RSI, Bollinger Bands, Volatility)
for 22+ tokens across crypto, delivered via Chainlink on supported networks.

Data source: Pythia's public feed-status.json, updated every 15 minutes.
"""

import json
from datetime import datetime, timezone

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Pythia Oracle",
    instructions=(
        "Pythia Oracle — the first oracle delivering calculated technical indicators "
        "on-chain. EMA, RSI, Bollinger Bands, Volatility for 22+ tokens across "
        "all of crypto (BTC, SOL, TAO, RENDER, ONDO and more), delivered via "
        "Chainlink across supported networks. Use these tools to explore available data, check "
        "oracle reliability, and get integration code."
    ),
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_URL = "https://pythia.c3x-solutions.com/feed-status.json"
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

# Cache — 60s TTL (JSON updates every 15min, but keep responsive)
_cache: dict = {}
CACHE_TTL_SECONDS = 60


async def _fetch_data() -> dict:
    """Fetch feed-status.json with cache."""
    now = datetime.now(timezone.utc)
    cached = _cache.get("data")
    if cached and (now - cached["at"]).total_seconds() < CACHE_TTL_SECONDS:
        return cached["data"]

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(DATA_URL)
        resp.raise_for_status()
        data = resp.json()

    _cache["data"] = {"data": data, "at": now}
    return data


# ---------------------------------------------------------------------------
# Tools — Token Discovery
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_tokens() -> str:
    """List all tokens tracked by Pythia with status and reliability info.

    Returns token symbols, categories, data source count, 30-day uptime,
    and operational status. Covers cross-chain tokens (BTC, SOL, TAO,
    RENDER, ONDO, etc.) and DeFi tokens.
    """
    data = await _fetch_data()
    tokens = data.get("tokens", [])
    stats = data.get("stats", {})

    lines = [f"Pythia Oracle — {stats.get('tokens', len(tokens))} tokens, "
             f"{stats.get('total_indicators', '?')} indicator feeds\n"]
    lines.append(f"{'Symbol':<8} {'Engine ID':<28} {'Category':<16} {'Status':<6} "
                 f"{'Uptime':>7}  {'Src':>3}")
    lines.append("-" * 78)
    for t in sorted(tokens, key=lambda x: x.get("category", "")):
        status = t.get("status", "?")
        uptime = f"{t['uptime_30d']:.1f}%" if t.get("uptime_30d") is not None else "?"
        lines.append(
            f"{t['symbol']:<8} {t['engine_id']:<28} {t.get('category', '?'):<16} "
            f"{status:<6} {uptime:>7}  {t.get('sources', '?'):>3}"
        )
    lines.append(f"\nData delivered on-chain via Chainlink.")
    lines.append(f"Free trial: PythiaFaucet at {CONTRACTS['faucet']}")
    return "\n".join(lines)


@mcp.tool()
async def get_token_feeds(engine_id: str) -> str:
    """Get all available indicator feeds for a specific token.

    Shows every feed name (EMA, RSI, Bollinger, Volatility across all
    timeframes), the token's reliability stats, and data source count.
    Feed names are what you pass to the on-chain oracle to request data.

    Args:
        engine_id: Token engine ID (e.g., 'bitcoin', 'solana', 'bittensor',
                   'aave', 'pol'). Use list_tokens() to see all available IDs.
    """
    data = await _fetch_data()
    tokens = data.get("tokens", [])

    token = next((t for t in tokens if t["engine_id"] == engine_id), None)
    if not token:
        available = sorted(t["engine_id"] for t in tokens)
        return (
            f"No token found for '{engine_id}'.\n\n"
            f"Available: {', '.join(available)}"
        )

    feed_names = token.get("feed_names", [])
    lines = [
        f"{token['symbol']} ({token['name']}) — {token.get('pair', '?')}",
        f"Status: {token.get('status', '?')}  |  "
        f"30d uptime: {token.get('uptime_30d', '?')}%  |  "
        f"Data sources: {token.get('sources', '?')}",
        f"Category: {token.get('category', '?')}  |  "
        f"Ecosystem: {token.get('ecosystem', '?')}",
        f"\n{len(feed_names)} indicator feeds available:\n",
    ]

    # Group by indicator type
    groups: dict[str, list[str]] = {}
    for name in sorted(feed_names):
        # Strip token prefix to get indicator part
        suffix = name[len(engine_id) + 1:]
        cat = suffix.split("_")[0]
        groups.setdefault(cat, []).append(suffix)

    for cat, feeds in sorted(groups.items()):
        lines.append(f"  {cat}:")
        for feed in feeds:
            lines.append(f"    {engine_id}_{feed}")
        lines.append("")

    lines.append("To request any feed on-chain, pass the full feed name")
    lines.append("(e.g., 'bitcoin_RSI_1H_14') to the Pythia consumer contract.")
    lines.append(f"\nUse get_integration_guide() for Solidity code.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tools — Market Summary & Health
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_market_summary() -> str:
    """Get a summary of all tokens tracked by Pythia with operational overview.

    Returns system-wide stats, tokens grouped by status, uptime distribution,
    data source health, and infrastructure status. Useful for quickly
    understanding what Pythia covers and whether the system is healthy.
    """
    data = await _fetch_data()
    tokens = data.get("tokens", [])
    stats = data.get("stats", {})
    system = data.get("system", {})
    generated = data.get("generated_at", "unknown")

    lines = [f"Pythia Oracle — System Overview (as of {generated})\n"]

    # Overall stats
    lines.append("System Stats:")
    lines.append(f"  Tokens:           {stats.get('tokens', '?')}")
    lines.append(f"  Indicator feeds:  {stats.get('total_indicators', '?')}")
    lines.append(f"  Chains:           {stats.get('chains', '?')}")
    lines.append(f"  Ecosystems:       {stats.get('ecosystems', '?')}")
    lines.append(f"  Avg response:     {stats.get('avg_response_ms', '?')}ms")
    lines.append(f"  Active incidents: {stats.get('active_incidents', 0)}")
    lines.append("")

    # Tokens by status
    by_status: dict[str, list[str]] = {}
    for t in tokens:
        s = t.get("status", "unknown")
        by_status.setdefault(s, []).append(t["symbol"])

    lines.append("Tokens by Status:")
    for status in ["live", "warn", "down", "unknown"]:
        if status in by_status:
            syms = ", ".join(sorted(by_status[status]))
            lines.append(f"  {status:<6} ({len(by_status[status])}): {syms}")
    lines.append("")

    # Tokens by ecosystem
    by_eco: dict[str, list[str]] = {}
    for t in tokens:
        eco = t.get("ecosystem", "Other")
        by_eco.setdefault(eco, []).append(t["symbol"])

    lines.append("Coverage by Ecosystem:")
    for eco, syms in sorted(by_eco.items(), key=lambda x: -len(x[1])):
        lines.append(f"  {eco:<20} {len(syms)} tokens: {', '.join(sorted(syms))}")
    lines.append("")

    # Data sources
    sources = system.get("sources", [])
    if sources:
        lines.append("Data Sources:")
        for s in sources:
            lines.append(f"  {s['name']:<15} status: {s['status']}  (tier {s['tier']})")
        lines.append("")

    # Infrastructure
    infra = system.get("infrastructure", {})
    if infra:
        lines.append("Infrastructure:")
        for component, status in infra.items():
            lines.append(f"  {component:<15} {status}")

    return "\n".join(lines)


@mcp.tool()
async def check_oracle_health() -> str:
    """Check the reliability and uptime of Pythia's oracle system.

    Returns per-token 30-day uptime (sorted worst-first so problems
    surface immediately), recent daily status history, data source
    health, and infrastructure status. Use this to verify Pythia's
    reliability before integrating or relying on its data.
    """
    data = await _fetch_data()
    tokens = data.get("tokens", [])
    system = data.get("system", {})
    stats = data.get("stats", {})
    generated = data.get("generated_at", "unknown")

    lines = [f"Pythia Oracle — Health Report (as of {generated})\n"]

    # System-level
    incidents = stats.get("active_incidents", 0)
    if incidents > 0:
        lines.append(f"  *** {incidents} ACTIVE INCIDENT(S) ***\n")
    else:
        lines.append("  No active incidents.\n")

    # Infrastructure
    infra = system.get("infrastructure", {})
    all_ok = all(v == "ok" for v in infra.values())
    lines.append(f"Infrastructure: {'ALL OK' if all_ok else 'ISSUES DETECTED'}")
    if not all_ok:
        for component, status in infra.items():
            if status != "ok":
                lines.append(f"  {component}: {status}")
    lines.append("")

    # Data sources
    sources = system.get("sources", [])
    sources_ok = all(s["status"] == "ok" for s in sources)
    lines.append(f"Data Sources: {'ALL OK' if sources_ok else 'ISSUES DETECTED'}")
    for s in sources:
        marker = " " if s["status"] == "ok" else "!"
        lines.append(f" {marker} {s['name']:<15} {s['status']}")
    lines.append("")

    # Per-token uptime, worst first
    lines.append(f"{'Token':<8} {'Uptime 30d':>10}  {'Status':<6}  {'Src':>3}  Last 7 days")
    lines.append("-" * 65)

    sorted_tokens = sorted(tokens, key=lambda t: t.get("uptime_30d", 0))
    for t in sorted_tokens:
        uptime = t.get("uptime_30d")
        uptime_str = f"{uptime:.1f}%" if uptime is not None else "?"
        status = t.get("status", "?")

        # Last 7 days from uptime_days (most recent last)
        days = t.get("uptime_days", [])
        last_7 = days[-7:] if len(days) >= 7 else days
        day_str = " ".join("." if d == "ok" else "W" if d == "warn" else "X" for d in last_7)

        flag = " " if (uptime is not None and uptime >= 99.0) else "*"
        lines.append(
            f"{flag}{t['symbol']:<7} {uptime_str:>10}  {status:<6}  "
            f"{t.get('sources', '?'):>3}  {day_str}"
        )

    lines.append("")
    lines.append("Legend: . = ok, W = warming up, X = down")
    lines.append("* = below 99% uptime (investigate)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tools — Integration (static, rarely changes)
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_contracts() -> str:
    """Get Pythia contract addresses on Polygon for on-chain integration."""
    lines = ["Pythia Oracle — Contract Addresses (Polygon Mainnet, Chain ID 137)\n"]
    lines.append(f"  Operator:             {CONTRACTS['operator']}")
    lines.append(f"  LINK Token (ERC-677):  {CONTRACTS['link_token_erc677']}")
    lines.append(f"  Faucet (free trial):   {CONTRACTS['faucet']}")
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
    """Get Pythia pricing tiers and free trial info."""
    return """Pythia Oracle — Pricing Tiers

  DISCOVERY — 0.01 LINK
    Any single indicator (EMA, RSI, Bollinger, Volatility)
    Returns: uint256
    Best for: one-off queries, specific signals

  ANALYSIS — 0.03 LINK
    All 1-hour, 1-day, and 1-week indicators bundled
    Returns: uint256[]
    Best for: protocols needing multi-timeframe view

  SPEED — 0.05 LINK
    All 5-minute indicators bundled
    Returns: uint256[]
    Best for: real-time trading, active rebalancing

  COMPLETE — 0.10 LINK
    Every indicator for a token (all timeframes)
    Returns: uint256[]
    Best for: comprehensive analysis

  FREE TRIAL — PythiaFaucet
    Address: 0x640fC3B9B607E324D7A3d89Fcb62C77Cc0Bd420A
    No LINK needed. 5 requests/day/address. Real data."""


@mcp.tool()
async def get_integration_guide(tier: str = "discovery") -> str:
    """Get Solidity code to integrate Pythia into a smart contract.

    Args:
        tier: 'discovery' (single value), 'analysis', 'speed', or 'complete'.
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
    /// @param feed Feed name, e.g. "bitcoin_RSI_1H_14" or "solana_EMA_5M_20"
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
3. Call requestIndicator("bitcoin_RSI_1H_14") — result arrives in fulfill()
4. Read lastValue — it's the indicator x 1e18

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
    /// @param engineId Token engine ID, e.g. "bitcoin", "solana", "aave"
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
3. Call requestBundle("bitcoin") — bundle arrives in fulfillBundle()
4. Read lastBundle[i] — each slot is an indicator x 1e18

Bundle contents vary by tier:
  Analysis = 1H + 1D + 1W indicators
  Speed = all 5M indicators
  Complete = everything

Docs: {WEBSITE_URL}"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Entry point for the CLI script."""
    mcp.run()


if __name__ == "__main__":
    main()
