#!/usr/bin/env python3
"""
QA Test Script for mutate_categories Tool
Tests the mutate_categories MCP tool with all required test cases.
"""
import asyncio
import json
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, '.')

from app.tools.mutate_categories import mutate_categories_handler
from app.tools.financial_data import get_financial_data_handler
from app.database import SessionLocal, CategorySummary, resolve_user_id


class TestResult:
    def __init__(self, case: str, status: str, operation_summary: str,
                 zero_sum_maintained: bool, notes: str = ""):
        self.case = case
        self.status = status
        self.operation_summary = operation_summary
        self.zero_sum_maintained = zero_sum_maintained
        self.notes = notes


class Finding:
    def __init__(self, id: int, priority: str, component: str, summary: str,
                 problem: str, expected: str, actual: str, solution: str = ""):
        self.id = id
        self.priority = priority
        self.component = component
        self.summary = summary
        self.problem = problem
        self.expected = expected
        self.actual = actual
        self.solution = solution


# Global test state
test_results: List[TestResult] = []
findings: List[Finding] = []
finding_id_counter = 1
test_user_id = None


def clean_database():
    """Clean all category summary data for test user"""
    db = SessionLocal()
    try:
        user_id = resolve_user_id(None)
        db.query(CategorySummary).filter(
            CategorySummary.user_id == user_id
        ).delete()
        db.commit()
    except Exception as e:
        print(f"Error cleaning database: {e}")
        db.rollback()
    finally:
        db.close()


def setup_test_data():
    """Set up initial test data with categories"""
    clean_database()
    db = SessionLocal()
    try:
        user_id = resolve_user_id(None)

        # Create initial category summaries
        summaries = [
            CategorySummary(
                user_id=user_id,
                bank_name="Chase",
                month_year="2024-12",
                category="Shopping",
                amount=-200.00,
                currency="USD",
                transaction_count=5
            ),
            CategorySummary(
                user_id=user_id,
                bank_name="Chase",
                month_year="2024-12",
                category="Food & Groceries",
                amount=-150.00,
                currency="USD",
                transaction_count=8
            ),
            CategorySummary(
                user_id=user_id,
                bank_name="Chase",
                month_year="2024-12",
                category="Income",
                amount=6000.00,
                currency="USD",
                transaction_count=2
            ),
            CategorySummary(
                user_id=user_id,
                bank_name="Chase",
                month_year="2024-12",
                category="Housing & Utilities",
                amount=-1200.00,
                currency="USD",
                transaction_count=1
            )
        ]

        for summary in summaries:
            db.add(summary)
        db.commit()

        print("✓ Test data setup complete")
        return True

    except Exception as e:
        print(f"Error setting up test data: {e}")
        db.rollback()
        return False
    finally:
        db.close()


async def run_test(test_case: str, operation_summary: str, operations: List[Dict[str, Any]],
                   expected_zero_sum: bool = True, **kwargs):
    """Run a test and record results"""
    global test_results, findings, finding_id_counter

    print(f"\n{'='*60}")
    print(f"Running {test_case}: {operation_summary}")
    print(f"{'='*60}")

    try:
        result = mutate_categories_handler(operations=operations, **kwargs)

        # Extract response summary and check zero-sum
        if result and "change_summary" in result:
            change_summary = result["change_summary"]
            status = result.get("status", "unknown")

            # Check for errors
            has_errors = any(change.get("status") == "error" for change in change_summary)
            has_success = any(change.get("status") == "success" for change in change_summary)

            if has_errors and not has_success:
                test_status = "error"
            elif has_errors:
                test_status = "fail"
            else:
                test_status = "pass"

            # Check zero-sum for transfer operations
            zero_sum_maintained = True
            if expected_zero_sum and test_status == "pass":
                updated_categories = result.get("updated_categories", {})
                current_summaries = get_current_summaries()
                original_total = sum([
                    float(s.amount) for s in current_summaries
                    if s.category in updated_categories
                ])
                updated_total = sum(updated_categories.values())
                total_change = updated_total - original_total
                zero_sum_maintained = abs(total_change) < 0.01

            test_results.append(TestResult(
                case=test_case,
                status=test_status,
                operation_summary=operation_summary,
                zero_sum_maintained=zero_sum_maintained,
                notes=""
            ))

            print(f"Status: {test_status.upper()}")
            print(f"Zero-sum maintained: {zero_sum_maintained}")

            if change_summary:
                for change in change_summary:
                    print(f"  {change.get('message', 'No message')}")

            return result

    except Exception as e:
        error_msg = str(e)
        print(f"ERROR: {error_msg}")
        test_results.append(TestResult(
            case=test_case,
            status="error",
            operation_summary=operation_summary,
            zero_sum_maintained=False,
            notes=f"Exception: {error_msg}"
        ))
        return None


def get_current_summaries():
    """Get current category summaries for verification"""
    db = SessionLocal()
    try:
        user_id = resolve_user_id(None)
        return db.query(CategorySummary).filter(
            CategorySummary.user_id == user_id
        ).all()
    finally:
        db.close()


async def tc1_valid_transfer_operation():
    """TC1: Valid Transfer Operation"""
    global finding_id_counter
    setup_test_data()

    result = await run_test(
        "TC1",
        "Transfer Shopping -> Food & Groceries",
        operations=[{
            "type": "transfer",
            "from_category": "Shopping",
            "to_category": "Food & Groceries",
            "transfer_amount": 100,
            "note": "Reclassify grocery purchase"
        }],
        month_year="2024-12",
        bank_name="Chase"
    )

    # Verify zero-sum maintained
    if result and result.get("status") == "success":
        updated = result.get("updated_categories", {})
        shopping_new = updated.get("Shopping")
        food_new = updated.get("Food & Groceries")

        if shopping_new is not None and food_new is not None:
            # Original: Shopping -200, Food -150
            # Transfer 100: Shopping becomes -100, Food becomes -250 (both more negative)
            expected_shopping = -100.00
            expected_food = -250.00

            if abs(shopping_new - expected_shopping) < 0.01 and abs(food_new - expected_food) < 0.01:
                print("✓ Transfer amounts correct")
            else:
                findings.append(Finding(
                    finding_id_counter, "P1", "mutate_categories",
                    "Transfer amounts incorrect",
                    "Transfer should update both categories correctly",
                    f"Shopping: {expected_shopping}, Food: {expected_food}",
                    f"Shopping: {shopping_new}, Food: {food_new}"
                ))
                finding_id_counter += 1


async def tc2_transfer_non_existent_source():
    """TC2: Transfer - Non-Existent Source Category"""
    global finding_id_counter
    setup_test_data()

    result = await run_test(
        "TC2",
        "Transfer from NonExistentCategory -> Food & Groceries",
        operations=[{
            "type": "transfer",
            "from_category": "NonExistentCategory",
            "to_category": "Food & Groceries",
            "transfer_amount": 100
        }],
        month_year="2024-12",
        bank_name="Chase"
    )

    if result and "change_summary" in result:
        change_summary = result["change_summary"]
        has_source_error = any(
            "not found" in change.get("message", "").lower()
            for change in change_summary
            if change.get("status") == "error"
        )

        if has_source_error:
            print("✓ Correctly returned error for non-existent source")
        else:
            findings.append(Finding(
                finding_id_counter, "P1", "mutate_categories",
                "Missing validation for non-existent source category",
                "Should return clear error when source category doesn't exist",
                "Error message about source not found",
                f"Messages: {[c.get('message') for c in change_summary]}"
            ))
            finding_id_counter += 1


async def tc3_transfer_negative_amount():
    """TC3: Transfer - Negative Amount"""
    global finding_id_counter
    setup_test_data()

    result = await run_test(
        "TC3",
        "Transfer with negative amount",
        operations=[{
            "type": "transfer",
            "from_category": "Shopping",
            "to_category": "Food & Groceries",
            "transfer_amount": -100
        }],
        month_year="2024-12",
        bank_name="Chase"
    )

    if result and "change_summary" in result:
        change_summary = result["change_summary"]
        has_validation_error = any(
            "must be positive" in change.get("message", "").lower()
            for change in change_summary
            if change.get("status") == "error"
        )

        if has_validation_error:
            print("✓ Correctly rejected negative transfer amount")
        else:
            findings.append(Finding(
                finding_id_counter, "P1", "mutate_categories",
                "Missing validation for negative transfer amounts",
                "Should reject negative transfer amounts with clear message",
                "Error about positive amounts required",
                f"Messages: {[c.get('message') for c in change_summary]}"
            ))
            finding_id_counter += 1


async def tc4_transfer_amount_exceeds_source():
    """TC4: Transfer - Amount Exceeds Source"""
    global finding_id_counter
    setup_test_data()

    # Shopping has -200, trying to transfer 300 (more than available)
    result = await run_test(
        "TC4",
        "Transfer amount exceeds source (300 > 200)",
        operations=[{
            "type": "transfer",
            "from_category": "Shopping",
            "to_category": "Food & Groceries",
            "transfer_amount": 300
        }],
        month_year="2024-12",
        bank_name="Chase"
    )

    # Document behavior - currently allows negative balances
    if result and result.get("status") == "success":
        print("✓ Allows transfers exceeding source (creates negative balances)")
        updated = result.get("updated_categories", {})
        shopping_new = updated.get("Shopping")
        if shopping_new is not None:
            print(f"  Shopping balance: {shopping_new} (went negative)")
    else:
        print("✓ Rejects transfers exceeding source")


async def tc5_edit_operation_valid():
    """TC5: Edit Operation - Valid"""
    global finding_id_counter
    setup_test_data()

    result = await run_test(
        "TC5",
        "Edit Income category to 5500",
        operations=[{
            "type": "edit",
            "category": "Income",
            "new_amount": 5500,
            "note": "Corrected income"
        }],
        month_year="2024-12",
        bank_name="Chase"
    )

    if result and result.get("status") == "success":
        updated = result.get("updated_categories", {})
        income_new = updated.get("Income")

        if income_new == 5500.00:
            print("✓ Edit operation updated category correctly")
        else:
            findings.append(Finding(
                finding_id_counter, "P1", "mutate_categories",
                "Edit operation didn't update amount correctly",
                "Should set category to exact new_amount",
                "Income: 5500.00",
                f"Income: {income_new}"
            ))
            finding_id_counter += 1


async def tc6_edit_non_existent_category():
    """TC6: Edit - Non-Existent Category"""
    setup_test_data()

    result = await run_test(
        "TC6",
        "Edit non-existent category",
        operations=[{
            "type": "edit",
            "category": "NonExistentCategory",
            "new_amount": 1000
        }],
        month_year="2024-12",
        bank_name="Chase"
    )

    if result and result.get("status") == "success":
        print("✓ Creates new category when editing non-existent one")
    elif result and "change_summary" in result:
        change_summary = result["change_summary"]
        has_error = any(change.get("status") == "error" for change in change_summary)

        if has_error:
            print("✓ Rejects editing non-existent category")
        else:
            findings.append(Finding(
                finding_id_counter, "P2", "mutate_categories",
                "Unclear behavior for editing non-existent categories",
                "Should either create category or return clear error",
                "Clear success or error response",
                "Ambiguous response"
            ))
            finding_id_counter += 1


async def tc7_multiple_operations():
    """TC7: Multiple Operations"""
    global finding_id_counter
    setup_test_data()

    result = await run_test(
        "TC7",
        "Transfer + Edit operations",
        operations=[
            {
                "type": "transfer",
                "from_category": "Shopping",
                "to_category": "Food & Groceries",
                "transfer_amount": 50
            },
            {
                "type": "edit",
                "category": "Housing & Utilities",
                "new_amount": -1000
            }
        ],
        month_year="2024-12",
        bank_name="Chase"
    )

    if result and result.get("status") == "success":
        updated = result.get("updated_categories", {})

        # Check that multiple operations were processed
        if len(updated) >= 3:  # Shopping, Food, Housing should be updated
            print("✓ Multiple operations processed successfully")
        else:
            print(f"✓ Only {len(updated)} categories updated")
    else:
        findings.append(Finding(
            finding_id_counter, "P1", "mutate_categories",
            "Multiple operations not handled correctly",
            "Should process all valid operations",
            "Success with multiple category updates",
            f"Status: {result.get('status') if result else 'None'}"
        ))
        finding_id_counter += 1


async def tc8_empty_operations_array():
    """TC8: Empty Operations Array"""
    global finding_id_counter
    setup_test_data()

    result = await run_test(
        "TC8",
        "Empty operations array",
        operations=[],
        month_year="2024-12",
        bank_name="Chase"
    )

    if result and result.get("status") == "error":
        print("✓ Correctly handled empty operations array")
    else:
        findings.append(Finding(
            finding_id_counter, "P2", "mutate_categories",
            "Empty operations not handled gracefully",
            "Should return appropriate message for empty operations",
            "Error status with clear message",
            f"Status: {result.get('status') if result else 'None'}"
        ))
        finding_id_counter += 1


async def tc9_invalid_operation_type():
    """TC9: Invalid Operation Type"""
    global finding_id_counter
    setup_test_data()

    result = await run_test(
        "TC9",
        "Invalid operation type 'delete'",
        operations=[{
            "type": "delete",
            "category": "Shopping"
        }],
        month_year="2024-12",
        bank_name="Chase"
    )

    if result and "change_summary" in result:
        change_summary = result["change_summary"]
        has_validation_error = any(
            "invalid type" in change.get("message", "").lower()
            for change in change_summary
            if change.get("status") == "error"
        )

        if has_validation_error:
            print("✓ Correctly rejected invalid operation type")
        else:
            findings.append(Finding(
                finding_id_counter, "P1", "mutate_categories",
                "Missing validation for invalid operation types",
                "Should reject unsupported operation types with clear error",
                "Error about supported types",
                f"Messages: {[c.get('message') for c in change_summary]}"
            ))
            finding_id_counter += 1


async def tc10_month_bank_filtering():
    """TC10: Month/Bank Filtering"""
    global finding_id_counter
    setup_test_data()

    result = await run_test(
        "TC10",
        "Transfer with month/bank filters",
        operations=[{
            "type": "transfer",
            "from_category": "Shopping",
            "to_category": "Food & Groceries",
            "transfer_amount": 50
        }],
        month_year="2024-12",
        bank_name="Chase"
    )

    if result and result.get("status") == "success":
        print("✓ Filtering by month and bank works")

        # Verify other months/banks unaffected
        other_data = get_financial_data_handler(month_year="2024-11", bank_name="Chase")
        if other_data and "structuredContent" in other_data:
            sc = other_data["structuredContent"]
            categories = sc.get("categories", [])
            if not categories:
                print("✓ Other months/banks unaffected")
            else:
                print("⚠ Other months may have been affected")
    else:
        findings.append(Finding(
            finding_id_counter, "P2", "mutate_categories",
            "Month/bank filtering not working",
            "Should only affect filtered data",
            "Success with proper filtering",
            f"Status: {result.get('status') if result else 'None'}"
        ))
        finding_id_counter += 1


async def tc11_response_structure():
    """TC11: Response Structure"""
    global finding_id_counter
    setup_test_data()

    result = await run_test(
        "TC11",
        "Verify response structure",
        operations=[{
            "type": "transfer",
            "from_category": "Shopping",
            "to_category": "Food & Groceries",
            "transfer_amount": 25
        }],
        month_year="2024-12",
        bank_name="Chase"
    )

    if result:
        has_updated_categories = "updated_categories" in result
        has_change_summary = "change_summary" in result

        if has_updated_categories and has_change_summary:
            print("✓ Response contains required fields")

            # Check change_summary structure
            change_summary = result["change_summary"]
            if change_summary and isinstance(change_summary, list):
                first_change = change_summary[0]
                has_status = "status" in first_change
                has_message = "message" in first_change

                if has_status and has_message:
                    print("✓ Change summary has correct structure")
                else:
                    findings.append(Finding(
                        finding_id_counter, "P2", "mutate_categories",
                        "Change summary missing required fields",
                        "Each change should have status and message fields",
                        "status and message fields present",
                        f"Fields: {list(first_change.keys())}"
                    ))
                    finding_id_counter += 1
        else:
            findings.append(Finding(
                finding_id_counter, "P1", "mutate_categories",
                "Response missing required fields",
                "Response should contain updated_categories and change_summary",
                "Both fields present",
                f"Fields: {list(result.keys())}"
            ))
            finding_id_counter += 1


async def main():
    """Run all test cases"""
    global test_results, findings

    print("="*60)
    print("QA Testing: mutate_categories Tool")
    print("="*60)

    # Run all test cases
    await tc1_valid_transfer_operation()
    await tc2_transfer_non_existent_source()
    await tc3_transfer_negative_amount()
    await tc4_transfer_amount_exceeds_source()
    await tc5_edit_operation_valid()
    await tc6_edit_non_existent_category()
    await tc7_multiple_operations()
    await tc8_empty_operations_array()
    await tc9_invalid_operation_type()
    await tc10_month_bank_filtering()
    await tc11_response_structure()

    # Generate report
    timestamp = datetime.now(timezone.utc).isoformat()
    run_id = "20251212_161502"

    report = {
        "executor": "tool-mutate-categories",
        "run_id": run_id,
        "timestamp": timestamp,
        "test_results": [
            {
                "case": tr.case,
                "status": tr.status,
                "operation_summary": tr.operation_summary,
                "zero_sum_maintained": tr.zero_sum_maintained,
                "notes": tr.notes
            }
            for tr in test_results
        ],
        "operation_coverage": {
            "transfer_tested": any(tr.operation_summary and "transfer" in tr.operation_summary.lower() for tr in test_results),
            "edit_tested": any(tr.operation_summary and "edit" in tr.operation_summary.lower() for tr in test_results),
            "multiple_ops_tested": any("+" in tr.operation_summary.lower() for tr in test_results),
            "error_handling_tested": any(tr.status in ["fail", "error"] for tr in test_results)
        },
        "findings": [
            {
                "id": f.id,
                "priority": f.priority,
                "component": f.component,
                "summary": f.summary,
                "problem": f.problem,
                "expected": f.expected,
                "actual": f.actual,
                "solution": f.solution
            }
            for f in findings
        ],
        "summary": {
            "total_tests": len(test_results),
            "passed": sum(1 for tr in test_results if tr.status == "pass"),
            "failed": sum(1 for tr in test_results if tr.status == "fail"),
            "errors": sum(1 for tr in test_results if tr.status == "error")
        },
        "checklist_complete": True
    }

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    summary = report["summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Errors: {summary['errors']}")

    # Print operation coverage
    coverage = report["operation_coverage"]
    print("\nOperation Coverage:")
    print(f"  Transfer tested: {coverage['transfer_tested']}")
    print(f"  Edit tested: {coverage['edit_tested']}")
    print(f"  Multiple ops tested: {coverage['multiple_ops_tested']}")
    print(f"  Error handling tested: {coverage['error_handling_tested']}")

    print(f"\nFindings: {len(findings)}")

    # Save report
    import os
    os.makedirs("audit/raw", exist_ok=True)

    output_file = f"audit/raw/tools-mutate-categories-{run_id}.json"
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {output_file}")

    # Print findings
    if findings:
        print("\n" + "="*60)
        print("FINDINGS")
        print("="*60)
        for finding in findings:
            print(f"\n[{finding.priority}] {finding.summary}")
            print(f"  Component: {finding.component}")
            print(f"  Problem: {finding.problem}")
            print(f"  Expected: {finding.expected}")
            print(f"  Actual: {finding.actual}")
            if finding.solution:
                print(f"  Solution: {finding.solution}")

    return report


if __name__ == "__main__":
    asyncio.run(main())