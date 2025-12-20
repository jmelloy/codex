---
title: Example Agents Configuration
version: 1.0
default_model: gpt-4
default_temperature: 0.7
---

# Agent Configuration

This is an example agents.md configuration file that can be placed in any folder's `.` directory.

## Overview

The agents.md file configures agent behavior for operations within this folder and its subfolders (unless overridden).

## Default Configuration

The frontmatter above sets default values for all agents:
- `default_model`: The AI model to use
- `default_temperature`: Temperature setting for creativity
- `version`: Configuration version

## Agent-Specific Configurations

You can define configurations for specific agents using blocks:

::: analyzer
model: claude-3-opus
temperature: 0.3
max_tokens: 4000

Special instructions for the analyzer agent:
- Focus on code quality
- Check for security vulnerabilities
- Suggest improvements
:::

::: writer
model: gpt-4
temperature: 0.9
max_tokens: 2000

Instructions for the writer agent:
- Use clear, concise language
- Follow markdown format standards
- Include code examples where appropriate
:::

::: reviewer
model: gpt-4
temperature: 0.5

Instructions for the code reviewer:
- Check for bugs and edge cases
- Verify test coverage
- Suggest optimizations
:::

## General Instructions

Any content outside of specific agent blocks applies to all agents in this folder.

### File Format Standards

All generated files should follow these standards:
1. Use markdown format with YAML frontmatter
2. Separate content blocks with ::: delimiters
3. Include metadata in frontmatter (title, date, author, etc.)

### Safety Guidelines

Agents should always:
- Verify changes before applying
- Provide clear rollback options
- Track all modifications
- Ask for confirmation on destructive operations
