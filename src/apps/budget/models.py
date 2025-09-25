from sqlalchemy import Column, String, Numeric, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.core.database import Base
from decimal import Decimal

class BudgetCategory(Base):
    __tablename__ = "budget_categories"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    budget_amount = Column(Numeric(10, 2), nullable=False)
    color = Column(String(7), nullable=True)  # Hex color code #RRGGBB
    icon = Column(String(50), nullable=True)  # Icon identifier
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="budget_categories")
    expenses = relationship("Expense", back_populates="category", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BudgetCategory(name='{self.name}', budget=${self.budget_amount})>"

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(String, ForeignKey("budget_categories.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(200), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    expense_date = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="expenses")
    category = relationship("BudgetCategory", back_populates="expenses")
    
    def __repr__(self):
        return f"<Expense(description='{self.description}', amount=${self.amount})>"