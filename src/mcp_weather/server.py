"""The `weather` MCP server instance and its tool guide."""

from jarvis_mcp_kit import ToolServer

INSTRUCTIONS = (
    "Current weather and forecasts. current_weather gives conditions right now; "
    "weather_forecast gives 1/3/7-day hourly or daily forecasts. Before answering anything "
    "tied to a date or a relative day ('today', 'tomorrow', 'jutro', 'weekend', a weekday), "
    "call get_current_date_and_time to learn today's date and weekday, map the user's day to "
    "a concrete date, and make sure the date you report matches it. Use the city's base "
    "(nominative) name. Temperatures from current_weather are in Kelvin."
)

server = ToolServer("weather", title="Jarvis Weather", instructions=INSTRUCTIONS)
