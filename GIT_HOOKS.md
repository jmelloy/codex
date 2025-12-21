# Git Hooks Integration

Codex provides Git hook integration to automatically track your commits in daily notes. This feature helps you maintain a chronological log of your development work across all repositories.

## Overview

The post-commit hook automatically captures commit information and appends it to your daily note file:
- Commit SHA (shortened)
- Commit message
- Branch name
- Repository name
- Timestamp

## Installation

### Quick Setup

Install the post-commit hook globally for all your Git repositories:

```bash
codex hooks install --global
```

This will:
1. Create a `.git-hooks` directory in your home folder
2. Install the post-commit hook script
3. Configure Git to use this hooks directory globally

### Custom Configuration

Specify a workspace for daily notes:

```bash
codex hooks install --global --workspace ~/my-lab
```

Or use a custom hooks directory:

```bash
codex hooks install --hooks-path ~/.my-custom-hooks --global
```

## Usage

Once installed, the hook runs automatically after every commit in any Git repository:

```bash
git commit -m "Implement feature X"
# Post-commit hook runs automatically
# Commit is logged to today's daily note
```

### Daily Notes Location

Daily notes are stored in the `daily-notes` directory within your workspace:

```
~/my-lab/
  daily-notes/
    2024-12-20.md
    2024-12-21.md
    2024-12-22.md
```

### Daily Note Format

Each daily note follows the Codex markdown format:

```markdown
---
title: Daily Note - 2024-12-21
date: 2024-12-21
tags:
  - daily-note
  - auto-generated
---

# Daily Note - 2024-12-21

## Commits

::: commit
**Time**: 14:30:15  
**Repo**: codex  
**Branch**: main  
**SHA**: `abc12345`  
**Message**: Implement feature X
:::

::: commit
**Time**: 15:45:22  
**Repo**: myproject  
**Branch**: feature-branch  
**SHA**: `def67890`  
**Message**: Fix bug in authentication
:::
```

## CLI Commands

### Hooks Management

```bash
# Install the post-commit hook
codex hooks install --global

# Uninstall the post-commit hook
codex hooks uninstall

# Check hook installation status
codex hooks status
```

### Daily Notes Management

```bash
# Create a new daily note
codex daily-note create

# Create a daily note for a specific date
codex daily-note create --date 2024-12-20

# List recent daily notes
codex daily-note list

# List more daily notes
codex daily-note list --limit 30

# View today's daily note
codex daily-note view

# View a specific daily note
codex daily-note view --date 2024-12-20
```

### Manual Commit Entry

You can also manually add commit entries:

```bash
codex daily-note add-commit \
    --sha abc123def \
    --message "Implement feature X" \
    --branch main \
    --repo myproject
```

## Configuration

### Workspace Configuration

The hook can be configured to use a specific workspace. If no workspace is specified, it uses the current directory.

**Set during installation:**
```bash
codex hooks install --workspace ~/my-lab --global
```

**Modify hook manually:**
Edit `~/.git-hooks/post-commit` and change the workspace path:
```bash
codex daily-note add-commit \
    --sha "$COMMIT_SHA" \
    --message "$COMMIT_MSG" \
    --branch "$BRANCH" \
    --repo "$REPO" \
    --workspace "/path/to/workspace"
```

### Per-Repository Hooks

To use different hooks for specific repositories, you can override the global configuration:

```bash
cd /path/to/specific/repo
git config core.hooksPath /path/to/custom/hooks
```

Or use repository-local hooks:

```bash
cd /path/to/specific/repo
cp ~/.git-hooks/post-commit .git/hooks/
```

## Troubleshooting

### Hook Not Running

1. **Check if global hooks path is set:**
   ```bash
   git config --global core.hooksPath
   ```

2. **Verify hook file exists and is executable:**
   ```bash
   ls -la ~/.git-hooks/post-commit
   ```
   The file should have execute permissions (`-rwxr-xr-x`).

3. **Check hook status:**
   ```bash
   codex hooks status
   ```

### Permission Issues

If the hook file is not executable:

```bash
chmod +x ~/.git-hooks/post-commit
```

### Hook Errors

The hook is designed to fail silently to avoid interrupting commits. To debug:

1. **Run the hook manually:**
   ```bash
   cd /path/to/repo
   .git/hooks/post-commit
   # Or if using global hooks:
   ~/.git-hooks/post-commit
   ```

2. **Check if codex is in PATH:**
   ```bash
   which codex
   ```

3. **Test the add-commit command:**
   ```bash
   codex daily-note add-commit \
       --sha test123 \
       --message "Test commit" \
       --branch main \
       --repo test
   ```

### Daily Notes Not Created

1. **Check workspace path:**
   Verify the workspace exists and is writable.

2. **Check daily-notes directory:**
   ```bash
   ls -la ~/my-lab/daily-notes/
   ```

3. **Manually create a daily note:**
   ```bash
   codex daily-note create --workspace ~/my-lab
   ```

## Advanced Usage

### Custom Daily Note Templates

You can customize the daily note format by modifying the `DailyNoteManager` class in `codex/core/git_hooks.py`.

### Multiple Workspaces

To track commits in different workspaces:

1. Install separate hook files in different directories
2. Configure repositories to use different hooks paths:
   ```bash
   cd /path/to/project1
   git config core.hooksPath ~/.git-hooks-work
   
   cd /path/to/project2
   git config core.hooksPath ~/.git-hooks-personal
   ```

### Integration with Notebooks

Daily notes are separate from notebooks but can be linked:

```bash
# Create a notebook for tracking daily work
codex notebook create "Daily Work Log"

# Create a page referencing a daily note
codex page create "Week of Dec 18-22" \
    --notebook "Daily Work Log" \
    --goal "See daily-notes/2024-12-*.md for detailed commits"
```

## Best Practices

1. **Use Descriptive Commit Messages**: Since commits are logged to daily notes, write clear, informative messages.

2. **Review Daily Notes Regularly**: Daily notes provide a chronological view of your work. Review them weekly or monthly.

3. **Combine with Manual Notes**: Add manual notes, tasks, and observations to your daily notes:
   ```bash
   # View today's note
   codex daily-note view
   
   # Edit in your favorite editor
   vim ~/my-lab/daily-notes/$(date +%Y-%m-%d).md
   ```

4. **Backup Daily Notes**: Daily notes are plain markdown files. Back them up with your workspace:
   ```bash
   cd ~/my-lab
   git add daily-notes/
   git commit -m "Update daily notes"
   ```

## Examples

### Example 1: Development Workflow

```bash
# Morning: Start work
codex daily-note create
vim ~/my-lab/daily-notes/$(date +%Y-%m-%d).md
# Add: ## Goals for Today
#      - Fix authentication bug
#      - Implement user profile page

# During day: Make commits (automatic logging)
git commit -m "Fix authentication timeout issue"
git commit -m "Add user profile page layout"
git commit -m "Update profile page with user data"

# Evening: Review work
codex daily-note view
# Shows all commits with timestamps
```

### Example 2: Multi-Project Tracking

```bash
# Install hook with workspace
codex hooks install --workspace ~/lab --global

# Work on different projects
cd ~/projects/backend
git commit -m "Add API endpoint"

cd ~/projects/frontend
git commit -m "Update dashboard UI"

cd ~/projects/mobile
git commit -m "Fix crash on startup"

# All commits logged to same daily note
codex daily-note view --workspace ~/lab
```

### Example 3: Weekly Review

```bash
# List last 7 daily notes
codex daily-note list --limit 7

# View each note
for i in {0..6}; do
    date=$(date -d "$i days ago" +%Y-%m-%d)
    echo "=== $date ==="
    codex daily-note view --date $date
    echo ""
done
```

## Uninstallation

To remove the git hook:

```bash
# Remove the post-commit hook
codex hooks uninstall

# Optionally, remove the global hooks path configuration
git config --global --unset core.hooksPath
```

## Related Documentation

- [Codex README](README.md) - Main documentation
- [Agent System](AGENT_SYSTEM.md) - AI agent integration
- [CLI Commands](backend/codex/cli/main.py) - Full CLI reference

## Contributing

Contributions to improve the git hooks integration are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.
