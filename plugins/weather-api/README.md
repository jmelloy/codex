# Weather API Integration

Display current weather and 5-day forecasts from OpenWeatherMap in your Codex notebooks.

## Features

- Current weather display for any location
- 5-day weather forecast
- Customizable temperature units (Celsius, Fahrenheit, Kelvin)
- Weather blocks for embedding in markdown

## Installation

1. Get a free API key from [OpenWeatherMap](https://openweathermap.org/api)
2. Configure the integration in your workspace settings
3. Enter your API key and preferred settings

## Usage

### Weather Block

Embed current weather in your markdown files:

\`\`\`weather
location: San Francisco
units: imperial
\`\`\`

### Configuration

- **API Key**: Required - Your OpenWeatherMap API key
- **Default Location**: Optional - Default location for weather queries
- **Temperature Units**: Optional - Choose between Celsius (metric), Fahrenheit (imperial), or Kelvin

## Rate Limits

- 60 requests per minute
- 1000 requests per day

These are the limits for the free tier of OpenWeatherMap API. 

## Example

A weather block for New York City:

\`\`\`weather
location: New York, US
units: imperial
show_forecast: true
\`\`\`

Will display:
- Current temperature
- "Feels like" temperature
- Humidity
- Wind speed
- Weather description with icon
- Optional 5-day forecast

## Troubleshooting

**"Invalid API key" error:**
- Verify your API key is correct
- Make sure your API key is activated (can take a few minutes after registration)

**"Location not found" error:**
- Try using the format "City, Country Code" (e.g., "London, UK")
- Verify the location name spelling

**Rate limit exceeded:**
- Wait for the rate limit window to reset
- Consider upgrading your OpenWeatherMap plan

## Privacy

Your API key is stored encrypted in the database and never exposed in API responses or logs.

## License

MIT
