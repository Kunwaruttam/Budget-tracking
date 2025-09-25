from pydantic import BaseModel, Field, validator
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
import re

class BudgetCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    budget_amount: Decimal = Field(..., gt=0)
    color: str = Field(..., min_length=7, max_length=7)
    
    @validator('budget_amount')
    def validate_budget_amount(cls, v):
        # Ensure only 2 decimal places
        if v.as_tuple().exponent < -2:
            raise ValueError('Budget amount cannot have more than 2 decimal places')
        return v
    
    @validator('color')
    def validate_color(cls, v):
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be a valid hex color code (e.g., #FF5733)')
        return v.upper()
    
    @validator('name')
    def validate_name(cls, v):
        return v.strip()

class BudgetCategoryCreate(BudgetCategoryBase):
    pass

class BudgetCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    budget_amount: Optional[Decimal] = Field(None, gt=0)
    color: Optional[str] = Field(None, min_length=7, max_length=7)
    
    @validator('budget_amount')
    def validate_budget_amount(cls, v):
        if v is not None:
            # Ensure only 2 decimal places
            if v.as_tuple().exponent < -2:
                raise ValueError('Budget amount cannot have more than 2 decimal places')
        return v
    
    @validator('color')
    def validate_color(cls, v):
        if v is not None:
            if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
                raise ValueError('Color must be a valid hex color code (e.g., #FF5733)')
            return v.upper()
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            return v.strip()
        return v

class BudgetCategoryResponse(BudgetCategoryBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    total_expenses: Optional[Decimal] = None
    remaining_budget: Optional[Decimal] = None
    
    class Config:
        from_attributes = True

class ExpenseBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=200)
    amount: Decimal = Field(..., gt=0)
    expense_date: datetime
    notes: Optional[str] = Field(None, max_length=1000)
    
    @validator('amount')
    def validate_amount(cls, v):
        # Ensure only 2 decimal places
        if v.as_tuple().exponent < -2:
            raise ValueError('Amount cannot have more than 2 decimal places')
        return v
    
    @validator('description')
    def validate_description(cls, v):
        return v.strip()
    
    @validator('notes')
    def validate_notes(cls, v):
        if v is not None:
            return v.strip() if v.strip() else None
        return v

class ExpenseCreate(ExpenseBase):
    category_id: str

class ExpenseUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=200)
    amount: Optional[Decimal] = Field(None, gt=0)
    expense_date: Optional[datetime] = None
    category_id: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)
    
    @validator('amount')
    def validate_amount(cls, v):
        if v is not None:
            # Ensure only 2 decimal places
            if v.as_tuple().exponent < -2:
                raise ValueError('Amount cannot have more than 2 decimal places')
        return v
    
    @validator('description')
    def validate_description(cls, v):
        if v is not None:
            return v.strip()
        return v
    
    @validator('notes')
    def validate_notes(cls, v):
        if v is not None:
            return v.strip() if v.strip() else None
        return v

class ExpenseResponse(ExpenseBase):
    id: str
    user_id: str
    category_id: str
    category_name: Optional[str] = None
    category_color: Optional[str] = None
    category_budget: Optional[Decimal] = None
    remaining_budget: Optional[Decimal] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class BudgetCategoryWithExpenses(BudgetCategoryResponse):
    expenses: List[ExpenseResponse] = []

class BudgetSummary(BaseModel):
    total_budget: Decimal
    total_expenses: Decimal
    remaining_budget: Decimal
    categories_count: int
    expenses_count: int
    categories: List[BudgetCategoryResponse] = []