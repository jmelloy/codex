# GitHub Integration

Embed GitHub issues, pull requests, and repositories directly in your Codex notebooks.

## Features

- Display GitHub issues with full details
- Show pull requests with status
- Repository information cards
- Support for private repositories with authentication
- Automatic URL detection

## Installation

1. Generate a GitHub personal access token at https://github.com/settings/tokens
2. Configure the integration in your workspace settings
3. Enter your access token

### Token Permissions

For public repositories:
- No specific scopes required

For private repositories:
- `repo` - Full control of private repositories

## Usage

### GitHub Issue Block

Display an issue in your markdown:

```github-issue
url: https://github.com/owner/repo/issues/123
```

Shows:
- Issue number and title
- Issue body
- State (open/closed)
- Author
- Labels
- Timestamps

### GitHub Pull Request Block

Display a pull request:

```github-pr
url: https://github.com/owner/repo/pull/456
```

Shows:
- PR number and title
- PR description
- State (open/closed/merged)
- Author
- Review status
- Merge status

### GitHub Repository Block

Display repository information:

```github-repo
url: https://github.com/owner/repo
```

Shows:
- Repository name and description
- Stars and forks count
- Open issues count
- Language
- License
- Last update

## Configuration

- **Access Token**: Required - Your GitHub personal access token
- **Default Organization**: Optional - Set a default org for shorter syntax

## Rate Limits

- 60 requests per minute for unauthenticated requests
- 5,000 requests per hour with authentication

## Privacy

Your access token is stored encrypted in the database. API requests are made directly from the Codex backend to GitHub's API.

## Example

Display a GitHub issue:

```github-issue
url: https://github.com/facebook/react/issues/12345
```

Will show the full issue details with formatting preserved.

## Troubleshooting

**"Not Found" error:**
- Verify the URL is correct
- For private repositories, ensure your token has `repo` scope
- Check that the repository/issue/PR exists

**Rate limit exceeded:**
- Wait for the rate limit to reset (shown in error message)
- Add or verify your access token for higher limits

## License

MIT
