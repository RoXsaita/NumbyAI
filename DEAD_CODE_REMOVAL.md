# Dead Code Removal Plan

## Files Identified for Removal

### 1. Static Server (Dead Code)
**File**: `mcp-server/static_server.py`
**Reason**: Backend now serves static files via `/static` mount in `main.py` (line 1346)
**Action**: Remove or archive

### 2. Test HTML Files
**Files**: 
- `mcp-server/dashboard-test.html`
- `mcp-server/test-dashboard.html`
**Reason**: Test files, not used in production
**Action**: Move to `mcp-server/tests/` or remove

### 3. Deprecated Module (Still in Use)
**File**: `web/src/lib/use-openai-global.ts`
**Status**: DEPRECATED but still imported in `dashboard.tsx:34`
**Action**: 
1. Replace usage in `dashboard.tsx` with direct window access
2. Then remove the file

### 4. Version History (Archive)
**Directory**: `mcp-server/app/tools/version_history/`
**Files**: 8 old version files
**Action**: Archive to `.archive/` or remove if not needed

### 5. Audit Directory (Test Artifacts)
**Directory**: `mcp-server/audit/`
**Action**: Already ignored by git, but could add explicit entry to `.gitignore`

## Implementation

To remove dead code, run:
```bash
# Remove static server (if confirmed not needed)
rm mcp-server/static_server.py

# Remove test HTML files
rm mcp-server/dashboard-test.html
rm mcp-server/test-dashboard.html

# Archive version history
mkdir -p .archive/tools
mv mcp-server/app/tools/version_history .archive/tools/

# After fixing dashboard.tsx, remove deprecated module
rm web/src/lib/use-openai-global.ts
```

## Notes

- `static_server.py` might be useful for development, consider keeping if needed
- `use-openai-global.ts` must be replaced in `dashboard.tsx` before removal
- Version history files might be useful for reference, consider archiving instead of deleting
