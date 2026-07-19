# Design Documents

This directory contains design documents and technical specifications for Codex features.

## Available Documents

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

### [Mac App](./mac-app.md)
**Status**: 🚧 Proposed (Draft)
**Version**: 1.0
**Date**: 2026-07-19

Design for shipping Codex as a native macOS application: a Swift/AppKit shell hosting the existing Vue frontend in WKWebView, with the engine ported to Swift and running in-process (no Python sidecar).

**Topics**:
- Shell architecture options (Electron vs Tauri vs Swift+WKWebView vs SwiftUI rewrite)
- Engine port to Swift: sizing, library mapping, server compatibility contract
- macOS integrations: Spotlight, Quick Look, quick capture, notifications, `codex://` links
- Sync strategies (remote workspace attach, git-based notebook sync)
- Distribution, signing, and phased rollout

## Document Status

| Document | Status | Version | Last Updated |
|----------|--------|---------|--------------|
| AI Agent Integration | ✅ Implemented (Phase 1 & 2) | 1.0 | 2026-02-06 |
| Mac App | 🚧 Proposed (Draft) | 1.0 | 2026-07-19 |

**Removed documents**: the Dynamic Views and Plugin System design docs were deleted along with most of the features they described. The plugin system that remains is CSS themes + backend integration proxies (see `backend/codex/plugins/`); custom view plugins and `.cdx` dynamic views no longer exist.

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
