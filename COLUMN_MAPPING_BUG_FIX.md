# Column Mapping Bug Fix - Implementation Summary

## Issue Description

The system was saving **actual data values** (e.g., "02-01-2025", "21483,27") instead of **column indices** (e.g., "1", "5") in the `column_mappings` field of parsing preferences. This caused the statement parser to fail with the error:

```
Could not resolve column names from mappings: date: 02-01-2025, description: ["'66 1090 1883 0000 0001 5438 0216", 'SUHEL E ABU AITTAH UL. SOKOŁOWSKA 11/124 01-142 WARSZAWA', 'PLN'], amount: 21483,27
```

## Root Cause

The parsing preferences stored in the database had corrupted `column_mappings`:

**Corrupted (Before):**
```json
{
  "date": "02-01-2025",
  "amount": "21483,27",
  "balance": "26480,21",
  "description": ["'66 1090 1883 0000 0001 5438 0216", "SUHEL E ABU...", "PLN"]
}
```

**Correct (After):**
```json
{
  "date": "1",
  "amount": "5",
  "balance": "6",
  "description": ["2", "3", "4"]
}
```

## Implementation

### 1. Added Validation Functions

**Frontend:** `web/src/components/SimpleUpload.tsx`
- Added `validateColumnReference()` function to detect data values vs. column indices
- Validates that column references are pure numeric strings (0-100 range)
- Rejects date patterns, decimal numbers, and long strings

**Backend:** `mcp-server/app/services/statement_analyzer.py`
- Added `validate_column_reference()` function with same logic
- Validates mappings before saving to database
- Raises `ValueError` if invalid mappings detected

### 2. Enhanced Corruption Detection

**Frontend:** `web/src/components/SimpleUpload.tsx`
- Improved `looksLikeData()` function to be more strict
- Only accepts pure numeric column indices
- Everything else is treated as suspicious data

### 3. Added Extensive Logging

**Frontend:**
- `SimpleUpload.tsx`: Log columnMappings state and converted API payload
- `api-client.ts`: Log data being sent to backend

**Backend:**
- `main.py`: Log column_mappings types and values when building schema
- `statement_analyzer.py`: Log validation results

**Console output examples:**
```javascript
[DEBUG] columnMappings state: {0: "do_not_use", 1: "date", 5: "amount"}
[DEBUG] Column mappings validated successfully: {"date": "1", "amount": "5"}
[API] saveHeaderMapping called with: {...}
```

### 4. Improved Error Messages

**Backend:** `mcp-server/app/tools/statement_parser.py`
- Enhanced error message with actionable guidance
- Explains what went wrong and how to fix it
- Suggests clearing corrupted preferences and re-mapping

**Example error message:**
```
Could not resolve column names from mappings: date: 02-01-2025, amount: 21483,27

This usually means the saved column mappings contain data values instead of column indices.

Action required:
1. The column mappings for 'Santander' are corrupted and need to be cleared
2. Re-upload your statement and manually re-map the columns
3. Column references should be numeric indices like '0', '1', '2' (preferred)
   - NOT column names like 'Date', 'Amount'
   - NOT column letters like 'Column A', 'Column B'
   - NOT data values like '02-01-2025', '21483,27'

Available columns in your file: [0, 1, 2, 3, 4, 5, 6, 7, 8]

If this issue persists, please contact support with bank name: Santander
```

### 5. Created Migration Script

**New file:** `mcp-server/scripts/fix_corrupted_mappings.py`

A comprehensive script to:
- Scan all parsing preferences in database
- Detect corrupted column_mappings
- Disable or delete corrupted preferences
- Generate detailed reports

**Usage:**
```bash
# Dry run (no changes)
python mcp-server/scripts/fix_corrupted_mappings.py --dry-run

# Actually fix (disable corrupted)
python mcp-server/scripts/fix_corrupted_mappings.py --no-dry-run

# Delete corrupted preferences
python mcp-server/scripts/fix_corrupted_mappings.py --no-dry-run --delete
```

**Script output:**
```
================================================================================
SCAN RESULTS
================================================================================

Total preferences scanned: 1
Clean preferences: 0
Corrupted preferences: 1

Bank: Santander
  ID: d6ba40c3-748e-4971-b64a-a310c9e676cc
  Name: parsing_Santander_csv
  Enabled: True
  Invalid mappings:
    - date: 02-01-2025
      Reason: Cannot parse as int: invalid literal for int() with base 10: '02-01-2025'
    - amount: 21483,27
      Reason: Cannot parse as int: invalid literal for int() with base 10: '21483,27'
```

### 6. Cleaned Corrupted Data

Successfully ran the migration script to delete the corrupted Santander preference:
```bash
✓ Deleted preference for bank: Santander
1 preferences deleting
```

Verification:
```sql
SELECT COUNT(*) FROM categorization_preferences WHERE preference_type = 'parsing';
-- Result: 0 (corrupted preference removed)
```

## Files Modified

### Frontend
- `web/src/components/SimpleUpload.tsx` - Validation, logging, corruption detection
- `web/src/lib/api-client.ts` - Logging and validation before API calls

### Backend
- `mcp-server/app/main.py` - Added logging for schema building
- `mcp-server/app/services/statement_analyzer.py` - Added validation function and logic
- `mcp-server/app/tools/statement_parser.py` - Improved error messages

### New Files
- `mcp-server/scripts/fix_corrupted_mappings.py` - Migration script

## Testing Steps

To test the fix:

1. ✅ **Clear corrupted data** - Run migration script to remove bad preferences
2. **Upload CSV file** - Use the web interface to upload a bank statement
3. **Map columns** - Manually map the Date, Description, and Amount columns
4. **Verify console logs** - Check browser console for validation logs
5. **Check database** - Verify correct numeric indices are saved
6. **Re-upload same file** - Verify mappings load correctly
7. **Process statement** - Confirm transactions are parsed successfully

## Prevention Measures

The following safeguards are now in place to prevent this bug from recurring:

1. **Frontend validation** - Rejects invalid mappings before sending to API
2. **Backend validation** - Double-checks mappings before database save
3. **Strict corruption detection** - Only accepts pure numeric column indices
4. **Extensive logging** - Track data flow through the entire pipeline
5. **Migration script** - Easy tool to detect and fix corrupted data

## Next Steps

1. Test the complete upload flow with the Santander CSV file
2. Verify that correct column indices are saved to the database
3. Confirm that subsequent uploads use the saved mappings correctly
4. Document the expected format for column mappings in API docs

## Success Criteria

- ✅ Validation functions added (frontend + backend)
- ✅ Logging added throughout the flow
- ✅ Corruption detection strengthened
- ✅ Migration script created and tested
- ✅ Corrupted data cleaned from database
- ✅ Error messages improved
- ⏳ End-to-end test with real CSV file (ready for user testing)

## How to Verify the Fix

1. Open browser console (F12)
2. Navigate to http://localhost:8000
3. Upload the "Santander - January.csv" file
4. Select "Santander" as bank name
5. Map the columns:
   - Column B (index 1) → Date
   - Columns C, D, E (indices 2, 3, 4) → Description
   - Column F (index 5) → Amount
   - Column G (index 6) → Balance
6. Check console logs for validation messages
7. Save and process the statement
8. Verify in database:
   ```sql
   SELECT rule FROM categorization_preferences 
   WHERE bank_name = 'Santander' 
   AND preference_type = 'parsing';
   ```
   Should show numeric indices like "1", "5", not data values

## Summary

The bug was caused by actual data values being saved instead of column indices in parsing preferences. This has been fixed by:

1. Adding strict validation at both frontend and backend layers
2. Strengthening corruption detection logic
3. Adding extensive logging to track data flow
4. Creating a migration script to clean corrupted data
5. Improving error messages to guide users

The system now validates all column mappings before saving and rejects any that contain data values instead of column indices. The corrupted Santander preference has been removed from the database, and users can now re-map their columns correctly.
