FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# WALLETWALLET_API_KEY and MCP_AUTH_TOKEN must be supplied at runtime as
# secrets, not baked in.
ENV PORT=8000
EXPOSE 8000

CMD ["python", "server.py"]
