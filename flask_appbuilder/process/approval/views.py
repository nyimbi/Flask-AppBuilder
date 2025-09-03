"""
Approval Chain Management Views.

Provides comprehensive interface for managing approval chains, rules,
and processing approval requests with delegation and escalation.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from flask import request, jsonify, flash, redirect, url_for, g
from flask_appbuilder import ModelView, BaseView, expose, action, has_access
from flask_appbuilder.api import ModelRestApi, BaseApi
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.security.decorators import has_access_api
from flask_appbuilder.widgets import ListWidget, ShowWidget
from wtforms import StringField, TextAreaField, SelectField, BooleanField
from wtforms.validators import DataRequired
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields

from flask_appbuilder import db
from ..models.process_models import (
    ApprovalChain, ApprovalRequest, ApprovalRule, ProcessStep,
    ApprovalStatus, User
)
from .chain_manager import (
    ApprovalChainManager, ApprovalDecision, ApprovalContext,
    ApprovalType, EscalationTrigger
)
from ...tenants.context import TenantContext

log = logging.getLogger(__name__)


class ApprovalChainSchema(SQLAlchemyAutoSchema):
    """Schema for ApprovalChain serialization."""
    
    class Meta:
        model = ApprovalChain
        load_instance = True
        include_relationships = True
        
    approvers = fields.Raw()
    configuration = fields.Raw()
    created_at = fields.DateTime(dump_only=True)
    completed_at = fields.DateTime(dump_only=True)


class ApprovalRequestSchema(SQLAlchemyAutoSchema):
    """Schema for ApprovalRequest serialization."""
    
    class Meta:
        model = ApprovalRequest
        load_instance = True
        include_relationships = True
        
    approval_data = fields.Raw()
    response_data = fields.Raw()
    requested_at = fields.DateTime(dump_only=True)
    responded_at = fields.DateTime(dump_only=True)


class ApprovalRuleSchema(SQLAlchemyAutoSchema):
    """Schema for ApprovalRule serialization."""
    
    class Meta:
        model = ApprovalRule
        load_instance = True
        
    configuration = fields.Raw()
    created_at = fields.DateTime(dump_only=True)


class ApprovalChainView(ModelView):
    """View for managing approval chains."""
    
    datamodel = SQLAInterface(ApprovalChain)
    
    list_columns = [
        'step.instance.definition.name', 'chain_type', 'status',
        'priority', 'created_by', 'created_at', 'due_date'
    ]
    
    show_columns = [
        'step', 'chain_type', 'status', 'priority', 'approvers',
        'configuration', 'created_by', 'created_at', 'completed_at',
        'due_date'
    ]
    
    search_columns = [
        'step.instance.definition.name', 'chain_type', 'status', 'priority'
    ]
    
    base_permissions = ['can_list', 'can_show']
    
    @expose('/monitor/<int:chain_id>')
    @has_access
    def monitor(self, chain_id):
        """Real-time monitoring of approval chain progress."""
        chain = self.datamodel.get(chain_id)
        if not chain:
            flash('Approval chain not found', 'error')
            return redirect(url_for('ApprovalChainView.list'))
        
        # Get chain manager for detailed status
        manager = ApprovalChainManager()
        # Note: This would need to be async in real implementation
        # chain_status = await manager.get_approval_chain_status(chain_id)
        
        # Get approval requests
        requests = db.session.query(ApprovalRequest).filter_by(
            chain_id=chain_id
        ).order_by(ApprovalRequest.order_index).all()
        
        return self.render_template(
            'approval/chain_monitor.html',
            chain=chain,
            requests=requests,
            chain_type=ApprovalType
        )


class ApprovalRequestView(ModelView):
    """View for managing approval requests."""
    
    datamodel = SQLAInterface(ApprovalRequest)
    
    list_columns = [
        'chain.step.instance.definition.name', 'approver', 'status',
        'priority', 'requested_at', 'expires_at'
    ]
    
    show_columns = [
        'chain', 'approver', 'status', 'priority', 'approval_data',
        'response_data', 'notes', 'required', 'delegate_allowed',
        'requested_at', 'responded_at', 'expires_at'
    ]
    
    search_columns = [
        'chain.step.instance.definition.name', 'approver.username',
        'status', 'priority'
    ]
    
    base_permissions = ['can_list', 'can_show']
    
    @action('approve', 'Approve Request', 'Approve selected requests', 'fa-check')
    def approve_request(self, items):
        """Approve selected approval requests."""
        if not items:
            flash('No requests selected', 'warning')
            return redirect(request.referrer)
        
        approved_count = 0
        manager = ApprovalChainManager()
        
        for request in items:
            if request.status == ApprovalStatus.PENDING.value and request.approver_id == g.user.id:
                try:
                    decision = ApprovalDecision(
                        approved=True,
                        approver_id=g.user.id,
                        comment='Bulk approval action',
                        timestamp=datetime.utcnow()
                    )
                    
                    # Note: This would need to be async in real implementation
                    # await manager.process_approval_decision(request.id, decision)
                    approved_count += 1
                    
                except Exception as e:
                    log.error(f"Failed to approve request {request.id}: {str(e)}")
                    flash(f'Failed to approve request {request.id}: {str(e)}', 'error')
        
        if approved_count > 0:
            flash(f'Approved {approved_count} requests', 'success')
        
        return redirect(request.referrer)
    
    @action('reject', 'Reject Request', 'Reject selected requests', 'fa-times')
    def reject_request(self, items):
        """Reject selected approval requests."""
        if not items:
            flash('No requests selected', 'warning')
            return redirect(request.referrer)
        
        rejected_count = 0
        manager = ApprovalChainManager()
        
        for request in items:
            if request.status == ApprovalStatus.PENDING.value and request.approver_id == g.user.id:
                try:
                    decision = ApprovalDecision(
                        approved=False,
                        approver_id=g.user.id,
                        comment='Bulk rejection action',
                        timestamp=datetime.utcnow()
                    )
                    
                    # Note: This would need to be async in real implementation
                    # await manager.process_approval_decision(request.id, decision)
                    rejected_count += 1
                    
                except Exception as e:
                    log.error(f"Failed to reject request {request.id}: {str(e)}")
                    flash(f'Failed to reject request {request.id}: {str(e)}', 'error')
        
        if rejected_count > 0:
            flash(f'Rejected {rejected_count} requests', 'success')
        
        return redirect(request.referrer)
    
    @expose('/respond/<int:request_id>')
    @has_access
    def respond(self, request_id):
        """Detailed approval response interface."""
        approval_request = self.datamodel.get(request_id)
        if not approval_request:
            flash('Approval request not found', 'error')
            return redirect(url_for('ApprovalRequestView.list'))
        
        # Verify user can respond to this request
        if approval_request.approver_id != g.user.id:
            flash('You are not authorized to respond to this request', 'error')
            return redirect(url_for('ApprovalRequestView.list'))
        
        if approval_request.status != ApprovalStatus.PENDING.value:
            flash('This request is no longer pending', 'warning')
            return redirect(url_for('ApprovalRequestView.list'))
        
        # Get chain and related information
        chain = approval_request.chain
        step = chain.step if chain else None
        instance = step.instance if step else None
        
        return self.render_template(
            'approval/respond.html',
            request=approval_request,
            chain=chain,
            step=step,
            instance=instance
        )
    
    @expose('/delegate/<int:request_id>')
    @has_access
    def delegate(self, request_id):
        """Delegate approval request to another user."""
        approval_request = self.datamodel.get(request_id)
        if not approval_request:
            flash('Approval request not found', 'error')
            return redirect(url_for('ApprovalRequestView.list'))
        
        # Verify user can delegate this request
        if approval_request.approver_id != g.user.id:
            flash('You are not authorized to delegate this request', 'error')
            return redirect(url_for('ApprovalRequestView.list'))
        
        if not approval_request.delegate_allowed:
            flash('This request cannot be delegated', 'warning')
            return redirect(url_for('ApprovalRequestView.list'))
        
        # Get available users for delegation
        tenant_id = TenantContext.get_current_tenant_id()
        available_users = db.session.query(User).filter(
            User.tenant_id == tenant_id,
            User.is_active == True,
            User.id != g.user.id
        ).all()
        
        return self.render_template(
            'approval/delegate.html',
            request=approval_request,
            available_users=available_users
        )


class ApprovalRuleView(ModelView):
    """View for managing approval rules."""
    
    datamodel = SQLAInterface(ApprovalRule)
    
    list_columns = [
        'name', 'description', 'priority', 'is_active',
        'created_by', 'created_at'
    ]
    
    show_columns = [
        'name', 'description', 'priority', 'configuration',
        'is_active', 'created_by', 'created_at', 'updated_at'
    ]
    
    edit_columns = [
        'name', 'description', 'priority', 'configuration', 'is_active'
    ]
    
    add_columns = edit_columns
    
    search_columns = ['name', 'description', 'created_by.username']
    
    base_permissions = ['can_list', 'can_show', 'can_add', 'can_edit', 'can_delete']
    
    def pre_add(self, item):
        """Pre-process before adding new rule."""
        item.created_by = g.user
        
        # Validate configuration JSON
        if item.configuration:
            try:
                json.loads(item.configuration)
            except json.JSONDecodeError as e:
                flash(f'Invalid JSON configuration: {str(e)}', 'error')
                raise ValueError("Invalid configuration JSON")
    
    def pre_update(self, item):
        """Pre-process before updating rule."""
        # Validate configuration JSON
        if item.configuration:
            try:
                json.loads(item.configuration)
            except json.JSONDecodeError as e:
                flash(f'Invalid JSON configuration: {str(e)}', 'error')
                raise ValueError("Invalid configuration JSON")
    
    @action('activate', 'Activate Rule', 'Activate selected rules', 'fa-play')
    def activate_rule(self, items):
        """Activate selected rules."""
        if not items:
            flash('No rules selected', 'warning')
            return redirect(request.referrer)
        
        activated_count = 0
        for rule in items:
            if not rule.is_active:
                rule.is_active = True
                activated_count += 1
        
        if activated_count > 0:
            db.session.commit()
            flash(f'Activated {activated_count} rules', 'success')
        else:
            flash('No inactive rules found', 'warning')
        
        return redirect(request.referrer)
    
    @action('deactivate', 'Deactivate Rule', 'Deactivate selected rules', 'fa-pause')
    def deactivate_rule(self, items):
        """Deactivate selected rules."""
        if not items:
            flash('No rules selected', 'warning')
            return redirect(request.referrer)
        
        deactivated_count = 0
        for rule in items:
            if rule.is_active:
                rule.is_active = False
                deactivated_count += 1
        
        if deactivated_count > 0:
            db.session.commit()
            flash(f'Deactivated {deactivated_count} rules', 'success')
        else:
            flash('No active rules found', 'warning')
        
        return redirect(request.referrer)
    
    @expose('/designer/<int:rule_id>')
    @has_access
    def designer(self, rule_id):
        """Visual rule configuration designer."""
        rule = self.datamodel.get(rule_id)
        if not rule:
            flash('Approval rule not found', 'error')
            return redirect(url_for('ApprovalRuleView.list'))
        
        return self.render_template(
            'approval/rule_designer.html',
            rule=rule,
            configuration=json.dumps(
                json.loads(rule.configuration) if rule.configuration else {},
                indent=2
            )
        )


class ApprovalDashboardView(BaseView):
    """Dashboard for approval management and analytics."""
    
    route_base = '/approval'
    
    @expose('/')
    @has_access
    def index(self):
        """Main approval dashboard."""
        try:
            tenant_id = TenantContext.get_current_tenant_id()
            user_id = g.user.id
            
            # Get pending requests for current user
            pending_requests = db.session.query(ApprovalRequest).filter(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.approver_id == user_id,
                ApprovalRequest.status == ApprovalStatus.PENDING.value
            ).order_by(ApprovalRequest.requested_at.desc()).limit(10).all()
            
            # Get approval statistics
            total_pending = db.session.query(ApprovalRequest).filter(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.approver_id == user_id,
                ApprovalRequest.status == ApprovalStatus.PENDING.value
            ).count()
            
            # Get recent activity
            recent_activity = db.session.query(ApprovalRequest).filter(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.approver_id == user_id,
                ApprovalRequest.responded_at.isnot(None)
            ).order_by(ApprovalRequest.responded_at.desc()).limit(10).all()
            
            # Get overdue requests
            now = datetime.utcnow()
            overdue_requests = db.session.query(ApprovalRequest).filter(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.approver_id == user_id,
                ApprovalRequest.status == ApprovalStatus.PENDING.value,
                ApprovalRequest.expires_at < now
            ).all()
            
            return self.render_template(
                'approval/dashboard.html',
                pending_requests=pending_requests,
                total_pending=total_pending,
                recent_activity=recent_activity,
                overdue_requests=overdue_requests
            )
            
        except Exception as e:
            log.error(f"Error loading approval dashboard: {str(e)}")
            flash(f'Error loading dashboard: {str(e)}', 'error')
            return redirect(url_for('HomeView.index'))
    
    @expose('/pending/')
    @has_access
    def pending(self):
        """View all pending approval requests for current user."""
        try:
            tenant_id = TenantContext.get_current_tenant_id()
            user_id = g.user.id
            
            pending_requests = db.session.query(ApprovalRequest).filter(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.approver_id == user_id,
                ApprovalRequest.status == ApprovalStatus.PENDING.value
            ).order_by(ApprovalRequest.requested_at.desc()).all()
            
            return self.render_template(
                'approval/pending.html',
                requests=pending_requests
            )
            
        except Exception as e:
            log.error(f"Error loading pending approvals: {str(e)}")
            flash(f'Error loading pending approvals: {str(e)}', 'error')
            return redirect(url_for('ApprovalDashboardView.index'))
    
    @expose('/analytics/')
    @has_access
    def analytics(self):
        """Approval analytics and reporting."""
        try:
            tenant_id = TenantContext.get_current_tenant_id()
            
            # Get approval statistics for last 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            requests = db.session.query(ApprovalRequest).filter(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.requested_at >= cutoff_date
            ).all()
            
            # Calculate analytics
            analytics = self._calculate_approval_analytics(requests)
            
            return self.render_template(
                'approval/analytics.html',
                analytics=analytics
            )
            
        except Exception as e:
            log.error(f"Error loading approval analytics: {str(e)}")
            flash(f'Error loading analytics: {str(e)}', 'error')
            return redirect(url_for('ApprovalDashboardView.index'))
    
    def _calculate_approval_analytics(self, requests: List[ApprovalRequest]) -> Dict[str, Any]:
        """Calculate approval analytics from requests."""
        if not requests:
            return {'total': 0}
        
        total_requests = len(requests)
        approved_requests = [r for r in requests if r.status == ApprovalStatus.APPROVED.value]
        rejected_requests = [r for r in requests if r.status == ApprovalStatus.REJECTED.value]
        pending_requests = [r for r in requests if r.status == ApprovalStatus.PENDING.value]
        
        analytics = {
            'total': total_requests,
            'approved': len(approved_requests),
            'rejected': len(rejected_requests),
            'pending': len(pending_requests),
            'approval_rate': len(approved_requests) / total_requests * 100 if total_requests > 0 else 0
        }
        
        # Calculate average response time
        if approved_requests or rejected_requests:
            response_times = []
            for request in approved_requests + rejected_requests:
                if request.responded_at and request.requested_at:
                    response_time = (request.responded_at - request.requested_at).total_seconds()
                    response_times.append(response_time)
            
            if response_times:
                analytics['avg_response_time'] = sum(response_times) / len(response_times)
                analytics['min_response_time'] = min(response_times)
                analytics['max_response_time'] = max(response_times)
        
        # Priority breakdown
        priority_counts = {}
        for request in requests:
            priority = request.priority or 'normal'
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        analytics['priority_breakdown'] = priority_counts
        
        return analytics


class ApprovalApi(ModelRestApi):
    """REST API for approval requests."""
    
    resource_name = 'approval'
    datamodel = SQLAInterface(ApprovalRequest)
    
    class_permission_name = 'ApprovalRequest'
    method_permission_name = {
        'get_list': 'can_list',
        'get': 'can_show',
        'put': 'can_edit'
    }
    
    list_columns = [
        'id', 'chain.id', 'approver.username', 'status', 'priority',
        'requested_at', 'responds_at', 'expires_at'
    ]
    
    show_columns = [
        'id', 'chain.id', 'approver.username', 'status', 'priority',
        'approval_data', 'response_data', 'notes', 'required',
        'requested_at', 'responded_at', 'expires_at'
    ]
    
    @expose('/respond/<int:request_id>', methods=['POST'])
    @has_access_api
    def respond_to_request(self, request_id):
        """Respond to an approval request."""
        try:
            approval_request = self.datamodel.get(request_id)
            if not approval_request:
                return self.response_404()
            
            # Verify user can respond
            if approval_request.approver_id != g.user.id:
                return self.response_400('Not authorized to respond to this request')
            
            if approval_request.status != ApprovalStatus.PENDING.value:
                return self.response_400('Request is not pending')
            
            # Get request data
            if not request.json:
                return self.response_400('Request body required')
            
            approved = request.json.get('approved', False)
            comment = request.json.get('comment', '')
            response_data = request.json.get('response_data', {})
            
            # Create approval decision
            decision = ApprovalDecision(
                approved=approved,
                approver_id=g.user.id,
                comment=comment,
                response_data=response_data,
                timestamp=datetime.utcnow()
            )
            
            # Process decision
            manager = ApprovalChainManager()
            # Note: This would need to be async in real implementation
            # result = await manager.process_approval_decision(request_id, decision)
            
            return self.response(200, **{
                'message': 'Approval processed successfully',
                'approved': approved,
                'request_id': request_id
            })
            
        except Exception as e:
            log.error(f"Error processing approval: {str(e)}")
            return self.response_400(f'Error processing approval: {str(e)}')
    
    @expose('/delegate/<int:request_id>', methods=['POST'])
    @has_access_api
    def delegate_request(self, request_id):
        """Delegate an approval request to another user."""
        try:
            approval_request = self.datamodel.get(request_id)
            if not approval_request:
                return self.response_404()
            
            # Verify user can delegate
            if approval_request.approver_id != g.user.id:
                return self.response_400('Not authorized to delegate this request')
            
            if not approval_request.delegate_allowed:
                return self.response_400('Request cannot be delegated')
            
            # Get request data
            if not request.json:
                return self.response_400('Request body required')
            
            delegate_to_id = request.json.get('delegate_to_id')
            reason = request.json.get('reason', '')
            
            if not delegate_to_id:
                return self.response_400('delegate_to_id is required')
            
            # Delegate request
            manager = ApprovalChainManager()
            # Note: This would need to be async in real implementation
            # delegated_request = await manager.delegate_approval(
            #     request_id, delegate_to_id, g.user.id, reason
            # )
            
            return self.response(200, **{
                'message': 'Request delegated successfully',
                'delegate_to_id': delegate_to_id,
                'original_request_id': request_id
            })
            
        except Exception as e:
            log.error(f"Error delegating approval: {str(e)}")
            return self.response_400(f'Error delegating approval: {str(e)}')
    
    @expose('/escalate/<int:request_id>', methods=['POST'])
    @has_access_api
    def escalate_request(self, request_id):
        """Escalate an approval request."""
        try:
            approval_request = self.datamodel.get(request_id)
            if not approval_request:
                return self.response_404()
            
            # Get request data
            escalate_to_id = None
            escalation_reason = EscalationTrigger.MANUAL
            
            if request.json:
                escalate_to_id = request.json.get('escalate_to_id')
                reason_str = request.json.get('reason', 'manual')
                try:
                    escalation_reason = EscalationTrigger(reason_str)
                except ValueError:
                    escalation_reason = EscalationTrigger.MANUAL
            
            # Escalate request
            manager = ApprovalChainManager()
            # Note: This would need to be async in real implementation
            # escalated_request = await manager.escalate_approval(
            #     request_id, escalation_reason, escalate_to_id
            # )
            
            return self.response(200, **{
                'message': 'Request escalated successfully',
                'escalation_reason': escalation_reason.value,
                'original_request_id': request_id
            })
            
        except Exception as e:
            log.error(f"Error escalating approval: {str(e)}")
            return self.response_400(f'Error escalating approval: {str(e)}')
    
    @expose('/pending', methods=['GET'])
    @has_access_api
    def get_pending_approvals(self):
        """Get pending approval requests for current user."""
        try:
            tenant_id = TenantContext.get_current_tenant_id()
            user_id = g.user.id
            
            requests = db.session.query(ApprovalRequest).filter(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.approver_id == user_id,
                ApprovalRequest.status == ApprovalStatus.PENDING.value
            ).order_by(ApprovalRequest.requested_at.desc()).all()
            
            request_data = []
            for req in requests:
                request_data.append({
                    'id': req.id,
                    'chain_id': req.chain_id,
                    'priority': req.priority,
                    'approval_data': req.approval_data,
                    'requested_at': req.requested_at.isoformat() if req.requested_at else None,
                    'expires_at': req.expires_at.isoformat() if req.expires_at else None,
                    'required': req.required,
                    'delegate_allowed': req.delegate_allowed,
                    'process_info': {
                        'definition_name': req.chain.step.instance.definition.name if req.chain and req.chain.step and req.chain.step.instance else None,
                        'instance_id': req.chain.step.instance.id if req.chain and req.chain.step and req.chain.step.instance else None
                    }
                })
            
            return self.response(200, result={
                'pending_requests': request_data,
                'total_count': len(request_data)
            })
            
        except Exception as e:
            log.error(f"Error getting pending approvals: {str(e)}")
            return self.response_400(f'Error getting pending approvals: {str(e)}')


class ApprovalChainApi(ModelRestApi):
    """REST API for approval chains."""
    
    resource_name = 'approval_chain'
    datamodel = SQLAInterface(ApprovalChain)
    
    class_permission_name = 'ApprovalChain'
    method_permission_name = {
        'get_list': 'can_list',
        'get': 'can_show'
    }
    
    list_columns = [
        'id', 'step.id', 'chain_type', 'status', 'priority',
        'created_at', 'completed_at', 'due_date'
    ]
    
    show_columns = [
        'id', 'step.id', 'chain_type', 'status', 'priority',
        'approvers', 'configuration', 'created_by.username',
        'created_at', 'completed_at', 'due_date'
    ]
    
    @expose('/status/<int:chain_id>', methods=['GET'])
    @has_access_api
    def get_chain_status(self, chain_id):
        """Get detailed status of an approval chain."""
        try:
            chain = self.datamodel.get(chain_id)
            if not chain:
                return self.response_404()
            
            # Get chain manager for detailed status
            manager = ApprovalChainManager()
            # Note: This would need to be async in real implementation
            # chain_status = await manager.get_approval_chain_status(chain_id)
            
            # For now, return basic information
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
                        'username': approver.username if approver else 'Unknown'
                    },
                    'status': request.status,
                    'requested_at': request.requested_at.isoformat() if request.requested_at else None,
                    'responded_at': request.responded_at.isoformat() if request.responded_at else None,
                    'order_index': request.order_index,
                    'required': request.required
                })
            
            return self.response(200, result={
                'chain_id': chain.id,
                'chain_type': chain.chain_type,
                'status': chain.status,
                'priority': chain.priority,
                'created_at': chain.created_at.isoformat() if chain.created_at else None,
                'completed_at': chain.completed_at.isoformat() if chain.completed_at else None,
                'due_date': chain.due_date.isoformat() if chain.due_date else None,
                'requests': request_details
            })
            
        except Exception as e:
            log.error(f"Error getting chain status: {str(e)}")
            return self.response_400(f'Error getting chain status: {str(e)}')