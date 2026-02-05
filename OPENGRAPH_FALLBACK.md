# OpenGraph.io Fallback Feature

## Overview

The OpenGraph scraper now includes a fallback mechanism that uses the [opengraph.io](https://www.opengraph.io/) API when direct HTML scraping fails. This improves reliability for link unfurling, especially for sites that:

- Block scrapers with bot detection
- Require JavaScript to load metadata
- Have strict rate limiting
- Use aggressive anti-scraping measures

## How It Works

1. **Primary Method**: Direct HTML scraping (default behavior)
   - Fetches the HTML directly from the target URL
   - Parses Open Graph meta tags using regex
   - Fast and doesn't require external API calls

2. **Fallback Method**: opengraph.io API (when direct scraping fails)
   - Triggered automatically when direct scraping fails
   - Uses opengraph.io's rendering engine to extract metadata
   - Handles JavaScript-rendered pages
   - Requires API key (optional)

## Setup

### 1. Get an API Key

Visit [opengraph.io](https://www.opengraph.io/) to sign up and get your API key.

### 2. Configure Environment Variable

Add your API key to the environment:

```bash
# In .env file
OPENGRAPH_IO_API_KEY=your-api-key-here

# Or export in shell
export OPENGRAPH_IO_API_KEY=your-api-key-here
```

### 3. Restart the Application

If using Docker:
```bash
docker compose restart
```

If running directly:
```bash
# Backend will automatically pick up the environment variable
python -m codex.main
```

## Behavior

### Without API Key
- Direct HTML scraping is attempted
- If it fails, the error is raised
- **No fallback occurs**

### With API Key
- Direct HTML scraping is attempted first
- If it fails, automatically tries opengraph.io API
- Returns metadata from whichever method succeeds

## Example Usage

### Testing the Fallback

```bash
# Run the demo script
python demo_opengraph_fallback.py https://github.com

# With API key set
export OPENGRAPH_IO_API_KEY=your-key
python demo_opengraph_fallback.py https://some-protected-site.com
```

### In Code

The fallback is completely transparent - no code changes needed:

```python
from codex.plugins.opengraph_scraper import OpenGraphScraper

scraper = OpenGraphScraper()
metadata = await scraper.scrape_url("https://example.com")

# Automatically uses fallback if needed and API key is available
```

## API Response Format

The opengraph.io API returns data in this format:

```json
{
  "hybridGraph": {
    "title": "Page Title",
    "description": "Page description",
    "image": "https://example.com/image.jpg",
    "url": "https://example.com",
    "site_name": "Example Site"
  },
  "openGraph": {
    "title": "Open Graph Title",
    "description": "Open Graph description",
    "image": [
      {"url": "https://example.com/og-image.jpg"}
    ],
    "url": "https://example.com",
    "siteName": "Example"
  }
}
```

The scraper automatically:
- Extracts data from both `hybridGraph` and `openGraph` sections
- Prefers `openGraph` data when available
- Handles images as arrays or objects
- Maps to the standard metadata format used by Codex

## Rate Limits

opengraph.io has the following rate limits:

- **Free tier**: 100 requests/month
- **Paid tiers**: Higher limits available

Check [opengraph.io pricing](https://www.opengraph.io/pricing) for current plans.

## Security Considerations

1. **API Key Storage**: Never commit API keys to git. Use environment variables.
2. **Key Rotation**: Rotate API keys periodically.
3. **Access Control**: Limit API key permissions if available.
4. **Monitoring**: Monitor API usage to detect abuse.

## Logging

The scraper logs its behavior:

```
INFO  - Scraping Open Graph metadata from: https://example.com
WARNING - Direct scraping failed for https://example.com, trying opengraph.io fallback: HTTPStatusError
INFO  - Fetching Open Graph metadata from opengraph.io API for: https://example.com
```

Check application logs to verify fallback behavior.

## Testing

Run the test suite to verify the fallback mechanism:

```bash
cd backend
pytest tests/test_opengraph_scraper.py -v
```

Tests cover:
- Direct scraping
- Fallback when direct scraping fails
- Behavior without API key
- API response parsing
- Image array handling

## Troubleshooting

### Fallback Not Working

1. Verify API key is set:
   ```bash
   echo $OPENGRAPH_IO_API_KEY
   ```

2. Check application logs for errors

3. Verify API key is valid at [opengraph.io](https://www.opengraph.io/)

### Both Methods Failing

If both direct scraping and the fallback fail:
- Check network connectivity
- Verify target URL is accessible
- Check opengraph.io service status
- Review rate limit quotas

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENGRAPH_IO_API_KEY` | No | None | API key for opengraph.io fallback |

## Files Modified

- `backend/codex/plugins/opengraph_scraper.py` - Added fallback logic
- `backend/tests/test_opengraph_scraper.py` - Added fallback tests
- `.env.example` - Added API key documentation
- `demo_opengraph_fallback.py` - Demo script

## Related Documentation

- [LINK_UNFURL_IMPLEMENTATION.md](LINK_UNFURL_IMPLEMENTATION.md) - Original link unfurl feature
- [opengraph.io API Documentation](https://www.opengraph.io/documentation/)
