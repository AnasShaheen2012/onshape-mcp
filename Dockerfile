# Minimal image for running the Onshape MCP server over stdio.
# The server starts and answers MCP introspection (tools/list) without credentials;
# pass ONSHAPE_ACCESS_KEY / ONSHAPE_SECRET_KEY at runtime to actually call Onshape.
FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

ENTRYPOINT ["onshape-mcp-server"]
