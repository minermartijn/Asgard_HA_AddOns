# Home Assistant MCP Server - New Add-on Tools Implementation

## High Priority - Essential Tools

### 1. Install Add-on Tool
**Validates: Requirements US-1 (Remote Add-on Management)**

- [x] 1.1 Implement `install_addon` method in `ha_client.py`
  - [x] Add POST request to `/addons/{addon_slug}/install` endpoint
  - [x] Handle installation progress/status
  - [x] Add error handling for installation failures
  - [x] Test with various add-ons from store

- [x] 1.2 Create `install_addon` tool definition in `addon_tools.py`
  - [x] Define input schema with `addon_slug` parameter
  - [x] Add optional `version` parameter for specific versions
  - [x] Write comprehensive tool description
  - [x] Document required permissions

- [x] 1.3 Implement `install_addon` tool handler
  - [x] Validate addon_slug parameter
  - [x] Call ha_client.install_addon()
  - [x] Format installation progress response
  - [x] Add success/failure confirmation
  - [x] Handle timeout for long installations

- [x] 1.4 Test install_addon tool
  - [-] Test installing from official store
  - [x] Test installing custom add-ons
  - [x] Test error cases (invalid slug, already installed)
  - [x] Verify add-on appears in list after install

### 2. Uninstall Add-on Tool
**Validates: Requirements US-1 (Remote Add-on Management)**

- [x] 2.1 Implement `uninstall_addon` method in `ha_client.py`
  - [x] Add POST request to `/addons/{addon_slug}/uninstall` endpoint
  - [x] Handle uninstallation process
  - [x] Add error handling for uninstall failures
  - [x] Test with various installed add-ons

- [x] 2.2 Create `uninstall_addon` tool definition in `addon_tools.py`
  - [ ] Define input schema with `addon_slug` parameter
  - [x] Add optional `remove_config` parameter (keep/remove config)
  - [x] Write comprehensive tool description with warnings
  - [x] Document destructive nature of operation

- [x] 2.3 Implement `uninstall_addon` tool handler
  - [ ] Validate addon_slug parameter
  - [x] Add confirmation check (optional confirm parameter)
  - [x] Call ha_client.uninstall_addon()
  - [x] Format uninstallation response
  - [x] Add success confirmation

- [ ] 2.4 Test uninstall_addon tool
  - [ ] Test uninstalling various add-ons
  - [ ] Test with/without config removal
  - [ ] Test error cases (not installed, in use)
  - [ ] Verify add-on removed from list

### 3. Get Add-on Configuration Tool
**Validates: Requirements US-5 (Configurable Server Settings)**

- [x] 3.1 Implement `get_addon_configuration` method in `ha_client.py`
  - [x] Add GET request to `/addons/{addon_slug}/options` endpoint
  - [x] Parse configuration options
  - [x] Handle add-ons without configuration
  - [ ] Test with various add-on types

- [x] 3.2 Create `get_addon_configuration` tool definition in `addon_tools.py`
  - [ ] Define input schema with `addon_slug` parameter
  - [ ] Write comprehensive tool description
  - [x] Document configuration structure

- [x] 3.3 Implement `get_addon_configuration` tool handler
  - [ ] Validate addon_slug parameter
  - [x] Call ha_client.get_addon_configuration()
  - [x] Format configuration as readable structure
  - [x] Include schema information if available
  - [x] Show current vs default values

- [ ] 3.4 Test get_addon_configuration tool
  - [ ] Test with add-ons that have configuration
  - [ ] Test with add-ons without configuration
  - [ ] Test error cases (invalid slug)
  - [ ] Verify configuration matches UI

### 4. Set Add-on Configuration Tool
**Validates: Requirements US-5 (Configurable Server Settings)**

- [x] 4.1 Implement `set_addon_configuration` method in `ha_client.py`
  - [x] Add POST request to `/addons/{addon_slug}/options` endpoint
  - [x] Support partial configuration updates
  - [x] Handle configuration validation errors
  - [ ] Test with various configuration types

- [x] 4.2 Create `set_addon_configuration` tool definition in `addon_tools.py`
  - [ ] Define input schema with `addon_slug` parameter
  - [x] Add `options` parameter (JSON object)
  - [x] Add optional `boot` parameter (auto/manual)
  - [x] Add optional `network` parameter
  - [ ] Write comprehensive tool description

- [x] 4.3 Implement `set_addon_configuration` tool handler
  - [ ] Validate addon_slug parameter
  - [x] Validate options against schema
  - [x] Call ha_client.set_addon_configuration()
  - [x] Format configuration update response
  - [x] Show before/after values
  - [x] Add restart recommendation if needed

- [ ] 4.4 Test set_addon_configuration tool
  - [ ] Test updating various configuration options
  - [ ] Test partial updates
  - [ ] Test validation errors
  - [ ] Test boot mode changes
  - [ ] Verify configuration persists

### 5. Validate Add-on Configuration Tool
**Validates: Requirements US-7 (Clean Error Handling)**

- [x] 5.1 Implement `validate_addon_configuration` method in `ha_client.py`
  - [x] Add POST request to `/addons/{addon_slug}/options/validate` endpoint
  - [x] Parse validation errors
  - [x] Return detailed validation results
  - [ ] Test with valid and invalid configurations

- [x] 5.2 Create `validate_addon_configuration` tool definition in `addon_tools.py`
  - [ ] Define input schema with `addon_slug` parameter
  - [x] Add `options` parameter (JSON object to validate)
  - [ ] Write comprehensive tool description
  - [x] Document validation rules

- [x] 5.3 Implement `validate_addon_configuration` tool handler
  - [ ] Validate addon_slug parameter
  - [x] Call ha_client.validate_addon_configuration()
  - [x] Format validation results
  - [x] Show specific validation errors
  - [x] Provide suggestions for fixes

- [ ] 5.4 Test validate_addon_configuration tool
  - [ ] Test with valid configurations
  - [ ] Test with invalid configurations
  - [ ] Test with missing required fields
  - [ ] Test with wrong data types
  - [ ] Verify error messages are helpful

## Medium Priority - Advanced Management Tools

### 6. Rebuild Add-on Tool
**Validates: Requirements US-1 (Remote Add-on Management)**

- [x] 6.1 Implement `rebuild_addon` method in `ha_client.py`
  - [x] Add POST request to `/addons/{addon_slug}/rebuild` endpoint
  - [x] Handle rebuild process
  - [x] Add error handling for build failures
  - [ ] Test with local/custom add-ons

- [x] 6.2 Create `rebuild_addon` tool definition in `addon_tools.py`
  - [ ] Define input schema with `addon_slug` parameter
  - [ ] Write comprehensive tool description
  - [x] Document when rebuild is needed

- [x] 6.3 Implement `rebuild_addon` tool handler
  - [ ] Validate addon_slug parameter
  - [x] Call ha_client.rebuild_addon()
  - [x] Format rebuild progress response
  - [x] Show build logs if available
  - [ ] Add success/failure confirmation

- [ ] 6.4 Test rebuild_addon tool
  - [ ] Test with local add-ons
  - [ ] Test with custom add-ons
  - [ ] Test error cases (not rebuildable)
  - [ ] Verify add-on works after rebuild

### 7. List Store Add-ons Tool
**Validates: Requirements US-1 (Remote Add-on Management)**

- [ ] 7.1 Implement `list_store_addons` method in `ha_client.py`
  - [ ] Add GET request to `/store/addons` endpoint
  - [ ] Parse store add-on list
  - [ ] Include installation status
  - [ ] Test with full store catalog

- [ ] 7.2 Create `list_store_addons` tool definition in `addon_tools.py`
  - [ ] Define input schema (no parameters or optional filters)
  - [ ] Add optional `repository` filter parameter
  - [ ] Add optional `search` parameter
  - [ ] Write comprehensive tool description

- [ ] 7.3 Implement `list_store_addons` tool handler
  - [ ] Call ha_client.list_store_addons()
  - [ ] Format store add-ons as readable list
  - [ ] Show installation status for each
  - [ ] Include version information
  - [ ] Add filtering logic if parameters provided

- [ ] 7.4 Test list_store_addons tool
  - [ ] Test listing all store add-ons
  - [ ] Test with repository filter
  - [ ] Test with search query
  - [ ] Verify installed status is accurate

### 8. Reload Add-ons Tool
**Validates: Requirements US-1 (Remote Add-on Management)**

- [ ] 8.1 Implement `reload_addons` method in `ha_client.py`
  - [ ] Add POST request to `/addons/reload` endpoint
  - [ ] Handle reload process
  - [ ] Add error handling
  - [ ] Test reload operation

- [ ] 8.2 Create `reload_addons` tool definition in `addon_tools.py`
  - [ ] Define input schema (no parameters)
  - [ ] Write comprehensive tool description
  - [ ] Document when reload is needed

- [ ] 8.3 Implement `reload_addons` tool handler
  - [ ] Call ha_client.reload_addons()
  - [ ] Format reload response
  - [ ] Show number of add-ons refreshed
  - [ ] Add success confirmation

- [ ] 8.4 Test reload_addons tool
  - [ ] Test reload operation
  - [ ] Verify add-on list updates
  - [ ] Test after adding new repository
  - [ ] Verify no disruption to running add-ons

## Lower Priority - Specialized Tools

### 9. Check Add-on Availability Tool
**Validates: Requirements US-1 (Remote Add-on Management)**

- [ ] 9.1 Implement `check_addon_availability` method in `ha_client.py`
  - [ ] Add GET request to `/addons/{addon_slug}/available` endpoint
  - [ ] Parse availability information
  - [ ] Include architecture compatibility
  - [ ] Test with various add-ons

- [ ] 9.2 Create `check_addon_availability` tool definition in `addon_tools.py`
  - [ ] Define input schema with `addon_slug` parameter
  - [ ] Write comprehensive tool description
  - [ ] Document availability criteria

- [ ] 9.3 Implement `check_addon_availability` tool handler
  - [ ] Validate addon_slug parameter
  - [ ] Call ha_client.check_addon_availability()
  - [ ] Format availability response
  - [ ] Show compatibility details
  - [ ] Explain why unavailable if applicable

- [ ] 9.4 Test check_addon_availability tool
  - [ ] Test with available add-ons
  - [ ] Test with unavailable add-ons
  - [ ] Test architecture compatibility
  - [ ] Verify accuracy of availability info

## Integration & Testing

### 10. Update Tool Registration
- [ ] 10.1 Update `get_addon_tool_definitions()` in `addon_tools.py`
  - [ ] Add all 9 new tool definitions to the list
  - [ ] Verify tool schemas are correct
  - [ ] Test tool discovery

- [ ] 10.2 Update `handle_addon_tool()` in `addon_tools.py`
  - [ ] Add handlers for all 9 new tools
  - [ ] Ensure proper error handling for each
  - [ ] Test tool routing

### 11. End-to-End Testing
- [ ] 11.1 Test all new tools with MCP Inspector
  - [ ] Verify tool schemas display correctly
  - [ ] Test each tool with valid inputs
  - [ ] Test error cases for each tool

- [ ] 11.2 Test all new tools with Kiro
  - [ ] Test through Cloudflare proxy
  - [ ] Verify authentication works
  - [ ] Test concurrent tool calls
  - [ ] Verify clean logs (no errors)

- [ ] 11.3 Integration testing
  - [ ] Test install → configure → start workflow
  - [ ] Test list store → install → verify workflow
  - [ ] Test validate → set config → restart workflow
  - [ ] Test uninstall → verify removed workflow

### 12. Documentation Updates
- [ ] 12.1 Update README.md
  - [ ] Add new tools to feature list
  - [ ] Update tool count (7 → 16)
  - [ ] Add usage examples for new tools

- [ ] 12.2 Update ARCHITECTURE.md
  - [ ] Document new tool capabilities
  - [ ] Update MCP Tools section
  - [ ] Add new API endpoints used

- [ ] 12.3 Update version
  - [ ] Bump version to 0.7.0 in config.yaml
  - [ ] Update CHANGELOG.md
  - [ ] Document new features

## Notes

- All tasks reference existing patterns from current add-on tools
- Each tool follows the same structure: ha_client method → tool definition → tool handler → tests
- Priority order: High (1-5) → Medium (6-8) → Low (9)
- Total new tools: 9 (bringing total from 7 to 16)
- Estimated implementation time: 2-3 days for all tools
