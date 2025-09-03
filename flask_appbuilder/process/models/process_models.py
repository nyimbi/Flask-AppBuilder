"""
Core data models for the Intelligent Business Process Engine.

Provides multi-tenant business process automation with comprehensive
state management, approval workflows, and ML-powered triggers.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, Index,
    ForeignKey, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from flask_appbuilder import Model
from flask_appbuilder.models.mixins import AuditMixin
from flask_appbuilder.models.tenant_models import TenantAwareMixin

log = logging.getLogger(__name__)


class ProcessStatus(Enum):
    """Process status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active" 
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"


class ProcessInstanceStatus(Enum):
    """Process instance status enumeration."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class ProcessStepStatus(Enum):
    """Process step status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"  # Waiting for approval or external event


class ApprovalStatus(Enum):
    """Approval status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELEGATED = "delegated"
    EXPIRED = "expired"


class TriggerStatus(Enum):
    """Smart trigger status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class ProcessDefinition(TenantAwareMixin, AuditMixin, Model):
    """
    Process definition model for storing workflow templates.
    
    Stores the complete process structure as a directed graph with nodes
    representing process steps and edges representing flow transitions.
    """
    
    __tablename__ = 'ab_process_definitions'
    __table_args__ = (
        Index('ix_process_def_tenant_name', 'tenant_id', 'name'),
        Index('ix_process_def_status', 'status'),
        Index('ix_process_def_category', 'category'),
        UniqueConstraint('tenant_id', 'name', 'version', name='uq_tenant_process_version'),
    )
    
    id = Column(Integer, primary_key=True)
    
    # Basic information
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(20), default=ProcessStatus.DRAFT.value, nullable=False)
    
    # Process structure (stored as JSON graph)
    process_graph = Column(JSONB, nullable=False, default=lambda: {'nodes': [], 'edges': []})
    
    # Configuration and metadata
    settings = Column(JSONB, default=lambda: {})
    category = Column(String(50), index=True)
    tags = Column(JSONB, default=lambda: [])
    
    # Process characteristics
    estimated_duration = Column(Integer)  # Estimated duration in minutes
    priority = Column(Integer, default=0)  # Process priority (0-10)
    
    # Versioning and lifecycle
    parent_definition_id = Column(Integer, ForeignKey('ab_process_definitions.id'))
    is_template = Column(Boolean, default=False)
    
    # Relationships
    instances = relationship("ProcessInstance", back_populates="definition", cascade="all, delete-orphan")
    child_versions = relationship("ProcessDefinition", remote_side=[id])
    templates = relationship("ProcessTemplate", back_populates="definition")
    triggers = relationship("SmartTrigger", back_populates="process_definition")
    
    @hybrid_property
    def node_count(self):
        """Get number of nodes in process graph."""
        return len(self.process_graph.get('nodes', []))
    
    @hybrid_property
    def edge_count(self):
        """Get number of edges in process graph."""
        return len(self.process_graph.get('edges', []))
    
    @hybrid_property
    def is_valid_graph(self):
        """Check if process graph is valid."""
        nodes = self.process_graph.get('nodes', [])
        edges = self.process_graph.get('edges', [])
        
        if not nodes:
            return False
        
        # Must have at least one start node
        start_nodes = [n for n in nodes if n.get('type') == 'start']
        if not start_nodes:
            return False
        
        return True
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate process status values."""
        valid_statuses = [s.value for s in ProcessStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of: {valid_statuses}")
        return status
    
    @validates('process_graph')
    def validate_process_graph(self, key, graph):
        """Validate process graph structure."""
        if not isinstance(graph, dict):
            raise ValueError("Process graph must be a dictionary")
        
        if 'nodes' not in graph or 'edges' not in graph:
            raise ValueError("Process graph must contain 'nodes' and 'edges' keys")
        
        nodes = graph.get('nodes', [])
        edges = graph.get('edges', [])
        
        # Validate nodes structure
        for node in nodes:
            if not isinstance(node, dict):
                raise ValueError("Each node must be a dictionary")
            if 'id' not in node or 'type' not in node:
                raise ValueError("Each node must have 'id' and 'type' fields")
        
        # Validate edges structure
        node_ids = {n['id'] for n in nodes}
        for edge in edges:
            if not isinstance(edge, dict):
                raise ValueError("Each edge must be a dictionary")
            if 'source' not in edge or 'target' not in edge:
                raise ValueError("Each edge must have 'source' and 'target' fields")
            if edge['source'] not in node_ids or edge['target'] not in node_ids:
                raise ValueError("Edge source/target must reference existing nodes")
        
        return graph
    
    def get_start_nodes(self) -> List[Dict[str, Any]]:
        """Get all start nodes in the process."""
        nodes = self.process_graph.get('nodes', [])
        return [n for n in nodes if n.get('type') == 'start']
    
    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node by ID."""
        nodes = self.process_graph.get('nodes', [])
        for node in nodes:
            if node.get('id') == node_id:
                return node
        return None
    
    def get_outgoing_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """Get all outgoing edges from a node."""
        edges = self.process_graph.get('edges', [])
        return [e for e in edges if e.get('source') == node_id]
    
    def __repr__(self):
        return f'<ProcessDefinition {self.name} v{self.version} ({self.status})>'


class ProcessInstance(TenantAwareMixin, AuditMixin, Model):
    """
    Process instance model for tracking running processes.
    
    Represents a specific execution of a process definition with
    context data, current state, and execution history.
    """
    
    __tablename__ = 'ab_process_instances'
    __table_args__ = (
        Index('ix_process_inst_tenant_status', 'tenant_id', 'status'),
        Index('ix_process_inst_definition', 'process_definition_id'),
        Index('ix_process_inst_current_step', 'current_step'),
        Index('ix_process_inst_started_at', 'started_at'),
        Index('ix_process_inst_priority', 'priority'),
    )
    
    id = Column(Integer, primary_key=True)
    process_definition_id = Column(Integer, ForeignKey('ab_process_definitions.id'), nullable=False)
    
    # Instance metadata
    name = Column(String(200))  # Optional custom name for this instance
    description = Column(Text)
    status = Column(String(20), default=ProcessInstanceStatus.RUNNING.value, nullable=False)
    current_step = Column(String(100))  # Current node ID
    
    # Context and data
    context = Column(JSONB, default=lambda: {})  # Process context data
    input_data = Column(JSONB, default=lambda: {})  # Initial input data
    output_data = Column(JSONB, default=lambda: {})  # Final output data
    variables = Column(JSONB, default=lambda: {})  # Process variables
    
    # Execution tracking
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    suspended_at = Column(DateTime)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    
    # Execution metadata
    initiated_by = Column(Integer, ForeignKey('ab_user.id'))  # User who started process
    priority = Column(Integer, default=5)  # Priority (1-10)
    max_duration = Column(Integer)  # Max duration in minutes
    
    # Error handling
    error_count = Column(Integer, default=0)
    last_error = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Parent/child process relationships
    parent_instance_id = Column(Integer, ForeignKey('ab_process_instances.id'))
    
    # Relationships
    definition = relationship("ProcessDefinition", back_populates="instances")
    steps = relationship("ProcessStep", back_populates="instance", cascade="all, delete-orphan")
    logs = relationship("ProcessLog", back_populates="instance", cascade="all, delete-orphan")
    approvals = relationship("ApprovalRequest", back_populates="process_instance")
    child_instances = relationship("ProcessInstance", remote_side=[id])
    metrics = relationship("ProcessMetric", back_populates="instance", cascade="all, delete-orphan")
    
    @hybrid_property
    def duration(self):
        """Calculate process duration."""
        if not self.started_at:
            return None
        
        end_time = self.completed_at if self.completed_at else datetime.utcnow()
        return (end_time - self.started_at).total_seconds()
    
    @hybrid_property
    def is_overdue(self):
        """Check if process is overdue."""
        if not self.max_duration or self.status in [ProcessInstanceStatus.COMPLETED.value, ProcessInstanceStatus.FAILED.value]:
            return False
        
        elapsed = (datetime.utcnow() - self.started_at).total_seconds() / 60
        return elapsed > self.max_duration
    
    @hybrid_property
    def progress_percentage(self):
        """Calculate progress percentage based on completed steps."""
        if not self.definition:
            return 0
        
        total_nodes = len(self.definition.process_graph.get('nodes', []))
        if total_nodes == 0:
            return 0
        
        completed_steps = sum(1 for step in self.steps if step.status == ProcessStepStatus.COMPLETED.value)
        return min(100, int((completed_steps / total_nodes) * 100))
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate process instance status."""
        valid_statuses = [s.value for s in ProcessInstanceStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of: {valid_statuses}")
        return status
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity_at = datetime.utcnow()
    
    def is_stuck(self, threshold_minutes: int = 60) -> bool:
        """Check if process appears stuck (no activity for threshold)."""
        if self.status in [ProcessInstanceStatus.COMPLETED.value, ProcessInstanceStatus.FAILED.value]:
            return False
        
        if not self.last_activity_at:
            return False
        
        elapsed = (datetime.utcnow() - self.last_activity_at).total_seconds() / 60
        return elapsed > threshold_minutes
    
    def __repr__(self):
        return f'<ProcessInstance {self.id} ({self.status}) - {self.name or "Unnamed"}>'


class ProcessStep(TenantAwareMixin, AuditMixin, Model):
    """
    Process step model for tracking individual step executions.
    
    Represents the execution state of a specific node within a
    process instance, including input/output data and timing.
    """
    
    __tablename__ = 'ab_process_steps'
    __table_args__ = (
        Index('ix_process_step_tenant_instance', 'tenant_id', 'process_instance_id'),
        Index('ix_process_step_node_id', 'node_id'),
        Index('ix_process_step_status', 'status'),
        Index('ix_process_step_started_at', 'started_at'),
        UniqueConstraint('process_instance_id', 'node_id', 'execution_order', 
                        name='uq_instance_node_execution'),
    )
    
    id = Column(Integer, primary_key=True)
    process_instance_id = Column(Integer, ForeignKey('ab_process_instances.id'), nullable=False)
    
    # Step identification
    node_id = Column(String(100), nullable=False)  # Node ID from process definition
    node_type = Column(String(50), nullable=False)  # Type of node (task, gateway, etc.)
    step_name = Column(String(200))  # Human-readable step name
    execution_order = Column(Integer, default=0)  # Order of execution
    
    # Execution state
    status = Column(String(20), default=ProcessStepStatus.PENDING.value, nullable=False)
    
    # Data
    input_data = Column(JSONB, default=lambda: {})
    output_data = Column(JSONB, default=lambda: {})
    configuration = Column(JSONB, default=lambda: {})  # Node configuration
    
    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    due_at = Column(DateTime)  # When step should be completed
    
    # Execution metadata
    assigned_to = Column(Integer, ForeignKey('ab_user.id'))  # User assigned to step
    executed_by = Column(Integer, ForeignKey('ab_user.id'))  # User who executed step
    retry_count = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text)
    error_details = Column(JSONB, default=lambda: {})
    
    # External references
    external_task_id = Column(String(100))  # Reference to external system task
    celery_task_id = Column(String(100))  # Celery task ID for async execution
    
    # Relationships
    instance = relationship("ProcessInstance", back_populates="steps")
    
    @hybrid_property
    def duration(self):
        """Calculate step duration."""
        if not self.started_at:
            return None
        
        end_time = self.completed_at if self.completed_at else datetime.utcnow()
        return (end_time - self.started_at).total_seconds()
    
    @hybrid_property
    def is_overdue(self):
        """Check if step is overdue."""
        if not self.due_at or self.status in [ProcessStepStatus.COMPLETED.value, ProcessStepStatus.FAILED.value]:
            return False
        
        return datetime.utcnow() > self.due_at
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate step status."""
        valid_statuses = [s.value for s in ProcessStepStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of: {valid_statuses}")
        return status
    
    @validates('node_type')
    def validate_node_type(self, key, node_type):
        """Validate node type."""
        valid_types = ['start', 'end', 'task', 'service', 'gateway', 'approval', 'notification', 'timer', 'script']
        if node_type not in valid_types:
            raise ValueError(f"Invalid node type: {node_type}. Must be one of: {valid_types}")
        return node_type
    
    def mark_started(self, executed_by: int = None):
        """Mark step as started."""
        self.status = ProcessStepStatus.RUNNING.value
        self.started_at = datetime.utcnow()
        if executed_by:
            self.executed_by = executed_by
    
    def mark_completed(self, output_data: Dict[str, Any] = None):
        """Mark step as completed."""
        self.status = ProcessStepStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()
        if output_data:
            self.output_data = output_data
    
    def mark_failed(self, error_message: str, error_details: Dict[str, Any] = None):
        """Mark step as failed."""
        self.status = ProcessStepStatus.FAILED.value
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        if error_details:
            self.error_details = error_details
    
    def __repr__(self):
        return f'<ProcessStep {self.node_id} ({self.status}) - {self.step_name or "Unnamed"}>'


class ProcessLog(TenantAwareMixin, AuditMixin, Model):
    """
    Process log model for detailed execution audit trail.
    
    Provides comprehensive logging of all process activities
    including step transitions, errors, and user actions.
    """
    
    __tablename__ = 'ab_process_logs'
    __table_args__ = (
        Index('ix_process_log_tenant_instance', 'tenant_id', 'process_instance_id'),
        Index('ix_process_log_timestamp', 'timestamp'),
        Index('ix_process_log_level', 'level'),
        Index('ix_process_log_event_type', 'event_type'),
    )
    
    id = Column(Integer, primary_key=True)
    process_instance_id = Column(Integer, ForeignKey('ab_process_instances.id'), nullable=False)
    process_step_id = Column(Integer, ForeignKey('ab_process_steps.id'))
    
    # Log entry details
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    level = Column(String(10), nullable=False)  # INFO, WARN, ERROR, DEBUG
    event_type = Column(String(50), nullable=False)  # step_started, step_completed, error, etc.
    message = Column(Text, nullable=False)
    
    # Context information
    user_id = Column(Integer, ForeignKey('ab_user.id'))
    node_id = Column(String(100))
    details = Column(JSONB, default=lambda: {})
    
    # Performance tracking
    execution_time = Column(Float)  # Execution time in seconds
    memory_usage = Column(Integer)  # Memory usage in bytes
    
    # Relationships
    instance = relationship("ProcessInstance", back_populates="logs")
    step = relationship("ProcessStep")
    
    @validates('level')
    def validate_level(self, key, level):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARN', 'ERROR']
        if level not in valid_levels:
            raise ValueError(f"Invalid log level: {level}. Must be one of: {valid_levels}")
        return level
    
    def __repr__(self):
        return f'<ProcessLog {self.event_type} ({self.level}) - {self.timestamp}>'


class ApprovalRequest(TenantAwareMixin, AuditMixin, Model):
    """
    Approval request model for managing approval workflows.
    
    Handles complex approval chains with escalation, delegation,
    and multi-level approval processes.
    """
    
    __tablename__ = 'ab_approval_requests'
    __table_args__ = (
        Index('ix_approval_tenant_status', 'tenant_id', 'status'),
        Index('ix_approval_approver', 'current_approver_id'),
        Index('ix_approval_due_at', 'due_at'),
        Index('ix_approval_process', 'process_instance_id'),
    )
    
    id = Column(Integer, primary_key=True)
    process_instance_id = Column(Integer, ForeignKey('ab_process_instances.id'), nullable=False)
    process_step_id = Column(Integer, ForeignKey('ab_process_steps.id'))
    
    # Approval metadata
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(20), default=ApprovalStatus.PENDING.value, nullable=False)
    priority = Column(Integer, default=5)  # Priority (1-10)
    
    # Approval chain configuration
    chain_definition = Column(JSONB, nullable=False)  # Complete approval chain
    current_level = Column(Integer, default=0)  # Current approval level
    current_approver_id = Column(Integer, ForeignKey('ab_user.id'))
    
    # Data
    request_data = Column(JSONB, default=lambda: {})  # Data to be approved
    form_schema = Column(JSONB, default=lambda: {})  # Form schema for approval
    attachments = Column(JSONB, default=lambda: [])  # File attachments
    
    # Timing
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_at = Column(DateTime)
    responded_at = Column(DateTime)
    escalated_at = Column(DateTime)
    
    # Response tracking
    responses = Column(JSONB, default=lambda: [])  # All approval responses
    final_response = Column(String(20))  # Final approval decision
    comments = Column(Text)
    
    # Escalation and delegation
    escalation_rules = Column(JSONB, default=lambda: {})
    delegation_history = Column(JSONB, default=lambda: [])
    
    # Relationships
    process_instance = relationship("ProcessInstance", back_populates="approvals")
    step = relationship("ProcessStep")
    
    @hybrid_property
    def is_overdue(self):
        """Check if approval is overdue."""
        if not self.due_at or self.status != ApprovalStatus.PENDING.value:
            return False
        return datetime.utcnow() > self.due_at
    
    @hybrid_property
    def days_pending(self):
        """Calculate days pending approval."""
        if self.status != ApprovalStatus.PENDING.value:
            return 0
        return (datetime.utcnow() - self.requested_at).days
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate approval status."""
        valid_statuses = [s.value for s in ApprovalStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of: {valid_statuses}")
        return status
    
    def get_current_approvers(self) -> List[int]:
        """Get list of current approvers."""
        if self.current_level >= len(self.chain_definition.get('levels', [])):
            return []
        
        current_level_config = self.chain_definition['levels'][self.current_level]
        return current_level_config.get('approvers', [])
    
    def can_approve(self, user_id: int) -> bool:
        """Check if user can approve this request."""
        return user_id in self.get_current_approvers()
    
    def add_response(self, approver_id: int, response: str, comments: str = None):
        """Add approval response."""
        response_data = {
            'level': self.current_level,
            'approver_id': approver_id,
            'response': response,
            'timestamp': datetime.utcnow().isoformat(),
            'comments': comments
        }
        
        if not isinstance(self.responses, list):
            self.responses = []
        
        self.responses.append(response_data)
        self.responded_at = datetime.utcnow()
    
    def __repr__(self):
        return f'<ApprovalRequest {self.title} ({self.status})>'


class SmartTrigger(TenantAwareMixin, AuditMixin, Model):
    """
    Smart trigger model for ML-powered process automation.
    
    Defines conditions and ML models for automatically triggering
    processes based on events and data patterns.
    """
    
    __tablename__ = 'ab_smart_triggers'
    __table_args__ = (
        Index('ix_trigger_tenant_status', 'tenant_id', 'status'),
        Index('ix_trigger_event_type', 'event_type'),
        Index('ix_trigger_priority', 'priority'),
        Index('ix_trigger_process', 'process_definition_id'),
    )
    
    id = Column(Integer, primary_key=True)
    process_definition_id = Column(Integer, ForeignKey('ab_process_definitions.id'))
    
    # Trigger metadata
    name = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(String(20), default=TriggerStatus.ACTIVE.value, nullable=False)
    priority = Column(Integer, default=5)  # Priority (1-10)
    
    # Trigger conditions
    event_type = Column(String(100), nullable=False)  # Type of event to monitor
    conditions = Column(JSONB, nullable=False)  # Trigger conditions
    ml_features = Column(JSONB, default=lambda: [])  # Features for ML model
    
    # ML configuration
    ml_model_path = Column(String(500))  # Path to ML model file
    ml_model_config = Column(JSONB, default=lambda: {})
    confidence_threshold = Column(Float, default=0.8)
    
    # Execution configuration
    action_config = Column(JSONB, nullable=False)  # Action to take when triggered
    cooldown_period = Column(Integer, default=0)  # Cooldown in seconds
    max_triggers_per_hour = Column(Integer, default=10)
    
    # Performance tracking
    trigger_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime)
    avg_confidence = Column(Float, default=0.0)
    
    # Relationships
    process_definition = relationship("ProcessDefinition", back_populates="triggers")
    
    @hybrid_property
    def success_rate(self):
        """Calculate trigger success rate."""
        if self.trigger_count == 0:
            return 0
        return (self.success_count / self.trigger_count) * 100
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate trigger status."""
        valid_statuses = [s.value for s in TriggerStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of: {valid_statuses}")
        return status
    
    @validates('confidence_threshold')
    def validate_confidence_threshold(self, key, threshold):
        """Validate confidence threshold."""
        if not 0 <= threshold <= 1:
            raise ValueError("Confidence threshold must be between 0 and 1")
        return threshold
    
    def is_in_cooldown(self) -> bool:
        """Check if trigger is in cooldown period."""
        if not self.last_triggered_at or self.cooldown_period == 0:
            return False
        
        elapsed = (datetime.utcnow() - self.last_triggered_at).total_seconds()
        return elapsed < self.cooldown_period
    
    def can_trigger(self) -> bool:
        """Check if trigger can fire (not in cooldown, under rate limit)."""
        if self.status != TriggerStatus.ACTIVE.value:
            return False
        
        if self.is_in_cooldown():
            return False
        
        # Check rate limit
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        # In a real implementation, you'd query a separate trigger_executions table
        
        return True
    
    def record_trigger(self, success: bool, confidence: float = None):
        """Record trigger execution."""
        self.trigger_count += 1
        if success:
            self.success_count += 1
        
        self.last_triggered_at = datetime.utcnow()
        
        if confidence is not None:
            # Update average confidence using exponential moving average
            alpha = 0.1  # Smoothing factor
            if self.avg_confidence == 0:
                self.avg_confidence = confidence
            else:
                self.avg_confidence = alpha * confidence + (1 - alpha) * self.avg_confidence
    
    def __repr__(self):
        return f'<SmartTrigger {self.name} ({self.status}) - {self.event_type}>'


class ProcessTemplate(TenantAwareMixin, AuditMixin, Model):
    """
    Process template model for reusable process patterns.
    
    Provides a library of common process templates that can be
    instantiated and customized for specific use cases.
    """
    
    __tablename__ = 'ab_process_templates'
    __table_args__ = (
        Index('ix_template_tenant_category', 'tenant_id', 'category'),
        Index('ix_template_public', 'is_public'),
        Index('ix_template_rating', 'rating'),
    )
    
    id = Column(Integer, primary_key=True)
    process_definition_id = Column(Integer, ForeignKey('ab_process_definitions.id'))
    
    # Template metadata
    name = Column(String(100), nullable=False)
    description = Column(Text)
    category = Column(String(50), index=True)
    tags = Column(JSONB, default=lambda: [])
    
    # Template configuration
    template_config = Column(JSONB, default=lambda: {})  # Customizable parameters
    default_values = Column(JSONB, default=lambda: {})  # Default parameter values
    required_fields = Column(JSONB, default=lambda: [])  # Required customizations
    
    # Visibility and sharing
    is_public = Column(Boolean, default=False)  # Available to all tenants
    is_featured = Column(Boolean, default=False)
    
    # Usage statistics
    usage_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    
    # Documentation
    documentation = Column(Text)  # Markdown documentation
    screenshot_url = Column(String(500))  # Template preview image
    
    # Relationships
    definition = relationship("ProcessDefinition", back_populates="templates")
    
    @hybrid_property
    def average_rating(self):
        """Calculate average rating."""
        return self.rating if self.rating_count > 0 else 0
    
    def add_rating(self, rating: float):
        """Add a new rating."""
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        # Update average using incremental formula
        self.rating = ((self.rating * self.rating_count) + rating) / (self.rating_count + 1)
        self.rating_count += 1
    
    def increment_usage(self):
        """Increment usage count."""
        self.usage_count += 1
    
    def __repr__(self):
        return f'<ProcessTemplate {self.name} ({self.category}) - {self.usage_count} uses>'


class ProcessMetric(TenantAwareMixin, AuditMixin, Model):
    """
    Process metric model for performance analytics.
    
    Stores aggregated metrics for process performance analysis,
    bottleneck identification, and optimization recommendations.
    """
    
    __tablename__ = 'ab_process_metrics'
    __table_args__ = (
        Index('ix_metric_tenant_process', 'tenant_id', 'process_definition_id'),
        Index('ix_metric_date', 'metric_date'),
        Index('ix_metric_type', 'metric_type'),
    )
    
    id = Column(Integer, primary_key=True)
    process_definition_id = Column(Integer, ForeignKey('ab_process_definitions.id'))
    process_instance_id = Column(Integer, ForeignKey('ab_process_instances.id'))
    
    # Metric metadata
    metric_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    metric_type = Column(String(50), nullable=False)  # duration, success_rate, step_time, etc.
    
    # Metric values
    value = Column(Float, nullable=False)
    count = Column(Integer, default=1)
    min_value = Column(Float)
    max_value = Column(Float)
    avg_value = Column(Float)
    
    # Context
    node_id = Column(String(100))  # Specific node if metric is node-specific
    context_data = Column(JSONB, default=lambda: {})  # Additional context
    
    # Relationships
    definition = relationship("ProcessDefinition")
    instance = relationship("ProcessInstance", back_populates="metrics")
    
    @validates('metric_type')
    def validate_metric_type(self, key, metric_type):
        """Validate metric type."""
        valid_types = [
            'duration', 'success_rate', 'error_rate', 'throughput',
            'step_duration', 'wait_time', 'approval_time', 'sla_compliance'
        ]
        if metric_type not in valid_types:
            log.warning(f"Unknown metric type: {metric_type}")
        return metric_type
    
    def __repr__(self):
        return f'<ProcessMetric {self.metric_type} = {self.value} ({self.metric_date})>'