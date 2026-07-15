# walletwallet-mcp

A remote MCP server that exposes the [WalletWallet](https://www.walletwallet.dev) pass
API as MCP tools: `create_pass`, `update_pass`, `get_google_wallet_link`, `check_usage`.

Transport: **streamable-http**, mounted at `/mcp` on whatever host/port you deploy to.

## 1. Get an API key

Sign up at https://www.walletwallet.dev — free tier is 1,000 passes/month, no card
required. Copy the `ww_live_...` key.

## 2. Generate an MCP auth token

This is separate from the WalletWallet key — it's what gates access to *your*
MCP server so random internet traffic can't call your tools and burn your
WalletWallet quota. Minimal static bearer token, not OAuth.

```bash
openssl rand -hex 32
```

Keep this value; you'll set it as `MCP_AUTH_TOKEN` and also give it to your
MCP client.

## 3. Run locally first

```bash
pip install -r requirements.txt
export WALLETWALLET_API_KEY=ww_live_your_key
export MCP_AUTH_TOKEN=the_hex_string_from_step_2
python server.py
```

Server listens on `0.0.0.0:8000`, MCP endpoint at `http://localhost:8000/mcp`.
Requests without `Authorization: Bearer <MCP_AUTH_TOKEN>` get a 401.

## 4. Deploy remotely

The Dockerfile is host-agnostic (reads `PORT` env var), so any of these work:

- **Fly.io** — fits your existing GitHub Actions + encrypted-secret pattern:
  ```bash
  fly launch --no-deploy   # generates fly.toml, don't overwrite Dockerfile
  fly secrets set WALLETWALLET_API_KEY=ww_live_your_key MCP_AUTH_TOKEN=the_hex_string
  fly deploy
  ```
- **Render / Railway** — connect the repo, set `WALLETWALLET_API_KEY` and
  `MCP_AUTH_TOKEN` as environment secrets in the dashboard, it'll build from
  the Dockerfile automatically.
- **Cloud Run** — `gcloud run deploy --source . --set-secrets WALLETWALLET_API_KEY=...,MCP_AUTH_TOKEN=...`

Whichever you pick, **both secrets go in as platform secrets, never committed,
never passed through chat.** Same pattern you're already using for
GITHUB_TOKEN-triggered scripts.

## 5. Point an MCP client at it

For Claude (claude.ai / Claude Code), add a remote MCP connector pointing at:

```
https://<your-deployed-host>/mcp
```

with an `Authorization: Bearer <MCP_AUTH_TOKEN>` header configured on the
connector (exact UI/config field depends on the client — Claude's remote MCP
connector setup supports custom headers).

This bearer token is a coarse gate: anyone with the token can call any tool.
It's appropriate for "just me, one client" use. If this server will ever be
shared with other people or other services, that's a different, heavier
problem — see the note below.

## Notes

- `create_pass` returns `serialNumber` — save it, you need it for `update_pass`.
- Updates are pushed only when a field's value actually changes AND that field
  has a `changeMessage` set; identical bodies are a silent no-op (per WalletWallet docs).
- `barcodeFormat` currently supports QR/PDF417/Aztec/Code128 per the documented
  format; iOS 27 is expected to add EAN-13/Code 39/Codabar/ITF — not yet reflected here.
- **On auth scope:** this server uses a single shared static bearer token —
  fine for "one person, one client." If you need per-user identity, login
  flows, or third parties calling this server, that's OAuth 2.1 (which the
  `mcp` Python SDK supports via `FastMCP(auth=...)` / `TokenVerifier`), not
  this. Don't retrofit OAuth onto this file for a multi-user case — treat
  that as a separate build with its own auth server, token issuance, and
  user store.
