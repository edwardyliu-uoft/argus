# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Comprehensive README.md with full project documentation
  - Project overview and features
  - Detailed installation and setup instructions
  - Configuration guide with all options documented
  - Plugin system documentation with examples
  - Development and testing guidelines
  - Troubleshooting section
  - Contributing guidelines reference

- CONTRIBUTING.md with developer guidelines
  - Development setup instructions
  - Code style guidelines and tools
  - Testing best practices
  - Pull request process
  - Areas for contribution

- Enhanced examples/README.md
  - Comprehensive documentation for all three example projects
  - Usage instructions for demo-project, simple-project, and example-plugin
  - Plugin development guide
  - Testing instructions

- Programmatic API documentation (src/argus/core/api.py)
  - Placeholder with planned API features
  - Examples of future programmatic usage
  - Clear indication that CLI should be used for now

### Changed

- Standardized configuration defaults (src/argus/core/config.py)
  - Added `orchestrator.cross_contract.max_contracts` (default: 10)
  - Added `orchestrator.parallel_test_generation` (default: true)
  - Added `orchestrator.exclude_dirs` to make excluded directories configurable
  - Added `generator.test_generation` with all options
    - `priority_only_threshold` (default: 20)
    - `priority_severities` (default: ["critical", "high"])
    - `test_file_prefix` (default: "Argus.")
  - Updated Gemini model comment to explain Flash vs Pro trade-offs

- Improved CLI command documentation (src/argus/core/cli.py)
  - Added clear docstrings indicating commands under development
  - Commands now warn users when they're not yet implemented
  - Better user experience for incomplete features

- Made excluded directories configurable (src/argus/core/orchestrator/orchestrator.py)
  - Now reads from `orchestrator.exclude_dirs` config
  - Falls back to sensible defaults
  - Resolves TODO comment about hard-coded exclusions

### Fixed

- Configuration inconsistencies between default config and examples
  - Standardized on `gemini-2.5-flash` as default (documented trade-offs)
  - Demo project uses `gemini-2.5-pro` (more thorough analysis)
  - Simple project follows default configuration

- Documentation gaps
  - Root README was minimal ("# argus"), now comprehensive
  - CLI commands advertised features that didn't work
  - No CONTRIBUTING.md for developers

### Documentation

- Project architecture overview
- 7-phase workflow explanation
- Complete configuration reference
- Plugin system guide with working examples
- Development setup and testing instructions
- Troubleshooting common issues

## [0.1.0] - 2025-12-11

### Initial Release

- Multi-phase security analysis workflow
- LLM-powered semantic analysis
- Static analysis integration (Slither, Mythril)
- Automated test generation
- Plugin system for extensibility
- MCP server for tool communication
- Support for Anthropic Claude and Google Gemini
- CLI interface with analyze and config commands
- Example projects demonstrating usage

[Unreleased]: https://github.com/calebchin/argus/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/calebchin/argus/releases/tag/v0.1.0
