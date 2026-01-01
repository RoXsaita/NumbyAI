# GitHub Issues to Create

## Issue 1: Remove Dead Code Files
**Title**: Clean up dead code after refactor
**Labels**: `cleanup`, `technical-debt`
**Priority**: Low
**Description**:
After the major refactor, several files are no longer needed:
- `mcp-server/static_server.py` - Backend now serves static files directly
- `mcp-server/dashboard-test.html` and `test-dashboard.html` - Test files
- `mcp-server/app/tools/version_history/` - Old version history (8 files)
- `web/src/lib/use-openai-global.ts` - Deprecated (needs replacement in dashboard.tsx first)

**Action Items**:
1. Replace `use-openai-global.ts` usage in `dashboard.tsx` with direct window access
2. Remove identified dead code files
3. Archive version history if needed for reference

---

## Issue 2: Fix Build Syntax Error
**Title**: Fixed syntax error in dashboard.tsx
**Labels**: `bug`, `frontend`
**Priority**: High (already fixed)
**Status**: ✅ Fixed
**Description**:
Fixed orphaned `catch` block without `try` statement at line 2404 in `dashboard.tsx`.

**Resolution**:
Added `try` block around the code in `handleToggleFullscreen` function.

---

## Issue 3: Address Authentication TODOs
**Title**: Implement proper authentication in REST API endpoints
**Labels**: `enhancement`, `security`, `backend`
**Priority**: High
**Description**:
Multiple REST API endpoints currently use `get_or_create_test_user()` with TODO comments to get user from auth:
- `/api/statements/upload` (line 939)
- `/api/transactions` GET (line 989)
- `/api/transactions` PATCH (line 1035)
- `/api/financial-data` (line 1077)
- `/api/budgets` GET/POST (lines 1106, 1138)
- `/api/preferences` GET/POST (line 1138)

**Action Items**:
1. Extract user from JWT token or OAuth2 token in middleware
2. Replace all `get_or_create_test_user()` calls with proper auth
3. Add authentication middleware to protect endpoints

---

## Issue 4: Implement Password Hashing
**Title**: Add password hashing for user registration/login
**Labels**: `security`, `backend`
**Priority**: High
**Description**:
Password handling in auth endpoints needs proper hashing:
- `/api/auth/register` (line 1177): `# TODO: Hash password properly`
- `/api/auth/login` (lines 1224, 1235): `# TODO: Verify password properly` and `# TODO: Verify password hash`

**Action Items**:
1. Use bcrypt or similar for password hashing
2. Hash passwords on registration
3. Verify password hashes on login

---

## Issue 5: Complete Chat Functionality
**Title**: Implement chat message and streaming endpoints
**Labels**: `enhancement`, `backend`
**Priority**: Medium
**Description**:
Chat endpoints have placeholder implementations:
- `/api/chat/messages` (line 907): `# TODO: Handle file uploads properly`
- `/api/chat/stream` (line 924): `# TODO: Implement SSE streaming with Cursor Agent`

**Action Items**:
1. Integrate with Cursor Agent service
2. Implement proper file upload handling
3. Implement Server-Sent Events (SSE) streaming

---

## Issue 6: Frontend TODO Items
**Title**: Complete frontend TODO implementations
**Labels**: `enhancement`, `frontend`
**Priority**: Medium
**Description**:
Two TODO items in `dashboard.tsx`:
- Line 2740: `// TODO: Implement proper transaction updates based on operations`
- Line 2993: `// TODO: Implement delete rule API endpoint`

**Action Items**:
1. Implement transaction update logic based on mutate operations
2. Add delete rule functionality to preferences API
3. Update frontend to use delete endpoint

---

## Issue 7: Improve Test Coverage
**Title**: Add integration tests for REST API endpoints
**Labels**: `testing`, `enhancement`
**Priority**: Medium
**Description**:
Created `test_rest_api.py` script but needs to be integrated into test suite. Some backend QA tests have failures that need investigation:
- `test_preferences_qa.py`: 3 failures
- `test_mutate_categories_qa.py`: 3 errors
- `test_save_statement_summary_qa.py`: Multiple failures (onboarding-related)

**Action Items**:
1. Integrate REST API tests into pytest suite
2. Investigate and fix test failures
3. Add more comprehensive test coverage

---

## Issue 8: Replace Deprecated use-openai-global Module
**Title**: Remove dependency on deprecated use-openai-global.ts
**Labels**: `refactor`, `frontend`
**Priority**: Low
**Description**:
`web/src/lib/use-openai-global.ts` is marked as DEPRECATED but still used in `dashboard.tsx`. Need to replace with direct window access or proper state management.

**Action Items**:
1. Replace `useTheme()` and `useDisplayMode()` calls in dashboard.tsx
2. Use direct `window.theme` and `window.displayMode` access
3. Remove deprecated file after replacement

---

## Issue 9: Update Documentation
**Title**: Update README with new Makefile commands
**Labels**: `documentation`
**Priority**: Low
**Description**:
Created Makefile with `make restart` command. Should document in README.

**Action Items**:
1. Add Makefile section to main README
2. Document all available commands
3. Add usage examples

---

## Summary

**Total Issues**: 9
**High Priority**: 3 (Issues 2, 3, 4)
**Medium Priority**: 3 (Issues 5, 6, 7)
**Low Priority**: 3 (Issues 1, 8, 9)

**Already Fixed**: Issue 2 (build syntax error)
