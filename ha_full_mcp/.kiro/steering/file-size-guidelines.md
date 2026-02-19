---
inclusion: always
---

# File Size and Organization Guidelines

## Core Principle: Keep Files AI-Friendly

**Maximum file size: 500 lines per file**

AI assistants work best with smaller, focused files. When files exceed 500 lines, they become difficult to read, edit, and maintain.

## Why 500 Lines?

- AI context windows can truncate large files
- Easier to understand and modify
- Better separation of concerns
- Faster to load and process
- Reduces merge conflicts
- Improves code navigation

## When to Split a File

Split a file when it:
- Exceeds 500 lines
- Contains multiple unrelated responsibilities
- Has distinct logical groupings
- Mixes definitions with implementations
- Combines different API domains

## How to Split Files

### 1. By Functionality
```
# Before: one large file
api_client.py (1,400 lines)

# After: split by domain
api/
├── base_client.py      (150 lines)
├── addon_api.py        (400 lines)
├── system_api.py       (250 lines)
├── backup_api.py       (150 lines)
├── integration_api.py  (150 lines)
└── entity_api.py       (200 lines)
```

### 2. By Responsibility
```
# Before: definitions + handlers together
addon_tools.py (2,005 lines)

# After: separate concerns (ACTUAL IMPLEMENTATION ✅)
tools/addon/
├── __init__.py                 (68 lines - router)
├── definitions.py              (323 lines - tool schemas)
├── basic_handlers.py           (64 lines - list, info)
├── lifecycle_handlers.py       (156 lines - start/stop/restart/logs/update)
├── addon_config_handlers.py    (351 lines - addon configuration)
├── management_handlers.py      (432 lines - install/uninstall)
├── store_handlers.py           (379 lines - store/rebuild/availability)
├── logs_handlers.py            (266 lines - system logs/HA restart)
└── config_file_handlers.py     (342 lines - config file operations)
```

### 3. Using Mixins for Classes
```python
# Base class with core functionality
class BaseClient:
    def __init__(self): ...
    def _make_request(self): ...

# Separate mixins for each domain
class AddonAPI:
    async def list_addons(self): ...
    async def install_addon(self): ...

class SystemAPI:
    async def get_logs(self): ...
    async def restart(self): ...

# Combine using multiple inheritance
class HomeAssistantClient(BaseClient, AddonAPI, SystemAPI):
    pass
```

## File Organization Patterns

### Pattern 1: API Modules
```
src/api/
├── __init__.py          # Exports main client
├── base_client.py       # Auth & requests
├── domain1_api.py       # Domain 1 methods
├── domain2_api.py       # Domain 2 methods
└── domain3_api.py       # Domain 3 methods
```

### Pattern 2: Tool Modules
```
src/tools/
├── __init__.py
├── tool_category1/
│   ├── __init__.py
│   ├── definitions.py   # Tool schemas
│   └── handlers.py      # Tool implementations
└── tool_category2/
    ├── __init__.py
    ├── definitions.py
    └── handlers.py
```

### Pattern 3: Feature Modules
```
src/features/
├── __init__.py
├── feature1/
│   ├── __init__.py
│   ├── models.py        # Data models
│   ├── service.py       # Business logic
│   └── handlers.py      # Request handlers
└── feature2/
    └── ...
```

## Refactoring Checklist

When refactoring large files:

- [ ] Identify logical groupings (by domain, responsibility, or feature)
- [ ] Create new directory structure
- [ ] Split file into modules (each < 500 lines)
- [ ] Update imports in dependent files
- [ ] Test that everything still works
- [ ] Update documentation
- [ ] Delete old large file

## Best Practices

### DO:
✅ Keep files under 500 lines
✅ Group related functionality together
✅ Use clear, descriptive file names
✅ Separate definitions from implementations
✅ Use mixins for shared behavior
✅ Create __init__.py files for clean imports
✅ Document module purpose at the top

### DON'T:
❌ Create files over 500 lines
❌ Mix unrelated functionality
❌ Use generic names like "utils.py" or "helpers.py"
❌ Put everything in one file
❌ Create deep nesting (max 3 levels)
❌ Duplicate code across modules

## Example: Current Project Structure

### API Client (Refactored)
```
src/api/                    # All API methods
├── __init__.py            # 26 lines - exports HomeAssistantClient
├── base_client.py         # 75 lines - auth & requests
├── addon_api.py           # 484 lines - addon management
├── system_api.py          # 188 lines - logs, config, restart
├── backup_api.py          # 81 lines - backup operations
├── integration_api.py     # 89 lines - integration management
└── entity_api.py          # 101 lines - entity & service operations
```

### Tools (All Refactored ✅)
```
src/tools/
├── addon/                 # 22 addon tools (refactored from 2,005 line monolith)
│   ├── __init__.py                 # 68 lines - ✓ Router
│   ├── definitions.py              # 323 lines - ✓ Tool schemas
│   ├── basic_handlers.py           # 64 lines - ✓ List, info
│   ├── lifecycle_handlers.py       # 156 lines - ✓ Start, stop, restart
│   ├── addon_config_handlers.py    # 351 lines - ✓ Configuration
│   ├── management_handlers.py      # 432 lines - ✓ Install, uninstall
│   ├── store_handlers.py           # 379 lines - ✓ Store operations
│   ├── logs_handlers.py            # 266 lines - ✓ System logs
│   └── config_file_handlers.py     # 342 lines - ✓ Config files
├── backup_tools.py        # 371 lines - ✓ Good size
├── entity_tools.py        # 425 lines - ✓ Good size
└── integration_tools.py   # 257 lines - ✓ Good size
```

## Monitoring File Sizes

Check file sizes regularly:
```bash
# List Python files by line count
find src -name "*.py" -type f -exec wc -l {} + | sort -rn

# Find files over 500 lines
find src -name "*.py" -type f -exec wc -l {} + | awk '$1 > 500'
```

## When Adding New Code

Before adding new functionality:
1. Check current file size
2. If file is approaching 500 lines, refactor first
3. Consider if new code belongs in existing file
4. Create new module if needed
5. Keep the 500-line limit in mind

## Benefits of This Approach

- **For AI**: Easier to read and edit entire files
- **For Developers**: Better code organization
- **For Maintenance**: Easier to find and fix issues
- **For Testing**: Smaller, focused test files
- **For Collaboration**: Fewer merge conflicts
- **For Performance**: Faster file operations

## Remember

> "The best code is code that's easy to change. Small, focused files are easy to change."

Keep files small, keep them focused, keep them maintainable.

---

**Last Updated**: 2026-02-15
**Applies To**: All Python files in the project
