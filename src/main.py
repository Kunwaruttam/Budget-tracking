from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.database import engine, Base
from src.apps.auth.views import router as auth_router
from src.apps.budget.categories import router as categories_router
from src.apps.budget.expenses import router as expenses_router
from src.apps.budget.reports import router as reports_router

# Import models to ensure they are registered with SQLAlchemy
from src.apps.auth.models import User
from src.apps.budget.models import BudgetCategory, Expense

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Budget Tracker API",
    description="Simple Budget Tracking System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(categories_router, tags=["Budget Categories"])
app.include_router(expenses_router, tags=["Expenses"])
app.include_router(reports_router, tags=["Reports"])

@app.get("/")
def read_root():
    return {"message": "Budget Tracker API", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)