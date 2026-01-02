#!/usr/bin/env python3
"""
Migration Script: Fix Corrupted Column Mappings

This script scans all parsing preferences in the database and identifies/fixes
those with corrupted column_mappings (containing data values instead of column indices).

Actions:
1. Scan all parsing preferences
2. Detect corrupted column_mappings
3. Disable corrupted preferences (so users can re-configure)
4. Log affected banks for user notification

Usage:
    python mcp-server/scripts/fix_corrupted_mappings.py [--dry-run] [--delete]
    
Options:
    --dry-run: Only report issues, don't modify database
    --delete: Delete corrupted preferences instead of disabling them
"""
import sys
import os
import re
import argparse
from pathlib import Path

# Add parent directory to path so we can import app modules
script_dir = Path(__file__).parent
mcp_server_dir = script_dir.parent
project_root = mcp_server_dir.parent

sys.path.insert(0, str(mcp_server_dir))

# Change to mcp-server directory so relative DB path works
os.chdir(str(mcp_server_dir))

from app.database import SessionLocal, CategorizationPreference
from app.logger import create_logger

logger = create_logger("fix_corrupted_mappings")


def validate_column_reference(column_ref) -> tuple[bool, str]:
    """
    Validate that a column reference is a valid numeric index, not data.
    
    Returns:
        (is_valid, reason) tuple
    """
    # Handle array (for description columns)
    if isinstance(column_ref, list):
        for i, ref in enumerate(column_ref):
            is_valid, reason = validate_column_reference(ref)
            if not is_valid:
                return False, f"Array item {i}: {reason}"
        return True, "OK"
    
    if not column_ref or not isinstance(column_ref, str):
        return False, f"Not a string: {type(column_ref).__name__}"
    
    # Must be numeric string like "0", "1", "2"
    try:
        idx = int(column_ref)
        if idx < 0 or idx > 100:
            return False, f"Index out of range: {idx}"
        # Must be EXACTLY the string representation of the number (no extra chars)
        if column_ref != str(idx):
            return False, f"Not pure numeric: '{column_ref}'"
    except (ValueError, TypeError) as e:
        return False, f"Cannot parse as int: {e}"
    
    # Additional checks: reject if it looks like data
    # Date pattern
    if re.match(r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$', column_ref):
        return False, "Looks like date pattern"
    # Number with decimal
    if re.match(r'^\d+[.,]\d+$', column_ref):
        return False, "Looks like decimal number"
    # Too long for a column index
    if len(column_ref) > 3:
        return False, f"Too long for index: {len(column_ref)} chars"
    
    return True, "OK"


def scan_parsing_preferences(dry_run: bool = True, delete_mode: bool = False):
    """
    Scan all parsing preferences and fix corrupted ones.
    
    Args:
        dry_run: If True, only report issues without modifying database
        delete_mode: If True, delete corrupted preferences instead of disabling
    """
    db = SessionLocal()
    try:
        # Get all parsing preferences
        all_prefs = db.query(CategorizationPreference).filter(
            CategorizationPreference.preference_type == "parsing"
        ).all()
        
        logger.info(f"Found {len(all_prefs)} parsing preferences to scan")
        
        corrupted = []
        clean = []
        
        for pref in all_prefs:
            bank_name = pref.bank_name or "Unknown"
            rule = pref.rule or {}
            column_mappings = rule.get('column_mappings', {})
            
            if not column_mappings:
                logger.info(f"Skipping {bank_name} - no column_mappings")
                continue
            
            # Check each mapping
            invalid_mappings = []
            for field_type, column_ref in column_mappings.items():
                is_valid, reason = validate_column_reference(column_ref)
                if not is_valid:
                    invalid_mappings.append({
                        'field_type': field_type,
                        'column_ref': column_ref,
                        'reason': reason
                    })
            
            if invalid_mappings:
                corrupted.append({
                    'id': pref.id,
                    'bank_name': bank_name,
                    'name': pref.name,
                    'enabled': pref.enabled,
                    'invalid_mappings': invalid_mappings,
                    'full_mappings': column_mappings
                })
            else:
                clean.append({
                    'bank_name': bank_name,
                    'name': pref.name
                })
        
        # Report findings
        print("\n" + "="*80)
        print("SCAN RESULTS")
        print("="*80)
        print(f"\nTotal preferences scanned: {len(all_prefs)}")
        print(f"Clean preferences: {len(clean)}")
        print(f"Corrupted preferences: {len(corrupted)}")
        
        if corrupted:
            print("\n" + "-"*80)
            print("CORRUPTED PREFERENCES FOUND:")
            print("-"*80)
            for item in corrupted:
                print(f"\nBank: {item['bank_name']}")
                print(f"  ID: {item['id']}")
                print(f"  Name: {item['name']}")
                print(f"  Enabled: {item['enabled']}")
                print(f"  Invalid mappings:")
                for invalid in item['invalid_mappings']:
                    print(f"    - {invalid['field_type']}: {invalid['column_ref']}")
                    print(f"      Reason: {invalid['reason']}")
                print(f"  Full column_mappings: {item['full_mappings']}")
        
        # Take action if not dry run
        if not dry_run and corrupted:
            print("\n" + "-"*80)
            action = "DELETING" if delete_mode else "DISABLING"
            print(f"{action} CORRUPTED PREFERENCES")
            print("-"*80)
            
            for item in corrupted:
                pref_id = item['id']
                bank_name = item['bank_name']
                
                if delete_mode:
                    # Delete the preference
                    db.query(CategorizationPreference).filter(
                        CategorizationPreference.id == pref_id
                    ).delete()
                    print(f"✓ Deleted preference for bank: {bank_name}")
                else:
                    # Disable the preference
                    pref = db.query(CategorizationPreference).filter(
                        CategorizationPreference.id == pref_id
                    ).first()
                    if pref:
                        pref.enabled = False
                        print(f"✓ Disabled preference for bank: {bank_name}")
            
            db.commit()
            print(f"\n{len(corrupted)} preferences {action.lower()}")
        
        elif dry_run and corrupted:
            print("\n" + "-"*80)
            print("DRY RUN MODE - No changes made")
            print("-"*80)
            print(f"\nTo fix these issues, run:")
            print(f"  python {__file__} --no-dry-run")
            print(f"Or to delete them:")
            print(f"  python {__file__} --no-dry-run --delete")
        
        print("\n" + "="*80)
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Scan and fix corrupted column mappings in parsing preferences"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Only report issues, do not modify database (default)'
    )
    parser.add_argument(
        '--no-dry-run',
        dest='dry_run',
        action='store_false',
        help='Actually modify the database'
    )
    parser.add_argument(
        '--delete',
        action='store_true',
        default=False,
        help='Delete corrupted preferences instead of disabling them'
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("CORRUPTED COLUMN MAPPINGS FIXER")
    print("="*80)
    print(f"Mode: {'DRY RUN (no changes)' if args.dry_run else 'LIVE (will modify database)'}")
    print(f"Action: {'DELETE' if args.delete else 'DISABLE'} corrupted preferences")
    print("="*80 + "\n")
    
    if not args.dry_run:
        response = input("Are you sure you want to modify the database? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return
    
    scan_parsing_preferences(dry_run=args.dry_run, delete_mode=args.delete)


if __name__ == "__main__":
    main()
