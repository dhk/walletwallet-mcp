# Security policy

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not open a public issue containing credentials, customer/pass data, exploit details, or sensitive logs. If private reporting is unavailable, contact the repository owner privately before disclosing details.

Include the affected revision, impact, reproduction steps using synthetic data, and any suggested mitigation. Never include a real WalletWallet API key, MCP bearer token, `.pkpass`, barcode, serial number, or customer data.

This prototype has one shared all-tools bearer token. It does not provide per-user authorization, tool scopes, rate limiting, confirmations, or a durable audit trail. Deploy it only for a trusted single-user/client context over TLS.

If a secret may be exposed, rotate/revoke it at its issuer, stop or isolate the service as needed, review appropriately redacted access logs, and assess whether passes or holder devices were affected.
