from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract, between
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel
import io
import csv
import json

from src.core.database import get_db
from src.apps.auth.dependencies import get_active_user
from src.apps.auth.models import User
from .models import BudgetCategory, Expense

router = APIRouter(prefix="/reports", tags=["Reports"])

# Enums
class PeriodType(str, Enum):
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"

class ExportFormat(str, Enum):
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "excel"

class AlertType(str, Enum):
    WARNING = "warning"
    DANGER = "danger"
    INFO = "info"

# Response Models
class StandardResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

class FinancialSummaryData(BaseModel):
    total_spent: float
    average_monthly: float
    budget_utilization: float
    savings_rate: float
    period_start: str
    period_end: str

class TrendData(BaseModel):
    period: str
    amount: float
    budget: float
    utilization: float

class CategoryBreakdownData(BaseModel):
    category_name: str
    spent: float
    budget: float
    percentage: float
    utilization: float

class RecentExpenseData(BaseModel):
    id: str
    amount: float
    description: str
    category_name: str
    expense_date: str
    days_ago: int

class InsightData(BaseModel):
    type: AlertType
    title: str
    message: str
    amount: Optional[float] = None
    category: Optional[str] = None

# Helper functions
def get_period_dates(period: PeriodType, start_date: Optional[date] = None, end_date: Optional[date] = None):
    """Get start and end dates for a period."""
    today = date.today()
    
    if period == PeriodType.CUSTOM and start_date and end_date:
        return start_date, end_date
    elif period == PeriodType.WEEK:
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif period == PeriodType.MONTH:
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    elif period == PeriodType.QUARTER:
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=quarter_month, day=1)
        if quarter_month + 2 <= 12:
            end = today.replace(month=quarter_month + 3, day=1) - timedelta(days=1)
        else:
            end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    elif period == PeriodType.YEAR:
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)
    else:
        # Default to current month
        start = today.replace(day=1)
        end = today
    
    return start, end

@router.get("/summary/")
def get_financial_summary(
    period: PeriodType = Query(PeriodType.MONTH),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Get financial summary for the specified period."""
    
    period_start, period_end = get_period_dates(period, start_date, end_date)
    
    # Get total spent in period
    total_spent = db.query(func.sum(Expense.amount)).filter(
        and_(
            Expense.user_id == current_user.id,
            Expense.expense_date >= period_start,
            Expense.expense_date <= period_end
        )
    ).scalar() or 0
    
    # Get total budget for active categories
    total_budget = db.query(func.sum(BudgetCategory.budget_amount)).filter(
        and_(
            BudgetCategory.user_id == current_user.id,
            BudgetCategory.is_active == True
        )
    ).scalar() or 0
    
    # Calculate metrics
    budget_utilization = (total_spent / total_budget * 100) if total_budget > 0 else 0
    savings_rate = ((total_budget - total_spent) / total_budget * 100) if total_budget > 0 else 0
    
    # Calculate average monthly (estimate based on period)
    days_in_period = (period_end - period_start).days + 1
    average_monthly = (total_spent / days_in_period * 30) if days_in_period > 0 else total_spent
    
    return StandardResponse(
        success=True,
        data=FinancialSummaryData(
            total_spent=float(total_spent),
            average_monthly=float(average_monthly),
            budget_utilization=float(budget_utilization),
            savings_rate=float(savings_rate),
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat()
        ).model_dump()
    )

@router.get("/trends/")
def get_spending_trends(
    period: PeriodType = Query(PeriodType.MONTH),
    months: int = Query(6, ge=1, le=24),
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Get spending trends over time."""
    
    trends = []
    today = date.today()
    
    # Get total budget for reference
    total_budget = db.query(func.sum(BudgetCategory.budget_amount)).filter(
        and_(
            BudgetCategory.user_id == current_user.id,
            BudgetCategory.is_active == True
        )
    ).scalar() or 0
    
    for i in range(months):
        # Calculate period for each month
        if today.month - i <= 0:
            month = today.month - i + 12
            year = today.year - 1
        else:
            month = today.month - i
            year = today.year
        
        period_start = date(year, month, 1)
        if month == 12:
            period_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = date(year, month + 1, 1) - timedelta(days=1)
        
        # Get spending for this period
        spent = db.query(func.sum(Expense.amount)).filter(
            and_(
                Expense.user_id == current_user.id,
                Expense.expense_date >= period_start,
                Expense.expense_date <= period_end
            )
        ).scalar() or 0
        
        utilization = (spent / total_budget * 100) if total_budget > 0 else 0
        
        trends.append(TrendData(
            period=f"{year}-{month:02d}",
            amount=float(spent),
            budget=float(total_budget),
            utilization=float(utilization)
        ))
    
    return StandardResponse(
        success=True,
        data={"trends": [trend.model_dump() for trend in reversed(trends)]}
    )

@router.get("/categories/")
def get_category_breakdown(
    period: PeriodType = Query(PeriodType.MONTH),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Get spending breakdown by category."""
    
    period_start, period_end = get_period_dates(period, start_date, end_date)
    
    # Get spending by category
    category_spending = db.query(
        BudgetCategory.name,
        BudgetCategory.budget_amount,
        func.coalesce(func.sum(Expense.amount), 0).label('spent')
    ).outerjoin(
        Expense,
        and_(
            Expense.category_id == BudgetCategory.id,
            Expense.expense_date >= period_start,
            Expense.expense_date <= period_end
        )
    ).filter(
        and_(
            BudgetCategory.user_id == current_user.id,
            BudgetCategory.is_active == True
        )
    ).group_by(BudgetCategory.id, BudgetCategory.name, BudgetCategory.budget_amount).all()
    
    # Calculate total for percentages
    total_spent = sum(row.spent for row in category_spending)
    
    categories = []
    for row in category_spending:
        percentage = (row.spent / total_spent * 100) if total_spent > 0 else 0
        utilization = (row.spent / row.budget_amount * 100) if row.budget_amount > 0 else 0
        
        categories.append(CategoryBreakdownData(
            category_name=row.name,
            spent=float(row.spent),
            budget=float(row.budget_amount),
            percentage=float(percentage),
            utilization=float(utilization)
        ))
    
    return StandardResponse(
        success=True,
        data={"categories": [cat.model_dump() for cat in categories]}
    )

@router.get("/recent-expenses/")
def get_recent_expenses(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Get recent expenses."""
    
    # Get recent expenses with category names
    recent_expenses = db.query(Expense, BudgetCategory.name).join(
        BudgetCategory, Expense.category_id == BudgetCategory.id
    ).filter(
        Expense.user_id == current_user.id
    ).order_by(
        Expense.expense_date.desc(),
        Expense.created_at.desc()
    ).limit(limit).all()
    
    today = date.today()
    expenses = []
    
    for expense, category_name in recent_expenses:
        days_ago = (today - expense.expense_date).days
        
        expenses.append(RecentExpenseData(
            id=expense.id,
            amount=float(expense.amount),
            description=expense.description,
            category_name=category_name,
            expense_date=expense.expense_date.isoformat(),
            days_ago=days_ago
        ))
    
    return StandardResponse(
        success=True,
        data={"expenses": [exp.model_dump() for exp in expenses]}
    )

@router.get("/insights/")
def get_financial_insights(
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Get financial insights and alerts."""
    
    insights = []
    today = date.today()
    current_month_start = today.replace(day=1)
    
    # Get current month spending by category
    category_spending = db.query(
        BudgetCategory.name,
        BudgetCategory.budget_amount,
        func.coalesce(func.sum(Expense.amount), 0).label('spent')
    ).outerjoin(
        Expense,
        and_(
            Expense.category_id == BudgetCategory.id,
            Expense.expense_date >= current_month_start,
            Expense.expense_date <= today
        )
    ).filter(
        and_(
            BudgetCategory.user_id == current_user.id,
            BudgetCategory.is_active == True
        )
    ).group_by(BudgetCategory.id, BudgetCategory.name, BudgetCategory.budget_amount).all()
    
    # Generate insights for categories
    for row in category_spending:
        utilization = (row.spent / row.budget_amount * 100) if row.budget_amount > 0 else 0
        
        if utilization >= 90:
            insights.append(InsightData(
                type=AlertType.DANGER,
                title="Budget Nearly Exceeded",
                message=f"You've spent {utilization:.1f}% of your {row.name} budget this month",
                amount=float(row.spent),
                category=row.name
            ))
        elif utilization >= 75:
            insights.append(InsightData(
                type=AlertType.WARNING,
                title="High Budget Usage",
                message=f"You've spent {utilization:.1f}% of your {row.name} budget this month",
                amount=float(row.spent),
                category=row.name
            ))
    
    # Check for categories with no spending
    no_spending_categories = [row for row in category_spending if row.spent == 0]
    if no_spending_categories and len(no_spending_categories) <= 3:
        for row in no_spending_categories[:3]:
            insights.append(InsightData(
                type=AlertType.INFO,
                title="Unused Budget",
                message=f"No expenses recorded for {row.name} this month",
                category=row.name
            ))
    
    return StandardResponse(
        success=True,
        data={"insights": [insight.model_dump() for insight in insights]}
    )

@router.get("/export/")
def export_report_data(
    format: ExportFormat = Query(ExportFormat.CSV),
    period: PeriodType = Query(PeriodType.MONTH),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_active_user),
    db: Session = Depends(get_db)
):
    """Export report data in various formats."""
    
    if format != ExportFormat.CSV:
        raise HTTPException(
            status_code=400,
            detail="Only CSV export is currently supported"
        )
    
    period_start, period_end = get_period_dates(period, start_date, end_date)
    
    # Get expenses with category information
    expenses = db.query(Expense, BudgetCategory.name).join(
        BudgetCategory, Expense.category_id == BudgetCategory.id
    ).filter(
        and_(
            Expense.user_id == current_user.id,
            Expense.expense_date >= period_start,
            Expense.expense_date <= period_end
        )
    ).order_by(Expense.expense_date.desc()).all()
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Date', 'Amount', 'Description', 'Category', 'Created At'
    ])
    
    # Write data
    for expense, category_name in expenses:
        writer.writerow([
            expense.expense_date.isoformat(),
            float(expense.amount),
            expense.description,
            category_name,
            expense.created_at.isoformat()
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=expenses_{period_start}_{period_end}.csv"}
    )