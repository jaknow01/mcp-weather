# mcp-weather

Current weather and forecasts as an [MCP](https://modelcontextprotocol.io) server.

| Tool | Source |
|---|---|
| `current_weather` | OpenWeather (needs `OPENWEATHER_API_KEY`) |
| `weather_forecast` | Open-Meteo (keyless), places geocoded via Nominatim |
| `get_current_date_and_time` | server clock in `TIMEZONE` (default `Europe/Warsaw`) |
| `whoami` | which client your key belongs to |

Part of the Jarvis tool servers; built on
[jarvis-mcp-kit](https://github.com/jaknow01/jarvis-mcp-kit) (API keys, rate limits, logs).

## Run

```bash
cp .env.example .env                              # set OPENWEATHER_API_KEY
cp config/clients.example.yaml config/clients.yaml
uv run jarvis-mcp-keys new me --servers weather   # paste the block into config/clients.yaml
uv run --env-file .env mcp-weather serve          # http://localhost:8010/mcp/weather
```

Docker: `docker run -p 8010:8010 --env-file .env -v $PWD/config:/config ghcr.io/jaknow01/mcp-weather:latest`.
Kubernetes: `deploy/kubernetes.yaml`.

## Connect

- **Claude Code:** `claude mcp add --transport http weather https://<host>/mcp/weather --header "Authorization: Bearer jvk_…"`
- **Claude app (custom connector):** URL `https://<host>/mcp/weather/jvk_…`
- **Jarvis:** an entry in its `config/subagents.yaml`.
