# Publishing Pythia MCP Server — Ivan's Steps

Everything is built and ready. You need to do these manual steps (accounts, auth).

## Step 1: Create GitHub Repo (5 min)

Go to https://github.com/new

- **Owner:** Create org `PythiaOracle` first (https://github.com/account/organizations/new) or use your personal account
- **Repo name:** `pythia-oracle-mcp`
- **Description:** `MCP server for Pythia Oracle — on-chain calculated indicators (EMA, RSI, VWAP, Bollinger) via Chainlink`
- **Public**, MIT license (already in the code)
- **Don't** initialize with README (we already have one)

Then push:
```bash
cd mcp-server
git init
git add .
git commit -m "Initial release v0.1.0"
git remote add origin https://github.com/PythiaOracle/pythia-oracle-mcp.git
git branch -M main
git push -u origin main
```

## Step 2: Publish to PyPI (5 min)

Create account at https://pypi.org/account/register/ if you don't have one.

Create API token at https://pypi.org/manage/account/token/
- Scope: Entire account (first time) or project-specific after first upload

```bash
pip install twine
cd mcp-server
# Package already built in dist/
twine upload dist/*
# Enter: __token__ as username, paste API token as password
```

After upload, verify at: https://pypi.org/project/pythia-oracle-mcp/

## Step 3: Submit to PulseMCP (2 min)

Go to https://www.pulsemcp.com/submit

- **Type:** MCP Server
- **URL:** `https://github.com/PythiaOracle/pythia-oracle-mcp`

That's it. They review and list it.

## Step 4: Submit to awesome-blockchain-mcps (3 min)

Go to https://github.com/royyannick/awesome-blockchain-mcps

Click "Fork" → edit README.md → add under "On-Chain Integration" section:

```
**[Pythia Oracle MCP](https://github.com/PythiaOracle/pythia-oracle-mcp)** – On-chain **calculated technical indicators** (EMA, RSI, VWAP, Bollinger Bands, volatility, liquidity) via **Chainlink across supported networks**. 8 tools: live feed data, contract addresses, Solidity integration code, pricing tiers. First oracle delivering computed metrics to smart contracts.
```

Then create a Pull Request.

## Step 5: Smithery.ai (2 min)

Go to https://smithery.ai — look for "Submit" or "Add Server"
- URL: `https://github.com/PythiaOracle/pythia-oracle-mcp`

## Step 6 (Optional): Official MCP Registry

This requires Go + Docker + domain verification. Lower priority — PulseMCP and Smithery get more developer traffic. Can do later.

---

## After Publishing — Update pyproject.toml

Once the GitHub repo exists, the `Repository` URL in `pyproject.toml` is already set to:
`https://github.com/PythiaOracle/pythia-oracle-mcp`

If you use a different org/name, update it before pushing.
