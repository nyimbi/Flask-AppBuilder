"""
Process Management Views for Flask-AppBuilder.

Provides comprehensive web interface and REST APIs for business process
management including process definitions, instances, execution, and monitoring.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from flask import request, jsonify, flash, redirect, url_for, current_app, g
from flask_appbuilder import ModelView, expose, action, has_access
from flask_appbuilder.api import ModelRestApi, BaseApi
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.security.decorators import has_access_api, permission_name, protect
from flask_appbuilder.api import safe
from flask_appbuilder.const import API_RESULT_RES_KEY
from flask_babel import lazy_gettext
from flask_appbuilder.widgets import ListWidget, ShowWidget
from wtforms import StringField, TextAreaField, SelectField
from wtforms.validators import DataRequired, ValidationError
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields, post_load

from flask_appbuilder import db
from flask_appbuilder.models.tenant_context import get_current_tenant_id
from .models.process_models import (
    ProcessDefinition, ProcessInstance, ProcessStep, ProcessTemplate,
    ApprovalRequest, SmartTrigger, ProcessMetric, ProcessInstanceStatus,
    ProcessStepStatus, ApprovalStatus
)
from .engine.process_service import get_process_service
from .tasks import execute_node_async, retry_step_async
from .security.validation import ProcessValidator

log = logging.getLogger(__name__)


class ProcessDefinitionSchema(SQLAlchemyAutoSchema):
    """Schema for ProcessDefinition serialization."""
    
    class Meta:
        model = ProcessDefinition
        load_instance = True
        include_relationships = True
        
    process_graph = fields.Raw()
    variables = fields.Raw()
    configuration = fields.Raw()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ProcessInstanceSchema(SQLAlchemyAutoSchema):
    """Schema for ProcessInstance serialization."""
    
    class Meta:
        model = ProcessInstance
        load_instance = True
        include_relationships = True
        
    input_data = fields.Raw()
    output_data = fields.Raw()
    context_variables = fields.Raw()
    error_details = fields.Raw()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ProcessStepSchema(SQLAlchemyAutoSchema):
    """Schema for ProcessStep serialization."""
    
    class Meta:
        model = ProcessStep
        load_instance = True
        
    input_data = fields.Raw()
    output_data = fields.Raw()
    configuration = fields.Raw()
    error_details = fields.Raw()
    created_at = fields.DateTime(dump_only=True)


class ProcessDefinitionView(ModelView):
    """View for managing process definitions."""
    
    datamodel = SQLAInterface(ProcessDefinition)
    
    list_columns = [
        'name', 'version', 'category', 'status', 'created_by', 'created_at'
    ]
    
    show_columns = [
        'name', 'description', 'version', 'category', 'status',
        'process_graph', 'variables', 'configuration',
        'created_by', 'created_at', 'updated_at'
    ]
    
    edit_columns = [
        'name', 'description', 'version', 'category', 'status',
        'process_graph', 'variables', 'configuration'
    ]
    
    add_columns = edit_columns
    
    search_columns = ['name', 'description', 'category', 'created_by.username']
    
    base_permissions = ['can_list', 'can_show', 'can_add', 'can_edit', 'can_delete']
    
    @action('deploy', lazy_gettext('Deploy Process'), lazy_gettext('Deploy this process definition'), 'fa-rocket')
    @permission_name('can_deploy_process')
    @has_access
    def deploy_process(self, items):
        """Deploy selected process definitions."""
        if not items:
            flash(lazy_gettext('No processes selected'), 'warning')
            return redirect(self.get_redirect())
            
        deployed_count = 0
        errors = []
        
        try:
            for definition in items:
                try:
                    # Validate process definition before deployment
                    if definition.process_graph:
                        ProcessValidator.validate_process_definition({
                            'name': definition.name,
                            'definition': definition.process_graph,
                            'description': definition.description or ''
                        })
                    
                    if definition.status == 'draft':
                        definition.status = 'active'
                        definition.deployed_at = datetime.utcnow()
                        deployed_count += 1
                        
                except ValidationError as e:
                    errors.append(lazy_gettext('Validation failed for %(name)s: %(error)s', name=definition.name, error=str(e)))
                except Exception as e:
                    log.error(f'Error deploying process {definition.name}: {e}')
                    errors.append(lazy_gettext('Error deploying %(name)s: %(error)s', name=definition.name, error=str(e)))
            
            # Single commit at the end
            if deployed_count > 0:
                self.datamodel.session.commit()
                flash(lazy_gettext('Deployed %(count)d process definitions', count=deployed_count), 'success')
            else:
                flash(lazy_gettext('No processes were deployed (only draft processes can be deployed)'), 'warning')
            
            # Report errors after successful operations
            for error in errors:
                flash(error, 'error')
                
        except Exception as e:
            self.datamodel.session.rollback()
            flash(lazy_gettext('Failed to deploy processes: %(error)s', error=str(e)), 'error')
            
        return redirect(self.get_redirect())
    
    @action('archive', lazy_gettext('Archive Process'), lazy_gettext('Archive this process definition'), 'fa-archive')
    @permission_name('can_edit_process')
    @has_access
    def archive_process(self, items):
        """Archive selected process definitions."""
        if not items:
            flash(lazy_gettext('No processes selected'), 'warning')
            return redirect(self.get_redirect())
            
        archived_count = 0
        
        try:
            for definition in items:
                if definition.status in ['active', 'inactive']:
                    definition.status = 'archived'
                    archived_count += 1
            
            if archived_count > 0:
                self.datamodel.session.commit()
                flash(lazy_gettext('Archived %(count)d process definitions', count=archived_count), 'success')
            else:
                flash(lazy_gettext('No processes were archived'), 'warning')
                
        except Exception as e:
            self.datamodel.session.rollback()
            flash(lazy_gettext('Failed to archive processes: %(error)s', error=str(e)), 'error')
            
        return redirect(self.get_redirect())
    
    @expose('/designer/<int:definition_id>')
    @has_access
    def designer(self, definition_id):
        """Visual process designer interface."""
        definition = self.datamodel.get(definition_id)
        if not definition:
            flash(lazy_gettext('Process definition not found'), 'error')
            return redirect(self.get_redirect())
            
        return self.render_template(
            'process/designer.html',
            definition=definition,
            process_graph=json.dumps(definition.process_graph or {'nodes': [], 'edges': []})
        )


class ProcessInstanceView(ModelView):
    """View for managing process instances."""
    
    datamodel = SQLAInterface(ProcessInstance)
    
    list_columns = [
        'definition.name', 'status', 'initiated_by', 'progress_percentage',
        'started_at', 'last_activity_at'
    ]
    
    show_columns = [
        'definition', 'status', 'initiated_by', 'current_step',
        'progress_percentage', 'input_data', 'output_data',
        'context_variables', 'error_message', 'error_details',
        'started_at', 'completed_at', 'last_activity_at'
    ]
    
    search_columns = [
        'definition.name', 'status', 'initiated_by.username', 'current_step'
    ]
    
    base_permissions = ['can_list', 'can_show', 'can_delete']
    
    @action('suspend', lazy_gettext('Suspend Process'), lazy_gettext('Suspend running processes'), 'fa-pause')
    @permission_name('can_execute_process')
    @has_access
    def suspend_process(self, items):
        """Suspend selected running process instances."""
        if not items:
            flash(lazy_gettext('No processes selected'), 'warning')
            return redirect(self.get_redirect())
            
        suspended_count = 0
        
        try:
            for instance in items:
                if instance.status == ProcessInstanceStatus.RUNNING.value:
                    instance.status = ProcessInstanceStatus.SUSPENDED.value
                    instance.suspended_at = datetime.utcnow()
                    suspended_count += 1
            
            if suspended_count > 0:
                self.datamodel.session.commit()
                flash(lazy_gettext('Suspended %(count)d process instances', count=suspended_count), 'success')
            else:
                flash(lazy_gettext('No running processes found to suspend'), 'warning')
                
        except Exception as e:
            self.datamodel.session.rollback()
            flash(lazy_gettext('Failed to suspend processes: %(error)s', error=str(e)), 'error')
            
        return redirect(self.get_redirect())
    
    @action('resume', lazy_gettext('Resume Process'), lazy_gettext('Resume suspended processes'), 'fa-play')
    @permission_name('can_execute_process')
    @has_access
    def resume_process(self, items):
        """Resume selected suspended process instances."""
        if not items:
            flash(lazy_gettext('No processes selected'), 'warning')
            return redirect(self.get_redirect())
            
        resumed_count = 0
        errors = []
        process_service = get_process_service()
        
        try:
            for instance in items:
                if instance.status == ProcessInstanceStatus.SUSPENDED.value:
                    try:
                        # Resume process execution using sync service
                        if process_service.resume_process(instance.id):
                            resumed_count += 1
                        else:
                            errors.append(f'Failed to resume process {instance.id}')
                    except Exception as e:
                        log.error(f"Failed to resume process {instance.id}: {str(e)}")
                        errors.append(f'Failed to resume process {instance.id}: {str(e)}')
            
            if resumed_count > 0:
                flash(lazy_gettext('Resumed %(count)d process instances', count=resumed_count), 'success')
            
            for error in errors:
                flash(error, 'error')
                
        except Exception as e:
            flash(lazy_gettext('Failed to resume processes: %(error)s', error=str(e)), 'error')
            
        return redirect(self.get_redirect())
    
    @action('cancel', lazy_gettext('Cancel Process'), lazy_gettext('Cancel running/suspended processes'), 'fa-stop')
    @permission_name('can_execute_process')
    @has_access
    def cancel_process(self, items):
        """Cancel selected process instances."""
        if not items:
            flash(lazy_gettext('No processes selected'), 'warning')
            return redirect(self.get_redirect())
            
        cancelled_count = 0
        
        try:
            for instance in items:
                if instance.status in [ProcessInstanceStatus.RUNNING.value, 
                                     ProcessInstanceStatus.SUSPENDED.value]:
                    instance.status = ProcessInstanceStatus.CANCELLED.value
                    instance.completed_at = datetime.utcnow()
                    cancelled_count += 1
            
            if cancelled_count > 0:
                self.datamodel.session.commit()
                flash(lazy_gettext('Cancelled %(count)d process instances', count=cancelled_count), 'success')
            else:
                flash(lazy_gettext('No active processes found to cancel'), 'warning')
                
        except Exception as e:
            self.datamodel.session.rollback()
            flash(lazy_gettext('Failed to cancel processes: %(error)s', error=str(e)), 'error')
            
        return redirect(self.get_redirect())
    
    @expose('/monitor/<int:instance_id>')
    @permission_name('can_show')
    @has_access
    def monitor(self, instance_id):
        """Real-time process monitoring interface."""
        instance = self.datamodel.get(instance_id)
        if not instance:
            flash(lazy_gettext('Process instance not found'), 'error')
            return redirect(self.get_redirect())
            
        # Get process steps for timeline using datamodel for security
        step_view = ProcessStepView()
        steps = step_view.datamodel.get_related_obj(
            ProcessStep, 'instance_id', instance_id
        )
        
        return self.render_template(
            'process/monitor.html',
            instance=instance,
            steps=steps,
            definition=instance.definition
        )


class ProcessStepView(ModelView):
    """View for managing process steps."""
    
    datamodel = SQLAInterface(ProcessStep)
    
    list_columns = [
        'instance.definition.name', 'node_id', 'node_type', 'status',
        'started_at', 'completed_at'
    ]
    
    show_columns = [
        'instance', 'node_id', 'node_type', 'status',
        'input_data', 'output_data', 'configuration',
        'error_message', 'error_details', 'retry_count',
        'started_at', 'completed_at'
    ]
    
    search_columns = [
        'instance.definition.name', 'node_id', 'node_type', 'status'
    ]
    
    base_permissions = ['can_list', 'can_show']
    
    @action('retry', lazy_gettext('Retry Step'), lazy_gettext('Retry failed process steps'), 'fa-refresh')
    @permission_name('can_edit_process_step')
    @has_access
    def retry_step(self, items):
        """Retry selected failed process steps."""
        if not items:
            flash('No steps selected', 'warning')
            return redirect(self.get_redirect())
            
        retried_count = 0
        errors = []
        
        try:
            for step in items:
                if step.status == ProcessStepStatus.FAILED.value:
                    try:
                        # Trigger async retry
                        retry_step_async.delay(step.id)
                        retried_count += 1
                    except Exception as e:
                        log.error(f"Failed to retry step {step.id}: {str(e)}")
                        errors.append(f'Failed to retry step {step.id}: {str(e)}')
            
            if retried_count > 0:
                flash(lazy_gettext('Triggered retry for %(count)d failed steps', count=retried_count), 'success')
            else:
                flash(lazy_gettext('No failed steps found to retry'), 'warning')
            
            for error in errors:
                flash(error, 'error')
                
        except Exception as e:
            flash(lazy_gettext('Failed to retry steps: %(error)s', error=str(e)), 'error')
            
        return redirect(self.get_redirect())


class ApprovalRequestView(ModelView):
    """View for managing approval requests."""
    
    datamodel = SQLAInterface(ApprovalRequest)
    
    list_columns = [
        'step.instance.definition.name', 'approver', 'status',
        'requested_at', 'responded_at'
    ]
    
    show_columns = [
        'step', 'approver', 'status', 'priority',
        'approval_data', 'response_data', 'notes',
        'requested_at', 'responded_at', 'expires_at'
    ]
    
    search_columns = [
        'step.instance.definition.name', 'approver.username', 'status'
    ]
    
    base_permissions = ['can_list', 'can_show']
    
    @action('approve', lazy_gettext('Approve Request'), lazy_gettext('Approve selected requests'), 'fa-check')
    @permission_name('can_approve_process')
    @has_access
    def approve_request(self, items):
        """Approve selected approval requests."""
        if not items:
            flash('No requests selected', 'warning')
            return redirect(self.get_redirect())
            
        approved_count = 0
        errors = []
        process_service = get_process_service()
        
        try:
            for request in items:
                if request.status == ApprovalStatus.PENDING.value:
                    try:
                        request.status = ApprovalStatus.APPROVED.value
                        request.responded_at = datetime.utcnow()
                        request.response_data = {'approved_by': g.user.username if g.user else 'system'}
                        
                        # Continue process execution
                        step = request.step
                        step.mark_completed({'approval_result': 'approved'})
                        
                        # Continue process using sync service
                        process_service.continue_from_step(step.instance, step.node_id)
                        
                        approved_count += 1
                        
                    except Exception as e:
                        log.error(f"Failed to approve request {request.id}: {str(e)}")
                        errors.append(f'Failed to approve request {request.id}: {str(e)}')
            
            if approved_count > 0:
                self.datamodel.session.commit()
                flash(lazy_gettext('Approved %(count)d requests', count=approved_count), 'success')
            
            for error in errors:
                flash(error, 'error')
                
        except Exception as e:
            self.datamodel.session.rollback()
            flash(lazy_gettext('Failed to approve requests: %(error)s', error=str(e)), 'error')
            
        return redirect(self.get_redirect())


class ProcessApi(ModelRestApi):
    """REST API for process definitions."""
    
    resource_name = 'process'
    datamodel = SQLAInterface(ProcessDefinition)
    
    class_permission_name = 'ProcessDefinition'
    method_permission_name = {
        'get_list': 'can_list',
        'get': 'can_show',
        'post': 'can_add',
        'put': 'can_edit',
        'delete': 'can_delete'
    }
    
    list_columns = [
        'id', 'name', 'description', 'version', 'category', 'status',
        'created_by.username', 'created_at'
    ]
    
    show_columns = [
        'id', 'name', 'description', 'version', 'category', 'status',
        'process_graph', 'variables', 'configuration',
        'created_by.username', 'created_at', 'updated_at'
    ]
    
    add_columns = [
        'name', 'description', 'version', 'category',
        'process_graph', 'variables', 'configuration'
    ]
    
    edit_columns = add_columns
    
    @expose('/deploy/<int:definition_id>', methods=['POST'])
    @protect()
    @safe
    @has_access_api
    def deploy_definition(self, definition_id):
        """Deploy a process definition."""
        definition = self.datamodel.get(definition_id)
        if not definition:
            return self.response_404()
            
        if definition.status != 'draft':
            return self.response_400(message=lazy_gettext('Only draft processes can be deployed'))
        
        try:
            # Validate process definition before deployment
            if definition.process_graph:
                ProcessValidator.validate_process_definition({
                    'name': definition.name,
                    'definition': definition.process_graph,
                    'description': definition.description or ''
                })
            
            definition.status = 'active'
            definition.deployed_at = datetime.utcnow()
            self.datamodel.session.commit()
            
            return self.response(200, message='Process deployed successfully')
            
        except ValidationError as e:
            return self.response_400(message=f'Validation failed: {str(e)}')
        except Exception as e:
            log.error(f"Failed to deploy process: {str(e)}")
            self.datamodel.session.rollback()
            return self.response_400(message=f'Failed to deploy process: {str(e)}')
    
    @expose('/start/<int:definition_id>', methods=['POST'])
    @protect()
    @safe
    @has_access_api
    def start_process(self, definition_id):
        """Start a new process instance."""
        definition = self.datamodel.get(definition_id)
        if not definition:
            return self.response_404()
            
        if definition.status != 'active':
            return self.response_400(message=lazy_gettext('Process is not active'))
        
        # Validate request format
        if not request.is_json:
            return self.response_400(message=lazy_gettext('Request must be JSON'))
        
        try:
            data = request.get_json() or {}
            input_data = data.get('input_data', {})
        except Exception:
            return self.response_400(message=lazy_gettext('Invalid JSON format'))
            
        try:
            process_service = get_process_service()
            instance = process_service.start_process(
                definition_id=definition_id,
                input_data=input_data,
                initiated_by=g.user.id if g.user else None
            )
            
            return self.response(201, **{
                API_RESULT_RES_KEY: {
                    'instance_id': instance.id,
                    'status': instance.status
                },
                'message': lazy_gettext('Process started successfully')
            })
            
        except Exception as e:
            log.error(f"Failed to start process: {str(e)}")
            return self.response_400(message=lazy_gettext('Failed to start process: %(error)s', error=str(e)))


class ProcessInstanceApi(ModelRestApi):
    """REST API for process instances."""
    
    resource_name = 'process_instance'
    datamodel = SQLAInterface(ProcessInstance)
    
    class_permission_name = 'ProcessInstance'
    method_permission_name = {
        'get_list': 'can_list',
        'get': 'can_show',
        'delete': 'can_delete'
    }
    
    list_columns = [
        'id', 'definition.name', 'status', 'initiated_by.username',
        'progress_percentage', 'started_at', 'last_activity_at'
    ]
    
    show_columns = [
        'id', 'definition.name', 'status', 'initiated_by.username',
        'current_step', 'progress_percentage', 'input_data', 'output_data',
        'context_variables', 'error_message', 'error_details',
        'started_at', 'completed_at', 'last_activity_at'
    ]
    
    @expose('/suspend/<int:instance_id>', methods=['POST'])
    @protect()
    @safe
    @has_access_api
    def suspend_instance(self, instance_id):
        """Suspend a running process instance."""
        instance = self.datamodel.get(instance_id)
        if not instance:
            return self.response_404()
            
        if instance.status != ProcessInstanceStatus.RUNNING.value:
            return self.response_400(message='Process is not running')
            
        instance.status = ProcessInstanceStatus.SUSPENDED.value
        instance.suspended_at = datetime.utcnow()
        self.datamodel.session.commit()
        
        return self.response(200, message=lazy_gettext('Process suspended successfully'))
    
    @expose('/resume/<int:instance_id>', methods=['POST'])
    @protect()
    @safe
    @has_access_api
    def resume_instance(self, instance_id):
        """Resume a suspended process instance."""
        instance = self.datamodel.get(instance_id)
        if not instance:
            return self.response_404()
            
        if instance.status != ProcessInstanceStatus.SUSPENDED.value:
            return self.response_400(message='Process is not suspended')
            
        try:
            process_service = get_process_service()
            if process_service.resume_process(instance_id):
                return self.response(200, message=lazy_gettext('Process resumed successfully'))
            else:
                return self.response_400(message='Failed to resume process')
            
        except Exception as e:
            log.error(f"Failed to resume process: {str(e)}")
            return self.response_400(f'Failed to resume process: {str(e)}')
    
    @expose('/cancel/<int:instance_id>', methods=['POST'])
    @protect()
    @safe
    @has_access_api
    def cancel_instance(self, instance_id):
        """Cancel a process instance."""
        instance = self.datamodel.get(instance_id)
        if not instance:
            return self.response_404()
            
        if instance.status not in [ProcessInstanceStatus.RUNNING.value, 
                                 ProcessInstanceStatus.SUSPENDED.value]:
            return self.response_400(message='Process cannot be cancelled in current status')
            
        instance.status = ProcessInstanceStatus.CANCELLED.value
        instance.completed_at = datetime.utcnow()
        self.datamodel.session.commit()
        
        return self.response(200, message=lazy_gettext('Process cancelled successfully'))
    
    @expose('/steps/<int:instance_id>', methods=['GET'])
    @protect()
    @safe
    @has_access_api
    def get_instance_steps(self, instance_id):
        """Get all steps for a process instance."""
        instance = self.datamodel.get(instance_id)
        if not instance:
            return self.response_404()
            
        # Get process steps using datamodel for security consistency
        step_datamodel = SQLAInterface(ProcessStep)
        _, steps = step_datamodel.query(filters=[('instance_id', '==', instance_id)])
        
        step_data = []
        for step in steps:
            step_data.append({
                'id': step.id,
                'node_id': step.node_id,
                'node_type': step.node_type,
                'status': step.status,
                'started_at': step.started_at.isoformat() if step.started_at else None,
                'completed_at': step.completed_at.isoformat() if step.completed_at else None,
                'error_message': step.error_message,
                'retry_count': step.retry_count
            })
            
        return self.response(200, result=step_data)


class ProcessMetricsApi(BaseApi):
    """API for process analytics and metrics."""
    
    resource_name = 'process_metrics'
    
    @expose('/dashboard', methods=['GET'])
    @protect()
    @safe
    @has_access_api
    def get_dashboard_metrics(self):
        """Get metrics for process dashboard."""
        try:
            tenant_id = get_current_tenant_id()
            
            # Get counts using FAB datamodel for security and consistency
            definition_datamodel = SQLAInterface(ProcessDefinition)
            instance_datamodel = SQLAInterface(ProcessInstance)
            metric_datamodel = SQLAInterface(ProcessMetric)
            
            # Apply tenant filtering
            tenant_filter = [('tenant_id', '==', tenant_id)] if tenant_id else []
            
            total_definitions, _ = definition_datamodel.query(
                filters=tenant_filter,
                page_size=0  # Just get count
            )
            
            active_definitions, _ = definition_datamodel.query(
                filters=tenant_filter + [('status', '==', 'active')],
                page_size=0
            )
            
            running_instances, _ = instance_datamodel.query(
                filters=tenant_filter + [('status', '==', ProcessInstanceStatus.RUNNING.value)],
                page_size=0
            )
            
            today = datetime.utcnow().date()
            completed_today, _ = instance_datamodel.query(
                filters=tenant_filter + [
                    ('status', '==', ProcessInstanceStatus.COMPLETED.value),
                    ('completed_at', '>=', today)
                ],
                page_size=0
            )
            
            failed_today, _ = instance_datamodel.query(
                filters=tenant_filter + [
                    ('status', '==', ProcessInstanceStatus.FAILED.value),
                    ('completed_at', '>=', today)
                ],
                page_size=0
            )
            
            # Get recent metrics using datamodel
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            _, recent_metrics = metric_datamodel.query(
                filters=tenant_filter + [('metric_date', '>=', cutoff_date)]
            )
            
            metrics_data = {}
            for metric in recent_metrics:
                if metric.metric_type not in metrics_data:
                    metrics_data[metric.metric_type] = []
                metrics_data[metric.metric_type].append({
                    'date': metric.metric_date.isoformat(),
                    'value': float(metric.value)
                })
            
            return self.response(200, result={
                'summary': {
                    'total_definitions': total_definitions,
                    'active_definitions': active_definitions,
                    'running_instances': running_instances,
                    'completed_today': completed_today,
                    'failed_today': failed_today
                },
                'metrics': metrics_data
            })
            
        except Exception as e:
            log.error(f"Failed to get dashboard metrics: {str(e)}")
            return self.response_400(f'Failed to get metrics: {str(e)}')
    
    @expose('/performance/<int:definition_id>', methods=['GET'])
    @protect()
    @safe
    @has_access_api
    def get_process_performance(self, definition_id):
        """Get performance metrics for a specific process definition."""
        try:
            tenant_id = get_current_tenant_id()
            
            # Verify definition exists and belongs to tenant using datamodel
            definition_datamodel = SQLAInterface(ProcessDefinition)
            definition = definition_datamodel.get(definition_id)
            
            if not definition or (tenant_id and getattr(definition, 'tenant_id', None) != tenant_id):
                return self.response_404()
            
            # Get performance data for last 30 days using datamodel
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            instance_datamodel = SQLAInterface(ProcessInstance)
            
            filters = [
                ('definition_id', '==', definition_id),
                ('started_at', '>=', cutoff_date)
            ]
            if tenant_id:
                filters.append(('tenant_id', '==', tenant_id))
            
            _, instances = instance_datamodel.query(filters=filters)
            
            performance_data = {
                'total_instances': len(instances),
                'completed': len([i for i in instances if i.status == ProcessInstanceStatus.COMPLETED.value]),
                'failed': len([i for i in instances if i.status == ProcessInstanceStatus.FAILED.value]),
                'running': len([i for i in instances if i.status == ProcessInstanceStatus.RUNNING.value]),
                'average_duration': None,
                'success_rate': 0
            }
            
            # Calculate average duration for completed processes
            completed_instances = [i for i in instances 
                                 if i.status == ProcessInstanceStatus.COMPLETED.value and i.completed_at]
            
            if completed_instances:
                total_duration = sum(
                    (i.completed_at - i.started_at).total_seconds() 
                    for i in completed_instances
                )
                performance_data['average_duration'] = total_duration / len(completed_instances)
                
            # Calculate success rate
            if instances:
                performance_data['success_rate'] = performance_data['completed'] / len(instances) * 100
                
            return self.response(200, result=performance_data)
            
        except Exception as e:
            log.error(f"Failed to get process performance: {str(e)}")
            return self.response_400(f'Failed to get performance metrics: {str(e)}')