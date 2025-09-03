"""
User Wallet System for Flask-AppBuilder

This package provides a comprehensive wallet system for tracking user expenditure
and income, with support for multiple currencies, transaction history, budgeting,
and financial analytics.

Features:
- Multi-currency wallet support
- Transaction tracking and categorization
- Budget management and alerts
- Financial analytics and reporting
- Payment method integration
- Subscription and recurring payment management
- Expense approval workflows
- Financial audit trails
- Real-time balance calculations
- Import/export functionality

Components:
- Models: Wallet, Transaction, Budget, PaymentMethod, etc.
- Views: Wallet management, transaction history, budget dashboard
- Services: Payment processing, currency conversion, analytics
- Widgets: Financial input widgets, charts, dashboards
"""

from .models import *
from .views import *
from .services import *
from .widgets import *

__version__ = '1.0.0'
__all__ = [
    # Models
    'UserWallet',
    'WalletTransaction', 
    'WalletBudget',
    'PaymentMethod',
    'TransactionCategory',
    'RecurringTransaction',
    'WalletAudit',
    
    # Views
    'WalletDashboardView',
    'TransactionView',
    'BudgetView', 
    'PaymentMethodView',
    'WalletAnalyticsView',
    'WalletReportsView',
    
    # Services
    'WalletService',
    'TransactionService',
    'BudgetService',
    'CurrencyService',
    'AnalyticsService',
    
    # Widgets
    'CurrencyInputWidget',
    'TransactionFormWidget',
    'BudgetProgressWidget',
    'WalletBalanceWidget',
    'ExpenseChartWidget'
]