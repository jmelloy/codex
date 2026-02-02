---
title: GitHub Integration Blocks Demo
created: 2026-02-02
tags: [github, integration, demo]
---

# GitHub Integration Blocks Demo

This document demonstrates the three GitHub integration blocks that display GitHub issues, pull requests, and repositories.

## GitHub Issue Block

Display information about a GitHub issue:

```github-issue
url: https://github.com/facebook/react/issues/12345
```

## GitHub Pull Request Block

Display information about a GitHub pull request:

```github-pr
url: https://github.com/vuejs/core/pull/456
```

## GitHub Repository Block

Display information about a GitHub repository:

```github-repo
url: https://github.com/jmelloy/codex
```

## Notes

These blocks require the GitHub integration to be enabled and configured with a personal access token.

### Token Permissions

For public repositories:
- No specific scopes required

For private repositories:
- `repo` - Full control of private repositories

### Rate Limits

- 60 requests per minute for unauthenticated requests
- 5,000 requests per hour with authentication
