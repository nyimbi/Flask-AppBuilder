"""
Approval Chain Management System.

Provides sophisticated approval workflows with multi-level chains, delegation,
escalation, conditional routing, and parallel approval processing.
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from enum import Enum
from dataclasses import dataclass
import threading

from flask import current_app, g
from flask_appbuilder import db
from sqlalchemy import and_, or_, desc

from ..models.process_models import (
    ApprovalRequest, ApprovalChain, ApprovalRule, ProcessStep,
    ProcessInstance, ApprovalStatus, User
)
from ...tenants.context import TenantContext
from ..engine.process_engine import ProcessEngine

log = logging.getLogger(__name__)


class ApprovalType(Enum):
    """Types of approval processes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    UNANIMOUS = "unanimous"
    MAJORITY = "majority"
    FIRST_RESPONSE = "first_response"


class EscalationTrigger(Enum):
    """Triggers for approval escalation."""
    TIMEOUT = "timeout"
    REJECTION = "rejection"
    NO_RESPONSE = "no_response"
    MANUAL = "manual"


@dataclass
class ApprovalContext:
    """Context information for approval processing."""
    step_id: int
    instance_id: int
    request_data: Dict[str, Any]
    initiator_id: int
    priority: str = 'normal'
    due_date: Optional[datetime] = None
    metadata: Dict[str, Any] = None


@dataclass
class ApprovalDecision:
    """Represents an approval decision."""
    approved: bool
    approver_id: int
    comment: Optional[str] = None
    timestamp: datetime = None
    response_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ApprovalChainManager:
    """Manages approval chains and processes approval requests."""
    
    def __init__(self):
        self._lock = threading.RLock()
        self.rule_engine = ApprovalRuleEngine()
        self.escalation_manager = EscalationManager()
        self.notification_handler = None
        
    async def create_approval_chain(self, context: ApprovalContext, 
                                  chain_config: Dict[str, Any]) -> ApprovalChain:
        """Create a new approval chain based on configuration."""
        with self._lock:
            try:
                # Determine approvers based on rules and configuration
                approvers = await self._determine_approvers(context, chain_config)
                
                if not approvers:
                    raise ValueError("No approvers found for approval chain")
                
                # Create approval chain
                chain = ApprovalChain(
                    tenant_id=TenantContext.get_current_tenant_id(),
                    step_id=context.step_id,
                    chain_type=chain_config.get('type', ApprovalType.SEQUENTIAL.value),
                    approvers=json.dumps(approvers),
                    configuration=json.dumps(chain_config),
                    status=ApprovalStatus.PENDING.value,
                    created_by=context.initiator_id,
                    priority=context.priority,
                    due_date=context.due_date
                )
                
                db.session.add(chain)
                db.session.flush()
                
                # Create individual approval requests
                requests = await self._create_approval_requests(chain, context, approvers)
                
                db.session.commit()
                
                log.info(f"Created approval chain {chain.id} with {len(requests)} requests")
                return chain
                
            except Exception as e:
                db.session.rollback()
                log.error(f"Failed to create approval chain: {str(e)}")
                raise
    
    async def _determine_approvers(self, context: ApprovalContext, 
                                 config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Determine approvers based on configuration and rules."""
        approvers = []
        
        # Get explicit approvers from configuration
        if 'approvers' in config:
            for approver_config in config['approvers']:
                approver_info = await self._resolve_approver(approver_config, context)
                if approver_info:
                    approvers.append(approver_info)
        
        # Apply approval rules
        rule_based_approvers = await self.rule_engine.get_approvers_for_context(context)
        approvers.extend(rule_based_approvers)
        
        # Remove duplicates and sort by order/priority
        unique_approvers = {}
        for approver in approvers:
            user_id = approver.get('user_id')
            if user_id and user_id not in unique_approvers:
                unique_approvers[user_id] = approver
        
        # Sort by order if specified
        sorted_approvers = sorted(
            unique_approvers.values(),
            key=lambda x: x.get('order', 999)
        )
        
        return sorted_approvers
    
    async def _resolve_approver(self, approver_config: Dict[str, Any], 
                              context: ApprovalContext) -> Optional[Dict[str, Any]]:
        """Resolve approver configuration to actual user information."""
        try:
            approver_type = approver_config.get('type', 'user')
            
            if approver_type == 'user':
                user_id = approver_config.get('user_id')
                if user_id:
                    user = db.session.query(User).get(user_id)
                    if user and user.is_active:
                        return {
                            'user_id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'order': approver_config.get('order', 0),
                            'required': approver_config.get('required', True),
                            'delegate_allowed': approver_config.get('delegate_allowed', False)
                        }
            
            elif approver_type == 'role':
                role_name = approver_config.get('role')
                if role_name:
                    # Get users with the specified role
                    users = db.session.query(User).join(User.roles).filter(
                        User.roles.any(name=role_name),
                        User.is_active == True
                    ).all()
                    
                    # Return first available user or all users depending on configuration
                    if users:
                        selection_mode = approver_config.get('selection_mode', 'first')
                        if selection_mode == 'all':
                            return [
                                {
                                    'user_id': user.id,
                                    'username': user.username,
                                    'email': user.email,
                                    'order': approver_config.get('order', 0),
                                    'required': approver_config.get('required', True),
                                    'delegate_allowed': approver_config.get('delegate_allowed', False)
                                }
                                for user in users
                            ]
                        else:
                            user = users[0]  # First available
                            return {
                                'user_id': user.id,
                                'username': user.username,
                                'email': user.email,
                                'order': approver_config.get('order', 0),
                                'required': approver_config.get('required', True),
                                'delegate_allowed': approver_config.get('delegate_allowed', False)
                            }
            
            elif approver_type == 'dynamic':
                # Dynamic approver resolution based on process data
                expression = approver_config.get('expression')
                if expression:
                    # Evaluate expression to determine approver
                    # This would need a safe expression evaluator
                    resolved_user_id = await self._evaluate_dynamic_approver(expression, context)
                    if resolved_user_id:
                        user = db.session.query(User).get(resolved_user_id)
                        if user and user.is_active:
                            return {
                                'user_id': user.id,
                                'username': user.username,
                                'email': user.email,
                                'order': approver_config.get('order', 0),
                                'required': approver_config.get('required', True),
                                'delegate_allowed': approver_config.get('delegate_allowed', False)
                            }
            
            return None
            
        except Exception as e:
            log.error(f"Error resolving approver: {str(e)}")
            return None
    
    async def _evaluate_dynamic_approver(self, expression: str, 
                                       context: ApprovalContext) -> Optional[int]:
        """Safely evaluate dynamic approver expression."""
        try:
            # Get process instance data
            instance = db.session.query(ProcessInstance).get(context.instance_id)
            if not instance:
                return None
            
            # Simple expression evaluation (in production, use a safer evaluator)
            variables = {
                'input_data': instance.input_data or {},
                'context_variables': instance.context_variables or {},
                'initiator_id': context.initiator_id,
                'priority': context.priority
            }
            
            # For safety, only allow specific patterns
            if 'input_data.manager_id' in expression:
                manager_id = variables['input_data'].get('manager_id')
                if manager_id:
                    return int(manager_id)
            elif 'initiator_manager' in expression:
                # Get initiator's manager
                initiator = db.session.query(User).get(context.initiator_id)
                if initiator and hasattr(initiator, 'manager_id'):
                    return initiator.manager_id
            
            return None
            
        except Exception as e:
            log.error(f"Error evaluating dynamic approver expression: {str(e)}")
            return None
    
    async def _create_approval_requests(self, chain: ApprovalChain, 
                                      context: ApprovalContext,
                                      approvers: List[Dict[str, Any]]) -> List[ApprovalRequest]:
        """Create individual approval requests for the chain."""
        requests = []
        
        chain_type = chain.chain_type
        
        for i, approver in enumerate(approvers):
            # Determine if this request should be created immediately
            create_immediately = True
            
            if chain_type == ApprovalType.SEQUENTIAL.value:
                # Only create first request for sequential approval
                create_immediately = (i == 0)
            
            if create_immediately:
                request = ApprovalRequest(
                    tenant_id=chain.tenant_id,
                    chain_id=chain.id,
                    step_id=context.step_id,
                    approver_id=approver['user_id'],
                    status=ApprovalStatus.PENDING.value,
                    priority=context.priority,
                    approval_data=context.request_data,
                    order_index=i,
                    required=approver.get('required', True),
                    delegate_allowed=approver.get('delegate_allowed', False),
                    requested_at=datetime.utcnow(),
                    expires_at=context.due_date
                )
                
                db.session.add(request)
                requests.append(request)
                
                # Send notification
                await self._send_approval_notification(request, approver)
        
        return requests
    
    async def process_approval_decision(self, request_id: int, 
                                      decision: ApprovalDecision) -> Dict[str, Any]:
        """Process an approval decision and update chain status."""
        with self._lock:
            try:
                # Get approval request
                request = db.session.query(ApprovalRequest).get(request_id)
                if not request:
                    raise ValueError(f"Approval request {request_id} not found")
                
                if request.status != ApprovalStatus.PENDING.value:
                    raise ValueError(f"Request {request_id} is not pending")
                
                # Update request with decision
                request.status = ApprovalStatus.APPROVED.value if decision.approved else ApprovalStatus.REJECTED.value
                request.responded_at = decision.timestamp
                request.notes = decision.comment
                request.response_data = decision.response_data
                
                # Get the approval chain
                chain = db.session.query(ApprovalChain).get(request.chain_id)
                if not chain:
                    raise ValueError(f"Approval chain {request.chain_id} not found")
                
                # Process chain logic based on type
                chain_result = await self._process_chain_decision(chain, request, decision)
                
                db.session.commit()
                
                # If chain is complete, continue process execution
                if chain_result['chain_complete']:
                    await self._handle_chain_completion(chain, chain_result['approved'])
                
                log.info(f"Processed approval decision for request {request_id}: {decision.approved}")
                
                return chain_result
                
            except Exception as e:
                db.session.rollback()
                log.error(f"Failed to process approval decision: {str(e)}")
                raise
    
    async def _process_chain_decision(self, chain: ApprovalChain, 
                                    current_request: ApprovalRequest,
                                    decision: ApprovalDecision) -> Dict[str, Any]:
        """Process approval decision based on chain type."""
        chain_type = chain.chain_type
        
        # Get all requests in the chain
        all_requests = db.session.query(ApprovalRequest).filter_by(
            chain_id=chain.id
        ).order_by(ApprovalRequest.order_index).all()
        
        pending_requests = [r for r in all_requests if r.status == ApprovalStatus.PENDING.value]
        approved_requests = [r for r in all_requests if r.status == ApprovalStatus.APPROVED.value]
        rejected_requests = [r for r in all_requests if r.status == ApprovalStatus.REJECTED.value]
        
        chain_complete = False
        chain_approved = False
        next_actions = []
        
        if chain_type == ApprovalType.SEQUENTIAL.value:
            chain_complete, chain_approved, next_actions = await self._process_sequential_chain(
                chain, all_requests, current_request, decision
            )
        
        elif chain_type == ApprovalType.PARALLEL.value:
            chain_complete, chain_approved = await self._process_parallel_chain(
                chain, approved_requests, rejected_requests, pending_requests
            )
        
        elif chain_type == ApprovalType.UNANIMOUS.value:
            # All approvers must approve
            if not decision.approved:
                chain_complete = True
                chain_approved = False
            elif len(pending_requests) == 0:
                chain_complete = True
                chain_approved = len(rejected_requests) == 0
        
        elif chain_type == ApprovalType.MAJORITY.value:
            total_requests = len(all_requests)
            required_approvals = (total_requests // 2) + 1
            
            if len(approved_requests) >= required_approvals:
                chain_complete = True
                chain_approved = True
            elif len(rejected_requests) > (total_requests - required_approvals):
                chain_complete = True
                chain_approved = False
        
        elif chain_type == ApprovalType.FIRST_RESPONSE.value:
            # First response determines the outcome
            chain_complete = True
            chain_approved = decision.approved
            
            # Cancel remaining requests
            for req in pending_requests:
                if req.id != current_request.id:
                    req.status = ApprovalStatus.CANCELLED.value
                    next_actions.append(f"Cancelled request {req.id}")
        
        # Update chain status
        if chain_complete:
            chain.status = ApprovalStatus.APPROVED.value if chain_approved else ApprovalStatus.REJECTED.value
            chain.completed_at = datetime.utcnow()
        
        return {
            'chain_complete': chain_complete,
            'approved': chain_approved,
            'next_actions': next_actions,
            'pending_requests': len(pending_requests),
            'approved_requests': len(approved_requests),
            'rejected_requests': len(rejected_requests)
        }
    
    async def _process_sequential_chain(self, chain: ApprovalChain,
                                      all_requests: List[ApprovalRequest],
                                      current_request: ApprovalRequest,
                                      decision: ApprovalDecision) -> Tuple[bool, bool, List[str]]:
        """Process sequential approval chain logic."""
        next_actions = []
        
        if not decision.approved:
            # Rejection stops the chain
            return True, False, next_actions
        
        # Find next request in sequence
        current_index = current_request.order_index
        next_requests = [r for r in all_requests if r.order_index > current_index]
        
        if not next_requests:
            # This was the last request, chain is complete
            return True, True, next_actions
        
        # Activate next request(s)
        next_request = min(next_requests, key=lambda r: r.order_index)
        
        if next_request.status == ApprovalStatus.PENDING.value:
            # Already exists, just send notification
            approver = db.session.query(User).get(next_request.approver_id)
            if approver:
                await self._send_approval_notification(next_request, {
                    'user_id': approver.id,
                    'username': approver.username,
                    'email': approver.email
                })
                next_actions.append(f"Notified next approver: {approver.username}")
        else:
            # Create next request
            # This would happen if requests weren't pre-created
            pass
        
        return False, False, next_actions
    
    async def _process_parallel_chain(self, chain: ApprovalChain,
                                    approved_requests: List[ApprovalRequest],
                                    rejected_requests: List[ApprovalRequest],
                                    pending_requests: List[ApprovalRequest]) -> Tuple[bool, bool]:
        """Process parallel approval chain logic."""
        config = json.loads(chain.configuration) if chain.configuration else {}
        approval_threshold = config.get('approval_threshold', 1)  # Default: at least 1 approval
        
        # Check if we have enough approvals
        if len(approved_requests) >= approval_threshold:
            return True, True
        
        # Check if it's impossible to get enough approvals
        total_possible = len(approved_requests) + len(pending_requests)
        if total_possible < approval_threshold:
            return True, False
        
        # Chain continues
        return False, False
    
    async def _handle_chain_completion(self, chain: ApprovalChain, approved: bool):
        """Handle completion of an approval chain."""
        try:
            # Get the process step
            step = db.session.query(ProcessStep).get(chain.step_id)
            if not step:
                log.error(f"Process step {chain.step_id} not found")
                return
            
            # Update step with approval result
            step_output = {
                'approval_result': 'approved' if approved else 'rejected',
                'approval_chain_id': chain.id,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            if approved:
                step.mark_completed(step_output)
            else:
                step.mark_failed('Approval was rejected', step_output)
            
            db.session.commit()
            
            # Continue process execution
            engine = ProcessEngine()
            await engine.continue_from_step(step.instance, step.node_id)
            
            log.info(f"Approval chain {chain.id} completed: {approved}")
            
        except Exception as e:
            log.error(f"Error handling chain completion: {str(e)}")
    
    async def delegate_approval(self, request_id: int, delegate_to_id: int, 
                              delegated_by_id: int, reason: str = None) -> ApprovalRequest:
        """Delegate an approval request to another user."""
        with self._lock:
            try:
                # Get original request
                original_request = db.session.query(ApprovalRequest).get(request_id)
                if not original_request:
                    raise ValueError(f"Approval request {request_id} not found")
                
                if not original_request.delegate_allowed:
                    raise ValueError("Delegation is not allowed for this request")
                
                if original_request.status != ApprovalStatus.PENDING.value:
                    raise ValueError("Only pending requests can be delegated")
                
                # Verify delegate_to user exists
                delegate_user = db.session.query(User).get(delegate_to_id)
                if not delegate_user or not delegate_user.is_active:
                    raise ValueError(f"Delegate user {delegate_to_id} not found or inactive")
                
                # Update original request to delegated status
                original_request.status = ApprovalStatus.DELEGATED.value
                original_request.delegated_to_id = delegate_to_id
                original_request.delegated_by_id = delegated_by_id
                original_request.delegation_reason = reason
                original_request.delegated_at = datetime.utcnow()
                
                # Create new request for delegate
                delegated_request = ApprovalRequest(
                    tenant_id=original_request.tenant_id,
                    chain_id=original_request.chain_id,
                    step_id=original_request.step_id,
                    approver_id=delegate_to_id,
                    status=ApprovalStatus.PENDING.value,
                    priority=original_request.priority,
                    approval_data=original_request.approval_data,
                    order_index=original_request.order_index,
                    required=original_request.required,
                    delegate_allowed=original_request.delegate_allowed,
                    requested_at=datetime.utcnow(),
                    expires_at=original_request.expires_at,
                    original_request_id=original_request.id
                )
                
                db.session.add(delegated_request)
                db.session.commit()
                
                # Send notification to delegate
                await self._send_approval_notification(delegated_request, {
                    'user_id': delegate_user.id,
                    'username': delegate_user.username,
                    'email': delegate_user.email
                })
                
                log.info(f"Delegated approval request {request_id} to user {delegate_to_id}")
                
                return delegated_request
                
            except Exception as e:
                db.session.rollback()
                log.error(f"Failed to delegate approval: {str(e)}")
                raise
    
    async def escalate_approval(self, request_id: int, escalation_reason: EscalationTrigger,
                              escalate_to_id: int = None) -> ApprovalRequest:
        """Escalate an approval request to a higher authority."""
        with self._lock:
            try:
                # Get original request
                original_request = db.session.query(ApprovalRequest).get(request_id)
                if not original_request:
                    raise ValueError(f"Approval request {request_id} not found")
                
                # Determine escalation target
                if not escalate_to_id:
                    escalate_to_id = await self._determine_escalation_target(original_request)
                
                if not escalate_to_id:
                    raise ValueError("No escalation target found")
                
                # Verify escalation user exists
                escalation_user = db.session.query(User).get(escalate_to_id)
                if not escalation_user or not escalation_user.is_active:
                    raise ValueError(f"Escalation user {escalate_to_id} not found or inactive")
                
                # Update original request
                original_request.status = ApprovalStatus.ESCALATED.value
                original_request.escalated_to_id = escalate_to_id
                original_request.escalation_reason = escalation_reason.value
                original_request.escalated_at = datetime.utcnow()
                
                # Create escalated request
                escalated_request = ApprovalRequest(
                    tenant_id=original_request.tenant_id,
                    chain_id=original_request.chain_id,
                    step_id=original_request.step_id,
                    approver_id=escalate_to_id,
                    status=ApprovalStatus.PENDING.value,
                    priority='high',  # Escalated requests are high priority
                    approval_data=original_request.approval_data,
                    order_index=original_request.order_index,
                    required=True,  # Escalated requests are always required
                    delegate_allowed=True,
                    requested_at=datetime.utcnow(),
                    expires_at=original_request.expires_at,
                    original_request_id=original_request.id,
                    is_escalated=True
                )
                
                db.session.add(escalated_request)
                db.session.commit()
                
                # Send notification
                await self._send_approval_notification(escalated_request, {
                    'user_id': escalation_user.id,
                    'username': escalation_user.username,
                    'email': escalation_user.email
                })
                
                log.info(f"Escalated approval request {request_id} to user {escalate_to_id}")
                
                return escalated_request
                
            except Exception as e:
                db.session.rollback()
                log.error(f"Failed to escalate approval: {str(e)}")
                raise
    
    async def _determine_escalation_target(self, request: ApprovalRequest) -> Optional[int]:
        """Determine the appropriate escalation target for a request."""
        try:
            # Get current approver
            approver = db.session.query(User).get(request.approver_id)
            if not approver:
                return None
            
            # Try to get manager
            if hasattr(approver, 'manager_id') and approver.manager_id:
                return approver.manager_id
            
            # Try to get users with higher roles
            # This would need role hierarchy configuration
            
            # Fallback: get tenant admin
            tenant_id = TenantContext.get_current_tenant_id()
            admin_users = db.session.query(User).join(User.roles).filter(
                User.roles.any(name='Admin'),
                User.tenant_id == tenant_id,
                User.is_active == True,
                User.id != request.approver_id
            ).first()
            
            return admin_users.id if admin_users else None
            
        except Exception as e:
            log.error(f"Error determining escalation target: {str(e)}")
            return None
    
    async def _send_approval_notification(self, request: ApprovalRequest, 
                                        approver: Dict[str, Any]):
        """Send notification to approver about pending request."""
        try:
            if self.notification_handler:
                await self.notification_handler.send_approval_notification(request, approver)
            else:
                log.info(f"Would send approval notification to {approver['username']} for request {request.id}")
                
        except Exception as e:
            log.error(f"Failed to send approval notification: {str(e)}")
    
    def set_notification_handler(self, handler):
        """Set the notification handler for sending approval notifications."""
        self.notification_handler = handler
    
    async def get_pending_approvals(self, user_id: int) -> List[ApprovalRequest]:
        """Get pending approval requests for a specific user."""
        try:
            tenant_id = TenantContext.get_current_tenant_id()
            
            requests = db.session.query(ApprovalRequest).filter(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.approver_id == user_id,
                ApprovalRequest.status == ApprovalStatus.PENDING.value
            ).order_by(desc(ApprovalRequest.requested_at)).all()
            
            return requests
            
        except Exception as e:
            log.error(f"Error getting pending approvals: {str(e)}")
            return []
    
    async def get_approval_chain_status(self, chain_id: int) -> Dict[str, Any]:
        """Get detailed status of an approval chain."""
        try:
            chain = db.session.query(ApprovalChain).get(chain_id)
            if not chain:
                return {}
            
            requests = db.session.query(ApprovalRequest).filter_by(
                chain_id=chain_id
            ).order_by(ApprovalRequest.order_index).all()
            
            request_details = []
            for request in requests:
                approver = db.session.query(User).get(request.approver_id)
                request_details.append({
                    'id': request.id,
                    'approver': {
                        'id': approver.id if approver else None,
                        'username': approver.username if approver else 'Unknown',
                        'email': approver.email if approver else None
                    },
                    'status': request.status,
                    'requested_at': request.requested_at.isoformat() if request.requested_at else None,
                    'responded_at': request.responded_at.isoformat() if request.responded_at else None,
                    'notes': request.notes,
                    'required': request.required,
                    'order_index': request.order_index
                })
            
            return {
                'chain_id': chain.id,
                'chain_type': chain.chain_type,
                'status': chain.status,
                'priority': chain.priority,
                'created_at': chain.created_at.isoformat() if chain.created_at else None,
                'completed_at': chain.completed_at.isoformat() if chain.completed_at else None,
                'due_date': chain.due_date.isoformat() if chain.due_date else None,
                'requests': request_details
            }
            
        except Exception as e:
            log.error(f"Error getting chain status: {str(e)}")
            return {}


class ApprovalRuleEngine:
    """Engine for evaluating approval rules and determining approvers."""
    
    def __init__(self):
        self.rules_cache = {}
        self.cache_timeout = 300  # 5 minutes
    
    async def get_approvers_for_context(self, context: ApprovalContext) -> List[Dict[str, Any]]:
        """Get approvers based on approval rules for the given context."""
        try:
            tenant_id = TenantContext.get_current_tenant_id()
            
            # Get applicable rules
            rules = db.session.query(ApprovalRule).filter(
                ApprovalRule.tenant_id == tenant_id,
                ApprovalRule.is_active == True
            ).order_by(ApprovalRule.priority.desc()).all()
            
            approvers = []
            
            for rule in rules:
                if await self._evaluate_rule_conditions(rule, context):
                    rule_approvers = await self._get_rule_approvers(rule, context)
                    approvers.extend(rule_approvers)
                    
                    # If rule is exclusive, don't process more rules
                    rule_config = json.loads(rule.configuration) if rule.configuration else {}
                    if rule_config.get('exclusive', False):
                        break
            
            return approvers
            
        except Exception as e:
            log.error(f"Error getting rule-based approvers: {str(e)}")
            return []
    
    async def _evaluate_rule_conditions(self, rule: ApprovalRule, 
                                      context: ApprovalContext) -> bool:
        """Evaluate if rule conditions are met for the context."""
        try:
            rule_config = json.loads(rule.configuration) if rule.configuration else {}
            conditions = rule_config.get('conditions', [])
            
            if not conditions:
                return True  # No conditions means rule applies
            
            # Get process data for condition evaluation
            instance = db.session.query(ProcessInstance).get(context.instance_id)
            if not instance:
                return False
            
            evaluation_context = {
                'input_data': instance.input_data or {},
                'context_variables': instance.context_variables or {},
                'priority': context.priority,
                'initiator_id': context.initiator_id,
                'process_definition_id': instance.definition_id
            }
            
            # Evaluate each condition
            for condition in conditions:
                if not await self._evaluate_condition(condition, evaluation_context):
                    return False
            
            return True
            
        except Exception as e:
            log.error(f"Error evaluating rule conditions: {str(e)}")
            return False
    
    async def _evaluate_condition(self, condition: Dict[str, Any], 
                                context: Dict[str, Any]) -> bool:
        """Evaluate a single rule condition."""
        try:
            field = condition.get('field')
            operator = condition.get('operator', '==')
            value = condition.get('value')
            
            # Get field value from context
            field_value = self._get_field_value(field, context)
            
            # Compare values
            return self._compare_values(field_value, value, operator)
            
        except Exception as e:
            log.error(f"Error evaluating condition: {str(e)}")
            return False
    
    def _get_field_value(self, field_path: str, context: Dict[str, Any]) -> Any:
        """Get value from context using dot notation field path."""
        try:
            parts = field_path.split('.')
            value = context
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            
            return value
            
        except Exception as e:
            log.error(f"Error getting field value: {str(e)}")
            return None
    
    def _compare_values(self, value1: Any, value2: Any, operator: str) -> bool:
        """Compare two values using the specified operator."""
        try:
            if operator == '==':
                return value1 == value2
            elif operator == '!=':
                return value1 != value2
            elif operator == '>':
                return float(value1) > float(value2)
            elif operator == '<':
                return float(value1) < float(value2)
            elif operator == '>=':
                return float(value1) >= float(value2)
            elif operator == '<=':
                return float(value1) <= float(value2)
            elif operator == 'contains':
                return str(value2) in str(value1)
            elif operator == 'startswith':
                return str(value1).startswith(str(value2))
            elif operator == 'in':
                return value1 in value2 if isinstance(value2, list) else False
            
            return False
            
        except (ValueError, TypeError):
            return False
    
    async def _get_rule_approvers(self, rule: ApprovalRule, 
                                context: ApprovalContext) -> List[Dict[str, Any]]:
        """Get approvers defined by the rule."""
        try:
            rule_config = json.loads(rule.configuration) if rule.configuration else {}
            approver_configs = rule_config.get('approvers', [])
            
            approvers = []
            
            for approver_config in approver_configs:
                # Resolve approver similar to chain manager
                approver_info = await self._resolve_rule_approver(approver_config, context)
                if approver_info:
                    if isinstance(approver_info, list):
                        approvers.extend(approver_info)
                    else:
                        approvers.append(approver_info)
            
            return approvers
            
        except Exception as e:
            log.error(f"Error getting rule approvers: {str(e)}")
            return []
    
    async def _resolve_rule_approver(self, approver_config: Dict[str, Any],
                                   context: ApprovalContext) -> Optional[Dict[str, Any]]:
        """Resolve rule-based approver configuration."""
        # This would be similar to ApprovalChainManager._resolve_approver
        # but with rule-specific logic
        pass


class EscalationManager:
    """Manages approval escalations and timeouts."""
    
    def __init__(self):
        self.escalation_jobs = {}
    
    async def schedule_escalation(self, request_id: int, escalation_time: datetime):
        """Schedule automatic escalation for a request."""
        # In production, this would integrate with a job scheduler like Celery
        pass
    
    async def cancel_escalation(self, request_id: int):
        """Cancel scheduled escalation for a request."""
        pass
    
    async def check_expired_requests(self):
        """Check for and handle expired approval requests."""
        try:
            tenant_id = TenantContext.get_current_tenant_id()
            now = datetime.utcnow()
            
            expired_requests = db.session.query(ApprovalRequest).filter(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.status == ApprovalStatus.PENDING.value,
                ApprovalRequest.expires_at < now
            ).all()
            
            for request in expired_requests:
                await self._handle_expired_request(request)
                
        except Exception as e:
            log.error(f"Error checking expired requests: {str(e)}")
    
    async def _handle_expired_request(self, request: ApprovalRequest):
        """Handle an expired approval request."""
        try:
            # Get chain configuration to determine timeout behavior
            chain = db.session.query(ApprovalChain).get(request.chain_id)
            if not chain:
                return
            
            chain_config = json.loads(chain.configuration) if chain.configuration else {}
            timeout_action = chain_config.get('timeout_action', 'escalate')
            
            if timeout_action == 'escalate':
                # Auto-escalate the request
                chain_manager = ApprovalChainManager()
                await chain_manager.escalate_approval(
                    request.id, 
                    EscalationTrigger.TIMEOUT
                )
            elif timeout_action == 'reject':
                # Auto-reject the request
                decision = ApprovalDecision(
                    approved=False,
                    approver_id=0,  # System rejection
                    comment='Request timed out',
                    timestamp=datetime.utcnow()
                )
                
                chain_manager = ApprovalChainManager()
                await chain_manager.process_approval_decision(request.id, decision)
            elif timeout_action == 'approve':
                # Auto-approve the request
                decision = ApprovalDecision(
                    approved=True,
                    approver_id=0,  # System approval
                    comment='Request auto-approved due to timeout',
                    timestamp=datetime.utcnow()
                )
                
                chain_manager = ApprovalChainManager()
                await chain_manager.process_approval_decision(request.id, decision)
            
            log.info(f"Handled expired request {request.id} with action: {timeout_action}")
            
        except Exception as e:
            log.error(f"Error handling expired request: {str(e)}")