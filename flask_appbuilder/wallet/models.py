"""
Wallet System Models

This module defines the database models for the user wallet system,
including wallets, transactions, budgets, and related entities.
"""

import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from enum import Enum

from flask import current_app
from flask_appbuilder import Model
from flask_appbuilder.models.mixins import AuditMixin
from flask_appbuilder.security import current_user
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Numeric, 
    ForeignKey, Index, CheckConstraint, UniqueConstraint, event
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func

# Import enhanced mixins if available
try:
    from flask_appbuilder.mixins import (
        BaseModelMixin, AuditLogMixin, SoftDeleteMixin, 
        EncryptionMixin, CacheMixin, SearchableMixin
    )
    ENHANCED_MIXINS_AVAILABLE = True
except ImportError:
    # Fallback to basic AuditMixin
    BaseModelMixin = AuditMixin
    AuditLogMixin = type('AuditLogMixin', (), {})
    SoftDeleteMixin = type('SoftDeleteMixin', (), {})
    EncryptionMixin = type('EncryptionMixin', (), {})
    CacheMixin = type('CacheMixin', (), {})
    SearchableMixin = type('SearchableMixin', (), {})
    ENHANCED_MIXINS_AVAILABLE = False

log = logging.getLogger(__name__)


class TransactionType(Enum):
    """Transaction types for wallet operations."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class TransactionStatus(Enum):
    """Transaction status values."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PROCESSING = "processing"


class BudgetPeriod(Enum):
    """Budget period types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class PaymentMethodType(Enum):
    """Payment method types."""
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"
    CRYPTOCURRENCY = "cryptocurrency"
    CHECK = "check"
    OTHER = "other"


class UserWallet(BaseModelMixin, CacheMixin, Model):
    """
    User wallet model for tracking balances and wallet settings.
    
    Each user can have multiple wallets (different currencies, purposes, etc.)
    with comprehensive balance tracking and transaction history.
    """
    
    __tablename__ = 'ab_user_wallets'
    __table_args__ = (
        UniqueConstraint('user_id', 'currency_code', 'wallet_name', 
                        name='uq_user_wallet_currency_name'),
        Index('ix_user_wallets_user_currency', 'user_id', 'currency_code'),
        Index('ix_user_wallets_active', 'is_active'),
        CheckConstraint('balance >= 0 OR allow_negative_balance = true', 
                       name='ck_wallet_balance_non_negative')
    )
    
    # Core wallet fields
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('ab_user.id'), nullable=False)
    wallet_name = Column(String(100), nullable=False, default='Default Wallet')
    currency_code = Column(String(3), nullable=False, default='USD')
    balance = Column(Numeric(precision=15, scale=2), nullable=False, default=0.00)
    
    # Wallet configuration
    is_active = Column(Boolean, nullable=False, default=True)
    is_primary = Column(Boolean, nullable=False, default=False)
    allow_negative_balance = Column(Boolean, nullable=False, default=False)
    daily_limit = Column(Numeric(precision=15, scale=2), nullable=True)
    monthly_limit = Column(Numeric(precision=15, scale=2), nullable=True)
    
    # Wallet metadata
    description = Column(Text, nullable=True)
    wallet_type = Column(String(50), nullable=False, default='personal')
    icon = Column(String(50), nullable=True)  # FontAwesome icon class
    color = Column(String(7), nullable=True)  # Hex color code
    
    # Security and privacy
    is_locked = Column(Boolean, nullable=False, default=False)
    locked_until = Column(DateTime, nullable=True)
    require_approval = Column(Boolean, nullable=False, default=False)
    approval_limit = Column(Numeric(precision=15, scale=2), nullable=True)
    
    # Calculated fields
    available_balance = Column(Numeric(precision=15, scale=2), nullable=False, default=0.00)
    pending_balance = Column(Numeric(precision=15, scale=2), nullable=False, default=0.00)
    last_transaction_date = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="wallets")
    transactions = relationship("WalletTransaction", back_populates="wallet", 
                              cascade="all, delete-orphan")
    budgets = relationship("WalletBudget", back_populates="wallet",
                          cascade="all, delete-orphan")
    
    # Cache configuration
    __cache_timeout__ = 300  # 5 minutes
    
    @hybrid_property
    def total_income(self):
        """Calculate total income for this wallet."""
        return self.get_transaction_total(TransactionType.INCOME)
    
    @hybrid_property 
    def total_expenses(self):
        """Calculate total expenses for this wallet."""
        return self.get_transaction_total(TransactionType.EXPENSE)
    
    @hybrid_property
    def net_worth(self):
        """Calculate net worth (income - expenses)."""
        return self.total_income - self.total_expenses
    
    def get_transaction_total(self, transaction_type: TransactionType, 
                            start_date: datetime = None, end_date: datetime = None) -> Decimal:
        """Get total transactions by type and date range."""
        from sqlalchemy.orm import sessionmaker
        
        query = WalletTransaction.query.filter(
            WalletTransaction.wallet_id == self.id,
            WalletTransaction.transaction_type == transaction_type.value,
            WalletTransaction.status == TransactionStatus.COMPLETED.value
        )
        
        if start_date:
            query = query.filter(WalletTransaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(WalletTransaction.transaction_date <= end_date)
        
        result = query.with_entities(func.sum(WalletTransaction.amount)).scalar()
        return result or Decimal('0.00')
    
    def can_transact(self, amount: Decimal, transaction_type: TransactionType) -> tuple[bool, str]:
        """Check if a transaction is allowed."""
        amount = Decimal(str(amount))
        
        # Check if wallet is active
        if not self.is_active:
            return False, "Wallet is inactive"
        
        # Check if wallet is locked
        if self.is_locked:
            if self.locked_until and self.locked_until > datetime.utcnow():
                return False, f"Wallet is locked until {self.locked_until}"
            elif self.locked_until is None:
                return False, "Wallet is permanently locked"
        
        # Check for expenses
        if transaction_type == TransactionType.EXPENSE:
            # Check negative balance allowance
            if not self.allow_negative_balance and (self.available_balance - amount) < 0:
                return False, "Insufficient funds"
            
            # Check daily limit
            if self.daily_limit:
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                today_expenses = self.get_transaction_total(
                    TransactionType.EXPENSE, today_start, datetime.utcnow()
                )
                if (today_expenses + amount) > self.daily_limit:
                    return False, f"Daily limit of {self.currency_code} {self.daily_limit} exceeded"
            
            # Check monthly limit
            if self.monthly_limit:
                month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                month_expenses = self.get_transaction_total(
                    TransactionType.EXPENSE, month_start, datetime.utcnow()
                )
                if (month_expenses + amount) > self.monthly_limit:
                    return False, f"Monthly limit of {self.currency_code} {self.monthly_limit} exceeded"
            
            # Check approval requirement
            if self.require_approval and self.approval_limit and amount > self.approval_limit:
                return False, f"Transactions over {self.currency_code} {self.approval_limit} require approval"
        
        return True, "Transaction allowed"
    
    def add_transaction(self, amount: Decimal, transaction_type: TransactionType,
                       description: str = None, category_id: int = None,
                       payment_method_id: int = None, metadata: dict = None,
                       auto_commit: bool = True) -> 'WalletTransaction':
        """Add a new transaction to the wallet."""
        from sqlalchemy.orm import sessionmaker
        
        amount = Decimal(str(amount))
        
        # Validate transaction
        can_transact, message = self.can_transact(amount, transaction_type)
        if not can_transact:
            raise ValueError(f"Transaction not allowed: {message}")
        
        # Create transaction
        transaction = WalletTransaction(
            wallet_id=self.id,
            amount=amount,
            transaction_type=transaction_type.value,
            description=description,
            category_id=category_id,
            payment_method_id=payment_method_id,
            metadata_json=json.dumps(metadata) if metadata else None,
            status=TransactionStatus.COMPLETED.value,
            transaction_date=datetime.utcnow()
        )
        
        # Update wallet balance
        if transaction_type == TransactionType.INCOME:
            self.balance += amount
            self.available_balance += amount
        elif transaction_type == TransactionType.EXPENSE:
            self.balance -= amount
            self.available_balance -= amount
        elif transaction_type == TransactionType.REFUND:
            self.balance += amount
            self.available_balance += amount
        elif transaction_type == TransactionType.ADJUSTMENT:
            # Adjustment can be positive or negative
            if amount >= 0:
                self.balance += amount
                self.available_balance += amount
            else:
                self.balance += amount  # amount is already negative
                self.available_balance += amount
        
        # Update last transaction date
        self.last_transaction_date = datetime.utcnow()
        
        # Add to session
        from flask_appbuilder import db
        db.session.add(transaction)
        
        if auto_commit:
            db.session.commit()
        
        # Clear cache
        self.clear_cache()
        
        return transaction
    
    def transfer_to(self, target_wallet: 'UserWallet', amount: Decimal,
                   description: str = None, auto_commit: bool = True) -> tuple['WalletTransaction', 'WalletTransaction']:
        """Transfer funds to another wallet."""
        amount = Decimal(str(amount))
        
        if target_wallet.id == self.id:
            raise ValueError("Cannot transfer to the same wallet")
        
        # Validate source wallet can make the transfer
        can_transact, message = self.can_transact(amount, TransactionType.TRANSFER)
        if not can_transact:
            raise ValueError(f"Transfer not allowed: {message}")
        
        # Create outgoing transaction
        outgoing = WalletTransaction(
            wallet_id=self.id,
            amount=amount,
            transaction_type=TransactionType.TRANSFER.value,
            description=f"Transfer to {target_wallet.wallet_name}: {description}" if description else f"Transfer to {target_wallet.wallet_name}",
            status=TransactionStatus.COMPLETED.value,
            transaction_date=datetime.utcnow(),
            metadata_json=json.dumps({
                'transfer_type': 'outgoing',
                'target_wallet_id': target_wallet.id,
                'target_wallet_name': target_wallet.wallet_name
            })
        )
        
        # Create incoming transaction
        incoming = WalletTransaction(
            wallet_id=target_wallet.id,
            amount=amount,
            transaction_type=TransactionType.TRANSFER.value,
            description=f"Transfer from {self.wallet_name}: {description}" if description else f"Transfer from {self.wallet_name}",
            status=TransactionStatus.COMPLETED.value,
            transaction_date=datetime.utcnow(),
            metadata_json=json.dumps({
                'transfer_type': 'incoming',
                'source_wallet_id': self.id,
                'source_wallet_name': self.wallet_name
            })
        )
        
        # Update balances
        self.balance -= amount
        self.available_balance -= amount
        self.last_transaction_date = datetime.utcnow()
        
        target_wallet.balance += amount
        target_wallet.available_balance += amount
        target_wallet.last_transaction_date = datetime.utcnow()
        
        # Add to session
        from flask_appbuilder import db
        db.session.add(outgoing)
        db.session.add(incoming)
        
        if auto_commit:
            db.session.commit()
        
        # Clear cache
        self.clear_cache()
        target_wallet.clear_cache()
        
        return outgoing, incoming
    
    def get_balance_history(self, days: int = 30) -> List[Dict]:
        """Get balance history for the specified number of days."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get transactions in date range
        transactions = WalletTransaction.query.filter(
            WalletTransaction.wallet_id == self.id,
            WalletTransaction.transaction_date >= start_date,
            WalletTransaction.transaction_date <= end_date,
            WalletTransaction.status == TransactionStatus.COMPLETED.value
        ).order_by(WalletTransaction.transaction_date.asc()).all()
        
        # Calculate running balance
        balance_history = []
        current_balance = self.balance
        
        # Start from current balance and work backwards
        for i in range(len(transactions) - 1, -1, -1):
            trans = transactions[i]
            if trans.transaction_type == TransactionType.INCOME.value:
                current_balance -= trans.amount
            elif trans.transaction_type == TransactionType.EXPENSE.value:
                current_balance += trans.amount
        
        # Now work forward to create history
        for trans in transactions:
            if trans.transaction_type == TransactionType.INCOME.value:
                current_balance += trans.amount
            elif trans.transaction_type == TransactionType.EXPENSE.value:
                current_balance -= trans.amount
            
            balance_history.append({
                'date': trans.transaction_date,
                'balance': float(current_balance),
                'transaction_id': trans.id,
                'transaction_type': trans.transaction_type,
                'amount': float(trans.amount)
            })
        
        return balance_history
    
    @validates('currency_code')
    def validate_currency_code(self, key, currency_code):
        """Validate currency code format."""
        if currency_code and len(currency_code) != 3:
            raise ValueError("Currency code must be 3 characters")
        return currency_code.upper() if currency_code else currency_code
    
    def __repr__(self):
        return f"<UserWallet(id={self.id}, user_id={self.user_id}, name='{self.wallet_name}', balance={self.balance} {self.currency_code})>"


class WalletTransaction(BaseModelMixin, AuditLogMixin, SearchableMixin, Model):
    """
    Transaction model for recording all wallet activities.
    
    Provides comprehensive transaction tracking with categorization,
    metadata, and audit trails.
    """
    
    __tablename__ = 'ab_wallet_transactions'
    __table_args__ = (
        Index('ix_wallet_transactions_wallet_date', 'wallet_id', 'transaction_date'),
        Index('ix_wallet_transactions_type_status', 'transaction_type', 'status'),
        Index('ix_wallet_transactions_category', 'category_id'),
        Index('ix_wallet_transactions_user_date', 'user_id', 'transaction_date'),
        CheckConstraint('amount > 0', name='ck_transaction_amount_positive')
    )
    
    # Core transaction fields
    id = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, ForeignKey('ab_user_wallets.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('ab_user.id'), nullable=False)
    
    # Transaction details
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # income, expense, transfer, refund, adjustment
    status = Column(String(20), nullable=False, default='completed')
    transaction_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Transaction metadata
    description = Column(Text, nullable=True)
    reference_number = Column(String(100), nullable=True)
    external_id = Column(String(100), nullable=True)  # External system reference
    
    # Categorization
    category_id = Column(Integer, ForeignKey('ab_transaction_categories.id'), nullable=True)
    tags = Column(Text, nullable=True)  # JSON array of tags
    
    # Payment details
    payment_method_id = Column(Integer, ForeignKey('ab_payment_methods.id'), nullable=True)
    
    # Additional data
    metadata_json = Column(Text, nullable=True)  # JSON metadata
    receipt_url = Column(String(500), nullable=True)
    location = Column(String(200), nullable=True)
    
    # Processing details
    processed_date = Column(DateTime, nullable=True)
    processor_id = Column(String(100), nullable=True)
    processing_fee = Column(Numeric(precision=15, scale=2), nullable=True, default=0.00)
    
    # Relationships
    wallet = relationship("UserWallet", back_populates="transactions")
    user = relationship("User")
    category = relationship("TransactionCategory", backref="transactions")
    payment_method = relationship("PaymentMethod", backref="transactions")
    
    # Search configuration
    __searchable__ = {
        'description': 'A',
        'reference_number': 'B', 
        'tags': 'C'
    }
    
    @hybrid_property
    def metadata(self):
        """Get metadata as dictionary."""
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @metadata.setter
    def metadata(self, value):
        """Set metadata from dictionary."""
        if value is not None:
            self.metadata_json = json.dumps(value)
        else:
            self.metadata_json = None
    
    @hybrid_property
    def tag_list(self):
        """Get tags as list."""
        if self.tags:
            try:
                return json.loads(self.tags)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @tag_list.setter
    def tag_list(self, value):
        """Set tags from list."""
        if value is not None:
            self.tags = json.dumps(value)
        else:
            self.tags = None
    
    def add_tag(self, tag: str):
        """Add a tag to the transaction."""
        tags = self.tag_list
        if tag not in tags:
            tags.append(tag)
            self.tag_list = tags
    
    def remove_tag(self, tag: str):
        """Remove a tag from the transaction."""
        tags = self.tag_list
        if tag in tags:
            tags.remove(tag)
            self.tag_list = tags
    
    @validates('transaction_type')
    def validate_transaction_type(self, key, transaction_type):
        """Validate transaction type."""
        valid_types = [t.value for t in TransactionType]
        if transaction_type not in valid_types:
            raise ValueError(f"Invalid transaction type: {transaction_type}")
        return transaction_type
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate transaction status."""
        valid_statuses = [s.value for s in TransactionStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid transaction status: {status}")
        return status
    
    def __repr__(self):
        return f"<WalletTransaction(id={self.id}, wallet_id={self.wallet_id}, amount={self.amount}, type='{self.transaction_type}')>"


class TransactionCategory(BaseModelMixin, SoftDeleteMixin, Model):
    """
    Categories for organizing transactions.
    
    Provides hierarchical categorization with budgeting integration
    and spending analysis capabilities.
    """
    
    __tablename__ = 'ab_transaction_categories'
    __table_args__ = (
        Index('ix_transaction_categories_parent', 'parent_id'),
        Index('ix_transaction_categories_type', 'category_type'),
        UniqueConstraint('name', 'parent_id', 'user_id', name='uq_category_name_parent_user')
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('ab_user.id'), nullable=True)  # NULL for system categories
    
    # Category details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # FontAwesome icon
    color = Column(String(7), nullable=True)  # Hex color
    
    # Hierarchy
    parent_id = Column(Integer, ForeignKey('ab_transaction_categories.id'), nullable=True)
    category_type = Column(String(20), nullable=False, default='expense')  # income, expense, transfer
    
    # Configuration
    is_system = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    
    # Budget integration
    has_budget = Column(Boolean, nullable=False, default=False)
    budget_alert_threshold = Column(Integer, nullable=True)  # Percentage threshold for alerts
    
    # Relationships
    parent = relationship("TransactionCategory", remote_side=[id], backref="children")
    user = relationship("User")
    
    @hybrid_property
    def full_name(self):
        """Get full category path."""
        if self.parent:
            return f"{self.parent.full_name} > {self.name}"
        return self.name
    
    @hybrid_property
    def transaction_count(self):
        """Get count of transactions in this category."""
        return WalletTransaction.query.filter_by(category_id=self.id).count()
    
    def get_spending_total(self, start_date: datetime = None, 
                          end_date: datetime = None, user_id: int = None) -> Decimal:
        """Get total spending in this category."""
        query = WalletTransaction.query.filter(
            WalletTransaction.category_id == self.id,
            WalletTransaction.transaction_type == TransactionType.EXPENSE.value,
            WalletTransaction.status == TransactionStatus.COMPLETED.value
        )
        
        if start_date:
            query = query.filter(WalletTransaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(WalletTransaction.transaction_date <= end_date)
        if user_id:
            query = query.filter(WalletTransaction.user_id == user_id)
        
        result = query.with_entities(func.sum(WalletTransaction.amount)).scalar()
        return result or Decimal('0.00')
    
    def __repr__(self):
        return f"<TransactionCategory(id={self.id}, name='{self.name}', type='{self.category_type}')>"


# Set up event listeners for wallet balance updates
@event.listens_for(WalletTransaction, 'after_insert')
def update_wallet_balance_on_insert(mapper, connection, target):
    """Update wallet balance when transaction is inserted."""
    # This is handled in the add_transaction method to ensure consistency
    pass


@event.listens_for(WalletTransaction, 'after_update') 
def update_wallet_balance_on_update(mapper, connection, target):
    """Update wallet balance when transaction is updated."""
    # Handle status changes that affect balance
    pass


class WalletBudget(BaseModelMixin, Model):
    """
    Budget tracking for wallet categories and spending limits.
    
    Provides comprehensive budget management with alerts,
    rollover options, and spending analytics.
    """
    
    __tablename__ = 'ab_wallet_budgets'
    __table_args__ = (
        Index('ix_wallet_budgets_wallet_period', 'wallet_id', 'period_type'),
        Index('ix_wallet_budgets_category', 'category_id'),
        UniqueConstraint('wallet_id', 'category_id', 'period_type', 'period_start',
                        name='uq_budget_wallet_category_period')
    )
    
    id = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, ForeignKey('ab_user_wallets.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('ab_transaction_categories.id'), nullable=True)
    
    # Budget details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    budget_amount = Column(Numeric(precision=15, scale=2), nullable=False)
    
    # Period configuration
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly, quarterly, yearly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Budget settings
    is_active = Column(Boolean, nullable=False, default=True)
    auto_rollover = Column(Boolean, nullable=False, default=False)
    rollover_limit = Column(Numeric(precision=15, scale=2), nullable=True)
    
    # Alert settings
    alert_threshold_1 = Column(Integer, nullable=False, default=75)  # 75% warning
    alert_threshold_2 = Column(Integer, nullable=False, default=90)  # 90% critical
    alert_threshold_3 = Column(Integer, nullable=False, default=100) # 100% exceeded
    
    # Tracking
    spent_amount = Column(Numeric(precision=15, scale=2), nullable=False, default=0.00)
    remaining_amount = Column(Numeric(precision=15, scale=2), nullable=False, default=0.00)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    wallet = relationship("UserWallet", back_populates="budgets")
    category = relationship("TransactionCategory")
    
    @hybrid_property
    def spent_percentage(self):
        """Calculate percentage of budget spent."""
        if self.budget_amount > 0:
            return (self.spent_amount / self.budget_amount) * 100
        return 0
    
    @hybrid_property
    def is_over_budget(self):
        """Check if budget is exceeded."""
        return self.spent_amount > self.budget_amount
    
    @hybrid_property
    def alert_level(self):
        """Get current alert level (0-3)."""
        percentage = self.spent_percentage
        if percentage >= self.alert_threshold_3:
            return 3
        elif percentage >= self.alert_threshold_2:
            return 2
        elif percentage >= self.alert_threshold_1:
            return 1
        return 0
    
    def update_spent_amount(self, auto_commit: bool = True):
        """Update spent amount based on actual transactions."""
        # Calculate spent amount for this budget period
        query = WalletTransaction.query.filter(
            WalletTransaction.wallet_id == self.wallet_id,
            WalletTransaction.transaction_type == TransactionType.EXPENSE.value,
            WalletTransaction.status == TransactionStatus.COMPLETED.value,
            WalletTransaction.transaction_date >= self.period_start,
            WalletTransaction.transaction_date <= self.period_end
        )
        
        if self.category_id:
            query = query.filter(WalletTransaction.category_id == self.category_id)
        
        spent = query.with_entities(func.sum(WalletTransaction.amount)).scalar() or Decimal('0.00')
        
        self.spent_amount = spent
        self.remaining_amount = self.budget_amount - spent
        self.last_updated = datetime.utcnow()
        
        if auto_commit:
            from flask_appbuilder import db
            db.session.commit()
    
    def get_daily_average_spending(self) -> Decimal:
        """Get average daily spending for this budget period."""
        days_in_period = (self.period_end - self.period_start).days + 1
        if days_in_period > 0:
            return self.spent_amount / days_in_period
        return Decimal('0.00')
    
    def get_projected_spending(self) -> Decimal:
        """Project total spending based on current daily average."""
        daily_avg = self.get_daily_average_spending()
        days_in_period = (self.period_end - self.period_start).days + 1
        return daily_avg * days_in_period
    
    def __repr__(self):
        return f"<WalletBudget(id={self.id}, name='{self.name}', amount={self.budget_amount})>"


class PaymentMethod(BaseModelMixin, EncryptionMixin, SoftDeleteMixin, Model):
    """
    Payment methods for transactions (cards, bank accounts, etc.).
    
    Provides secure storage of payment method details with encryption
    and comprehensive transaction tracking.
    """
    
    __tablename__ = 'ab_payment_methods'
    __table_args__ = (
        Index('ix_payment_methods_user_type', 'user_id', 'method_type'),
        Index('ix_payment_methods_active', 'is_active'),
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('ab_user.id'), nullable=False)
    
    # Payment method details
    name = Column(String(100), nullable=False)
    method_type = Column(String(20), nullable=False)  # cash, credit_card, etc.
    description = Column(Text, nullable=True)
    
    # Card/Account details (encrypted)
    account_number = Column(String(200), nullable=True)  # Last 4 digits only
    account_holder = Column(String(100), nullable=True)
    bank_name = Column(String(100), nullable=True)
    
    # Configuration
    is_active = Column(Boolean, nullable=False, default=True)
    is_primary = Column(Boolean, nullable=False, default=False)
    currency_code = Column(String(3), nullable=False, default='USD')
    
    # Limits and restrictions
    daily_limit = Column(Numeric(precision=15, scale=2), nullable=True)
    monthly_limit = Column(Numeric(precision=15, scale=2), nullable=True)
    per_transaction_limit = Column(Numeric(precision=15, scale=2), nullable=True)
    
    # Tracking
    last_used_date = Column(DateTime, nullable=True)
    total_transactions = Column(Integer, nullable=False, default=0)
    total_amount = Column(Numeric(precision=15, scale=2), nullable=False, default=0.00)
    
    # Security
    requires_verification = Column(Boolean, nullable=False, default=False)
    verification_method = Column(String(50), nullable=True)  # sms, email, biometric
    
    # Relationships
    user = relationship("User")
    
    # Encryption configuration
    __encrypted_fields__ = ['account_number', 'account_holder']
    
    @validates('method_type')
    def validate_method_type(self, key, method_type):
        """Validate payment method type."""
        valid_types = [t.value for t in PaymentMethodType]
        if method_type not in valid_types:
            raise ValueError(f"Invalid payment method type: {method_type}")
        return method_type
    
    @hybrid_property
    def masked_account_number(self):
        """Get masked account number for display."""
        if self.account_number and len(self.account_number) > 4:
            return '*' * (len(self.account_number) - 4) + self.account_number[-4:]
        return self.account_number
    
    def can_transact(self, amount: Decimal) -> tuple[bool, str]:
        """Check if payment method can handle the transaction amount."""
        amount = Decimal(str(amount))
        
        if not self.is_active:
            return False, "Payment method is inactive"
        
        if self.per_transaction_limit and amount > self.per_transaction_limit:
            return False, f"Amount exceeds per-transaction limit of {self.currency_code} {self.per_transaction_limit}"
        
        # Check daily limit
        if self.daily_limit:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_total = WalletTransaction.query.filter(
                WalletTransaction.payment_method_id == self.id,
                WalletTransaction.transaction_date >= today_start,
                WalletTransaction.status == TransactionStatus.COMPLETED.value
            ).with_entities(func.sum(WalletTransaction.amount)).scalar() or Decimal('0.00')
            
            if (today_total + amount) > self.daily_limit:
                return False, f"Daily limit of {self.currency_code} {self.daily_limit} exceeded"
        
        # Check monthly limit
        if self.monthly_limit:
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_total = WalletTransaction.query.filter(
                WalletTransaction.payment_method_id == self.id,
                WalletTransaction.transaction_date >= month_start,
                WalletTransaction.status == TransactionStatus.COMPLETED.value
            ).with_entities(func.sum(WalletTransaction.amount)).scalar() or Decimal('0.00')
            
            if (month_total + amount) > self.monthly_limit:
                return False, f"Monthly limit of {self.currency_code} {self.monthly_limit} exceeded"
        
        return True, "Transaction allowed"
    
    def update_usage_stats(self, amount: Decimal, auto_commit: bool = True):
        """Update usage statistics after a transaction."""
        self.last_used_date = datetime.utcnow()
        self.total_transactions += 1
        self.total_amount += Decimal(str(amount))
        
        if auto_commit:
            from flask_appbuilder import db
            db.session.commit()
    
    def __repr__(self):
        return f"<PaymentMethod(id={self.id}, name='{self.name}', type='{self.method_type}')>"


class RecurringTransaction(BaseModelMixin, Model):
    """
    Recurring transaction templates for subscriptions and regular payments.
    
    Provides automated transaction scheduling with comprehensive
    recurrence patterns and exception handling.
    """
    
    __tablename__ = 'ab_recurring_transactions'
    __table_args__ = (
        Index('ix_recurring_transactions_wallet', 'wallet_id'),
        Index('ix_recurring_transactions_next_date', 'next_execution_date'),
        Index('ix_recurring_transactions_active', 'is_active'),
    )
    
    id = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, ForeignKey('ab_user_wallets.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('ab_user.id'), nullable=False)
    
    # Transaction template
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    transaction_type = Column(String(20), nullable=False)
    category_id = Column(Integer, ForeignKey('ab_transaction_categories.id'), nullable=True)
    payment_method_id = Column(Integer, ForeignKey('ab_payment_methods.id'), nullable=True)
    
    # Recurrence configuration
    recurrence_pattern = Column(String(20), nullable=False)  # daily, weekly, monthly, yearly
    recurrence_interval = Column(Integer, nullable=False, default=1)  # every N periods
    
    # Schedule
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)  # NULL for indefinite
    next_execution_date = Column(DateTime, nullable=False)
    last_execution_date = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    execution_count = Column(Integer, nullable=False, default=0)
    max_executions = Column(Integer, nullable=True)  # NULL for unlimited
    
    # Processing
    auto_execute = Column(Boolean, nullable=False, default=True)
    requires_approval = Column(Boolean, nullable=False, default=False)
    
    # Failure handling
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    last_error = Column(Text, nullable=True)
    
    # Relationships
    wallet = relationship("UserWallet")
    user = relationship("User")
    category = relationship("TransactionCategory")
    payment_method = relationship("PaymentMethod")
    
    def calculate_next_execution_date(self):
        """Calculate the next execution date based on recurrence pattern."""
        current_date = self.last_execution_date or self.start_date
        
        if self.recurrence_pattern == 'daily':
            next_date = current_date + timedelta(days=self.recurrence_interval)
        elif self.recurrence_pattern == 'weekly':
            next_date = current_date + timedelta(weeks=self.recurrence_interval)
        elif self.recurrence_pattern == 'monthly':
            # Handle month boundaries properly
            month = current_date.month
            year = current_date.year
            
            month += self.recurrence_interval
            while month > 12:
                month -= 12
                year += 1
            
            try:
                next_date = current_date.replace(year=year, month=month)
            except ValueError:
                # Handle cases like Jan 31 -> Feb 31 (invalid)
                next_date = current_date.replace(year=year, month=month, day=28)
                
        elif self.recurrence_pattern == 'yearly':
            next_date = current_date.replace(year=current_date.year + self.recurrence_interval)
        else:
            raise ValueError(f"Invalid recurrence pattern: {self.recurrence_pattern}")
        
        return next_date
    
    def is_ready_for_execution(self) -> bool:
        """Check if recurring transaction is ready for execution."""
        if not self.is_active:
            return False
        
        if self.next_execution_date > datetime.utcnow():
            return False
        
        if self.end_date and datetime.utcnow() > self.end_date:
            return False
        
        if self.max_executions and self.execution_count >= self.max_executions:
            return False
        
        return True
    
    def execute_transaction(self, auto_commit: bool = True) -> 'WalletTransaction':
        """Execute the recurring transaction."""
        if not self.is_ready_for_execution():
            raise ValueError("Recurring transaction is not ready for execution")
        
        try:
            # Create transaction
            transaction = self.wallet.add_transaction(
                amount=self.amount,
                transaction_type=TransactionType(self.transaction_type),
                description=f"{self.name}: {self.description}" if self.description else self.name,
                category_id=self.category_id,
                payment_method_id=self.payment_method_id,
                metadata={
                    'recurring_transaction_id': self.id,
                    'execution_count': self.execution_count + 1
                },
                auto_commit=False
            )
            
            # Update recurring transaction
            self.last_execution_date = datetime.utcnow()
            self.execution_count += 1
            self.next_execution_date = self.calculate_next_execution_date()
            self.retry_count = 0
            self.last_error = None
            
            # Check if we've reached max executions
            if self.max_executions and self.execution_count >= self.max_executions:
                self.is_active = False
            
            if auto_commit:
                from flask_appbuilder import db
                db.session.commit()
            
            return transaction
            
        except Exception as e:
            self.retry_count += 1
            self.last_error = str(e)
            
            if self.retry_count >= self.max_retries:
                self.is_active = False
                log.error(f"Recurring transaction {self.id} disabled after {self.max_retries} failed attempts: {e}")
            
            if auto_commit:
                from flask_appbuilder import db
                db.session.commit()
            
            raise
    
    def __repr__(self):
        return f"<RecurringTransaction(id={self.id}, name='{self.name}', amount={self.amount})>"


class WalletAudit(BaseModelMixin, Model):
    """
    Audit trail for wallet operations and security events.
    
    Provides comprehensive audit logging for compliance and security monitoring.
    """
    
    __tablename__ = 'ab_wallet_audits'
    __table_args__ = (
        Index('ix_wallet_audits_wallet_date', 'wallet_id', 'audit_date'),
        Index('ix_wallet_audits_event_type', 'event_type'),
        Index('ix_wallet_audits_user', 'user_id'),
    )
    
    id = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, ForeignKey('ab_user_wallets.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('ab_user.id'), nullable=False)
    transaction_id = Column(Integer, ForeignKey('ab_wallet_transactions.id'), nullable=True)
    
    # Audit details
    event_type = Column(String(50), nullable=False)  # transaction, balance_update, settings_change, etc.
    event_description = Column(Text, nullable=False)
    audit_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Context
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Data
    old_values = Column(Text, nullable=True)  # JSON
    new_values = Column(Text, nullable=True)  # JSON
    metadata_json = Column(Text, nullable=True)  # Additional audit data
    
    # Security
    risk_score = Column(Integer, nullable=False, default=0)  # 0-100 risk score
    is_suspicious = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    wallet = relationship("UserWallet")
    user = relationship("User")
    transaction = relationship("WalletTransaction")
    
    @hybrid_property
    def old_data(self):
        """Get old values as dictionary."""
        if self.old_values:
            try:
                return json.loads(self.old_values)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @old_data.setter
    def old_data(self, value):
        """Set old values from dictionary."""
        if value is not None:
            self.old_values = json.dumps(value, default=str)
        else:
            self.old_values = None
    
    @hybrid_property
    def new_data(self):
        """Get new values as dictionary."""
        if self.new_values:
            try:
                return json.loads(self.new_values)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @new_data.setter
    def new_data(self, value):
        """Set new values from dictionary."""
        if value is not None:
            self.new_values = json.dumps(value, default=str)
        else:
            self.new_values = None
    
    @hybrid_property
    def metadata(self):
        """Get metadata as dictionary."""
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @metadata.setter
    def metadata(self, value):
        """Set metadata from dictionary."""
        if value is not None:
            self.metadata_json = json.dumps(value, default=str)
        else:
            self.metadata_json = None
    
    @classmethod
    def log_event(cls, wallet_id: int, user_id: int, event_type: str, 
                  event_description: str, transaction_id: int = None,
                  old_values: dict = None, new_values: dict = None,
                  metadata: dict = None, risk_score: int = 0,
                  auto_commit: bool = True) -> 'WalletAudit':
        """Log an audit event."""
        from flask import request
        
        audit = cls(
            wallet_id=wallet_id,
            user_id=user_id,
            transaction_id=transaction_id,
            event_type=event_type,
            event_description=event_description,
            risk_score=risk_score,
            is_suspicious=risk_score > 70
        )
        
        # Set data
        if old_values:
            audit.old_data = old_values
        if new_values:
            audit.new_data = new_values
        if metadata:
            audit.metadata = metadata
        
        # Capture request context if available
        try:
            if request:
                audit.ip_address = request.remote_addr
                audit.user_agent = request.headers.get('User-Agent')
                audit.session_id = request.session.get('session_id')
        except RuntimeError:
            # Outside request context
            pass
        
        from flask_appbuilder import db
        db.session.add(audit)
        
        if auto_commit:
            db.session.commit()
        
        return audit
    
    def __repr__(self):
        return f"<WalletAudit(id={self.id}, event='{self.event_type}', user_id={self.user_id})>"


__all__ = [
    'TransactionType',
    'TransactionStatus', 
    'BudgetPeriod',
    'PaymentMethodType',
    'UserWallet',
    'WalletTransaction',
    'TransactionCategory',
    'WalletBudget',
    'PaymentMethod',
    'RecurringTransaction',
    'WalletAudit'
]