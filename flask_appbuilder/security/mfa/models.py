"""
Multi-Factor Authentication Database Models

This module contains the database models for storing MFA-related data including
user MFA configurations, backup codes, verification attempts, and organizational
policies.

Models:
    UserMFA: Stores user-specific MFA configuration and secrets
    MFABackupCode: Recovery codes for account access when MFA device unavailable
    MFAVerification: Audit trail of MFA verification attempts
    MFAPolicy: Organization-wide MFA policies and requirements

Security Notes:
    - All sensitive data (secrets, codes) are encrypted before storage
    - Backup codes are hashed using bcrypt
    - Rate limiting data is tracked for brute force protection
    - Complete audit trail for compliance requirements
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from flask import current_app
from flask_appbuilder import Model
from flask_appbuilder.models.mixins import AuditMixin
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey,
    Index, CheckConstraint, UniqueConstraint, event, func
)
from sqlalchemy.orm import relationship, validates, Session
from sqlalchemy.ext.hybrid import hybrid_property
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash

log = logging.getLogger(__name__)


class MFAEncryptionMixin:
    """
    Mixin for handling encryption of sensitive MFA data.
    
    Provides methods for encrypting and decrypting sensitive fields
    like TOTP secrets using application-configured encryption keys.
    """
    
    @staticmethod
    def _get_encryption_key() -> bytes:
        """
        Get the encryption key for MFA data.
        
        Returns:
            bytes: Encryption key for Fernet encryption
            
        Raises:
            ValueError: If no encryption key is configured
        """
        key = current_app.config.get('MFA_ENCRYPTION_KEY')
        if not key:
            # Generate a key if none configured (for development only)
            if current_app.debug:
                key = Fernet.generate_key()
                log.warning("Using auto-generated MFA encryption key. Configure MFA_ENCRYPTION_KEY for production.")
            else:
                raise ValueError("MFA_ENCRYPTION_KEY must be configured for production use")
        
        if isinstance(key, str):
            key = key.encode('utf-8')
        
        return key
    
    def _encrypt_data(self, data: str) -> str:
        """
        Encrypt sensitive data for storage.
        
        Args:
            data: Plain text data to encrypt
            
        Returns:
            str: Base64 encoded encrypted data
        """
        if not data:
            return data
            
        key = self._get_encryption_key()
        fernet = Fernet(key)
        encrypted = fernet.encrypt(data.encode('utf-8'))
        return encrypted.decode('utf-8')
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data from storage.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            str: Decrypted plain text data
        """
        if not encrypted_data:
            return encrypted_data
            
        key = self._get_encryption_key()
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_data.encode('utf-8'))
        return decrypted.decode('utf-8')


class UserMFA(MFAEncryptionMixin, AuditMixin, Model):
    """
    User Multi-Factor Authentication configuration model.
    
    Stores MFA settings and secrets for individual users including
    TOTP configuration, phone numbers for SMS, and MFA preferences.
    
    Attributes:
        user_id: Foreign key to Flask-AppBuilder User model
        is_enabled: Whether MFA is enabled for this user
        totp_secret: Encrypted TOTP secret key
        phone_number: Encrypted phone number for SMS MFA
        backup_phone: Encrypted backup phone number
        preferred_method: User's preferred MFA method
        last_used_method: Most recently used MFA method
        setup_completed: Whether initial MFA setup is complete
        recovery_email: Encrypted recovery email address
        is_enforced: Whether MFA is enforced by policy
        failed_attempts: Number of recent failed MFA attempts
        locked_until: Timestamp when account will be unlocked
        last_success: Timestamp of last successful MFA verification
        
    Security Features:
        - TOTP secrets encrypted at rest
        - Phone numbers encrypted for privacy
        - Failed attempt tracking for brute force protection
        - Account lockout mechanism
        - Audit trail through AuditMixin
    """
    
    __tablename__ = 'ab_user_mfa'
    __table_args__ = (
        Index('ix_user_mfa_user_id', 'user_id'),
        Index('ix_user_mfa_enabled', 'is_enabled'),
        Index('ix_user_mfa_locked', 'locked_until'),
        UniqueConstraint('user_id', name='uq_user_mfa_user_id'),
        CheckConstraint('failed_attempts >= 0', name='ck_user_mfa_failed_attempts'),
        CheckConstraint(
            "preferred_method IN ('totp', 'sms', 'email', 'backup')",
            name='ck_user_mfa_preferred_method'
        )
    )
    
    # Primary key and relationships
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('ab_user.id'), nullable=False)
    
    # MFA configuration
    is_enabled = Column(Boolean, nullable=False, default=False)
    is_enforced = Column(Boolean, nullable=False, default=False)
    setup_completed = Column(Boolean, nullable=False, default=False)
    preferred_method = Column(String(10), nullable=True)
    last_used_method = Column(String(10), nullable=True)
    
    # Encrypted secrets and contact information
    totp_secret_encrypted = Column(Text, nullable=True)
    phone_number_encrypted = Column(Text, nullable=True) 
    backup_phone_encrypted = Column(Text, nullable=True)
    recovery_email_encrypted = Column(Text, nullable=True)
    
    # Security and rate limiting
    failed_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)
    
    # Metadata
    totp_last_counter = Column(Integer, nullable=True)
    setup_token = Column(String(100), nullable=True)  # Temporary setup token
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="mfa_config")
    backup_codes = relationship("MFABackupCode", back_populates="user_mfa", cascade="all, delete-orphan")
    verifications = relationship("MFAVerification", back_populates="user_mfa", cascade="all, delete-orphan")
    
    @hybrid_property
    def totp_secret(self) -> Optional[str]:
        """
        Get decrypted TOTP secret.
        
        Returns:
            Optional[str]: Decrypted TOTP secret or None if not set
        """
        if self.totp_secret_encrypted:
            return self._decrypt_data(self.totp_secret_encrypted)
        return None
    
    @totp_secret.setter
    def totp_secret(self, value: Optional[str]) -> None:
        """
        Set encrypted TOTP secret.
        
        Args:
            value: Plain text TOTP secret to encrypt and store
        """
        if value:
            self.totp_secret_encrypted = self._encrypt_data(value)
        else:
            self.totp_secret_encrypted = None
    
    @hybrid_property
    def phone_number(self) -> Optional[str]:
        """
        Get decrypted phone number.
        
        Returns:
            Optional[str]: Decrypted phone number or None if not set
        """
        if self.phone_number_encrypted:
            return self._decrypt_data(self.phone_number_encrypted)
        return None
    
    @phone_number.setter
    def phone_number(self, value: Optional[str]) -> None:
        """
        Set encrypted phone number.
        
        Args:
            value: Plain text phone number to encrypt and store
        """
        if value:
            self.phone_number_encrypted = self._encrypt_data(value)
        else:
            self.phone_number_encrypted = None
    
    @hybrid_property
    def backup_phone(self) -> Optional[str]:
        """
        Get decrypted backup phone number.
        
        Returns:
            Optional[str]: Decrypted backup phone number or None if not set
        """
        if self.backup_phone_encrypted:
            return self._decrypt_data(self.backup_phone_encrypted)
        return None
    
    @backup_phone.setter 
    def backup_phone(self, value: Optional[str]) -> None:
        """
        Set encrypted backup phone number.
        
        Args:
            value: Plain text backup phone number to encrypt and store
        """
        if value:
            self.backup_phone_encrypted = self._encrypt_data(value)
        else:
            self.backup_phone_encrypted = None
    
    @hybrid_property
    def recovery_email(self) -> Optional[str]:
        """
        Get decrypted recovery email address.
        
        Returns:
            Optional[str]: Decrypted recovery email or None if not set
        """
        if self.recovery_email_encrypted:
            return self._decrypt_data(self.recovery_email_encrypted)
        return None
    
    @recovery_email.setter
    def recovery_email(self, value: Optional[str]) -> None:
        """
        Set encrypted recovery email address.
        
        Args:
            value: Plain text recovery email to encrypt and store
        """
        if value:
            self.recovery_email_encrypted = self._encrypt_data(value)
        else:
            self.recovery_email_encrypted = None
    
    @validates('preferred_method')
    def validate_preferred_method(self, key: str, method: str) -> str:
        """
        Validate MFA method selection.
        
        Args:
            key: Field name being validated
            method: MFA method string to validate
            
        Returns:
            str: Validated method string
            
        Raises:
            ValueError: If method is not supported
        """
        valid_methods = {'totp', 'sms', 'email', 'backup'}
        if method and method not in valid_methods:
            raise ValueError(f"Invalid MFA method: {method}. Must be one of {valid_methods}")
        return method
    
    def is_locked(self) -> bool:
        """
        Check if account is currently locked due to failed MFA attempts.
        
        Returns:
            bool: True if account is locked, False otherwise
        """
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until
    
    def can_attempt_mfa(self) -> bool:
        """
        Check if user can attempt MFA verification.
        
        Returns:
            bool: True if MFA attempt is allowed, False if locked
        """
        return not self.is_locked()
    
    def record_failed_attempt(self, session: Session = None) -> None:
        """
        Record a failed MFA attempt and apply lockout if necessary.
        
        Args:
            session: Database session for transaction
        """
        self.failed_attempts += 1
        
        # Get lockout policy from app config
        max_attempts = current_app.config.get('MFA_MAX_FAILED_ATTEMPTS', 5)
        lockout_duration = current_app.config.get('MFA_LOCKOUT_DURATION', 900)  # 15 minutes
        
        if self.failed_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(seconds=lockout_duration)
            log.warning(f"User {self.user_id} MFA locked after {self.failed_attempts} failed attempts")
        
        if session:
            session.commit()
    
    def record_successful_attempt(self, method: str, session: Session = None) -> None:
        """
        Record a successful MFA attempt and reset failed counters.
        
        Args:
            method: MFA method that was successful
            session: Database session for transaction
        """
        self.failed_attempts = 0
        self.locked_until = None
        self.last_success = datetime.utcnow()
        self.last_used_method = method
        
        if session:
            session.commit()
    
    def generate_setup_token(self) -> str:
        """
        Generate a secure token for MFA setup process.
        
        Returns:
            str: Secure random token for setup verification
        """
        token = secrets.token_urlsafe(32)
        self.setup_token = token
        return token
    
    def verify_setup_token(self, token: str) -> bool:
        """
        Verify a setup token for MFA configuration.
        
        Args:
            token: Token to verify
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        return self.setup_token and self.setup_token == token
    
    def clear_setup_token(self) -> None:
        """Clear the setup token after successful setup."""
        self.setup_token = None
    
    def __repr__(self) -> str:
        """String representation of UserMFA object."""
        return (
            f"<UserMFA(id={self.id}, user_id={self.user_id}, "
            f"enabled={self.is_enabled}, method='{self.preferred_method}')>"
        )


class MFABackupCode(AuditMixin, Model):
    """
    MFA backup/recovery codes for account recovery.
    
    Backup codes allow users to access their account when their primary
    MFA device is unavailable. Each code can only be used once and codes
    are hashed before storage for security.
    
    Attributes:
        user_mfa_id: Foreign key to UserMFA configuration
        code_hash: Bcrypt hash of the backup code
        is_used: Whether this code has been consumed
        used_at: Timestamp when code was used
        used_from_ip: IP address where code was used
        
    Security Features:
        - Codes are hashed using bcrypt before storage
        - One-time use enforcement
        - Usage audit trail with IP tracking
        - Automatic expiration after use
    """
    
    __tablename__ = 'ab_mfa_backup_codes'
    __table_args__ = (
        Index('ix_mfa_backup_codes_user_mfa_id', 'user_mfa_id'),
        Index('ix_mfa_backup_codes_is_used', 'is_used'),
        Index('ix_mfa_backup_codes_used_at', 'used_at'),
    )
    
    # Primary key and relationships
    id = Column(Integer, primary_key=True)
    user_mfa_id = Column(Integer, ForeignKey('ab_user_mfa.id'), nullable=False)
    
    # Code storage and usage tracking
    code_hash = Column(String(128), nullable=False)
    is_used = Column(Boolean, nullable=False, default=False)
    used_at = Column(DateTime, nullable=True)
    used_from_ip = Column(String(45), nullable=True)  # Support IPv6
    
    # Relationships
    user_mfa = relationship("UserMFA", back_populates="backup_codes")
    
    @staticmethod
    def generate_codes(user_mfa_id: int, count: int = 8) -> List[str]:
        """
        Generate backup codes for a user.
        
        Args:
            user_mfa_id: ID of UserMFA configuration
            count: Number of backup codes to generate
            
        Returns:
            List[str]: List of generated backup codes (plain text)
        """
        from flask_appbuilder import db
        
        # Clear existing unused codes
        db.session.query(MFABackupCode).filter_by(
            user_mfa_id=user_mfa_id,
            is_used=False
        ).delete()
        
        codes = []
        for _ in range(count):
            # Generate secure 8-digit code
            code = ''.join([str(secrets.randbelow(10)) for _ in range(8)])
            codes.append(code)
            
            # Store hashed version
            backup_code = MFABackupCode(
                user_mfa_id=user_mfa_id,
                code_hash=generate_password_hash(code)
            )
            db.session.add(backup_code)
        
        db.session.commit()
        log.info(f"Generated {count} backup codes for user_mfa_id {user_mfa_id}")
        
        return codes
    
    @staticmethod
    def verify_and_consume(user_mfa_id: int, code: str, ip_address: str = None) -> bool:
        """
        Verify a backup code and mark it as used if valid.
        
        Args:
            user_mfa_id: ID of UserMFA configuration
            code: Backup code to verify
            ip_address: IP address of verification attempt
            
        Returns:
            bool: True if code was valid and consumed, False otherwise
        """
        from flask_appbuilder import db
        
        # Find unused backup codes for user
        backup_codes = db.session.query(MFABackupCode).filter_by(
            user_mfa_id=user_mfa_id,
            is_used=False
        ).all()
        
        for backup_code in backup_codes:
            if check_password_hash(backup_code.code_hash, code):
                # Mark as used
                backup_code.is_used = True
                backup_code.used_at = datetime.utcnow()
                backup_code.used_from_ip = ip_address
                db.session.commit()
                
                log.info(f"Backup code used for user_mfa_id {user_mfa_id} from IP {ip_address}")
                return True
        
        log.warning(f"Invalid backup code attempt for user_mfa_id {user_mfa_id} from IP {ip_address}")
        return False
    
    def __repr__(self) -> str:
        """String representation of MFABackupCode object."""
        return (
            f"<MFABackupCode(id={self.id}, user_mfa_id={self.user_mfa_id}, "
            f"used={self.is_used})>"
        )


class MFAVerification(AuditMixin, Model):
    """
    Audit trail for MFA verification attempts.
    
    Records all MFA verification attempts (successful and failed) for
    security monitoring, compliance, and forensic analysis.
    
    Attributes:
        user_mfa_id: Foreign key to UserMFA configuration
        method: MFA method used for verification
        success: Whether verification was successful
        failure_reason: Reason for failure if not successful
        ip_address: IP address of verification attempt
        user_agent: Browser user agent string
        verification_time: Timestamp of verification attempt
        otp_used: Encrypted OTP that was submitted (for audit)
        
    Security Features:
        - Complete audit trail of all attempts
        - IP and user agent tracking
        - Failure reason classification
        - Submitted OTP storage (encrypted) for forensics
    """
    
    __tablename__ = 'ab_mfa_verifications'
    __table_args__ = (
        Index('ix_mfa_verifications_user_mfa_id', 'user_mfa_id'),
        Index('ix_mfa_verifications_success', 'success'),
        Index('ix_mfa_verifications_method', 'method'),
        Index('ix_mfa_verifications_time', 'verification_time'),
        Index('ix_mfa_verifications_ip', 'ip_address'),
        CheckConstraint(
            "method IN ('totp', 'sms', 'email', 'backup')",
            name='ck_mfa_verifications_method'
        )
    )
    
    # Primary key and relationships
    id = Column(Integer, primary_key=True)
    user_mfa_id = Column(Integer, ForeignKey('ab_user_mfa.id'), nullable=False)
    
    # Verification details
    method = Column(String(10), nullable=False)
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(100), nullable=True)
    verification_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Audit information (encrypted)
    otp_used_encrypted = Column(Text, nullable=True)
    
    # Relationships
    user_mfa = relationship("UserMFA", back_populates="verifications")
    
    @hybrid_property
    def otp_used(self) -> Optional[str]:
        """
        Get decrypted OTP that was used for verification.
        
        Returns:
            Optional[str]: Decrypted OTP or None if not stored
        """
        if self.otp_used_encrypted:
            encryption_mixin = MFAEncryptionMixin()
            return encryption_mixin._decrypt_data(self.otp_used_encrypted)
        return None
    
    @otp_used.setter
    def otp_used(self, value: Optional[str]) -> None:
        """
        Set encrypted OTP for audit purposes.
        
        Args:
            value: Plain text OTP to encrypt and store
        """
        if value:
            encryption_mixin = MFAEncryptionMixin()
            self.otp_used_encrypted = encryption_mixin._encrypt_data(value)
        else:
            self.otp_used_encrypted = None
    
    @staticmethod
    def record_attempt(user_mfa_id: int, method: str, success: bool,
                      failure_reason: str = None, otp_used: str = None,
                      ip_address: str = None, user_agent: str = None) -> 'MFAVerification':
        """
        Record an MFA verification attempt.
        
        Args:
            user_mfa_id: ID of UserMFA configuration
            method: MFA method used
            success: Whether verification succeeded
            failure_reason: Reason for failure if applicable
            otp_used: OTP code that was submitted
            ip_address: IP address of attempt
            user_agent: Browser user agent
            
        Returns:
            MFAVerification: Created verification record
        """
        from flask_appbuilder import db
        
        verification = MFAVerification(
            user_mfa_id=user_mfa_id,
            method=method,
            success=success,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if otp_used:
            verification.otp_used = otp_used
        
        db.session.add(verification)
        db.session.commit()
        
        log.info(
            f"MFA verification recorded: user_mfa_id={user_mfa_id}, "
            f"method={method}, success={success}, ip={ip_address}"
        )
        
        return verification
    
    @validates('method')
    def validate_method(self, key: str, method: str) -> str:
        """
        Validate MFA method.
        
        Args:
            key: Field name being validated
            method: MFA method to validate
            
        Returns:
            str: Validated method
            
        Raises:
            ValueError: If method is invalid
        """
        valid_methods = {'totp', 'sms', 'email', 'backup'}
        if method not in valid_methods:
            raise ValueError(f"Invalid MFA method: {method}")
        return method
    
    def __repr__(self) -> str:
        """String representation of MFAVerification object."""
        return (
            f"<MFAVerification(id={self.id}, user_mfa_id={self.user_mfa_id}, "
            f"method='{self.method}', success={self.success})>"
        )


class MFAPolicy(AuditMixin, Model):
    """
    Organization-wide MFA policies and requirements.
    
    Defines MFA policies that can be applied across the organization
    including enforcement rules, method requirements, and exemptions.
    
    Attributes:
        name: Policy name for identification
        description: Human-readable policy description
        is_active: Whether policy is currently active
        enforce_for_roles: JSON list of roles that must use MFA
        allowed_methods: JSON list of allowed MFA methods
        require_backup_codes: Whether backup codes are required
        max_failed_attempts: Maximum failed attempts before lockout
        lockout_duration: Duration of lockout in seconds
        session_timeout: MFA session timeout in seconds
        require_setup_within: Time limit for completing MFA setup
        
    Policy Features:
        - Role-based enforcement
        - Method restrictions
        - Configurable security parameters
        - Setup time limits
        - Session management
    """
    
    __tablename__ = 'ab_mfa_policies'
    __table_args__ = (
        Index('ix_mfa_policies_active', 'is_active'),
        Index('ix_mfa_policies_name', 'name'),
        UniqueConstraint('name', name='uq_mfa_policies_name'),
        CheckConstraint('max_failed_attempts > 0', name='ck_mfa_policies_max_attempts'),
        CheckConstraint('lockout_duration > 0', name='ck_mfa_policies_lockout'),
    )
    
    # Primary key and identification
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Policy configuration (JSON fields)
    enforce_for_roles = Column(Text, nullable=True)  # JSON array of role names
    allowed_methods = Column(Text, nullable=True)    # JSON array of method names
    
    # Security parameters
    require_backup_codes = Column(Boolean, nullable=False, default=True)
    max_failed_attempts = Column(Integer, nullable=False, default=5)
    lockout_duration = Column(Integer, nullable=False, default=900)  # 15 minutes
    session_timeout = Column(Integer, nullable=False, default=3600)   # 1 hour
    require_setup_within = Column(Integer, nullable=True)  # Days
    
    @hybrid_property
    def enforced_roles(self) -> List[str]:
        """
        Get list of roles that must use MFA.
        
        Returns:
            List[str]: Role names that require MFA
        """
        import json
        if self.enforce_for_roles:
            return json.loads(self.enforce_for_roles)
        return []
    
    @enforced_roles.setter
    def enforced_roles(self, roles: List[str]) -> None:
        """
        Set roles that must use MFA.
        
        Args:
            roles: List of role names requiring MFA
        """
        import json
        self.enforce_for_roles = json.dumps(roles) if roles else None
    
    @hybrid_property
    def permitted_methods(self) -> List[str]:
        """
        Get list of allowed MFA methods.
        
        Returns:
            List[str]: Allowed MFA method names
        """
        import json
        if self.allowed_methods:
            return json.loads(self.allowed_methods)
        return ['totp', 'sms', 'email', 'backup']  # Default all methods
    
    @permitted_methods.setter
    def permitted_methods(self, methods: List[str]) -> None:
        """
        Set allowed MFA methods.
        
        Args:
            methods: List of allowed MFA method names
        """
        import json
        valid_methods = {'totp', 'sms', 'email', 'backup'}
        invalid_methods = set(methods) - valid_methods
        if invalid_methods:
            raise ValueError(f"Invalid MFA methods: {invalid_methods}")
        
        self.allowed_methods = json.dumps(methods) if methods else None
    
    def applies_to_user(self, user) -> bool:
        """
        Check if this policy applies to a given user.
        
        Args:
            user: Flask-AppBuilder User object
            
        Returns:
            bool: True if policy applies to user, False otherwise
        """
        if not self.is_active:
            return False
        
        if not self.enforced_roles:
            return False  # No roles specified means policy doesn't apply
        
        user_roles = {role.name for role in user.roles}
        policy_roles = set(self.enforced_roles)
        
        # Policy applies if user has any of the enforced roles
        return bool(user_roles & policy_roles)
    
    def is_method_allowed(self, method: str) -> bool:
        """
        Check if an MFA method is allowed by this policy.
        
        Args:
            method: MFA method name to check
            
        Returns:
            bool: True if method is allowed, False otherwise
        """
        return method in self.permitted_methods
    
    @staticmethod
    def get_policy_for_user(user) -> Optional['MFAPolicy']:
        """
        Get the active MFA policy that applies to a user.
        
        Args:
            user: Flask-AppBuilder User object
            
        Returns:
            Optional[MFAPolicy]: Applicable policy or None
        """
        from flask_appbuilder import db
        
        policies = db.session.query(MFAPolicy).filter_by(is_active=True).all()
        
        for policy in policies:
            if policy.applies_to_user(user):
                return policy
        
        return None
    
    def __repr__(self) -> str:
        """String representation of MFAPolicy object."""
        return (
            f"<MFAPolicy(id={self.id}, name='{self.name}', "
            f"active={self.is_active})>"
        )


# Event listeners for additional model behavior
@event.listens_for(UserMFA, 'before_insert')
def generate_mfa_setup_defaults(mapper, connection, target):
    """Generate default values when creating UserMFA records."""
    if not target.setup_token and not target.setup_completed:
        target.generate_setup_token()


@event.listens_for(UserMFA, 'after_update')
def log_mfa_changes(mapper, connection, target):
    """Log significant changes to MFA configuration."""
    from sqlalchemy.orm.attributes import get_history
    
    # Check if MFA was enabled/disabled
    enabled_history = get_history(target, 'is_enabled')
    if enabled_history.has_changes():
        old_value = enabled_history.deleted[0] if enabled_history.deleted else None
        new_value = target.is_enabled
        
        log.info(
            f"MFA status changed for user {target.user_id}: "
            f"{old_value} -> {new_value}"
        )


__all__ = [
    'MFAEncryptionMixin',
    'UserMFA',
    'MFABackupCode', 
    'MFAVerification',
    'MFAPolicy',
]