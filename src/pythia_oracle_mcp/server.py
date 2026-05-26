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
        "oracle reliability, get integration code, learn about Pythia Events "
        "(on-chain indicator alert subscriptions), and Pythia Visions "
        "(walk-forward validated market intelligence on-chain — pattern type, confidence, indicator snapshot, and feeds-to-watch for confirmation)."
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

# No baked-in fallbacks. The MCP server is a thin client over feed-status.json
# (the canonical source updated every 15 min by the data engine). If the live
# JSON is unreachable, tools raise a clear error rather than serve stale data.
# Rationale: Pythia is hot data — token catalogs, Vision patterns, pricing tiers,
# and contract addresses change. Baked-in defaults rot the moment the package
# version drifts from production state. Fail-loud beats silent stale.

_CONDITION_NAMES = {0: "ABOVE", 1: "BELOW", 2: "CROSSES_ABOVE", 3: "CROSSES_BELOW"}


def _parse_consumers(raw: dict) -> dict[str, str]:
    """Convert {"Discovery (0.01 LINK)": "0x..."} → {"discovery": "0x..."}."""
    parsed = {}
    for display_name, address in raw.items():
        tier = display_name.split()[0].lower() if display_name else ""
        if tier and address:
            parsed[tier] = address
    return parsed


def _get_contracts(data: dict) -> dict:
    """Extract normalized contracts from live feed-status.json data.

    Raises RuntimeError if the data is missing the developer.contracts section
    (would only happen if generate_site_data.py is broken or schema changed).
    """
    contracts = data.get("developer", {}).get("contracts")
    if not contracts:
        raise RuntimeError(
            "feed-status.json is missing developer.contracts. "
            "This is a structural error in the live data — check the data engine."
        )

    result = {}
    for chain_key, chain_data in contracts.items():
        consumers_raw = chain_data.get("consumers", {})
        result[chain_key] = {
            "display_name": chain_data.get("display_name", chain_key),
            "chain_id": chain_data.get("chain_id"),
            "explorer": chain_data.get("explorer", ""),
            "operator": chain_data.get("operator", ""),
            "link_token": chain_data.get("link_token", ""),
            "consumers": _parse_consumers(consumers_raw),
        }
    return result


def _get_mainnet(data: dict) -> dict:
    """Get polygon_mainnet contracts entry from live data."""
    contracts = _get_contracts(data)
    return contracts.get("polygon_mainnet", next(iter(contracts.values())))


def _vision_registries(data: dict) -> list[dict]:
    """Return visions.registries[] (multi-chain), falling back to the legacy singular shape."""
    visions = data.get("visions", {}) if data else {}
    regs = visions.get("registries", [])
    if regs:
        return regs
    legacy = visions.get("registry", "")
    return [{"chain": "mainnet", "address": legacy}] if legacy else []


def _chain_display_names(data: dict) -> dict[str, str]:
    """Map registry chain key ('mainnet', 'arbitrum', ...) to display name."""
    return {
        chain_key.removeprefix("polygon_"): c.get("display_name", chain_key)
        for chain_key, c in _get_contracts(data).items()
    }


def _get_tier_fees(data: dict) -> dict[str, float]:
    """Extract tier fees from live feed-status.json data.

    Raises RuntimeError if tiers section is missing.
    """
    tiers = data.get("tiers")
    if not tiers:
        raise RuntimeError(
            "feed-status.json is missing the tiers section. "
            "This is a structural error in the live data — check the data engine."
        )
    return {t["id"]: t["fee"] for t in tiers if "id" in t and "fee" in t}


def _get_tier_fee(data: dict, tier: str) -> str:
    """Get fee string like '0.01 LINK' for a tier from live data."""
    fees = _get_tier_fees(data)
    if tier not in fees:
        raise RuntimeError(f"Tier '{tier}' not found in live pricing data. Available: {list(fees)}")
    return f"{fees[tier]} LINK"

# Cache — 60s TTL (JSON updates every 15min, but keep responsive)
_cache: dict = {}
CACHE_TTL_SECONDS = 60


async def _fetch_data() -> dict:
    """Fetch feed-status.json from the live Pythia data engine.

    Cached for CACHE_TTL_SECONDS to keep tool responses fast. Raises RuntimeError
    with a clear message if the live URL is unreachable — there is no baked-in
    fallback. AI consumers should retry shortly or check status; serving stale
    data silently would be worse than a clear failure.
    """
    now = datetime.now(timezone.utc)
    cached = _cache.get("data")
    if cached and (now - cached["at"]).total_seconds() < CACHE_TTL_SECONDS:
        return cached["data"]

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(DATA_URL)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(
            f"Pythia data unreachable: GET {DATA_URL} failed with "
            f"{type(e).__name__}: {e}. "
            "MCP cannot serve token, pattern, pricing, or contract data without the "
            "live JSON. Retry shortly, or check https://pythia.c3x-solutions.com/status."
        ) from e

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

    chain_meta = {
        chain_key.removeprefix("polygon_"): {
            "display_name": c.get("display_name", chain_key),
            "link_token": c.get("link_token", ""),
        }
        for chain_key, c in _get_contracts(data).items()
    }
    registries = events.get("registries", [])
    name_width = max(
        (len(chain_meta.get(r["chain"], {}).get("display_name", r["chain"])) for r in registries),
        default=0,
    )
    header_lines = ["Event Registry — deploy on whichever chain you integrate with:"]
    for r in registries:
        name = chain_meta.get(r["chain"], {}).get("display_name", r["chain"])
        header_lines.append(f"  {name:<{name_width}}  {r['address']}")
    header_block = "\n".join(header_lines)

    deploy_lines = ["Deployment addresses (LINK token + registry per chain):"]
    for r in registries:
        meta = chain_meta.get(r["chain"], {})
        name = meta.get("display_name", r["chain"])
        link = meta.get("link_token") or "CHECK_WEBSITE"
        deploy_lines.append(f"  {name:<{name_width}}  _link={link}  _registry={r['address']}")
    deploy_block = "\n".join(deploy_lines)

    return f"""Pythia Events Integration — On-Chain Indicator Alerts

{header_block}

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

{deploy_block}"""


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
# Tools — Pythia Visions (AI market intelligence)
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_visions_info() -> str:
    """Get overview of Pythia Visions — walk-forward validated market intelligence on-chain.

    Returns the walk-forward validated patterns with accuracy stats, the Vision Registry
    contract address, subscription info (FREE), evaluation frequency, and
    supported tokens. Visions are pattern detections that passed walk-forward
    validation across multiple years of history. Live token + pattern set is
    returned in the response (canonical source: feed-status.json visions section).
    """
    data = await _fetch_data()
    visions = data.get("visions", {})

    registries = _vision_registries(data)
    patterns = visions.get("patterns", [])
    tokens = visions.get("tokens", [])
    stats = visions.get("stats", {})

    if not patterns:
        return (
            "Pythia Visions catalog is empty in the live data. "
            "This may mean Visions are not yet deployed on this environment, "
            "or feed-status.json is missing the visions.patterns section. "
            "Check https://pythia.c3x-solutions.com/feed-status.json directly."
        )

    lines = ["Pythia Visions — Walk-Forward Validated Market Intelligence On-Chain\n"]
    lines.append(
        "Walk-forward validated pattern detections delivered on-chain via "
        "Chainlink. FREE to subscribe."
    )
    lines.append("")

    lines.append("Detected Patterns (validated 2017-2026, 75K+ candles):\n")
    lines.append(f"  {'Token':<5} {'Pattern':<22} {'Code':<6} {'Accuracy':<10} {'Avg Return':<14} {'Frequency':<14} {'Folds'}")
    lines.append(f"  {'-'*5} {'-'*22} {'-'*6} {'-'*10} {'-'*14} {'-'*14} {'-'*5}")
    for p in patterns:
        lines.append(
            f"  {p.get('token', '?'):<5} {p['name']:<22} {p['code']:<6} {p['accuracy']:<10} "
            f"{p['avg_return']:<14} {p['frequency']:<14} {p.get('fold_validation', '?')}"
        )
    lines.append("")

    lines.append("How to Use:")
    lines.append("  1. Subscribe — one call, free, permissionless: subscribe(keccak256(\"BTC\"))")
    lines.append("  2. Receive — your contract gets VisionFired events with pattern, confidence, indicators, analysis, and feeds-to-watch")
    lines.append("  3. React — read the payload on-chain, auto-subscribe to confirmation Events, trigger your strategy")
    lines.append("")

    display_for = _chain_display_names(data)
    lines.append("Vision Registry (deployed on every chain — subscription is FREE everywhere):")
    name_width = max((len(display_for.get(r["chain"], r["chain"])) for r in registries), default=0)
    for r in registries:
        name = display_for.get(r["chain"], r["chain"])
        lines.append(f"  {name:<{name_width}}  {r['address']}")
    lines.append(f"Subscription fee: FREE")
    lines.append(f"Tokens: {', '.join(tokens)}")
    lines.append(f"Signal frequency: ~107 Visions/year for BTC (100 OVERSOLD + 7 CAPITULATION), ~13/year for ETH")
    lines.append("")

    if stats.get("total_fired"):
        lines.append(f"Stats: {stats['total_fired']} total fired, "
                     f"avg confidence {stats.get('avg_confidence', 'N/A')}")
        lines.append("")

    lines.append("Use get_visions_guide() for Solidity integration code.")
    lines.append("Use get_vision_history() for recent Visions fired.")
    return "\n".join(lines)


@mcp.tool()
async def get_visions_guide() -> str:
    """Get Solidity code to subscribe to Pythia Visions and listen for VisionFired events.

    Returns a complete contract that subscribes to the PythiaVisionRegistry,
    receives VisionFired events with pattern type, confidence, direction, price,
    and full analysis payload. Subscription is FREE (no LINK required).
    """
    data = await _fetch_data()
    registries = _vision_registries(data)
    if not registries:
        raise RuntimeError(
            "Pythia Visions registries missing from live data. "
            "Visions may not be deployed on this environment yet. "
            "Check https://pythia.c3x-solutions.com/feed-status.json visions.registries."
        )

    display_for = _chain_display_names(data)
    name_width = max(
        (len(display_for.get(r["chain"], r["chain"])) for r in registries),
        default=0,
    )
    header_lines = ["Vision Registry — subscription is FREE on every chain (no LINK required):"]
    for r in registries:
        name = display_for.get(r["chain"], r["chain"])
        header_lines.append(f"  {name:<{name_width}}  {r['address']}")
    header_block = "\n".join(header_lines)

    deploy_lines = ["Deployment (deploy one subscriber per chain you want to listen on):"]
    for r in registries:
        name = display_for.get(r["chain"], r["chain"])
        deploy_lines.append(f"  {name:<{name_width}}  _registry={r['address']}")
    deploy_block = "\n".join(deploy_lines)

    return f"""Pythia Visions Integration — Walk-Forward Validated Market Intelligence On-Chain

{header_block}

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IPythiaVisionRegistry {{
    function subscribe(bytes32 tokenId) external;
    function unsubscribe(bytes32 tokenId) external;
    function isSubscribed(address subscriber, bytes32 tokenId) external view returns (bool);
    function getSubscriberCount(bytes32 tokenId) external view returns (uint256);
    function getVisionCount(bytes32 tokenId) external view returns (uint256);
    function getLastVisionAt(bytes32 tokenId) external view returns (uint256);
}}

contract MyVisionSubscriber {{
    IPythiaVisionRegistry public immutable registry;

    // Token IDs are keccak256 hashes of the token name
    bytes32 public constant BTC = keccak256("BTC");
    bytes32 public constant ETH = keccak256("ETH");

    // Fired by PythiaVisionRegistry when a pattern is detected
    event VisionFired(
        bytes32 indexed tokenId,   // keccak256("BTC") or keccak256("ETH")
        uint8 patternType,          // per-token high nibble: BTC=0x1_, ETH=0x2_
        uint8 confidence,           // Confidence score within pattern's historical range
        uint8 direction,            // 1 = BULLISH
        uint256 price,              // 18 decimals
        bytes payload               // Full JSON (indicators + analysis)
    );

    constructor(address _registry) {{
        registry = IPythiaVisionRegistry(_registry);
    }}

    /// @notice Subscribe to Visions for a token. FREE — no LINK required.
    function subscribeToken(bytes32 tokenId) external {{
        registry.subscribe(tokenId);
    }}

    /// @notice Unsubscribe.
    function unsubscribeToken(bytes32 tokenId) external {{
        registry.unsubscribe(tokenId);
    }}

    /// @notice Subscribe to BTC Visions.
    function subscribeBTC() external {{
        registry.subscribe(BTC);
    }}

    /// @notice Subscribe to ETH Visions.
    function subscribeETH() external {{
        registry.subscribe(ETH);
    }}
}}
```

Steps:
1. Deploy with (_registry) for the chain you want to subscribe on (addresses below)
2. Call subscribeBTC() / subscribeETH() — no LINK needed, subscription is FREE
3. Listen for VisionFired events on the registry contract via RPC/WebSocket
4. Decode the payload bytes to get the full analysis JSON

Pattern Types (walk-forward validated):
  Per-token high nibble: BTC=0x1_, ETH=0x2_, next token=0x3_, etc.
  Live pattern catalog (codes, accuracy ranges, fold validation, fires/yr,
  failure profile) — call get_visions_info() for the current set.

Payload JSON includes: indicators (RSI, EMA, Bollinger, VWAP, ATR),
pattern details, confidence score, analysis narrative,
and feeds-to-watch for confirmation.

Token IDs: keccak256 of the token name.
  BTC = keccak256("BTC") = 0xe98e2830be1a7e4156d656a7505e65d08c67660dc618072422e9c78053c261e9
  ETH = keccak256("ETH") = 0xaaaebeba3810b1e6b70781f14b2d72c1cb89c0b2b320c43bb67ff79f562f5ff4

{deploy_block}"""


@mcp.tool()
async def get_vision_history(token: str = "BTC") -> str:
    """Get recent Pythia Visions fired for a token with pattern breakdown and stats.

    Args:
        token: Token symbol to check (default: BTC). Case-insensitive.
               Currently live: BTC, ETH.
    """
    data = await _fetch_data()
    visions = data.get("visions", {})

    if not visions:
        return ("Pythia Visions data not available yet. "
                "Use get_visions_info() for pattern details and contract address.")

    recent = visions.get("recent", [])
    stats = visions.get("stats", {})
    registries = _vision_registries(data)
    token_upper = token.upper()

    # Filter by token
    filtered = [v for v in recent if v.get("token", "").upper() == token_upper]

    lines = [f"Pythia Visions — {token_upper} History\n"]
    if registries:
        display_for = _chain_display_names(data)
        chain_list = ", ".join(
            f"{display_for.get(r['chain'], r['chain'])} ({r['address']})" for r in registries
        )
        lines.append(f"Registry deployed on: {chain_list}")
    lines.append(f"Subscription: FREE\n")

    if not filtered:
        lines.append(f"No Visions have fired for {token_upper} yet.")
        lines.append(f"\nAvailable tokens: {', '.join(visions.get('tokens', []))}")
        lines.append("\nUse get_visions_info() for pattern details.")
        return "\n".join(lines)

    lines.append(f"Recent Visions ({len(filtered)} shown):\n")
    for v in filtered:
        lines.append(f"  {v.get('fired_at', '?')}")
        lines.append(f"    Pattern:    {v.get('pattern_name', '?')}")
        lines.append(f"    Confidence: {v.get('confidence', '?')}")
        lines.append(f"    Direction:  {v.get('direction', '?')}")
        lines.append(f"    Price:      ${v.get('price_usd', 0):,.2f}")
        lines.append("")

    # Pattern breakdown
    pattern_counts: dict[str, list[int]] = {}
    for v in filtered:
        name = v.get("pattern_name", "?")
        conf = v.get("confidence", 0)
        if name not in pattern_counts:
            pattern_counts[name] = []
        pattern_counts[name].append(conf)

    lines.append("Pattern Breakdown:\n")
    lines.append(f"  {'Pattern':<28} {'Fires':<7} {'Avg Confidence'}")
    lines.append(f"  {'-'*28} {'-'*7} {'-'*14}")
    for name, confs in sorted(pattern_counts.items(), key=lambda x: -len(x[1])):
        avg = sum(confs) / len(confs) if confs else 0
        lines.append(f"  {name:<28} {len(confs):<7} {avg:.1f}")
    lines.append("")

    if stats.get("total_fired"):
        lines.append(f"Overall: {stats['total_fired']} total fired, "
                     f"avg confidence {stats.get('avg_confidence', 'N/A')}")

    lines.append("\nUse get_vision_payload(vision_id) for the full enriched object")
    lines.append("(failure profile, cooldown context, concurrent fires).")
    lines.append("Use get_visions_guide() for Solidity integration code.")
    return "\n".join(lines)


@mcp.tool()
async def get_vision_payload(vision_id: int) -> str:
    """Get the full enriched object for a fired Pythia Vision by id.

    Returns the rich AI-facing companion to the on-chain VisionFired event:
    pattern metadata with numeric ranges, failure profile (avg return when
    correct, avg drawdown when wrong, worst drawdown), cooldown context
    (hours since last same-pattern fire on this token, confidence delta vs
    last fire), and concurrent fires from other tokens within the last 24h.

    Lightweight on-chain consumers can decode the VisionFired payload bytes
    directly. AI agents reasoning about a specific Vision should use this
    tool — it contains the data needed to size positions and compare against
    historical failure modes, which the on-chain event payload does not.

    Args:
        vision_id: integer id of the Vision (returned by get_vision_history)

    Returns:
        Multi-section text report. If vision_id is not in the recent window
        (last 20 fires per token), returns a helpful pointer to history.
    """
    data = await _fetch_data()
    visions = data.get("visions", {})
    recent = visions.get("recent", [])
    patterns = visions.get("patterns", [])

    found = next((v for v in recent if v.get("id") == vision_id), None)
    if not found:
        return (
            f"Vision id={vision_id} not in recent fires (last 20 per token).\n"
            f"Use get_vision_history(token=...) to find available ids per token."
        )

    pattern_meta = next(
        (p for p in patterns
         if p.get("name") == found.get("pattern_name")
         and p.get("token") == found.get("token")),
        None,
    )

    out = [
        f"Pythia Vision — id={vision_id}",
        f"Schema version: {visions.get('schema_version', 'v1')}",
        "",
        "─── Fire ───────────────────────────────────────",
        f"  Token:         {found.get('token')}",
        f"  Pattern:       {found.get('pattern_name')} ({hex(found.get('pattern_type', 0)) if isinstance(found.get('pattern_type'), int) else found.get('pattern_type')})",
        f"  Direction:     {found.get('direction')}",
        f"  Confidence:    {found.get('confidence')} / 100",
        f"  Price at fire: ${found.get('price_usd', 0):,.2f}",
        f"  Fired at:      {found.get('fired_at')}",
        f"  Chain:         {found.get('chain')}",
        f"  AI narrative:  {'available' if found.get('haiku_available') else 'mechanical only (AI agent unavailable at fire time)'}",
    ]

    # Cooldown / context
    out += ["", "─── Cooldown context ──────────────────────────"]
    cd_same = found.get("cooldown_hours_same_pattern")
    cd_tok = found.get("cooldown_hours_token")
    last_conf = found.get("last_same_pattern_confidence")
    delta = found.get("confidence_delta")
    if cd_same is None and cd_tok is None:
        out.append("  No prior fires for this token — first Vision recorded.")
    else:
        if cd_same is not None:
            out.append(f"  Hours since last same-pattern fire ({found.get('pattern_name')}): {cd_same}")
            if last_conf is not None:
                out.append(f"  Last same-pattern confidence: {last_conf}  →  delta: {delta:+d}")
        else:
            out.append(f"  First time {found.get('pattern_name')} has fired on {found.get('token')}.")
        if cd_tok is not None and cd_tok != cd_same:
            out.append(f"  Hours since last fire on {found.get('token')} (any pattern): {cd_tok}")

    # Concurrent
    concurrent = found.get("concurrent_patterns_24h", []) or []
    out += ["", "─── Concurrent fires (last 24h, other contexts) ──"]
    if not concurrent:
        out.append("  No other fires in the prior 24h — this Vision is idiosyncratic, not market-wide.")
    else:
        for c in concurrent:
            out.append(f"  {c.get('fired_at')}  {c.get('token')} {c.get('pattern_name')}  conf={c.get('confidence')}")
        same_token_count = sum(1 for c in concurrent if c.get("token") == found.get("token"))
        cross_token_count = len(concurrent) - same_token_count
        if cross_token_count >= 2:
            out.append(f"  → {cross_token_count} cross-token fires in last 24h suggests market-wide context.")

    # Failure profile
    out += ["", "─── Failure profile (9-year backtest) ─────────"]
    if pattern_meta:
        fp = pattern_meta.get("failure_profile", {})
        out.append(f"  Pattern:                {pattern_meta.get('name')} ({pattern_meta.get('code')})")
        out.append(f"  Data span:              {pattern_meta.get('data_span_years')}")
        out.append(f"  Total fires (backtest): {fp.get('total_fires_backtest', '?')}")
        out.append(f"  Up-rate (24h):          {fp.get('up_rate_pct', '?')}%  (vs {fp.get('base_up_rate_pct', '?')}% baseline → +{fp.get('edge_vs_baseline_pp', '?')}pp edge)")
        out.append(f"  Avg return when correct: {fp.get('avg_return_when_correct_pct', '?'):+}%")
        out.append(f"  Avg return when wrong:   {fp.get('avg_return_when_wrong_pct', '?'):+}%  ← drawdown profile")
        out.append(f"  Worst single drawdown:   {fp.get('worst_drawdown_pct', '?'):+}%")
        out.append(f"  Best single return:      {fp.get('best_return_pct', '?'):+}%")
        out.append(f"  Median 24h return:       {fp.get('median_return_pct', '?'):+}%")
        out.append("")
        ar = pattern_meta.get("accuracy_range_pct", {})
        fv = pattern_meta.get("fold_validation_ratio", {})
        out.append(f"  Accuracy range:         {ar.get('min')}–{ar.get('max')}% (point: {ar.get('point')}%)")
        out.append(f"  Fold validation:        {fv.get('passed')}/{fv.get('total')} ({fv.get('ratio', 0)*100:.0f}%)")
        out.append(f"  Fires/year (estimate):  {pattern_meta.get('fires_per_year_estimate')}")
    else:
        out.append("  Pattern metadata not found in catalog. Use get_visions_info() for catalog.")

    out.append("")
    out.append("Note: failure profile is from backtest. Live calibration arrives once vision_outcomes")
    out.append("populates (outcome-tracking cron).")

    return "\n".join(out)


@mcp.tool()
async def lookup_event_feed(feed_id_hex: str) -> str:
    """Reverse-lookup a Pythia Event feedId (bytes32) to its human-readable feed name.

    Subscribers receive `bytes32 feedId` in SubscriptionCreated and PythiaEvent
    events. This tool maps that hash back to the canonical feed name (e.g.
    'pol_RSI_5M_14') so dApps don't need to maintain their own feedId → name
    table or query the registry contract on every event.

    Args:
        feed_id_hex: bytes32 hash, with or without '0x' prefix, any case.

    Returns:
        Single-section report with feed_name + matching token + indicator
        suffix. If the hash is not in the registered lookup table, returns
        a diagnostic pointer.
    """
    h = feed_id_hex.strip().lower()
    if not h.startswith("0x"):
        h = "0x" + h

    data = await _fetch_data()
    events = data.get("events", {}) if data else {}
    lookup = events.get("feed_hash_lookup", {})

    feed_name = lookup.get(h)
    if not feed_name:
        return (
            f"Feed id {feed_id_hex} not found in registered lookup table.\n"
            "Possible reasons:\n"
            "  - Invalid hash (must be keccak256(feed_name) as bytes32)\n"
            "  - Feed not yet registered with the Event registry\n"
            "  - Feed deactivated\n"
            f"Total registered feeds: {len(lookup)}. Use list_tokens() + "
            "get_token_feeds(engine_id) to discover live feed names."
        )

    parts = feed_name.split("_", 1)
    engine_id = parts[0] if parts else feed_name
    suffix = parts[1] if len(parts) > 1 else ""

    tokens = data.get("tokens", []) if data else []
    token = next((t for t in tokens if t.get("engine_id") == engine_id), None)

    out = [
        f"Feed name: {feed_name}",
        f"Feed ID:   {h}",
    ]
    if token:
        out.append(f"Token:     {token.get('symbol')} ({token.get('name')})")
        out.append(f"Engine id: {engine_id}")
    if suffix:
        out.append(f"Indicator: {suffix}")
    return "\n".join(out)


@mcp.tool()
async def list_subscriptions(owner_address: str) -> str:
    """Enumerate active Pythia Event subscriptions owned by an address.

    Returns every subscription where active=true (not yet fired, expired, or
    cancelled). Without this tool, dApps and dashboards have to replay every
    SubscriptionCreated log from the registry deploy block to discover what
    an owner is currently subscribed to.

    Args:
        owner_address: subscriber wallet address ('0x...', case-insensitive).

    Returns:
        Multi-section report listing each active subscription with feed name,
        condition + threshold, expiry, registry address, and creation tx.
    """
    addr = owner_address.strip().lower()
    if not addr.startswith("0x"):
        addr = "0x" + addr

    data = await _fetch_data()
    events = data.get("events", {}) if data else {}
    subs = events.get("subscriptions", [])

    matched = [s for s in subs if (s.get("owner") or "").lower() == addr]

    if not matched:
        return (
            f"No active subscriptions for {addr}.\n"
            "This means: never subscribed on a tracked registry, all "
            "subscriptions already fired / expired / cancelled, or the\n"
            "off-chain sync hasn't caught up yet (event_sync.py runs every "
            "2 minutes)."
        )

    out = [
        f"Active Pythia Event subscriptions for {addr}",
        f"Count: {len(matched)}",
        "",
    ]
    for i, s in enumerate(matched, 1):
        out.append(f"[{i}] sub_id={s.get('sub_id')} on {s.get('source_chain')}")
        out.append(f"    Registry:   {s.get('registry')}")
        feed_id = s.get("feed_id") or ""
        feed_id_short = (feed_id[:12] + "…") if len(feed_id) > 14 else feed_id
        out.append(f"    Feed:       {s.get('feed_name', '?')} ({feed_id_short})")
        out.append(f"    Condition:  {s.get('condition')} {s.get('threshold')}")
        out.append(f"    Feed chain: {s.get('feed_chain')}")
        out.append(f"    Expires:    {s.get('expires_at')}")
        out.append(f"    Created:    {s.get('created_at')}")
        if s.get("tx_hash"):
            out.append(f"    Tx:         {s.get('tx_hash')}")
        out.append("")

    out.append(
        "Cancel early via cancelSubscription(sub_id) on the registry — "
        "refunds remaining whole-day LINK."
    )
    return "\n".join(out)


@mcp.tool()
async def get_feed_value(feed_name: str) -> str:
    """Get the latest computed value of a Pythia indicator feed.

    Reads from the live cache (feed_values table) populated by the indicator
    pipeline on every cycle. Off-chain AI agents use this when reasoning
    about a Vision context, choosing an Event threshold, or sanity-checking
    a feed's current level. On-chain consumers should request the value
    through oracle.request() to get a Chainlink-attested response — see
    get_integration_guide().

    Args:
        feed_name: full feed name (e.g. 'bitcoin_RSI_1H_14', 'pol_EMA_5M_20').

    Returns:
        Latest value + computed_at + chain, one block per chain if a feed
        exists on multiple chains. If the feed has no cached value, returns
        a diagnostic pointer (warm-up window, deactivated, or unknown name).
    """
    data = await _fetch_data()
    feeds = data.get("feed_values_current", []) if data else []

    matches = [f for f in feeds if f.get("feed_name") == feed_name]
    if not matches:
        return (
            f"Feed '{feed_name}' has no current value in the live cache.\n"
            "Possible reasons:\n"
            "  - Feed name not registered (use list_tokens() + "
            "get_token_feeds(engine_id) to discover)\n"
            "  - Feed inside its warm-up window (1H/1D/1W indicators on "
            "freshly-onboarded tokens)\n"
            "  - Pipeline degraded — check check_oracle_health()"
        )

    out = [f"Feed: {feed_name}"]
    for m in matches:
        out.append("")
        out.append(f"  Chain:       {m.get('chain')}")
        out.append(f"  Value:       {m.get('value')}")
        out.append(f"  Computed at: {m.get('computed_at')}")
    out.append("")
    out.append(
        "Cached value updated by the indicator pipeline. For a Chainlink-"
        "attested on-chain value, use oracle.request() — see "
        "get_integration_guide()."
    )
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Entry point for the CLI script."""
    mcp.run()


if __name__ == "__main__":
    main()
