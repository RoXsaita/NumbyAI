"""
Typed Operation Schemas for mutate_categories

This module provides TypedDict definitions for the operation types
used by the mutate_categories tool, enabling better type safety
and documentation.
"""

from typing import Literal, Optional, TypedDict, Union, List


class EditOperation(TypedDict, total=False):
    """
    Edit operation - set a category's absolute total directly.
    
    Attributes:
        type: Must be 'edit'
        category: Category name to modify
        new_amount: New absolute amount (negative for expenses, positive for income)
        note: Optional description of the change
    """
    type: Literal['edit']
    category: str
    new_amount: float
    note: str


class TransferOperation(TypedDict, total=False):
    """
    Transfer operation - move amounts between categories (zero-sum).
    
    Sign handling is automatic:
    - If source is expense (negative): source +amount, dest -amount
    - If source is income (positive): source -amount, dest +amount
    
    Attributes:
        type: Must be 'transfer'
        from_category: Source category name
        to_category: Destination category name
        transfer_amount: Positive amount to move
        note: Optional description of the change
    """
    type: Literal['transfer']
    from_category: str
    to_category: str
    transfer_amount: float
    note: str


# Union type for any valid operation
Operation = Union[EditOperation, TransferOperation]

# List of operations
OperationList = List[Operation]


def validate_edit_operation(op: dict) -> tuple[bool, Optional[str]]:
    """
    Validate an edit operation dict.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if op.get('type') != 'edit':
        return False, "Edit operation must have type='edit'"
    
    if not op.get('category'):
        return False, "Edit operation requires 'category' field"
    
    if 'new_amount' not in op:
        return False, "Edit operation requires 'new_amount' field"
    
    if not isinstance(op.get('new_amount'), (int, float)):
        return False, "'new_amount' must be a number"
    
    return True, None


def validate_transfer_operation(op: dict) -> tuple[bool, Optional[str]]:
    """
    Validate a transfer operation dict.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if op.get('type') != 'transfer':
        return False, "Transfer operation must have type='transfer'"
    
    if not op.get('from_category'):
        return False, "Transfer operation requires 'from_category' field"
    
    if not op.get('to_category'):
        return False, "Transfer operation requires 'to_category' field"
    
    if op.get('from_category') == op.get('to_category'):
        return False, "Cannot transfer to the same category"
    
    if 'transfer_amount' not in op:
        return False, "Transfer operation requires 'transfer_amount' field"
    
    transfer_amount = op.get('transfer_amount')
    if not isinstance(transfer_amount, (int, float)):
        return False, "'transfer_amount' must be a number"
    
    if transfer_amount <= 0:
        return False, "'transfer_amount' must be positive"
    
    return True, None


def validate_operation(op: dict) -> tuple[bool, Optional[str]]:
    """
    Validate any operation dict.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    op_type = op.get('type')
    
    if op_type == 'edit':
        return validate_edit_operation(op)
    elif op_type == 'transfer':
        return validate_transfer_operation(op)
    else:
        return False, f"Unknown operation type: {op_type}. Supported: 'edit', 'transfer'"


def validate_operations(operations: list) -> tuple[bool, List[str]]:
    """
    Validate a list of operations.
    
    Returns:
        Tuple of (all_valid, list_of_error_messages)
    """
    errors = []
    
    for idx, op in enumerate(operations):
        is_valid, error = validate_operation(op)
        if not is_valid:
            errors.append(f"Operation {idx + 1}: {error}")
    
    return len(errors) == 0, errors

