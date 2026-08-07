import importlib
import os
import subprocess
import sys
import unittest

import httpx
from starlette.testclient import TestClient


os.environ.setdefault("WALLETWALLET_API_KEY", "test-walletwallet-key")
os.environ.setdefault("MCP_AUTH_TOKEN", "test-mcp-token")
server = importlib.import_module("server")


async def asgi_request(app, *, token=None, path="/mcp"):
    messages = []
    headers = []
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 1),
        "server": ("test", 80),
    }
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    return messages


class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_and_wrong_tokens_are_rejected(self):
        async def downstream(scope, receive, send):
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        app = server.BearerAuthMiddleware(downstream, "expected")
        for token in (None, "wrong"):
            with self.subTest(token=token):
                messages = await asgi_request(app, token=token)
                self.assertEqual(messages[0]["status"], 401)

    async def test_correct_token_reaches_mcp_app(self):
        reached = False

        async def downstream(scope, receive, send):
            nonlocal reached
            reached = True
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        app = server.BearerAuthMiddleware(downstream, "expected")
        messages = await asgi_request(app, token="expected")
        self.assertTrue(reached)
        self.assertEqual(messages[0]["status"], 204)


class McpInitializationTests(unittest.TestCase):
    def test_authenticated_mcp_initialize(self):
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "mock-client", "version": "1"},
            },
        }
        with TestClient(server.app) as client:
            response = client.post(
                "/mcp",
                json=request,
                headers={
                    "Authorization": f"Bearer {server.MCP_AUTH_TOKEN}",
                    "Accept": "application/json, text/event-stream",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("result", response.text)
        self.assertIn("walletwallet", response.text)


class UpstreamTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_client = server._client

    async def asyncTearDown(self):
        await server._client.aclose()
        server._client = self.original_client

    def use_transport(self, handler):
        server._client = httpx.AsyncClient(
            base_url=server.API_BASE,
            headers={"Authorization": "Bearer test-walletwallet-key"},
            transport=httpx.MockTransport(handler),
        )

    async def test_create_pass_posts_payload_and_returns_response(self):
        def handler(request):
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.url.path, "/api/passes")
            self.assertEqual(request.headers["authorization"], "Bearer test-walletwallet-key")
            self.assertIn(b'"barcodeValue":"synthetic-value"', request.content)
            return httpx.Response(200, json={"serialNumber": "synthetic-serial"})

        self.use_transport(handler)
        payload = server.PassPayload(barcodeValue="synthetic-value", logoText="Example")
        result = await server.create_pass(payload)
        self.assertEqual(result, {"serialNumber": "synthetic-serial"})

    async def test_update_pass_raises_upstream_error(self):
        self.use_transport(lambda request: httpx.Response(503, json={"error": "unavailable"}))
        payload = server.PassPayload(barcodeValue="synthetic-value", logoText="Example")
        with self.assertRaises(httpx.HTTPStatusError):
            await server.update_pass("synthetic-serial", payload)

    async def test_google_link_returns_redirect_without_following(self):
        def handler(request):
            self.assertEqual(request.url.path, "/api/passes/synthetic-serial/google")
            return httpx.Response(302, headers={"Location": "https://example.invalid/save"})

        self.use_transport(handler)
        result = await server.get_google_wallet_link("synthetic-serial")
        self.assertEqual(result, "https://example.invalid/save")


class StartupTests(unittest.TestCase):
    def test_import_requires_both_configuration_values(self):
        for missing, expected in (
            ("WALLETWALLET_API_KEY", "WALLETWALLET_API_KEY is not set"),
            ("MCP_AUTH_TOKEN", "MCP_AUTH_TOKEN is not set"),
        ):
            with self.subTest(missing=missing):
                env = os.environ.copy()
                env["WALLETWALLET_API_KEY"] = "test-walletwallet-key"
                env["MCP_AUTH_TOKEN"] = "test-mcp-token"
                env.pop(missing)
                result = subprocess.run(
                    [sys.executable, "-c", "import server"],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
