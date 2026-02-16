# Design Documents

This directory contains design documents and technical specifications for Codex features.

## Core Architecture Documentation

For comprehensive system architecture information, see the parent docs directory:

- **[Architecture Guide](../ARCHITECTURE.md)** - Complete system architecture overview
- **[Database Schema](../DATABASE_SCHEMA.md)** - Detailed database documentation
- **[Deployment Guide](../DEPLOYMENT.md)** - Production deployment instructions
- **[Architecture Review](../ARCHITECTURE_REVIEW.md)** - Architecture assessment and recommendations

## Feature Design Documents

### [Dynamic Views](./dynamic-views.md)
**Status**: Implemented (v1)  
**Version**: 1.1  
**Date**: 2026-01-24

Design document for Codex's dynamic view system, enabling documents that execute queries and render interactive visualizations.

**Topics**:
- View definition format (.cdx files)
- Query and aggregation API
- Frontend component architecture
- ViewRenderer and plugin integration

**Current Implementation**:
- ViewRenderer component with plugin-based view loading
- Query service for executing view queries
- View plugin service for component management
- Support for .cdx files with YAML frontmatter

### [Plugin System](./plugin-system.md)
**Status**: ✅ Implemented  
**Version**: 1.0  
**Date**: 2026-01-28

Comprehensive design and implementation guide for Codex's plugin system.

**Plugin Types**:
1. **Custom Views**: View components (Kanban, Gallery, Rollup, Task lists, Corkboard, etc.)
2. **Themes**: Visual styling packages (Antiquarian, Cream, Fieldnotes, Manila, Notebook, Obsidian, White, etc.)
3. **Integrations**: External API connections (GitHub, OpenGraph, Weather API)

**Topics**:
- Plugin manifest specifications (`manifest.yml`)
- Vue component interfaces and build system
- Plugin registration API endpoints
- Security and permissions
- Example plugins in `/plugins` directory

**Current Implementation**:
- Plugin build system with TypeScript/Vue compilation
- Plugin registration API (`/api/v1/plugins/`)
- Frontend plugin loading with dynamic imports
- Multiple working plugins: tasks, gallery, rollup, corkboard, themes, integrations

### [AI Agent Integration](./ai-agent-integration.md)
**Status**: ✅ Implemented (Phase 1 & 2)  
**Version**: 1.0  
**Date**: 2026-01-30  
**Last Updated**: 2026-02-06

Design and implementation of scoped AI agents for automated assistance within Codex workspaces.

**Topics**:
- Agent configuration and credentials
- Scope guards and permission boundaries
- Tool routing and execution
- Provider adapters (LiteLLM)
- Agent sessions and action logging
- Frontend agent UI components

**Current Implementation**:
- Agent CRUD API (`/api/v1/agents/`)
- Agent execution engine with scope guards
- Multiple provider support via LiteLLM
- Agent session management and chat interface
- Tool routing for file operations
- Action logging for auditability

## Document Status

| Document | Status | Version | Last Updated |
|----------|--------|---------|--------------|
| Dynamic Views | ✅ Implemented (v1) | 1.1 | 2026-01-24 |
| Plugin System | ✅ Implemented | 1.0 | 2026-01-28 |
| AI Agent Integration | ✅ Implemented (Phase 1 & 2) | 1.0 | 2026-02-06 |

## Contributing

When creating new design documents:

1. Use the existing documents as templates
2. Include metadata (version, date, status)
3. Provide clear goals and use cases
4. Include implementation details and examples
5. Add references and related documents
6. Update this README with the new document

## Feedback

For questions or feedback on design documents:
- Create an issue in the repository
- Start a discussion in the team chat
- Comment on the relevant pull request
