# Codex Documentation

This directory contains comprehensive documentation for the Codex project.

## Architecture Documentation

### [Architecture Overview](ARCHITECTURE.md)
**Status**: Current  
**Last Updated**: 2026-02-16

Comprehensive architecture review covering:
- System overview and technology stack
- Architecture patterns (two-database, clean architecture, plugin system)
- Core components (backend and frontend)
- Data architecture and database schemas
- Security architecture and authentication
- Integration points and deployment
- Strengths and recommendations for improvement

**Essential reading for:**
- New developers onboarding to the project
- Anyone planning significant architectural changes
- Security reviews and audits
- Scaling and performance optimization

### [Architecture Diagrams](ARCHITECTURE_DIAGRAMS.md)
**Status**: Current  
**Last Updated**: 2026-02-16

Visual representations of the Codex architecture using ASCII diagrams:
- System architecture overview
- Data hierarchy and relationships
- Request flow diagrams
- Authentication flow
- Agent system architecture
- Plugin system lifecycle
- Deployment architecture
- Database migration strategy
- Security layers

**Use these diagrams for:**
- Understanding system structure at a glance
- Onboarding presentations
- Design discussions
- Documentation in other materials

## Design Documents

Design documents for specific features and systems are in the [`design/`](design/) subdirectory.

### [Dynamic Views](design/dynamic-views.md)
**Status**: ✅ Implemented (v1)  
**Version**: 1.1  
**Date**: 2026-01-24

Query-based dynamic views enabling documents that execute queries and render interactive visualizations.

**Topics**:
- View definition format (.cdx files)
- Query and aggregation API
- Frontend component architecture
- ViewRenderer and plugin integration

### [Plugin System](design/plugin-system.md)
**Status**: ✅ Implemented  
**Version**: 1.0  
**Date**: 2026-01-28

Extensible plugin architecture for custom views, themes, and integrations.

**Plugin Types**:
1. **Custom Views**: Kanban, Gallery, Rollup, Task lists, Corkboard, etc.
2. **Themes**: Antiquarian, Cream, Fieldnotes, Manila, Notebook, etc.
3. **Integrations**: GitHub, OpenGraph, Weather API

**Topics**:
- Plugin manifest specifications
- Vue component interfaces and build system
- Plugin registration API endpoints
- Security and permissions

### [AI Agent Integration](design/ai-agent-integration.md)
**Status**: ✅ Implemented (Phase 1 & 2)  
**Version**: 1.0  
**Date**: 2026-01-30  
**Last Updated**: 2026-02-06

Scoped AI agents for automated assistance within workspaces.

**Topics**:
- Agent configuration and credentials
- Scope guards and permission boundaries
- Tool routing and execution
- Provider adapters (LiteLLM)
- Agent sessions and action logging

## Additional Documentation

### Development

- [CLAUDE.md](../CLAUDE.md) - Development guidelines for AI assistants
- [TEST_CREDENTIALS.md](../TEST_CREDENTIALS.md) - Test user accounts
- [README.md](../README.md) - Project overview and quick start

### API Documentation

Interactive API documentation available when running the backend:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Document Status Summary

| Document | Type | Status | Version | Last Updated |
|----------|------|--------|---------|--------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture | Current | 1.0 | 2026-02-16 |
| [ARCHITECTURE_DIAGRAMS.md](ARCHITECTURE_DIAGRAMS.md) | Architecture | Current | 1.0 | 2026-02-16 |
| [dynamic-views.md](design/dynamic-views.md) | Design | ✅ Implemented | 1.1 | 2026-01-24 |
| [plugin-system.md](design/plugin-system.md) | Design | ✅ Implemented | 1.0 | 2026-01-28 |
| [ai-agent-integration.md](design/ai-agent-integration.md) | Design | ✅ Implemented | 1.0 | 2026-02-06 |

## Contributing to Documentation

When creating or updating documentation:

1. **Use clear structure**: Table of contents, sections, subsections
2. **Include metadata**: Version, date, status, author
3. **Provide context**: Goals, use cases, rationale for decisions
4. **Add examples**: Code snippets, diagrams, screenshots
5. **Link related docs**: Cross-reference to maintain consistency
6. **Update this README**: Add new documents to the index above

### Documentation Review Schedule

- **Architecture docs**: Review every 6 months or after major changes
- **Design docs**: Review when implementation status changes
- **API docs**: Keep in sync with code changes

## Questions or Feedback

For questions or feedback on documentation:
- Open an issue in the repository
- Tag it with `documentation` label
- Reference the specific document and section
