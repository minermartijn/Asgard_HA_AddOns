# Documentation Guidelines

## Core Principle: Minimal Documentation Files

**DO NOT create excessive markdown documentation files in the repository root.**

## Essential Files Only

For Home Assistant addon repositories, only these documentation files should exist in the root:

1. **README.md** - Main project documentation
2. **CHANGELOG.md** - Version history
3. **CONTRIBUTING.md** - Contribution guidelines
4. **LICENSE** - License file

That's it. Nothing more.

## What NOT to Create

### ❌ Never Create These Files

- Implementation status files (IMPLEMENTATION_COMPLETE.md, REFACTORING_COMPLETE.md)
- Test result files (TEST_RESULTS.md, TOOL_TOGGLE_TEST_RESULTS.md)
- Version update files (VERSION_UPDATE_COMPLETE.md, VERSION_1.X.0_RELEASE_NOTES.md)
- Internal development notes (DEPLOYMENT_CHECKLIST.md, IMPLEMENTATION_PROGRESS.md)
- Summary files (SUMMARY.md, WORKSPACE_IMPROVEMENT_SUMMARY.md)
- Status files (STATUS.md, READY_FOR_TESTING.md)
- Guide files (GUIDE.md, NEW_TOOLS_GUIDE.md)
- Any other internal documentation

### Why Not?

- **Clutters the repository** - Makes it look unprofessional
- **Confuses users** - They don't need internal development notes
- **Hard to maintain** - More files = more to keep updated
- **Not standard practice** - Professional addons don't do this
- **Wastes space** - Information should be in proper places

## Where to Put Information Instead

### Version Release Notes
- **Don't**: Create VERSION_1.8.0_RELEASE_NOTES.md
- **Do**: Add comprehensive entry to CHANGELOG.md

### Implementation Status
- **Don't**: Create IMPLEMENTATION_COMPLETE.md
- **Do**: Use git commit messages and PR descriptions

### Test Results
- **Don't**: Create TEST_RESULTS.md
- **Do**: Document in code comments or git commit messages

### Development Notes
- **Don't**: Create internal .md files in root
- **Do**: Use .kiro/steering/ for development guidelines (hidden from users)

### Feature Documentation
- **Don't**: Create separate feature guide files
- **Do**: Add to README.md in appropriate section

## README.md Structure

The README should contain all user-facing information:

```markdown
# Project Title

Brief description

## Features
- Feature list

## Installation
- Installation steps

## Configuration
- Configuration guide

## Usage
- Usage examples

## Tools
- Complete tool list

## Troubleshooting
- Common issues

## Contributing
- Link to CONTRIBUTING.md

## License
- License information
```

## CHANGELOG.md Structure

Version history with all changes:

```markdown
# Changelog

## [1.8.0] - 2026-02-19

### Added
- New features

### Changed
- Breaking changes
- Improvements

### Fixed
- Bug fixes

## [1.7.1] - 2026-02-15
...
```

## When You're Tempted to Create a New .md File

Ask yourself:

1. **Is this for users?** → Add to README.md
2. **Is this version history?** → Add to CHANGELOG.md
3. **Is this for contributors?** → Add to CONTRIBUTING.md
4. **Is this internal development?** → Use git commits or .kiro/steering/
5. **Is this temporary status?** → Don't document it at all

## Examples from Real Projects

### Good (Professional Addons)
```
addon_repo/
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── config.yaml
├── Dockerfile
└── src/
```

### Bad (Cluttered)
```
addon_repo/
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── IMPLEMENTATION_COMPLETE.md      ❌
├── TEST_RESULTS.md                 ❌
├── VERSION_UPDATE_COMPLETE.md      ❌
├── REFACTORING_STATUS.md           ❌
├── DEPLOYMENT_CHECKLIST.md         ❌
├── READY_FOR_TESTING.md            ❌
└── ... (too many files)
```

## Steering Files Exception

Development guidelines CAN be in `.kiro/steering/`:
- These are hidden from users (not in root)
- Used for AI assistant context
- Help maintain consistency
- Don't clutter the repository

Examples:
- `.kiro/steering/ha-mcp-development.md` ✅
- `.kiro/steering/file-size-guidelines.md` ✅
- `.kiro/steering/documentation-guidelines.md` ✅ (this file)

## Summary

**Rule of thumb**: If you're about to create a new .md file in the root directory, STOP and ask:
- Is this one of the 4 essential files? (README, CHANGELOG, CONTRIBUTING, LICENSE)
- If no → Don't create it
- If yes → Make sure it doesn't already exist

Keep repositories clean, professional, and user-friendly.

---

**Last Updated**: 2026-02-20  
**Applies To**: All markdown files in repository root
