# Contributing

Keep changes focused on the small, single-user MCP bridge. OAuth, multitenancy, rate limiting, and broader pass-management features should be proposed in an issue before implementation.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Tests must use placeholder credentials, mocked HTTP transports, and synthetic pass data. They must never call the live WalletWallet API, create a real pass, or include customer/pass data. Document whether a proposed tool is read-only or mutating and its quota, pass, and installed-device effects.

Submit a focused pull request explaining the change, safety impact, and commands used to validate it. Do not commit `.env`, API keys, bearer tokens, `.pkpass` files, serial numbers, barcodes, save URLs, or copied production logs.
