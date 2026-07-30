# Remote deployment image for the Amakomaya Pregnancy Care MCP server
# (browser custom connector).
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e .

# Hosting platforms set PORT; default to 8000 locally.
ENV MCP_TRANSPORT=http
ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE 8000

CMD ["digital-health-mcp"]
