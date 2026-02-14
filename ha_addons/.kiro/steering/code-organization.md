# Code Organization & Best Practices

## File Size Management

### Critical Rule: Keep Files Small and Focused

**Maximum file sizes:**
- Python modules: 300-400 lines maximum
- Tool modules: 500 lines maximum (due to multiple tool handlers)
- Configuration files: 100 lines maximum
- Documentation files: 500 lines maximum

**When a file exceeds limits:**
1. Stop and analyze what can be split out
2. Create new focused modules
3. Use clear naming conventions
4. Update imports across the codebase

### File Splitting Strategies

#### For Tool Modules (src/tools/)

**Current situation:**
- `addon_tools.py` has 7 tools and is approaching size limit
- Adding 9 more tools would make it unmaintainable

**Solution: Split by functionality**

```
src/tools/
├── __init__.py
├── addon_management.py      # list, info, start, stop, restart
├── addon_lifecycle.py        # install, uninstall, update, rebuild
├── addon_configuration.py    # get_config, set_config, validate_config
├── addon_discovery.py        # list_store, reload, check_availability
└── addon_logs.py            # get_logs (separate due to size)
```

**Benefits:**
- Each file has 2-4 related tools
- Clear separation of concerns
- Easy to find and maintain
- Can be tested independently

#### For API Client (src/ha_client.py)

**Current situation:**
- `ha_client.py` has 9 methods and is manageable
- Adding 9+ more methods would exceed limits

**Solution: Split by API domain**

```
src/clients/
├── __init__.py
├── base_client.py           # Base HTTP client, auth, error handling
├── addon_client.py          # All addon-related API calls
├── entity_client.py         # Entity API calls (future)
├── device_client.py         # Device API calls (future)
└── system_client.py         # System control API calls (future)
```

**Benefits:**
- Each client focuses on one API domain
- Shared base client for common functionality
- Easy to add new API domains
- Clear responsibility boundaries

#### For Route Handlers (src/routes.py)

**Current situation:**
- `routes.py` has 4 route handlers and is manageable
- File is well-organized and under limit

**Keep as-is:** No splitting needed unless adding many new routes

#### For MCP Handlers (src/mcp_handlers.py)

**Current situation:**
- `mcp_handlers.py` routes to tool modules
- Will grow as more tool modules are added

**Solution: Keep routing logic minimal**

```python
# Good: Minimal routing
def create_call_tool_handler(clients):
    async def handler(name, arguments):
        # Route to appropriate module
        if name.startswith("addon_"):
            return await addon_tools.handle(name, arguments, clients.addon)
        elif name.startswith("entity_"):
            return await entity_tools.handle(name, arguments, clients.entity)
        # ...
    return handler
```

## Planning Before Coding

### Step 1: Analyze Current State

Before adding new features:
1. **Check file sizes**: Use `wc -l src/**/*.py` to see line counts
2. **Identify large files**: Flag any file over 250 lines
3. **Review structure**: Understand current organization
4. **Plan splits**: Decide what needs to be split before adding code

### Step 2: Design the Split

For each file that needs splitting:
1. **List all functions/classes**: What does the file contain?
2. **Group by responsibility**: What belongs together?
3. **Name the new modules**: Clear, descriptive names
4. **Plan imports**: How will modules import each other?
5. **Consider dependencies**: What depends on this file?

### Step 3: Create Split Plan Document

Before making changes, create a plan:

```markdown
## File Split Plan: addon_tools.py

### Current State
- 7 tools, ~350 lines
- Adding 9 tools would reach ~700 lines (TOO BIG)

### Proposed Split
1. addon_management.py (5 tools, ~200 lines)
   - list_addons
   - get_addon_info
   - start_addon
   - stop_addon
   - restart_addon

2. addon_lifecycle.py (4 tools, ~250 lines)
   - install_addon
   - uninstall_addon
   - update_addon
   - rebuild_addon

3. addon_configuration.py (3 tools, ~150 lines)
   - get_addon_configuration
   - set_addon_configuration
   - validate_addon_configuration

4. addon_discovery.py (3 tools, ~150 lines)
   - list_store_addons
   - reload_addons
   - check_addon_availability

5. addon_logs.py (1 tool, ~100 lines)
   - get_addon_logs

### Migration Steps
1. Create new files with proper structure
2. Move tool definitions to new files
3. Move tool handlers to new files
4. Update __init__.py to export all tools
5. Update mcp_handlers.py imports
6. Test each module independently
7. Delete old addon_tools.py
```

### Step 4: Implement Incrementally

1. **Create one new module at a time**
2. **Test after each module**
3. **Update imports immediately**
4. **Verify nothing breaks**
5. **Move to next module**

### Step 5: Verify and Clean Up

After splitting:
1. **Run all tests**: Ensure nothing broke
2. **Check imports**: No circular dependencies
3. **Verify file sizes**: All under limits
4. **Update documentation**: Reflect new structure
5. **Clean up**: Remove old files

## Code Organization Principles

### 1. Single Responsibility Principle

Each file should have ONE clear purpose:
- ✅ `addon_management.py` - Manage running add-ons
- ✅ `addon_lifecycle.py` - Install/uninstall add-ons
- ❌ `addon_stuff.py` - Too vague, unclear purpose

### 2. Clear Naming Conventions

**Module names:**
- Use descriptive nouns: `addon_configuration.py`
- Avoid generic names: `utils.py`, `helpers.py`
- Group by domain: `addon_*.py`, `entity_*.py`

**Function names:**
- Use verb_noun pattern: `get_addon_info`, `set_addon_configuration`
- Be specific: `validate_addon_configuration` not `validate_config`
- Match tool names: Tool `install_addon` → function `handle_install_addon`

### 3. Consistent Structure

Every tool module should follow this pattern:

```python
"""Module docstring explaining purpose."""
import logging
from typing import Any
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# 1. Tool Definitions
def get_tool_definitions() -> list[Tool]:
    """Return tool definitions for this module."""
    return [
        Tool(name="tool1", ...),
        Tool(name="tool2", ...),
    ]

# 2. Tool Handlers
async def handle_tool1(arguments: dict, client) -> list[TextContent]:
    """Handle tool1 execution."""
    # Implementation
    pass

async def handle_tool2(arguments: dict, client) -> list[TextContent]:
    """Handle tool2 execution."""
    # Implementation
    pass

# 3. Main Handler Dispatcher
async def handle(name: str, arguments: dict, client) -> list[TextContent]:
    """Route tool calls to appropriate handler."""
    if name == "tool1":
        return await handle_tool1(arguments, client)
    elif name == "tool2":
        return await handle_tool2(arguments, client)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
```

### 4. Dependency Management

**Import order:**
1. Standard library imports
2. Third-party imports
3. Local imports

**Avoid circular dependencies:**
- Use dependency injection
- Import at function level if needed
- Keep imports at top when possible

### 5. Testing Structure

Mirror the source structure:

```
src/
├── tools/
│   ├── addon_management.py
│   └── addon_lifecycle.py
tests/
├── tools/
│   ├── test_addon_management.py
│   └── test_addon_lifecycle.py
```

## When to Split Files

### Triggers for Splitting

Split a file when:
1. **Line count > 300**: File is getting too large
2. **Multiple responsibilities**: File does more than one thing
3. **Hard to navigate**: Takes too long to find functions
4. **Merge conflicts**: Multiple people editing same file
5. **Testing is hard**: Too many things to test in one file

### How to Split

1. **Identify natural boundaries**: What groups together?
2. **Create new files**: One per responsibility
3. **Move code**: Copy functions to new files
4. **Update imports**: Fix all import statements
5. **Test thoroughly**: Ensure nothing broke
6. **Delete old code**: Remove from original file
7. **Update docs**: Reflect new structure

## Example: Splitting addon_tools.py

### Before (addon_tools.py - 350 lines, adding 9 tools → 700 lines)

```python
# TOO BIG - NEEDS SPLITTING

def get_addon_tool_definitions():
    return [
        # 7 existing tools
        # 9 new tools (would make file huge)
    ]

async def handle_addon_tool(name, args, client):
    if name == "list_addons":
        # 50 lines
    elif name == "get_addon_info":
        # 40 lines
    # ... 14 more tools (700+ lines total)
```

### After (Multiple focused files)

```python
# src/tools/addon_management.py (200 lines)
def get_tool_definitions():
    return [
        Tool(name="list_addons", ...),
        Tool(name="get_addon_info", ...),
        Tool(name="start_addon", ...),
        Tool(name="stop_addon", ...),
        Tool(name="restart_addon", ...),
    ]

async def handle(name, args, client):
    # Route to handlers
    pass

# src/tools/addon_lifecycle.py (250 lines)
def get_tool_definitions():
    return [
        Tool(name="install_addon", ...),
        Tool(name="uninstall_addon", ...),
        Tool(name="update_addon", ...),
        Tool(name="rebuild_addon", ...),
    ]

async def handle(name, args, client):
    # Route to handlers
    pass

# src/tools/__init__.py (aggregator)
from .addon_management import get_tool_definitions as get_mgmt_tools
from .addon_lifecycle import get_tool_definitions as get_lifecycle_tools
from .addon_configuration import get_tool_definitions as get_config_tools
from .addon_discovery import get_tool_definitions as get_discovery_tools
from .addon_logs import get_tool_definitions as get_log_tools

def get_all_addon_tools():
    """Get all addon tool definitions."""
    return (
        get_mgmt_tools() +
        get_lifecycle_tools() +
        get_config_tools() +
        get_discovery_tools() +
        get_log_tools()
    )
```

## Pre-Implementation Checklist

Before writing ANY new code:

- [ ] Check current file sizes (`wc -l src/**/*.py`)
- [ ] Identify files that will exceed 300 lines
- [ ] Create file split plan if needed
- [ ] Design new module structure
- [ ] Plan import changes
- [ ] Document the plan
- [ ] Get approval for structure
- [ ] THEN start coding

## Implementation Checklist

When implementing new features:

- [ ] Create new files if needed (don't add to large files)
- [ ] Follow consistent structure pattern
- [ ] Keep functions focused and small
- [ ] Add docstrings to all functions
- [ ] Use type hints
- [ ] Test each module independently
- [ ] Update imports in other files
- [ ] Verify file sizes stay under limits
- [ ] Update documentation

## Red Flags

Stop and refactor if you see:

- ❌ File over 400 lines
- ❌ Function over 50 lines
- ❌ File with multiple unrelated responsibilities
- ❌ Difficulty finding specific code
- ❌ Import statements getting complex
- ❌ Circular dependencies
- ❌ Copy-pasted code across files

## Summary

**Golden Rules:**
1. **Plan before coding** - Design the structure first
2. **Keep files small** - Max 300-400 lines
3. **Split by responsibility** - One purpose per file
4. **Use clear names** - Descriptive and specific
5. **Test after changes** - Verify nothing broke
6. **Document structure** - Update docs to match code

**Remember:** It's easier to split files BEFORE adding code than to refactor a 1000-line monster later!
