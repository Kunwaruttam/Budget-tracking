from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Optional
from datetime import datetime, date
import uuid

from src.core.database import get_db
from src.apps.auth.dependencies import get_active_user
from src.apps.auth.models import User
from .models import BudgetCategory, Expense
from .schemas import (
    ExpenseCreate, ExpenseUpdate, ExpenseResponse
)

router = APIRouter(prefix="/budget/expenses", tags=["Expenses"])

@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense_data: ExpenseCreate,
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Create a new expense."""
    
    # Verify category exists and belongs to the user
    category = db.query(BudgetCategory).filter(
        and_(
            BudgetCategory.id == expense_data.category_id,
            BudgetCategory.user_id == current_user.id
        )
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget category not found"
        )
    
    # Create new expense
    new_expense = Expense(
        id=str(uuid.uuid4()),
        amount=expense_data.amount,
        description=expense_data.description,
        category_id=expense_data.category_id,
        user_id=current_user.id,
        expense_date=expense_data.expense_date or datetime.utcnow().date()
    )
    
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    
    # Calculate remaining budget for the category
    total_spent = db.query(func.sum(Expense.amount)).filter(
        and_(
            Expense.category_id == category.id,
            Expense.user_id == current_user.id
        )
    ).scalar() or 0
    
    remaining_budget = category.budget_amount - total_spent
    
    return ExpenseResponse(
        id=new_expense.id,
        amount=new_expense.amount,
        description=new_expense.description,
        category_id=new_expense.category_id,
        category_name=category.name,
        user_id=new_expense.user_id,
        expense_date=new_expense.expense_date,
        created_at=new_expense.created_at,
        updated_at=new_expense.updated_at,
        remaining_budget=remaining_budget
    )

@router.get("/", response_model=List[ExpenseResponse])
def get_expenses(
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db),
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    start_date: Optional[date] = Query(None, description="Filter expenses from this date"),
    end_date: Optional[date] = Query(None, description="Filter expenses until this date"),
    limit: int = Query(100, le=1000, description="Maximum number of expenses to return"),
    offset: int = Query(0, ge=0, description="Number of expenses to skip")
):
    """Get user's expenses with optional filtering."""
    
    # Build query filters
    filters = [Expense.user_id == current_user.id]
    
    if category_id:
        filters.append(Expense.category_id == category_id)
    if start_date:
        filters.append(Expense.expense_date >= start_date)
    if end_date:
        filters.append(Expense.expense_date <= end_date)
    
    # Get expenses with category information
    expenses = db.query(Expense)\
        .join(BudgetCategory, Expense.category_id == BudgetCategory.id)\
        .filter(and_(*filters))\
        .order_by(desc(Expense.expense_date), desc(Expense.created_at))\
        .offset(offset)\
        .limit(limit)\
        .all()
    
    # Calculate remaining budget for each category
    expense_responses = []
    category_budgets = {}
    
    for expense in expenses:
        category = expense.category
        
        # Cache budget calculations per category
        if category.id not in category_budgets:
            total_spent = db.query(func.sum(Expense.amount)).filter(
                and_(
                    Expense.category_id == category.id,
                    Expense.user_id == current_user.id
                )
            ).scalar() or 0
            category_budgets[category.id] = category.budget_amount - total_spent
        
        expense_responses.append(ExpenseResponse(
            id=expense.id,
            amount=expense.amount,
            description=expense.description,
            category_id=expense.category_id,
            category_name=category.name,
            user_id=expense.user_id,
            expense_date=expense.expense_date,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
            remaining_budget=category_budgets[category.id]
        ))
    
    return expense_responses

@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: str,
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific expense by ID."""
    
    expense = db.query(Expense)\
        .join(BudgetCategory, Expense.category_id == BudgetCategory.id)\
        .filter(
            and_(
                Expense.id == expense_id,
                Expense.user_id == current_user.id
            )
        ).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    # Calculate remaining budget
    total_spent = db.query(func.sum(Expense.amount)).filter(
        and_(
            Expense.category_id == expense.category_id,
            Expense.user_id == current_user.id
        )
    ).scalar() or 0
    
    remaining_budget = expense.category.budget_amount - total_spent
    
    return ExpenseResponse(
        id=expense.id,
        amount=expense.amount,
        description=expense.description,
        category_id=expense.category_id,
        category_name=expense.category.name,
        user_id=expense.user_id,
        expense_date=expense.expense_date,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
        remaining_budget=remaining_budget
    )

@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: str,
    expense_update: ExpenseUpdate,
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Update an expense."""
    
    # Get expense
    expense = db.query(Expense).filter(
        and_(
            Expense.id == expense_id,
            Expense.user_id == current_user.id
        )
    ).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    # If category is being changed, verify new category belongs to user
    if expense_update.category_id and expense_update.category_id != expense.category_id:
        category = db.query(BudgetCategory).filter(
            and_(
                BudgetCategory.id == expense_update.category_id,
                BudgetCategory.user_id == current_user.id
            )
        ).first()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New budget category not found"
            )
    
    # Update expense fields
    update_data = expense_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expense, field, value)
    
    expense.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(expense)
    
    # Get category for response
    category = db.query(BudgetCategory).filter(BudgetCategory.id == expense.category_id).first()
    
    # Calculate remaining budget
    total_spent = db.query(func.sum(Expense.amount)).filter(
        and_(
            Expense.category_id == expense.category_id,
            Expense.user_id == current_user.id
        )
    ).scalar() or 0
    
    remaining_budget = category.budget_amount - total_spent
    
    return ExpenseResponse(
        id=expense.id,
        amount=expense.amount,
        description=expense.description,
        category_id=expense.category_id,
        category_name=category.name,
        user_id=expense.user_id,
        expense_date=expense.expense_date,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
        remaining_budget=remaining_budget
    )

@router.delete("/{expense_id}")
def delete_expense(
    expense_id: str,
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Delete an expense."""
    
    expense = db.query(Expense).filter(
        and_(
            Expense.id == expense_id,
            Expense.user_id == current_user.id
        )
    ).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    db.delete(expense)
    db.commit()
    
    return {"message": "Expense deleted successfully"}