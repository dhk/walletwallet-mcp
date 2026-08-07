# Deployment templates

These are starting-point templates, not permanent or exhaustive provider instructions. Provider products, pricing, defaults, and commands change; check the linked official documentation before deploying. The repository currently ships a `Dockerfile` that reads `PORT` (default `8000`) and `render.yaml`.

For every provider, configure `WALLETWALLET_API_KEY` and `MCP_AUTH_TOKEN` in its secret-management UI. Do not commit values, bake them into an image, put them in build arguments, or paste them into chat. Expose `/mcp` only over HTTPS and verify that headers and request/response bodies are not recorded in ordinary logs.

## Render template

The included `render.yaml` defines a Docker web service and prompts for both secrets. Review it, choose an appropriate plan, and follow Render's current [Blueprint](https://render.com/docs/blueprint-spec) and [environment variable](https://render.com/docs/configure-environment-variables) documentation.

## Fly.io template

Create an app from the repository's Dockerfile, set both values as secrets, and deploy using the current [Fly Launch](https://fly.io/docs/launch/) and [Secrets](https://fly.io/docs/apps/secrets/) documentation. Review any generated configuration before committing it.

## Railway template

Deploy the repository using its Dockerfile and configure both values as variables/secrets. Follow Railway's current [Dockerfile](https://docs.railway.com/guides/dockerfiles) and [variables](https://docs.railway.com/guides/variables) documentation.

## Google Cloud Run template

Build/deploy the repository as a container, map both values from Secret Manager, and configure ingress/authentication for the intended client. Follow the current [Cloud Run container](https://cloud.google.com/run/docs/deploying) and [Secret Manager](https://cloud.google.com/run/docs/configuring/services/secrets) documentation.

## Post-deployment checks

1. Confirm the public URL is HTTPS and resolves `/mcp`.
2. Confirm missing and incorrect bearer tokens return `401`.
3. Initialize an MCP session with the correct bearer token and list tools.
4. Invoke `check_usage` before any mutating tool.
5. Treat `create_pass` or `update_pass` as an explicit live change; use synthetic data for a smoke test and understand the quota/device effects.
