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
        "oracle reliability, get integration code, and learn about Pythia Events "
        "(on-chain indicator alert subscriptions)."
    ),
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_URL = "https://pythia.c3x-solutions.com/feed-status.json"
PRICING_URL = "https://pythia.c3x-solutions.com/feed-status.json"
WEBSITE_URL = "https://pythia.c3x-solutions.com"

FAUCET_ADDRESS = "0x640fC3B9B607E324D7A3d89Fcb62C77Cc0Bd420A"

# Job IDs live in Chainlink node job specs, not in feed-status.json
_JOB_IDS = {
    "discovery": "0x8920841054eb4082b5910af84afa005e00000000000000000000000000000000",
    "analysis": "0xa1ecae215cd9471a95095ab52e2f403600000000000000000000000000000000",
    "speed": "0x8a50dfe4645f41a993a175b486d9840600000000000000000000000000000000",
    "complete": "0x48d135697ade4c8faec5fe67bbc3f65b00000000000000000000000000000000",
}

_TIER_RETURNS = {
    "discovery": "uint256 (single indicator)",
    "analysis": "uint256[] (1H/1D/1W bundle)",
    "speed": "uint256[] (5M bundle)",
    "complete": "uint256[] (all indicators)",
}

# Fallback pricing — used when feed-status.json is unreachable
_FALLBACK_PRICING = {
    "discovery": 0.01,
    "analysis": 0.03,
    "speed": 0.05,
    "complete": 0.10,
}

# Fallback contracts — offline resilience
_FALLBACK_CONTRACTS = {
    "polygon_mainnet": {
        "display_name": "Polygon PoS",
        "chain_id": 137,
        "explorer": "https://polygonscan.com",
        "operator": "0xAA37710aF244514691629Aa15f4A5c271EaE6891",
        "link_token": "0xb0897686c545045aFc77CF20eC7A532E3120E0F1",
        "consumers": {
            "discovery": "0xeC2865d66ae6Af47926B02edd942A756b394F820",
            "analysis": "0x3b3aC62d73E537E3EF84D97aB5B84B51aF8dB316",
            "speed": "0xC406e7d9AC385e7AB43cBD56C74ad487f085d47B",
            "complete": "0x2dEC98fd7173802b351d1E28d0Cd5DdD20C24252",
        },
    },
}

_CONDITION_NAMES = {0: "ABOVE", 1: "BELOW", 2: "CROSSES_ABOVE", 3: "CROSSES_BELOW"}


def _parse_consumers(raw: dict) -> dict[str, str]:
    """Convert {"Discovery (0.01 LINK)": "0x..."} → {"discovery": "0x..."}."""
    parsed = {}
    for display_name, address in raw.items():
        tier = display_name.split()[0].lower() if display_name else ""
        if tier and address:
            parsed[tier] = address
    return parsed


def _get_contracts(data: dict | None = None) -> dict:
    """Get normalized contracts from feed-status.json, or fallback."""
    if data and "developer" in data and "contracts" in data["developer"]:
        result = {}
        for chain_key, chain_data in data["developer"]["contracts"].items():
            consumers_raw = chain_data.get("consumers", {})
            result[chain_key] = {
                "display_name": chain_data.get("display_name", chain_key),
                "chain_id": chain_data.get("chain_id"),
                "explorer": chain_data.get("explorer", ""),
                "operator": chain_data.get("operator", ""),
                "link_token": chain_data.get("link_token", ""),
                "consumers": _parse_consumers(consumers_raw),
            }
        if result:
            return result
    return _FALLBACK_CONTRACTS.copy()


def _get_mainnet(data: dict | None = None) -> dict:
    """Get polygon_mainnet contracts entry."""
    contracts = _get_contracts(data)
    return contracts.get("polygon_mainnet", next(iter(contracts.values())))


def _get_tier_fees(data: dict | None = None) -> dict[str, float]:
    """Extract tier fees from feed-status.json data, or return fallback."""
    if data and "tiers" in data:
        return {t["id"]: t["fee"] for t in data["tiers"] if "id" in t and "fee" in t}
    return _FALLBACK_PRICING.copy()


def _get_tier_fee(data: dict | None, tier: str) -> str:
    """Get fee string like '0.01 LINK' for a tier."""
    fees = _get_tier_fees(data)
    return f"{fees.get(tier, _FALLBACK_PRICING.get(tier, '?'))} LINK"

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
    lines.append(f"Free trial: PythiaFaucet at {FAUCET_ADDRESS}")
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
    """Get Pythia contract addresses for on-chain integration. Shows all supported chains."""
    data = await _fetch_data()
    all_contracts = _get_contracts(data)
    fees = _get_tier_fees(data)
    events = data.get("events", {}) if data else {}

    lines = ["Pythia Oracle — Contract Addresses\n"]

    for chain_key, chain in sorted(all_contracts.items()):
        chain_id = chain.get("chain_id", "?")
        lines.append(f"  {chain['display_name']} (Chain ID {chain_id})")
        lines.append(f"    Operator:            {chain['operator']}")
        lines.append(f"    LINK Token (ERC-677): {chain['link_token']}")
        lines.append("")
        lines.append("    Consumer Contracts (by tier):")
        for tier in ("discovery", "analysis", "speed", "complete"):
            addr = chain["consumers"].get(tier)
            if not addr:
                continue
            fee_val = fees.get(tier, "?")
            lines.append(f"      {tier.upper()} — {fee_val} LINK")
            lines.append(f"        Address: {addr}")
            lines.append(f"        Returns: {_TIER_RETURNS.get(tier, '?')}")
            lines.append(f"        Job ID:  {_JOB_IDS.get(tier, 'see website')}")
        lines.append("")

    # Events registries
    registries = events.get("registries", [])
    if registries:
        lines.append("  Event Registry (indicator alerts):")
        for reg in registries:
            lines.append(f"    {reg['chain']}: {reg['address']}")
        lines.append("")

    lines.append(f"  Faucet (free trial): {FAUCET_ADDRESS}")
    lines.append("\nIMPORTANT: Use ERC-677 LINK only (0xb08976...).")
    lines.append("Bridged ERC-20 LINK (0x53e0bc...) does NOT work with Chainlink.")
    lines.append("Use PegSwap (pegswap.chain.link) to convert if needed.")
    return "\n".join(lines)


@mcp.tool()
async def get_pricing() -> str:
    """Get Pythia pricing tiers and free trial info. Prices are live from the data feed."""
    data = await _fetch_data()
    fees = _get_tier_fees(data)

    d = fees.get("discovery", "?")
    a = fees.get("analysis", "?")
    s = fees.get("speed", "?")
    c = fees.get("complete", "?")

    return f"""Pythia Oracle — Pricing Tiers

  DISCOVERY — {d} LINK
    Any single indicator (EMA, RSI, Bollinger, Volatility)
    Returns: uint256
    Best for: one-off queries, specific signals

  ANALYSIS — {a} LINK
    All 1-hour, 1-day, and 1-week indicators bundled
    Returns: uint256[]
    Best for: protocols needing multi-timeframe view

  SPEED — {s} LINK
    All 5-minute indicators bundled
    Returns: uint256[]
    Best for: real-time trading, active rebalancing

  COMPLETE — {c} LINK
    Every indicator for a token (all timeframes)
    Returns: uint256[]
    Best for: comprehensive analysis

  FREE TRIAL — PythiaFaucet
    Address: {FAUCET_ADDRESS}
    No LINK needed. 5 requests/day/address. Real data."""


@mcp.tool()
async def get_integration_guide(tier: str = "discovery") -> str:
    """Get Solidity code to integrate Pythia into a smart contract.

    Args:
        tier: 'discovery' (single value), 'analysis', 'speed', or 'complete'.
    """
    tier = tier.lower()
    if tier not in _JOB_IDS:
        return f"Unknown tier '{tier}'. Choose: discovery, analysis, speed, complete"

    data = await _fetch_data()
    mainnet = _get_mainnet(data)
    consumer_addr = mainnet["consumers"].get(tier, "CHECK_WEBSITE")
    job_id = _JOB_IDS[tier]
    operator = mainnet["operator"]
    link_token = mainnet["link_token"]
    fee_str = _get_tier_fee(data, tier)

    if tier == "discovery":
        fee_num = _get_tier_fees(data).get("discovery", 0.01)
        return f"""Pythia Integration — Discovery Tier (Single Indicator)

Consumer: {consumer_addr}
Fee: {fee_str}
Job ID: {job_id}

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";

contract MyPythiaConsumer is ChainlinkClient, ConfirmedOwner {{
    using Chainlink for Chainlink.Request;

    uint256 public lastValue;
    bytes32 private jobId = {job_id};
    uint256 private fee = {fee_num} ether; // {fee_str}
    address private oracle = {operator};

    constructor() ConfirmedOwner(msg.sender) {{
        _setChainlinkToken({link_token});
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

Free trial: Use PythiaFaucet ({FAUCET_ADDRESS}) instead — no LINK needed."""

    else:
        fee_num = _get_tier_fees(data).get(tier, 0.10)
        return f"""Pythia Integration — {tier.upper()} Tier (Bundle)

Consumer: {consumer_addr}
Fee: {fee_str}
Job ID: {job_id}

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";

contract MyPythiaBundleConsumer is ChainlinkClient, ConfirmedOwner {{
    using Chainlink for Chainlink.Request;

    uint256[] public lastBundle;
    bytes32 private jobId = {job_id};
    uint256 private fee = {fee_num} ether; // {fee_str}
    address private oracle = {operator};

    constructor() ConfirmedOwner(msg.sender) {{
        _setChainlinkToken({link_token});
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
# Tools — Pythia Events (on-chain indicator alerts)
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_events_info() -> str:
    """Get overview of Pythia Events — on-chain indicator alert subscriptions.

    Returns pricing, supported conditions, subscriber flow, registry
    addresses per chain, and current subscription stats. Events let you
    subscribe once and get notified when an indicator crosses a threshold.
    """
    data = await _fetch_data()
    events = data.get("events", {}) if data else {}
    if not events:
        return ("Pythia Events info not available. "
                "Visit https://pythia.c3x-solutions.com for details.")

    lines = ["Pythia Events — On-Chain Indicator Alerts\n"]
    lines.append("Subscribe once, get notified when your condition is met.")
    lines.append("One-shot: fires once, remaining whole days refunded in LINK.\n")

    lines.append(f"Pricing: {events.get('pricing', '?')}")
    lines.append(f"Max duration: {events.get('max_days', 365)} days")
    lines.append(f"Threshold scale: {events.get('threshold_scale', '?')}")
    lines.append(f"Refund policy: {events.get('refund', '?')}\n")

    conditions = events.get("conditions", {})
    active = conditions.get("active", [])
    future = conditions.get("future", [])
    lines.append("Conditions:")
    for c in active:
        lines.append(f"  {c}  [active]")
    for c in future:
        lines.append(f"  {c}  [future — accepted, not yet processed]")
    lines.append("")

    lines.append("Subscriber Flow:")
    for i, step in enumerate(events.get("subscriber_flow", []), 1):
        lines.append(f"  {i}. {step}")
    lines.append("")

    registries = events.get("registries", [])
    if registries:
        lines.append("Event Registry Contracts:")
        for reg in registries:
            lines.append(f"  {reg['chain']}: {reg['address']}")
        lines.append("")

    stats = events.get("stats", {})
    active_subs = stats.get("active_subscriptions", 0)
    total_subs = stats.get("total_subscriptions", 0)
    lines.append(f"Stats: {active_subs} active / {total_subs} total subscriptions")
    lines.append("\nUse get_events_guide() for Solidity integration code.")
    lines.append("Use subscribe_info() to plan a specific subscription.")
    return "\n".join(lines)


@mcp.tool()
async def get_events_guide() -> str:
    """Get Solidity code to subscribe to Pythia Events (indicator alerts).

    Returns a complete contract that approves LINK, subscribes to an
    indicator alert, listens for PythiaEvent, and can cancel for a refund.
    """
    data = await _fetch_data()
    events = data.get("events", {}) if data else {}
    mainnet = _get_mainnet(data)
    link_token = mainnet["link_token"]

    registries = events.get("registries", [])
    mainnet_reg = next((r for r in registries if r["chain"] == "mainnet"), None)
    amoy_reg = next((r for r in registries if r["chain"] == "amoy"), None)
    mainnet_addr = mainnet_reg["address"] if mainnet_reg else "CHECK_WEBSITE"
    amoy_addr = amoy_reg["address"] if amoy_reg else "CHECK_WEBSITE"

    return f"""Pythia Events Integration — On-Chain Indicator Alerts

Registry (Mainnet): {mainnet_addr}
Registry (Amoy):    {amoy_addr}
LINK Token:         {link_token}

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@chainlink/contracts/src/v0.8/shared/interfaces/LinkTokenInterface.sol";
import "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";

interface IPythiaEventRegistry {{
    function subscribe(string calldata feedName, uint16 numDays,
        uint8 condition, int256 threshold) external returns (uint256 eventId);
    function cancelSubscription(uint256 eventId) external;
    function getCost(uint16 numDays) external view returns (uint256);
    function isActive(uint256 eventId) external view returns (bool);
}}

contract MyEventSubscriber is ConfirmedOwner {{
    LinkTokenInterface public immutable LINK;
    IPythiaEventRegistry public registry;
    uint256 public lastEventId;

    event Subscribed(uint256 indexed eventId, string feed);
    event Cancelled(uint256 indexed eventId);

    constructor(address _link, address _registry) ConfirmedOwner(msg.sender) {{
        LINK = LinkTokenInterface(_link);
        registry = IPythiaEventRegistry(_registry);
    }}

    /// @notice Subscribe to an indicator alert. Fund this contract with LINK first.
    /// @param feedName e.g. "pol_RSI_5M_14"
    /// @param numDays  1-365
    /// @param condition 0=ABOVE, 1=BELOW
    /// @param threshold 8 decimals (e.g. RSI 30 = 3000000000)
    function subscribe(
        string calldata feedName,
        uint16 numDays,
        uint8 condition,
        int256 threshold
    ) external onlyOwner returns (uint256 eventId) {{
        uint256 cost = registry.getCost(numDays);
        LINK.approve(address(registry), cost);
        eventId = registry.subscribe(feedName, numDays, condition, threshold);
        lastEventId = eventId;
        emit Subscribed(eventId, feedName);
    }}

    /// @notice Cancel subscription. Remaining whole days refunded in LINK.
    function cancel(uint256 eventId) external onlyOwner {{
        registry.cancelSubscription(eventId);
        emit Cancelled(eventId);
    }}

    function isActive(uint256 eventId) external view returns (bool) {{
        return registry.isActive(eventId);
    }}

    function withdrawLink() external onlyOwner {{
        LINK.transfer(msg.sender, LINK.balanceOf(address(this)));
    }}
}}
```

Steps:
1. Deploy with (_link, _registry) for your target chain
2. Fund the contract with LINK (e.g. 7 LINK for 7 days)
3. Call subscribe("pol_RSI_5M_14", 7, 1, 3000000000)
   → condition 1 = BELOW, threshold = RSI 30 (8 decimals)
4. Note the returned eventId
5. Listen for PythiaEvent(eventId) on the registry contract via RPC
6. When fired: the condition was met, react in your protocol

Conditions: 0=ABOVE, 1=BELOW (active). 2=CROSSES_ABOVE, 3=CROSSES_BELOW (future).
Threshold: 8 decimal places. RSI 30 = 3000000000, RSI 70 = 7000000000.
Refund: unused whole days returned in LINK on fire or cancel.

Deployment addresses:
  Mainnet: _link={link_token}, _registry={mainnet_addr}
  Amoy:    _link=0x0Fd9e8d3aF1aaee056EB9e802c3A762a667b1904, _registry={amoy_addr}"""


@mcp.tool()
async def subscribe_info(
    feed_name: str,
    condition: int = 1,
    days: int = 7,
) -> str:
    """Plan a specific Pythia Events subscription with cost and exact calls.

    Args:
        feed_name: Feed name to monitor (e.g. 'pol_RSI_5M_14', 'bitcoin_EMA_1H_20')
        condition: 0=ABOVE, 1=BELOW, 2=CROSSES_ABOVE, 3=CROSSES_BELOW
        days: Subscription duration in days (1-365)
    """
    if condition < 0 or condition > 3:
        return "Invalid condition. Use: 0=ABOVE, 1=BELOW, 2=CROSSES_ABOVE, 3=CROSSES_BELOW"
    if days < 1 or days > 365:
        return "Days must be 1-365."

    data = await _fetch_data()
    events = data.get("events", {}) if data else {}
    mainnet = _get_mainnet(data)
    registries = events.get("registries", [])
    cond_name = _CONDITION_NAMES.get(condition, "UNKNOWN")

    lines = [f"Pythia Events — Subscription Plan\n"]
    lines.append(f"  Feed:      {feed_name}")
    lines.append(f"  Condition: {cond_name} ({condition})")
    lines.append(f"  Duration:  {days} days")
    lines.append(f"  Cost:      {days} LINK ({events.get('pricing', '1 LINK/day')})")

    if condition >= 2:
        lines.append(f"\n  WARNING: {cond_name} is accepted but not yet processed.")
        lines.append("  Subscription will be stored; it fires when condition is activated.")

    lines.append(f"\n  Threshold: YOU MUST SET THIS — scaled to 8 decimals.")
    lines.append("  Examples:")
    lines.append("    RSI 30      → 3000000000")
    lines.append("    RSI 70      → 7000000000")
    lines.append("    EMA $2500   → 250000000000  (2500 * 1e8)")
    lines.append("    Vol 5%      → 500000000     (0.05 * 1e8)")

    lines.append("\nExact Calls (from your contract or EOA):\n")
    lines.append("  // Step 1: Approve LINK spending")
    lines.append(f'  LINK.approve(registry, {days} * 1e18);')
    lines.append("")
    lines.append("  // Step 2: Subscribe")
    lines.append(f'  uint256 eventId = registry.subscribe(')
    lines.append(f'      "{feed_name}",')
    lines.append(f"      {days},          // numDays")
    lines.append(f"      {condition},          // {cond_name}")
    lines.append(f"      YOUR_THRESHOLD  // 8 decimal places")
    lines.append(f"  );")
    lines.append("")
    lines.append("  // Step 3: Listen for the alert")
    lines.append("  // Off-chain: registry.on('PythiaEvent', (eventId, value) => { ... })")

    if registries:
        lines.append("\nRegistry Addresses:")
        for reg in registries:
            lines.append(f"  {reg['chain']}: {reg['address']}")

    lines.append(f"\nLINK Token (mainnet): {mainnet['link_token']}")
    lines.append(f"Refund: {events.get('refund', 'unused whole days refunded')}")
    lines.append(f"\nUse get_events_guide() for a complete Solidity contract.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Entry point for the CLI script."""
    mcp.run()


if __name__ == "__main__":
    main()
