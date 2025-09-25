from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
import uuid
from decimal import Decimal

from src.core.database import get_db
from src.apps.auth.dependencies import get_active_user
from src.apps.auth.models import User
from .models import BudgetCategory, Expense
from .schemas import (
    BudgetCategoryCreate, BudgetCategoryUpdate, BudgetCategoryResponse,
    BudgetCategoryWithExpenses, BudgetSummary
)

router = APIRouter(prefix="/budget/categories", tags=["Budget Categories"])

@router.post("/", response_model=BudgetCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_budget_category(
    category_data: BudgetCategoryCreate,
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Create a new budget category."""
    
    # Check if category name already exists for this user
    existing_category = db.query(BudgetCategory).filter(
        and_(
            BudgetCategory.user_id == current_user.id,
            BudgetCategory.name == category_data.name,
            BudgetCategory.is_active == True
        )
    ).first()
    
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Budget category '{category_data.name}' already exists"
        )
    
    # Create new category
    new_category = BudgetCategory(
        id=str(uuid.uuid4()),
        name=category_data.name,
        description=category_data.description,
        budget_amount=category_data.budget_amount,
        user_id=current_user.id,
        color=category_data.color,
        icon=category_data.icon,
        is_active=True
    )
    
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    # Calculate spent amount (should be 0 for new category)
    spent_amount = db.query(func.sum(Expense.amount)).filter(
        and_(
            Expense.category_id == new_category.id,
            Expense.user_id == current_user.id
        )
    ).scalar() or 0
    
    remaining_budget = new_category.budget_amount - spent_amount
    
    return BudgetCategoryResponse(
        id=new_category.id,
        name=new_category.name,
        description=new_category.description,
        budget_amount=new_category.budget_amount,
        spent_amount=spent_amount,
        remaining_budget=remaining_budget,
        user_id=new_category.user_id,
        color=new_category.color,
        icon=new_category.icon,
        is_active=new_category.is_active,
        created_at=new_category.created_at,
        updated_at=new_category.updated_at
    )

@router.get("/", response_model=List[BudgetCategoryResponse])
def get_budget_categories(
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db),
    include_inactive: bool = Query(False, description="Include inactive categories")
):
    """Get all budget categories for the current user."""
    
    # Build query filters
    filters = [BudgetCategory.user_id == current_user.id]
    if not include_inactive:
        filters.append(BudgetCategory.is_active == True)
    
    # Get categories
    categories = db.query(BudgetCategory).filter(and_(*filters)).all()
    
    category_responses = []
    for category in categories:
        # Calculate spent amount for each category
        spent_amount = db.query(func.sum(Expense.amount)).filter(
            and_(
                Expense.category_id == category.id,
                Expense.user_id == current_user.id
            )
        ).scalar() or 0
        
        remaining_budget = category.budget_amount - spent_amount
        
        category_responses.append(BudgetCategoryResponse(
            id=category.id,
            name=category.name,
            description=category.description,
            budget_amount=category.budget_amount,
            spent_amount=spent_amount,
            remaining_budget=remaining_budget,
            user_id=category.user_id,
            color=category.color,
            icon=category.icon,
            is_active=category.is_active,
            created_at=category.created_at,
            updated_at=category.updated_at
        ))
    
    return category_responses

@router.get("/{category_id}", response_model=BudgetCategoryWithExpenses)
def get_budget_category(
    category_id: str,
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, le=100, description="Maximum number of recent expenses to include")
):
    """Get a specific budget category with recent expenses."""
    
    # Get category
    category = db.query(BudgetCategory).filter(
        and_(
            BudgetCategory.id == category_id,
            BudgetCategory.user_id == current_user.id
        )
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget category not found"
        )
    
    # Get recent expenses for this category
    recent_expenses = db.query(Expense).filter(
        and_(
            Expense.category_id == category_id,
            Expense.user_id == current_user.id
        )
    ).order_by(Expense.expense_date.desc(), Expense.created_at.desc()).limit(limit).all()
    
    # Calculate totals
    spent_amount = db.query(func.sum(Expense.amount)).filter(
        and_(
            Expense.category_id == category_id,
            Expense.user_id == current_user.id
        )
    ).scalar() or 0
    
    remaining_budget = category.budget_amount - spent_amount
    
    return BudgetCategoryWithExpenses(
        id=category.id,
        name=category.name,
        description=category.description,
        budget_amount=category.budget_amount,
        spent_amount=spent_amount,
        remaining_budget=remaining_budget,
        user_id=category.user_id,
        color=category.color,
        icon=category.icon,
        is_active=category.is_active,
        created_at=category.created_at,
        updated_at=category.updated_at,
        recent_expenses=[
            {
                "id": expense.id,
                "amount": expense.amount,
                "description": expense.description,
                "expense_date": expense.expense_date,
                "created_at": expense.created_at
            }
            for expense in recent_expenses
        ]
    )

@router.put("/{category_id}", response_model=BudgetCategoryResponse)
def update_budget_category(
    category_id: str,
    category_update: BudgetCategoryUpdate,
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Update a budget category."""
    
    # Get category
    category = db.query(BudgetCategory).filter(
        and_(
            BudgetCategory.id == category_id,
            BudgetCategory.user_id == current_user.id
        )
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget category not found"
        )
    
    # Check for name conflicts if name is being changed
    if category_update.name and category_update.name != category.name:
        existing_category = db.query(BudgetCategory).filter(
            and_(
                BudgetCategory.user_id == current_user.id,
                BudgetCategory.name == category_update.name,
                BudgetCategory.is_active == True,
                BudgetCategory.id != category_id
            )
        ).first()
        
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Budget category '{category_update.name}' already exists"
            )
    
    # Update category fields
    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    
    # Calculate spent amount
    spent_amount = db.query(func.sum(Expense.amount)).filter(
        and_(
            Expense.category_id == category_id,
            Expense.user_id == current_user.id
        )
    ).scalar() or 0
    
    remaining_budget = category.budget_amount - spent_amount
    
    return BudgetCategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        budget_amount=category.budget_amount,
        spent_amount=spent_amount,
        remaining_budget=remaining_budget,
        user_id=category.user_id,
        color=category.color,
        icon=category.icon,
        is_active=category.is_active,
        created_at=category.created_at,
        updated_at=category.updated_at
    )

@router.delete("/{category_id}")
def delete_budget_category(
    category_id: str,
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db),
    force: bool = Query(False, description="Force delete even if there are associated expenses")
):
    """Delete a budget category (soft delete by default)."""
    
    # Get category
    category = db.query(BudgetCategory).filter(
        and_(
            BudgetCategory.id == category_id,
            BudgetCategory.user_id == current_user.id
        )
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget category not found"
        )
    
    # Check if category has associated expenses
    expense_count = db.query(func.count(Expense.id)).filter(
        and_(
            Expense.category_id == category_id,
            Expense.user_id == current_user.id
        )
    ).scalar()
    
    if expense_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete category with {expense_count} associated expenses. Use force=true to override."
        )
    
    if force:
        # Hard delete - remove all associated expenses first
        db.query(Expense).filter(
            and_(
                Expense.category_id == category_id,
                Expense.user_id == current_user.id
            )
        ).delete()
        
        # Delete the category
        db.delete(category)
    else:
        # Soft delete - mark as inactive
        category.is_active = False
    
    db.commit()
    
    action = "deleted" if force else "deactivated"
    return {"message": f"Budget category {action} successfully"}

@router.get("/summary/overview")
def get_budget_summary(
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Get overall budget summary for the current user."""
    
    # Get all active categories with their spending
    categories_with_spending = db.query(
        BudgetCategory.id,
        BudgetCategory.name,
        BudgetCategory.budget_amount,
        func.coalesce(func.sum(Expense.amount), 0).label('spent_amount')
    ).outerjoin(
        Expense, 
        and_(
            Expense.category_id == BudgetCategory.id,
            Expense.user_id == current_user.id
        )
    ).filter(
        and_(
            BudgetCategory.user_id == current_user.id,
            BudgetCategory.is_active == True
        )
    ).group_by(BudgetCategory.id).all()
    
    # Calculate totals
    total_budget = sum(cat.budget_amount for cat in categories_with_spending)
    total_spent = sum(cat.spent_amount for cat in categories_with_spending)
    total_remaining = total_budget - total_spent
    
    # Calculate budget utilization
    budget_utilization = (total_spent / total_budget * 100) if total_budget > 0 else 0
    
    # Prepare category summaries
    category_summaries = []
    for cat in categories_with_spending:
        remaining = cat.budget_amount - cat.spent_amount
        utilization = (cat.spent_amount / cat.budget_amount * 100) if cat.budget_amount > 0 else 0
        
        category_summaries.append({
            "id": cat.id,
            "name": cat.name,
            "budget_amount": float(cat.budget_amount),
            "spent_amount": float(cat.spent_amount),
            "remaining_budget": float(remaining),
            "utilization_percentage": float(utilization)
        })
    
    return BudgetSummary(
        total_budget=float(total_budget),
        total_spent=float(total_spent),
        total_remaining=float(total_remaining),
        budget_utilization=float(budget_utilization),
        category_count=len(categories_with_spending),
        categories=category_summaries
    )