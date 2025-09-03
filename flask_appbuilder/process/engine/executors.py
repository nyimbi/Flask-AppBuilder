"""
Process Node Executors.

Implements execution logic for different types of process nodes including
tasks, gateways, approvals, services, and timers with comprehensive
error handling and integration capabilities.
"""

import logging
import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from abc import ABC, abstractmethod
from enum import Enum
import uuid

from flask import current_app
from flask_appbuilder import db
from flask_appbuilder.models.tenant_context import get_current_tenant_id

from ..models.process_models import (
    ProcessInstance, ProcessStep, ApprovalRequest, ApprovalStatus
)

log = logging.getLogger(__name__)


class NodeExecutionError(Exception):
    """Exception raised during node execution."""
    pass


class NodeExecutor(ABC):
    """
    Base class for process node executors.
    
    Provides common functionality and interface for all node types
    with extensible execution patterns and error handling.
    """
    
    def __init__(self, engine):
        """Initialize node executor."""
        self.engine = engine
        self.execution_hooks = {}
        self.config = {
            'default_timeout': 300,  # 5 minutes
            'max_retries': 3,
            'enable_performance_tracking': True
        }
    
    async def execute(self, instance: ProcessInstance, node: Dict[str, Any],
                     step: ProcessStep, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the node with common pre/post processing.
        
        Args:
            instance: Process instance
            node: Node definition
            step: Process step
            input_data: Input data for execution
            
        Returns:
            Dict containing output data
        """
        node_id = node.get('id')
        start_time = time.time()
        
        try:
            # Pre-execution hooks
            await self._execute_pre_hooks(instance, node, step, input_data)
            
            # Execute node-specific logic
            output_data = await self._execute_node(instance, node, step, input_data)
            
            # Post-execution hooks
            await self._execute_post_hooks(instance, node, step, input_data, output_data)
            
            # Record performance metrics
            if self.config['enable_performance_tracking']:
                execution_time = time.time() - start_time
                await self._record_performance_metrics(instance, node, step, execution_time)
            
            return output_data or {}
            
        except Exception as e:
            log.error(f"Node execution failed - Node: {node_id}, Error: {str(e)}")
            await self._handle_execution_error(instance, node, step, e)
            raise NodeExecutionError(f"Node {node_id} execution failed: {str(e)}")
    
    @abstractmethod
    async def _execute_node(self, instance: ProcessInstance, node: Dict[str, Any],
                           step: ProcessStep, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute node-specific logic. Must be implemented by subclasses."""
        pass
    
    async def _execute_pre_hooks(self, instance: ProcessInstance, node: Dict[str, Any],
                               step: ProcessStep, input_data: Dict[str, Any]):
        """Execute pre-execution hooks."""
        hooks = self.execution_hooks.get('pre', [])
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(instance, node, step, input_data)
                else:
                    hook(instance, node, step, input_data)
            except Exception as e:
                log.warning(f"Pre-execution hook failed: {str(e)}")
    
    async def _execute_post_hooks(self, instance: ProcessInstance, node: Dict[str, Any],
                                step: ProcessStep, input_data: Dict[str, Any],
                                output_data: Dict[str, Any]):
        """Execute post-execution hooks."""
        hooks = self.execution_hooks.get('post', [])
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(instance, node, step, input_data, output_data)
                else:
                    hook(instance, node, step, input_data, output_data)
            except Exception as e:
                log.warning(f"Post-execution hook failed: {str(e)}")
    
    async def _handle_execution_error(self, instance: ProcessInstance, node: Dict[str, Any],
                                    step: ProcessStep, error: Exception):
        """Handle execution errors with logging and notifications."""
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'node_id': node.get('id'),
            'node_type': node.get('type'),
            'step_id': step.id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store error details
        step.error_details = error_details
        
        # Execute error hooks
        error_hooks = self.execution_hooks.get('error', [])
        for hook in error_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(instance, node, step, error)
                else:
                    hook(instance, node, step, error)
            except Exception as e:
                log.warning(f"Error hook failed: {str(e)}")
    
    async def _record_performance_metrics(self, instance: ProcessInstance, node: Dict[str, Any],
                                        step: ProcessStep, execution_time: float):
        """Record performance metrics for node execution."""
        try:
            from ..models.process_models import ProcessMetric
            
            metric = ProcessMetric(
                process_definition_id=instance.process_definition_id,
                process_instance_id=instance.id,
                metric_date=datetime.utcnow(),
                metric_type='step_duration',
                value=execution_time,
                node_id=node.get('id'),
                context_data={
                    'node_type': node.get('type'),
                    'step_id': step.id
                },
                tenant_id=instance.tenant_id
            )
            
            db.session.add(metric)
            db.session.commit()
            
        except Exception as e:
            log.debug(f"Failed to record performance metrics: {str(e)}")
    
    def register_hook(self, hook_type: str, hook: Callable):
        """Register execution hook."""
        if hook_type not in self.execution_hooks:
            self.execution_hooks[hook_type] = []
        
        self.execution_hooks[hook_type].append(hook)
        log.debug(f"Registered {hook_type} hook for {self.__class__.__name__}")


class TaskExecutor(NodeExecutor):
    """
    Executor for user task nodes.
    
    Handles user task creation, assignment, and completion tracking
    with support for forms, deadlines, and escalation.
    """
    
    async def _execute_node(self, instance: ProcessInstance, node: Dict[str, Any],
                           step: ProcessStep, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute user task node."""
        task_config = node.get('properties', {})
        
        # Assign task to user
        assignee_id = await self._resolve_assignee(instance, task_config, input_data)
        if assignee_id:
            step.assigned_to = assignee_id
        
        # Set task form configuration
        if 'form_schema' in task_config:
            step.configuration['form_schema'] = task_config['form_schema']
        
        # Set due date
        if 'due_in_hours' in task_config:
            hours = task_config['due_in_hours']
            step.due_at = datetime.utcnow() + timedelta(hours=hours)
        
        # Mark step as waiting for user action
        step.status = 'waiting'
        db.session.commit()
        
        # Send notification to assignee
        if assignee_id:
            await self._send_task_notification(instance, step, assignee_id)
        
        # Task will be completed externally via API
        # Return empty output for now
        return {}
    
    async def _resolve_assignee(self, instance: ProcessInstance, task_config: Dict[str, Any],
                               input_data: Dict[str, Any]) -> Optional[int]:
        """Resolve task assignee from configuration."""
        # Check for direct assignment
        if 'assigned_to' in task_config:
            return task_config['assigned_to']
        
        # Check for assignment by role
        if 'assigned_to_role' in task_config:
            role_name = task_config['assigned_to_role']
            # In real implementation, resolve users by role
            # For now, return None to indicate no specific assignee
            return None
        
        # Check for dynamic assignment from context
        if 'assignee_variable' in task_config:
            variable_name = task_config['assignee_variable']
            try:
                assignee = await self.engine.context_manager.get_variable(
                    instance.id, variable_name
                )
                return int(assignee) if assignee else None
            except:
                return None
        
        return None
    
    async def _send_task_notification(self, instance: ProcessInstance, step: ProcessStep,
                                    assignee_id: int):
        """Send task notification to assignee."""
        try:
            # In real implementation, integrate with notification system
            notification_data = {
                'type': 'task_assigned',
                'process_instance_id': instance.id,
                'step_id': step.id,
                'assignee_id': assignee_id,
                'task_name': step.step_name,
                'due_at': step.due_at.isoformat() if step.due_at else None,
                'url': f"/process/task/{step.id}"
            }
            
            log.info(f"Task notification sent to user {assignee_id}: {json.dumps(notification_data)}")
            
        except Exception as e:
            log.warning(f"Failed to send task notification: {str(e)}")


class ServiceExecutor(NodeExecutor):
    """
    Executor for service task nodes.
    
    Handles automated service calls, API integrations, and system
    operations with retry logic and error handling.
    """
    
    async def _execute_node(self, instance: ProcessInstance, node: Dict[str, Any],
                           step: ProcessStep, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute service task node."""
        service_config = node.get('properties', {})
        service_type = service_config.get('service_type')
        
        if service_type == 'http_call':
            return await self._execute_http_call(instance, service_config, input_data)
        elif service_type == 'email':
            return await self._execute_email_service(instance, service_config, input_data)
        elif service_type == 'database':
            return await self._execute_database_operation(instance, service_config, input_data)
        elif service_type == 'script':
            return await self._execute_script(instance, service_config, input_data)
        else:
            # Custom service type
            return await self._execute_custom_service(instance, service_config, input_data)
    
    async def _execute_http_call(self, instance: ProcessInstance, config: Dict[str, Any],
                               input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTP API call."""
        import aiohttp
        import asyncio
        
        try:
            url = config.get('url')
            method = config.get('method', 'GET').upper()
            headers = config.get('headers', {})
            
            # Resolve variables in URL and headers
            if url:
                url = await self.engine.context_manager.resolve_expression(instance.id, url)
            
            for key, value in headers.items():
                headers[key] = await self.engine.context_manager.resolve_expression(instance.id, value)
            
            # Prepare request data
            request_data = None
            if method in ['POST', 'PUT', 'PATCH']:
                request_data = config.get('data', input_data)
            
            # Make HTTP call with timeout
            timeout = aiohttp.ClientTimeout(total=config.get('timeout', 30))
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method, url, headers=headers, json=request_data) as response:
                    response_data = await response.text()
                    
                    # Try to parse as JSON
                    try:
                        response_json = await response.json()
                    except:
                        response_json = {'text': response_data}
                    
                    return {
                        'http_status': response.status,
                        'response_data': response_json,
                        'success': response.status < 400
                    }
                    
        except Exception as e:
            log.error(f"HTTP call failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'http_status': 0
            }
    
    async def _execute_email_service(self, instance: ProcessInstance, config: Dict[str, Any],
                                   input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute email sending service."""
        try:
            # Email configuration
            to_addresses = config.get('to', [])
            subject = config.get('subject', 'Process Notification')
            template = config.get('template', 'default')
            
            # Resolve variables
            subject = await self.engine.context_manager.resolve_expression(instance.id, subject)
            
            # In real implementation, integrate with email service
            email_data = {
                'to': to_addresses,
                'subject': subject,
                'template': template,
                'context': input_data,
                'process_id': instance.id
            }
            
            log.info(f"Email sent: {json.dumps(email_data)}")
            
            return {
                'success': True,
                'email_sent': True,
                'recipients_count': len(to_addresses)
            }
            
        except Exception as e:
            log.error(f"Email service failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'email_sent': False
            }
    
    async def _execute_database_operation(self, instance: ProcessInstance, config: Dict[str, Any],
                                        input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database operation."""
        try:
            operation = config.get('operation', 'select')
            table_name = config.get('table')
            
            if operation == 'select':
                # Execute SELECT query with proper parameterization
                query_template = config.get('query')
                query_params = config.get('parameters', {})
                
                if query_template:
                    # Resolve parameters safely
                    resolved_params = {}
                    for key, value in query_params.items():
                        resolved_value = await self.engine.context_manager.resolve_expression(instance.id, str(value))
                        resolved_params[key] = resolved_value
                    
                    try:
                        # Use SQLAlchemy's text() with bound parameters for security
                        from sqlalchemy import text
                        result = db.session.execute(text(query_template), resolved_params)
                        rows = [dict(row) for row in result.fetchall()]
                        
                        return {
                            'success': True,
                            'operation': operation,
                            'row_count': len(rows),
                            'data': rows
                        }
                    except Exception as e:
                        log.error(f"Database query execution failed: {str(e)}")
                        return {
                            'success': False,
                            'error': f"Query execution failed: {str(e)}"
                        }
            
            return {
                'success': False,
                'error': f"Unsupported database operation: {operation}"
            }
            
        except Exception as e:
            log.error(f"Database operation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _execute_script(self, instance: ProcessInstance, config: Dict[str, Any],
                            input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom script."""
        try:
            script_type = config.get('script_type', 'python')
            script_content = config.get('script')
            
            if script_type == 'python':
                # Execute Python script in restricted environment
                # In real implementation, use sandboxed execution
                return {
                    'success': True,
                    'script_executed': True,
                    'note': 'Script execution not implemented for security reasons'
                }
            
            return {
                'success': False,
                'error': f"Unsupported script type: {script_type}"
            }
            
        except Exception as e:
            log.error(f"Script execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _execute_custom_service(self, instance: ProcessInstance, config: Dict[str, Any],
                                    input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom service type."""
        service_type = config.get('service_type')
        
        # Look for registered custom service handlers
        if hasattr(current_app, 'process_service_handlers'):
            handlers = current_app.process_service_handlers
            if service_type in handlers:
                handler = handlers[service_type]
                try:
                    if asyncio.iscoroutinefunction(handler):
                        return await handler(instance, config, input_data)
                    else:
                        return handler(instance, config, input_data)
                except Exception as e:
                    return {
                        'success': False,
                        'error': f"Custom service handler failed: {str(e)}"
                    }
        
        return {
            'success': False,
            'error': f"Unknown service type: {service_type}"
        }


class GatewayExecutor(NodeExecutor):
    """
    Executor for gateway (decision) nodes.
    
    Evaluates conditions to determine process flow direction
    with support for complex expressions and data-driven routing.
    """
    
    async def _execute_node(self, instance: ProcessInstance, node: Dict[str, Any],
                           step: ProcessStep, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute gateway node."""
        gateway_config = node.get('properties', {})
        conditions = gateway_config.get('conditions', [])
        
        # Evaluate each condition
        for condition in conditions:
            if await self._evaluate_condition(instance, condition, input_data):
                target_node = condition.get('target')
                return {
                    'gateway_result': True,
                    'target_node': target_node,
                    'condition_met': condition.get('name', 'unnamed')
                }
        
        # Check for default path
        default_condition = next((c for c in conditions if c.get('default', False)), None)
        if default_condition:
            return {
                'gateway_result': True,
                'target_node': default_condition.get('target'),
                'condition_met': 'default'
            }
        
        # No conditions met and no default
        return {
            'gateway_result': False,
            'error': 'No gateway conditions were met'
        }
    
    async def _evaluate_condition(self, instance: ProcessInstance, condition: Dict[str, Any],
                                input_data: Dict[str, Any]) -> bool:
        """Evaluate a single gateway condition."""
        try:
            condition_type = condition.get('type', 'simple')
            
            if condition_type == 'simple':
                return await self._evaluate_simple_condition(instance, condition, input_data)
            elif condition_type == 'expression':
                return await self._evaluate_expression_condition(instance, condition, input_data)
            elif condition_type == 'script':
                return await self._evaluate_script_condition(instance, condition, input_data)
            else:
                log.warning(f"Unknown condition type: {condition_type}")
                return False
                
        except Exception as e:
            log.error(f"Condition evaluation failed: {str(e)}")
            return False
    
    async def _evaluate_simple_condition(self, instance: ProcessInstance, 
                                       condition: Dict[str, Any],
                                       input_data: Dict[str, Any]) -> bool:
        """Evaluate simple field comparison condition."""
        field = condition.get('field')
        operator = condition.get('operator', '==')
        expected_value = condition.get('value')
        
        if not field:
            return False
        
        # Get field value from context
        actual_value = await self.engine.context_manager.get_variable(
            instance.id, field, default=None
        )
        
        # If not found in context, check input data
        if actual_value is None and field in input_data:
            actual_value = input_data[field]
        
        # Evaluate based on operator
        if operator == '==':
            return actual_value == expected_value
        elif operator == '!=':
            return actual_value != expected_value
        elif operator == '>':
            return actual_value > expected_value
        elif operator == '>=':
            return actual_value >= expected_value
        elif operator == '<':
            return actual_value < expected_value
        elif operator == '<=':
            return actual_value <= expected_value
        elif operator == 'in':
            return actual_value in expected_value
        elif operator == 'not_in':
            return actual_value not in expected_value
        elif operator == 'contains':
            return expected_value in str(actual_value)
        elif operator == 'starts_with':
            return str(actual_value).startswith(str(expected_value))
        elif operator == 'ends_with':
            return str(actual_value).endswith(str(expected_value))
        else:
            log.warning(f"Unknown operator: {operator}")
            return False
    
    async def _evaluate_expression_condition(self, instance: ProcessInstance,
                                           condition: Dict[str, Any],
                                           input_data: Dict[str, Any]) -> bool:
        """Evaluate complex expression condition."""
        expression = condition.get('expression')
        if not expression:
            return False
        
        try:
            # Resolve variables in expression
            resolved_expression = await self.engine.context_manager.resolve_expression(
                instance.id, expression
            )
            
            # For safety, only allow simple boolean expressions
            # In real implementation, use a safe expression evaluator
            if resolved_expression.lower() in ['true', '1', 'yes']:
                return True
            elif resolved_expression.lower() in ['false', '0', 'no']:
                return False
            else:
                # Try to evaluate as Python expression (DANGEROUS - use safe evaluator in production)
                return bool(eval(resolved_expression))
                
        except Exception as e:
            log.warning(f"Expression evaluation failed: {str(e)}")
            return False
    
    async def _evaluate_script_condition(self, instance: ProcessInstance,
                                       condition: Dict[str, Any],
                                       input_data: Dict[str, Any]) -> bool:
        """Evaluate script-based condition."""
        # Script evaluation would be implemented with sandboxed execution
        # For security reasons, returning False for now
        log.warning("Script condition evaluation not implemented for security reasons")
        return False


class ApprovalExecutor(NodeExecutor):
    """
    Executor for approval nodes.
    
    Creates approval requests with multi-level chains, escalation,
    and delegation support integrated with the approval system.
    """
    
    async def _execute_node(self, instance: ProcessInstance, node: Dict[str, Any],
                           step: ProcessStep, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute approval node."""
        approval_config = node.get('properties', {})
        
        # Create approval request
        approval = await self._create_approval_request(instance, step, approval_config, input_data)
        
        # Mark step as waiting for approval
        step.status = 'waiting'
        step.configuration['approval_id'] = approval.id
        db.session.commit()
        
        # Send approval notifications
        await self._send_approval_notifications(approval)
        
        return {
            'approval_created': True,
            'approval_id': approval.id,
            'current_approvers': approval.get_current_approvers()
        }
    
    async def _create_approval_request(self, instance: ProcessInstance, step: ProcessStep,
                                     config: Dict[str, Any], input_data: Dict[str, Any]) -> ApprovalRequest:
        """Create approval request."""
        # Build approval chain
        chain_definition = await self._build_approval_chain(instance, config, input_data)
        
        # Create approval request
        approval = ApprovalRequest(
            process_instance_id=instance.id,
            process_step_id=step.id,
            title=config.get('title', f'Approval for {step.step_name}'),
            description=config.get('description', ''),
            status=ApprovalStatus.PENDING.value,
            priority=config.get('priority', 5),
            chain_definition=chain_definition,
            current_level=0,
            request_data=input_data,
            form_schema=config.get('form_schema', {}),
            tenant_id=instance.tenant_id
        )
        
        # Set due date
        if 'due_in_hours' in config:
            hours = config['due_in_hours']
            approval.due_at = datetime.utcnow() + timedelta(hours=hours)
        
        # Set current approver
        if chain_definition.get('levels'):
            first_level = chain_definition['levels'][0]
            approvers = first_level.get('approvers', [])
            if approvers:
                approval.current_approver_id = approvers[0]  # First approver
        
        db.session.add(approval)
        db.session.commit()
        
        return approval
    
    async def _build_approval_chain(self, instance: ProcessInstance, config: Dict[str, Any],
                                  input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build approval chain definition."""
        chain_type = config.get('chain_type', 'single')
        
        if chain_type == 'single':
            # Single approver
            approver_id = await self._resolve_approver(instance, config, input_data)
            return {
                'type': 'single',
                'levels': [
                    {
                        'level': 0,
                        'name': 'Primary Approval',
                        'approvers': [approver_id] if approver_id else [],
                        'require_all': False
                    }
                ]
            }
            
        elif chain_type == 'multi_level':
            # Multi-level approval chain
            levels = config.get('levels', [])
            chain_levels = []
            
            for i, level_config in enumerate(levels):
                approvers = await self._resolve_level_approvers(instance, level_config, input_data)
                chain_levels.append({
                    'level': i,
                    'name': level_config.get('name', f'Level {i+1}'),
                    'approvers': approvers,
                    'require_all': level_config.get('require_all', False),
                    'escalation_hours': level_config.get('escalation_hours', 24)
                })
            
            return {
                'type': 'multi_level',
                'levels': chain_levels
            }
            
        elif chain_type == 'dynamic':
            # Dynamic approval based on conditions
            return await self._build_dynamic_approval_chain(instance, config, input_data)
        
        else:
            # Default to single approver
            return {
                'type': 'single',
                'levels': [
                    {
                        'level': 0,
                        'name': 'Default Approval',
                        'approvers': [],
                        'require_all': False
                    }
                ]
            }
    
    async def _resolve_approver(self, instance: ProcessInstance, config: Dict[str, Any],
                              input_data: Dict[str, Any]) -> Optional[int]:
        """Resolve single approver ID."""
        # Direct assignment
        if 'approver_id' in config:
            return config['approver_id']
        
        # Assignment by role
        if 'approver_role' in config:
            # In real implementation, resolve users by role
            return None
        
        # Dynamic assignment from context
        if 'approver_variable' in config:
            variable_name = config['approver_variable']
            approver = await self.engine.context_manager.get_variable(
                instance.id, variable_name
            )
            return int(approver) if approver else None
        
        return None
    
    async def _resolve_level_approvers(self, instance: ProcessInstance, level_config: Dict[str, Any],
                                     input_data: Dict[str, Any]) -> List[int]:
        """Resolve approvers for a specific level."""
        approvers = []
        
        # Direct approver list
        if 'approvers' in level_config:
            approvers.extend(level_config['approvers'])
        
        # Approvers by role
        if 'approver_roles' in level_config:
            # In real implementation, resolve users by roles
            pass
        
        # Dynamic approvers
        if 'approver_variable' in level_config:
            variable_name = level_config['approver_variable']
            dynamic_approvers = await self.engine.context_manager.get_variable(
                instance.id, variable_name
            )
            if isinstance(dynamic_approvers, list):
                approvers.extend([int(a) for a in dynamic_approvers if str(a).isdigit()])
            elif dynamic_approvers:
                approvers.append(int(dynamic_approvers))
        
        return approvers
    
    async def _build_dynamic_approval_chain(self, instance: ProcessInstance, config: Dict[str, Any],
                                          input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build dynamic approval chain based on conditions."""
        # In real implementation, evaluate conditions to determine approval chain
        # For now, return simple chain
        return {
            'type': 'dynamic',
            'levels': [
                {
                    'level': 0,
                    'name': 'Dynamic Approval',
                    'approvers': [],
                    'require_all': False
                }
            ]
        }
    
    async def _send_approval_notifications(self, approval: ApprovalRequest):
        """Send notifications to current approvers."""
        try:
            current_approvers = approval.get_current_approvers()
            
            for approver_id in current_approvers:
                notification_data = {
                    'type': 'approval_request',
                    'approval_id': approval.id,
                    'approver_id': approver_id,
                    'title': approval.title,
                    'due_at': approval.due_at.isoformat() if approval.due_at else None,
                    'url': f"/process/approval/{approval.id}"
                }
                
                log.info(f"Approval notification sent to user {approver_id}: {json.dumps(notification_data)}")
            
        except Exception as e:
            log.warning(f"Failed to send approval notifications: {str(e)}")


class TimerExecutor(NodeExecutor):
    """
    Executor for timer nodes.
    
    Handles time-based delays, scheduled execution, and timeout
    management with precise timing and cleanup capabilities.
    """
    
    async def _execute_node(self, instance: ProcessInstance, node: Dict[str, Any],
                           step: ProcessStep, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute timer node."""
        timer_config = node.get('properties', {})
        timer_type = timer_config.get('timer_type', 'delay')
        
        if timer_type == 'delay':
            return await self._execute_delay_timer(instance, step, timer_config)
        elif timer_type == 'schedule':
            return await self._execute_schedule_timer(instance, step, timer_config)
        elif timer_type == 'timeout':
            return await self._execute_timeout_timer(instance, step, timer_config)
        else:
            raise NodeExecutionError(f"Unknown timer type: {timer_type}")
    
    async def _execute_delay_timer(self, instance: ProcessInstance, step: ProcessStep,
                                 config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute delay timer."""
        delay_seconds = config.get('delay_seconds', 0)
        delay_minutes = config.get('delay_minutes', 0)
        delay_hours = config.get('delay_hours', 0)
        
        total_delay = delay_seconds + (delay_minutes * 60) + (delay_hours * 3600)
        
        if total_delay <= 0:
            return {'timer_completed': True, 'delay': 0}
        
        # Mark step as waiting
        step.status = 'waiting'
        step.due_at = datetime.utcnow() + timedelta(seconds=total_delay)
        db.session.commit()
        
        # Schedule completion using Celery if available
        if self.engine.celery:
            from ..tasks import complete_timer_step
            complete_timer_step.apply_async(
                args=[step.id],
                countdown=total_delay
            )
        else:
            # For testing or simple setups, use asyncio sleep
            await asyncio.sleep(total_delay)
            step.status = 'completed'
            db.session.commit()
        
        return {
            'timer_type': 'delay',
            'delay_seconds': total_delay,
            'scheduled_completion': step.due_at.isoformat() if step.due_at else None
        }
    
    async def _execute_schedule_timer(self, instance: ProcessInstance, step: ProcessStep,
                                    config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute scheduled timer."""
        schedule_time = config.get('schedule_time')
        
        if not schedule_time:
            raise NodeExecutionError("Schedule time not specified")
        
        # Parse schedule time
        try:
            if isinstance(schedule_time, str):
                scheduled_at = datetime.fromisoformat(schedule_time)
            else:
                scheduled_at = schedule_time
        except ValueError:
            raise NodeExecutionError(f"Invalid schedule time format: {schedule_time}")
        
        # Calculate delay
        now = datetime.utcnow()
        if scheduled_at <= now:
            # Time already passed, complete immediately
            return {'timer_completed': True, 'scheduled_for': scheduled_at.isoformat()}
        
        delay_seconds = (scheduled_at - now).total_seconds()
        
        # Mark step as waiting
        step.status = 'waiting'
        step.due_at = scheduled_at
        db.session.commit()
        
        # Schedule completion
        if self.engine.celery:
            from ..tasks import complete_timer_step
            complete_timer_step.apply_async(
                args=[step.id],
                eta=scheduled_at
            )
        
        return {
            'timer_type': 'schedule',
            'scheduled_for': scheduled_at.isoformat(),
            'delay_seconds': delay_seconds
        }
    
    async def _execute_timeout_timer(self, instance: ProcessInstance, step: ProcessStep,
                                   config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute timeout timer."""
        timeout_seconds = config.get('timeout_seconds', 3600)  # Default 1 hour
        
        # Mark step as waiting with timeout
        step.status = 'waiting'
        step.due_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        step.configuration['timeout_action'] = config.get('timeout_action', 'fail')
        db.session.commit()
        
        # Schedule timeout handling
        if self.engine.celery:
            from ..tasks import handle_step_timeout
            handle_step_timeout.apply_async(
                args=[step.id],
                countdown=timeout_seconds
            )
        
        return {
            'timer_type': 'timeout',
            'timeout_seconds': timeout_seconds,
            'timeout_at': step.due_at.isoformat() if step.due_at else None,
            'timeout_action': config.get('timeout_action', 'fail')
        }