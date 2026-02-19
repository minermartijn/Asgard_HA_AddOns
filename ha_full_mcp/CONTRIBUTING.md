# Contributing to HA Full MCP Server

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

## Code of Conduct

Be respectful, constructive, and collaborative. We're all here to make this project better.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/ha-full-mcp-server/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Home Assistant version
   - Addon version
   - Relevant logs from the addon

### Suggesting Features

1. Check [existing feature requests](https://github.com/yourusername/ha-full-mcp-server/issues?q=is%3Aissue+label%3Aenhancement)
2. Create a new issue with:
   - Clear description of the feature
   - Use case and benefits
   - Possible implementation approach

### Contributing Code

1. **Fork the repository**
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following our code standards
4. **Test your changes** with a real Home Assistant instance
5. **Commit with clear messages**:
   ```bash
   git commit -m "Add feature: brief description"
   ```
6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Create a Pull Request** with:
   - Description of changes
   - Related issue numbers
   - Testing performed

## Development Setup

### Prerequisites

- Home Assistant installation (for testing)
- Python 3.11 or later
- Git

### Local Development

1. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/ha-full-mcp-server.git
   cd ha-full-mcp-server
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```bash
   export SUPERVISOR_TOKEN="your_supervisor_token"
   export HA_TOKEN="your_ha_token"
   ```

4. Run the server:
   ```bash
   python src/server.py
   ```

### Testing

Test your changes with a real Home Assistant instance:

1. Install the addon in Home Assistant
2. Configure it with your changes
3. Test all affected tools through an MCP client
4. Verify error handling with invalid inputs
5. Check logs for any errors or warnings

## Code Standards

### File Organization

- **Keep files under 500 lines** - See [file size guidelines](.kiro/steering/file-size-guidelines.md)
- **One responsibility per file** - Split large files by domain or feature
- **Clear naming** - Use descriptive file and function names

### Python Style

- Follow PEP 8 style guidelines
- Use type hints for function parameters and returns
- Include docstrings for all public functions
- Use async/await for all I/O operations

### Example Function

```python
async def get_addon_info(self, addon_slug: str) -> dict[str, Any]:
    """Get detailed information about a specific addon.
    
    Args:
        addon_slug: The slug identifier of the addon
    
    Returns:
        Dictionary containing addon information
    
    Raises:
        ValueError: If addon_slug is invalid
        aiohttp.ClientError: If API request fails
    """
    if not addon_slug:
        raise ValueError("addon_slug cannot be empty")
    
    try:
        result = await self._make_request(
            "GET",
            f"{self.hassio_url}/addons/{addon_slug}/info",
            use_ha_token=False
        )
        return result.get("data", {})
    except aiohttp.ClientError as e:
        logger.error(f"Failed to get addon info: {e}")
        raise
```

### Error Handling

- Always use try-except blocks for API calls
- Provide helpful error messages
- Log errors with appropriate severity
- Return user-friendly error responses

### Tool Implementation Pattern

When adding new tools, follow this pattern:

1. **Define the tool** in `src/tools/category_tools.py`:
   ```python
   Tool(
       name="tool_name",
       description="Clear description",
       inputSchema={...}
   )
   ```

2. **Implement the handler** in the same file:
   ```python
   async def handle_tool(name, arguments, ha_client):
       # Implementation
   ```

3. **Add API method** in `src/api/category_api.py`:
   ```python
   async def api_method(self, param):
       # API call
   ```

4. **Register in handlers** (`src/mcp_handlers.py`):
   - Import the tool module
   - Add to tool list
   - Add to routing

5. **Add configuration** (`src/config.py` and `config.yaml`):
   - Add tool toggle mapping
   - Add to config schema

6. **Update documentation**:
   - Add to README.md
   - Add to CHANGELOG.md
   - Update tool count

See [development guide](.kiro/steering/ha-mcp-development.md) for detailed patterns.

## Documentation

### User Documentation

- **README.md** - Main project documentation
- **docs/TOOLS_REFERENCE.md** - Complete tool reference
- **docs/TOOL_CUSTOMIZATION.md** - Configuration guide
- **docs/QUICK_REFERENCE.md** - Quick reference
- **CHANGELOG.md** - Version history

### Developer Documentation

- **.kiro/steering/ha-mcp-development.md** - Development guide
- **.kiro/steering/file-size-guidelines.md** - Code organization
- **Code comments** - Inline documentation

### Writing Documentation

- Use clear, concise language
- Include code examples
- Provide real-world use cases
- Keep formatting consistent
- Update all relevant docs when making changes

## Pull Request Process

1. **Ensure your PR**:
   - Follows code standards
   - Includes tests (if applicable)
   - Updates documentation
   - Has a clear description

2. **PR will be reviewed for**:
   - Code quality and style
   - Functionality and correctness
   - Documentation completeness
   - Breaking changes

3. **After approval**:
   - Squash commits if requested
   - Maintainer will merge

## Versioning

We use [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.x.x) - Breaking changes
- **MINOR** (x.1.x) - New features, backward compatible
- **PATCH** (x.x.1) - Bug fixes, backward compatible

## Release Process

1. Update version in `config.yaml`
2. Update CHANGELOG.md with changes
3. Create release notes in `docs/releases/`
4. Tag the release: `git tag v1.x.x`
5. Push tags: `git push --tags`

## Questions?

- Open a [Discussion](https://github.com/yourusername/ha-full-mcp-server/discussions)
- Ask in the [Home Assistant Community](https://community.home-assistant.io/)
- Check existing [Issues](https://github.com/yourusername/ha-full-mcp-server/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to HA Full MCP Server! 🎉
