"""
WalletWallet MCP Server

Exposes the WalletWallet API (https://www.walletwallet.dev/docs/) as MCP tools so
any MCP client (Claude, or another agent) can create and update Apple/Google
Wallet passes without touching certificates or signing.

Auth: reads WALLETWALLET_API_KEY from the environment. Never hardcode the key
or pass it as a tool argument — it should live in a deploy-time secret.
"""

import hmac
import os
from typing import Any, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

API_BASE = "https://api.walletwallet.dev"
API_KEY = os.environ.get("WALLETWALLET_API_KEY")
MCP_AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN")

if not API_KEY:
    # Fail loud at startup rather than on first tool call.
    raise RuntimeError(
        "WALLETWALLET_API_KEY is not set. Set it as an environment variable "
        "(deploy-time secret), never as a tool argument."
    )

if not MCP_AUTH_TOKEN:
    # This is the token MCP clients must present to reach the server at all.
    # It is unrelated to WALLETWALLET_API_KEY and never forwarded upstream.
    raise RuntimeError(
        "MCP_AUTH_TOKEN is not set. Generate one (e.g. `openssl rand -hex 32`) "
        "and set it as a deploy-time secret."
    )


class BearerAuthMiddleware:
    """
    Minimal static-bearer-token gate in front of the MCP app. Not OAuth --
    just enough to stop random internet traffic from calling your tools and
    burning your WalletWallet quota. Rejects anything that doesn't present
    `Authorization: Bearer <MCP_AUTH_TOKEN>`.
    """

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        header = request.headers.get("authorization", "")
        presented = (
            header.removeprefix("Bearer ").strip()
            if header.startswith("Bearer ")
            else ""
        )

        # constant-time comparison to avoid timing side channels
        if not presented or not hmac.compare_digest(presented, self.token):
            response = JSONResponse({"error": "unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

mcp = FastMCP(
    name="walletwallet",
    instructions=(
        "Create and update Apple Wallet / Google Wallet passes via the "
        "WalletWallet API. Use create_pass to issue a new pass, update_pass "
        "to push a change to an existing pass (identified by serial_number), "
        "and get_google_wallet_link to fetch the Save-to-Google-Wallet URL "
        "for a pass."
    ),
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
    stateless_http=True,
)

_client = httpx.AsyncClient(
    base_url=API_BASE,
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    },
    timeout=15.0,
)


class PassField(BaseModel):
    label: str
    value: str
    changeMessage: str | None = Field(
        default=None,
        description="Push notification text shown when this field's value "
        "changes on update, e.g. 'You earned %@ points'.",
    )


class PassPayload(BaseModel):
    barcodeValue: str = Field(description="Content encoded in the barcode/QR.")
    barcodeFormat: Literal["QR", "PDF417", "Aztec", "Code128"] = "QR"
    logoText: str = Field(description="Text shown next to the logo, e.g. business name.")
    colorPreset: str | None = Field(default=None, description="e.g. 'dark', 'light'.")
    color: str | None = Field(
        default=None, description="Custom hex background color, Pro plan only."
    )
    headerFields: list[PassField] | None = None
    primaryFields: list[PassField] | None = None
    secondaryFields: list[PassField] | None = None
    backFields: list[PassField] | None = None


def _payload_dict(payload: PassPayload) -> dict[str, Any]:
    return payload.model_dump(exclude_none=True)


@mcp.tool()
async def create_pass(payload: PassPayload) -> dict[str, Any]:
    """
    Create a new Apple/Google Wallet pass. Returns serialNumber (save this to
    push updates later), googleSaveUrl, and the base64-encoded applePass
    (.pkpass file contents).
    """
    resp = await _client.post("/api/passes", json=_payload_dict(payload))
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def update_pass(serial_number: str, payload: PassPayload) -> dict[str, Any]:
    """
    Update an existing pass by serial number. Any field with a changed value
    triggers a push notification to every device that has the pass installed
    (only if changeMessage is set on that field). Identical bodies are a no-op.
    """
    resp = await _client.put(f"/api/passes/{serial_number}", json=_payload_dict(payload))
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def get_google_wallet_link(serial_number: str) -> str:
    """
    Get the 'Save to Google Wallet' URL for an already-issued pass.
    """
    resp = await _client.get(
        f"/api/passes/{serial_number}/google", follow_redirects=False
    )
    if resp.status_code in (301, 302, 303, 307, 308):
        return resp.headers.get("location", "")
    resp.raise_for_status()
    return resp.text


@mcp.tool()
async def check_usage() -> dict[str, Any]:
    """
    Check current API usage/quota for this account this billing period.
    """
    resp = await _client.get("/api/auth/usage")
    resp.raise_for_status()
    return resp.json()


def build_app():
    """MCP's streamable-http ASGI app.

    TEMPORARILY UNGATED: the bearer-token wrapper is disabled for now. Re-enable
    by restoring `return BearerAuthMiddleware(mcp.streamable_http_app(), token=MCP_AUTH_TOKEN)`
    before leaving this deployed anywhere reachable from the internet.
    """
    return mcp.streamable_http_app()


app = build_app()  # for `uvicorn server:app` / most PaaS auto-detection

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

