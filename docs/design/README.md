# Design Documents

This directory contains design documents and technical specifications for Codex features.

## Available Documents

### [Dynamic Views](./dynamic-views.md)
**Status**: Implemented (v1)  
**Version**: 1.1  
**Date**: 2026-01-24

Design document for Codex's dynamic view system, enabling documents that execute queries and render interactive visualizations.

**Topics**:
- View definition format (.cdx files)
- Supported view types (Kanban, Gallery, Rollup, Calendar, Table)
- Query and aggregation API
- Frontend component architecture
- Mini-views and composability

### [Plugin System](./plugin-system.md)
**Status**: Design Proposal  
**Version**: 1.0  
**Date**: 2026-01-28

Comprehensive design document for Codex's plugin system, inspired by Obsidian's plugin architecture.

**Plugin Types**:
1. **Custom Views & Templates**: Extend dynamic views with new visualization patterns
2. **Themes**: Visual styling packages with CSS and configuration
3. **Integrations**: External API connections and data transformations

**Topics**:
- Plugin manifest specifications
- Vue component interfaces
- Database schema for plugin management
- API endpoints and plugin loader
- Security considerations
- Implementation roadmap
- Example plugins (Tasks, Weather API, GitHub, OpenGraph unfurling)

## Document Status

| Document | Status | Version | Last Updated |
|----------|--------|---------|--------------|
| Dynamic Views | ✅ Implemented | 1.1 | 2026-01-24 |
| Plugin System | 📋 Design Proposal | 1.0 | 2026-01-28 |

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
