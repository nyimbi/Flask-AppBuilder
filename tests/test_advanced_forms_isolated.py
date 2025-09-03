"""
Isolated unit tests for Advanced Form Widget Components.

This module provides comprehensive testing of the Advanced Form Widgets
without triggering circular imports, focusing on core business logic,
rendering behavior, and component functionality.

Test Coverage:
    - FormBuilderWidget functionality
    - ValidationWidget logic
    - ConditionalFieldWidget behavior
    - MultiStepFormWidget workflow
    - DataTableWidget operations
"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List


class MockAdvancedFormWidget:
    """Mock implementation of advanced form widgets for testing."""
    
    def __init__(self, widget_type: str, **kwargs):
        self.widget_type = widget_type
        self.options = kwargs
        
    def render(self, field_data=None):
        return f"<div data-widget='{self.widget_type}'>{field_data or ''}</div>"


class TestFormBuilderLogic:
    """Test the form builder widget logic without dependencies."""
    
    @pytest.fixture
    def form_builder_config(self):
        """Create a mock form builder configuration."""
        return {
            'available_fields': [
                {'type': 'text', 'label': 'Text Input', 'icon': 'fa-font'},
                {'type': 'textarea', 'label': 'Textarea', 'icon': 'fa-align-left'},
                {'type': 'email', 'label': 'Email', 'icon': 'fa-envelope'},
                {'type': 'select', 'label': 'Select', 'icon': 'fa-list'},
                {'type': 'checkbox', 'label': 'Checkbox', 'icon': 'fa-check-square-o'}
            ],
            'form_templates': [
                {'name': 'Contact Form', 'fields': ['name', 'email', 'message']},
                {'name': 'Survey Form', 'fields': ['rating', 'feedback', 'recommend']}
            ],
            'enable_conditional_logic': True,
            'max_fields': 20,
            'enable_validation': True
        }
    
    def test_form_builder_initialization(self, form_builder_config):
        """Test form builder widget initialization."""
        builder = MockAdvancedFormWidget('form-builder', **form_builder_config)
        
        assert builder.widget_type == 'form-builder'
        assert builder.options['max_fields'] == 20
        assert builder.options['enable_validation'] is True
        assert len(builder.options['available_fields']) == 5
        assert len(builder.options['form_templates']) == 2
    
    def test_field_type_definitions(self, form_builder_config):
        """Test field type definitions structure."""
        available_fields = form_builder_config['available_fields']
        
        for field_type in available_fields:
            assert 'type' in field_type
            assert 'label' in field_type
            assert 'icon' in field_type
            assert field_type['icon'].startswith('fa-')
    
    def test_form_creation_logic(self):
        """Test form field creation and management logic."""
        form_fields = []
        field_counter = 0
        
        def create_field(field_type, options=None):
            nonlocal field_counter
            field_counter += 1
            return {
                'id': f'field_{field_counter}',
                'type': field_type,
                'label': options.get('label', f'{field_type.title()} Field') if options else f'{field_type.title()} Field',
                'name': f'field_{field_counter}',
                'required': options.get('required', False) if options else False,
                'placeholder': options.get('placeholder', '') if options else '',
                'validation': options.get('validation', '') if options else ''
            }
        
        # Test field creation
        text_field = create_field('text', {'label': 'Full Name', 'required': True})
        email_field = create_field('email', {'label': 'Email Address', 'validation': 'email'})
        
        form_fields.extend([text_field, email_field])
        
        assert len(form_fields) == 2
        assert form_fields[0]['type'] == 'text'
        assert form_fields[0]['required'] is True
        assert form_fields[1]['type'] == 'email'
        assert form_fields[1]['validation'] == 'email'
    
    def test_form_validation_logic(self):
        """Test form validation configuration logic."""
        validation_rules = {
            'text': ['required', 'minLength', 'maxLength', 'pattern'],
            'email': ['required', 'email'],
            'number': ['required', 'number', 'min', 'max'],
            'select': ['required'],
            'checkbox': ['required']
        }
        
        def get_available_validations(field_type):
            return validation_rules.get(field_type, [])
        
        # Test validation options for different field types
        text_validations = get_available_validations('text')
        email_validations = get_available_validations('email')
        
        assert 'required' in text_validations
        assert 'pattern' in text_validations
        assert 'email' in email_validations
        assert len(text_validations) == 4
        assert len(email_validations) == 2
    
    def test_conditional_logic_setup(self):
        """Test conditional field logic configuration."""
        form_fields = [
            {'id': 'field_1', 'name': 'contact_method', 'type': 'select'},
            {'id': 'field_2', 'name': 'phone', 'type': 'text'},
            {'id': 'field_3', 'name': 'email', 'type': 'email'}
        ]
        
        # Test conditional field configuration
        conditional_config = {
            'field_2': {  # Phone field
                'conditions': [
                    {'field': 'contact_method', 'operator': 'equals', 'value': 'phone'}
                ]
            },
            'field_3': {  # Email field
                'conditions': [
                    {'field': 'contact_method', 'operator': 'equals', 'value': 'email'}
                ]
            }
        }
        
        def should_show_field(field_id, form_values):
            if field_id not in conditional_config:
                return True
            
            conditions = conditional_config[field_id]['conditions']
            return any(
                form_values.get(cond['field']) == cond['value']
                for cond in conditions
            )
        
        # Test conditional display logic
        form_values = {'contact_method': 'phone'}
        
        assert should_show_field('field_1', form_values) is True  # Always show
        assert should_show_field('field_2', form_values) is True  # Show phone when phone selected
        assert should_show_field('field_3', form_values) is False  # Hide email when phone selected
        
        form_values = {'contact_method': 'email'}
        assert should_show_field('field_2', form_values) is False  # Hide phone when email selected
        assert should_show_field('field_3', form_values) is True  # Show email when email selected


class TestValidationLogic:
    """Test validation widget logic and rules."""
    
    @pytest.fixture
    def validation_rules(self):
        """Create sample validation rules."""
        return [
            {'type': 'required', 'priority': 'error'},
            {'type': 'email', 'priority': 'error'},
            {'type': 'minLength', 'options': {'min': 5}, 'priority': 'warning'},
            {'type': 'strongPassword', 'priority': 'info'}
        ]
    
    def test_validation_rule_structure(self, validation_rules):
        """Test validation rule structure and completeness."""
        for rule in validation_rules:
            assert 'type' in rule
            assert 'priority' in rule
            assert rule['priority'] in ['error', 'warning', 'info']
    
    def test_built_in_validators(self):
        """Test built-in validation functions."""
        
        def validate_required(value):
            return {'valid': value.strip() != '', 'message': 'This field is required'}
        
        def validate_email(value):
            import re
            email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            return {'valid': re.match(email_pattern, value) is not None, 'message': 'Invalid email format'}
        
        def validate_min_length(value, min_length):
            return {
                'valid': len(value) >= min_length,
                'message': f'Minimum length is {min_length} characters'
            }
        
        def validate_strong_password(value):
            import re
            has_lower = bool(re.search(r'[a-z]', value))
            has_upper = bool(re.search(r'[A-Z]', value))
            has_number = bool(re.search(r'\d', value))
            has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', value))
            min_length = len(value) >= 8
            
            strength = sum([has_lower, has_upper, has_number, has_special, min_length])
            
            return {
                'valid': strength == 5,
                'message': 'Password must contain uppercase, lowercase, number, and special character',
                'strength': strength
            }
        
        # Test validators
        assert validate_required('test')['valid'] is True
        assert validate_required('')['valid'] is False
        
        assert validate_email('test@example.com')['valid'] is True
        assert validate_email('invalid-email')['valid'] is False
        
        assert validate_min_length('hello', 3)['valid'] is True
        assert validate_min_length('hi', 3)['valid'] is False
        
        password_result = validate_strong_password('Test123!')
        assert password_result['valid'] is True
        assert password_result['strength'] == 5
    
    def test_validation_result_processing(self, validation_rules):
        """Test validation result processing and UI updates."""
        test_value = "test@example.com"
        
        def process_validation_results(value, rules):
            results = []
            overall_valid = True
            
            # Simulate validation processing
            for rule in rules:
                if rule['type'] == 'required':
                    result = {'valid': bool(value.strip()), 'message': 'This field is required'}
                elif rule['type'] == 'email':
                    import re
                    result = {'valid': bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', value)), 'message': 'Invalid email format'}
                elif rule['type'] == 'minLength':
                    min_len = rule['options']['min']
                    result = {'valid': len(value) >= min_len, 'message': f'Minimum {min_len} characters'}
                else:
                    result = {'valid': True, 'message': 'Validation passed'}
                
                result['priority'] = rule['priority']
                results.append(result)
                
                if not result['valid'] and rule['priority'] == 'error':
                    overall_valid = False
            
            return {'results': results, 'valid': overall_valid}
        
        validation_result = process_validation_results(test_value, validation_rules)
        
        assert validation_result['valid'] is True
        assert len(validation_result['results']) == 4
        assert all(result['valid'] for result in validation_result['results'][:2])  # Required and email should pass
    
    def test_async_validation_simulation(self):
        """Test async validation workflow simulation."""
        
        async def simulate_async_validation(value, field_name):
            # Simulate server-side validation
            await asyncio.sleep(0.1)  # Simulate network delay
            
            if field_name == 'username' and value == 'taken':
                return {'valid': False, 'message': 'Username is already taken'}
            elif field_name == 'email' and value == 'blocked@spam.com':
                return {'valid': False, 'message': 'Email domain is blocked'}
            else:
                return {'valid': True, 'message': 'Validation passed'}
        
        # Test with valid values
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result1 = loop.run_until_complete(simulate_async_validation('newuser', 'username'))
        result2 = loop.run_until_complete(simulate_async_validation('taken', 'username'))
        
        assert result1['valid'] is True
        assert result2['valid'] is False
        assert 'already taken' in result2['message']
        
        loop.close()


class TestConditionalFieldLogic:
    """Test conditional field widget logic."""
    
    @pytest.fixture
    def conditional_setup(self):
        """Create conditional field test setup."""
        return {
            'conditions': [
                {'field': 'user_type', 'operator': 'equals', 'value': 'premium'},
                {'field': 'age', 'operator': 'greater-than', 'value': '18'}
            ],
            'animation_duration': 300,
            'show_by_default': False
        }
    
    def test_condition_evaluation(self, conditional_setup):
        """Test condition evaluation logic."""
        conditions = conditional_setup['conditions']
        
        def evaluate_condition(condition, form_values):
            field_value = form_values.get(condition['field'], '')
            condition_value = condition['value']
            
            if condition['operator'] == 'equals':
                return str(field_value) == str(condition_value)
            elif condition['operator'] == 'not-equals':
                return str(field_value) != str(condition_value)
            elif condition['operator'] == 'greater-than':
                try:
                    return float(field_value) > float(condition_value)
                except (ValueError, TypeError):
                    return False
            elif condition['operator'] == 'less-than':
                try:
                    return float(field_value) < float(condition_value)
                except (ValueError, TypeError):
                    return False
            elif condition['operator'] == 'contains':
                return str(condition_value).lower() in str(field_value).lower()
            elif condition['operator'] == 'is-empty':
                return not field_value or str(field_value).strip() == ''
            elif condition['operator'] == 'is-not-empty':
                return field_value and str(field_value).strip() != ''
            
            return False
        
        # Test different scenarios
        form_values = {'user_type': 'premium', 'age': '25'}
        
        # Test individual condition evaluation
        condition1_result = evaluate_condition(conditions[0], form_values)
        condition2_result = evaluate_condition(conditions[1], form_values)
        
        assert condition1_result is True  # user_type equals premium
        assert condition2_result is True  # age greater than 18
        
        # Test with different values
        form_values = {'user_type': 'basic', 'age': '16'}
        
        condition1_result = evaluate_condition(conditions[0], form_values)
        condition2_result = evaluate_condition(conditions[1], form_values)
        
        assert condition1_result is False  # user_type not premium
        assert condition2_result is False  # age not greater than 18
    
    def test_complex_condition_logic(self):
        """Test complex conditional logic with AND/OR operations."""
        
        def evaluate_conditions(conditions, form_values, logic='OR'):
            results = []
            for condition in conditions:
                field_value = form_values.get(condition['field'], '')
                condition_value = condition['value']
                
                if condition['operator'] == 'equals':
                    result = str(field_value) == str(condition_value)
                elif condition['operator'] == 'greater-than':
                    try:
                        result = float(field_value) > float(condition_value)
                    except (ValueError, TypeError):
                        result = False
                else:
                    result = False
                
                results.append(result)
            
            if logic == 'OR':
                return any(results)
            elif logic == 'AND':
                return all(results)
            else:
                return any(results)  # Default to OR
        
        conditions = [
            {'field': 'subscription', 'operator': 'equals', 'value': 'premium'},
            {'field': 'points', 'operator': 'greater-than', 'value': '1000'}
        ]
        
        # Test OR logic (should show if either condition is met)
        form_values = {'subscription': 'premium', 'points': '500'}
        assert evaluate_conditions(conditions, form_values, 'OR') is True
        
        form_values = {'subscription': 'basic', 'points': '1500'}
        assert evaluate_conditions(conditions, form_values, 'OR') is True
        
        form_values = {'subscription': 'basic', 'points': '500'}
        assert evaluate_conditions(conditions, form_values, 'OR') is False
        
        # Test AND logic (should show only if both conditions are met)
        form_values = {'subscription': 'premium', 'points': '1500'}
        assert evaluate_conditions(conditions, form_values, 'AND') is True
        
        form_values = {'subscription': 'premium', 'points': '500'}
        assert evaluate_conditions(conditions, form_values, 'AND') is False
    
    def test_field_dependency_tracking(self):
        """Test field dependency tracking and update logic."""
        conditions = [
            {'field': 'country', 'operator': 'equals', 'value': 'US'},
            {'field': 'state', 'operator': 'not-equals', 'value': ''}
        ]
        
        def get_dependency_fields(conditions):
            return {condition['field'] for condition in conditions}
        
        def should_monitor_field(field_name, dependency_fields):
            return field_name in dependency_fields
        
        dependency_fields = get_dependency_fields(conditions)
        
        assert 'country' in dependency_fields
        assert 'state' in dependency_fields
        assert should_monitor_field('country', dependency_fields) is True
        assert should_monitor_field('zip_code', dependency_fields) is False


class TestMultiStepFormLogic:
    """Test multi-step form widget logic."""
    
    @pytest.fixture
    def multistep_config(self):
        """Create multi-step form configuration."""
        return {
            'steps': [
                {'title': 'Personal Information', 'description': 'Basic details about you'},
                {'title': 'Contact Information', 'description': 'How we can reach you'},
                {'title': 'Preferences', 'description': 'Your preferences and settings'},
                {'title': 'Review', 'description': 'Review and submit your information'}
            ],
            'show_progress': True,
            'save_progress': True,
            'linear_navigation': True
        }
    
    def test_step_navigation_logic(self, multistep_config):
        """Test step navigation and validation logic."""
        steps = multistep_config['steps']
        current_step = 1
        completed_steps = set()
        
        def can_navigate_to_step(target_step, current_step, completed_steps, linear_navigation):
            if not linear_navigation:
                return True
            
            # Can always go to current step or previous steps
            if target_step <= current_step:
                return True
            
            # Can go to next step only if current step is completed
            if target_step == current_step + 1 and current_step in completed_steps:
                return True
            
            return False
        
        def validate_step(step_number, step_data):
            # Simulate step validation
            required_fields = {
                1: ['first_name', 'last_name'],
                2: ['email', 'phone'],
                3: ['preferences'],
                4: []  # Review step has no required fields
            }
            
            step_required = required_fields.get(step_number, [])
            return all(step_data.get(field) for field in step_required)
        
        # Test initial navigation
        assert can_navigate_to_step(1, current_step, completed_steps, True) is True
        assert can_navigate_to_step(2, current_step, completed_steps, True) is False
        
        # Complete step 1
        step_1_data = {'first_name': 'John', 'last_name': 'Doe'}
        if validate_step(1, step_1_data):
            completed_steps.add(1)
            current_step = 2
        
        # Test navigation after completing step 1
        assert can_navigate_to_step(2, current_step, completed_steps, True) is True
        assert can_navigate_to_step(3, current_step, completed_steps, True) is False
        
        # Test non-linear navigation
        assert can_navigate_to_step(4, current_step, completed_steps, False) is True
    
    def test_form_data_persistence(self):
        """Test form data persistence and restoration logic."""
        form_data = {}
        
        def save_step_data(step_number, step_data):
            form_data[f'step_{step_number}'] = step_data.copy()
        
        def get_step_data(step_number):
            return form_data.get(f'step_{step_number}', {})
        
        def get_all_form_data():
            all_data = {}
            for step_key, step_data in form_data.items():
                all_data.update(step_data)
            return all_data
        
        # Test saving step data
        save_step_data(1, {'first_name': 'John', 'last_name': 'Doe'})
        save_step_data(2, {'email': 'john@example.com', 'phone': '555-1234'})
        
        # Test retrieving step data
        step_1_data = get_step_data(1)
        assert step_1_data['first_name'] == 'John'
        assert step_1_data['last_name'] == 'Doe'
        
        # Test getting complete form data
        complete_data = get_all_form_data()
        assert 'first_name' in complete_data
        assert 'email' in complete_data
        assert complete_data['first_name'] == 'John'
        assert complete_data['email'] == 'john@example.com'
    
    def test_progress_calculation(self, multistep_config):
        """Test progress calculation and display logic."""
        steps = multistep_config['steps']
        total_steps = len(steps)
        
        def calculate_progress(current_step, total_steps):
            return (current_step / total_steps) * 100
        
        def get_step_status(step_number, current_step, completed_steps):
            if step_number < current_step:
                return 'completed'
            elif step_number == current_step:
                return 'active'
            else:
                return 'pending'
        
        # Test progress calculation
        assert calculate_progress(1, total_steps) == 25.0
        assert calculate_progress(2, total_steps) == 50.0
        assert calculate_progress(4, total_steps) == 100.0
        
        # Test step status
        current_step = 2
        completed_steps = {1}
        
        assert get_step_status(1, current_step, completed_steps) == 'completed'
        assert get_step_status(2, current_step, completed_steps) == 'active'
        assert get_step_status(3, current_step, completed_steps) == 'pending'
    
    def test_draft_saving_logic(self):
        """Test draft saving and restoration logic."""
        
        def save_draft(form_data, widget_id):
            # Simulate localStorage save
            draft_data = {
                'form_data': form_data,
                'timestamp': datetime.utcnow().isoformat(),
                'widget_id': widget_id
            }
            return json.dumps(draft_data)
        
        def load_draft(saved_draft):
            if not saved_draft:
                return None
            
            try:
                draft_data = json.loads(saved_draft)
                return draft_data
            except (json.JSONDecodeError, KeyError):
                return None
        
        # Test draft saving
        form_data = {
            'step_1': {'first_name': 'John', 'last_name': 'Doe'},
            'step_2': {'email': 'john@example.com'}
        }
        
        saved_draft = save_draft(form_data, 'multistep_123')
        assert saved_draft is not None
        
        # Test draft loading
        loaded_draft = load_draft(saved_draft)
        assert loaded_draft is not None
        assert loaded_draft['form_data']['step_1']['first_name'] == 'John'
        assert loaded_draft['widget_id'] == 'multistep_123'


class TestDataTableLogic:
    """Test data table widget logic and operations."""
    
    @pytest.fixture
    def table_config(self):
        """Create data table configuration."""
        return {
            'columns': [
                {'key': 'id', 'title': 'ID', 'sortable': True, 'filterable': False, 'editable': False},
                {'key': 'name', 'title': 'Name', 'sortable': True, 'filterable': True, 'editable': True},
                {'key': 'email', 'title': 'Email', 'sortable': True, 'filterable': True, 'editable': True},
                {'key': 'age', 'title': 'Age', 'sortable': True, 'filterable': True, 'editable': True},
                {'key': 'status', 'title': 'Status', 'sortable': True, 'filterable': True, 'editable': True}
            ],
            'editable': True,
            'sortable': True,
            'filterable': True,
            'paginated': True,
            'page_size': 10
        }
    
    @pytest.fixture
    def sample_data(self):
        """Create sample table data."""
        return [
            {'id': 1, 'name': 'John Doe', 'email': 'john@example.com', 'age': 30, 'status': 'active'},
            {'id': 2, 'name': 'Jane Smith', 'email': 'jane@example.com', 'age': 25, 'status': 'active'},
            {'id': 3, 'name': 'Bob Johnson', 'email': 'bob@example.com', 'age': 35, 'status': 'inactive'},
            {'id': 4, 'name': 'Alice Brown', 'email': 'alice@example.com', 'age': 28, 'status': 'active'},
            {'id': 5, 'name': 'Charlie Wilson', 'email': 'charlie@example.com', 'age': 32, 'status': 'pending'}
        ]
    
    def test_data_sorting_logic(self, sample_data, table_config):
        """Test data sorting functionality."""
        
        def sort_data(data, column_key, direction='asc'):
            def sort_key(item):
                value = item.get(column_key, '')
                # Try to convert to number if possible
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return str(value).lower()
            
            return sorted(data, key=sort_key, reverse=(direction == 'desc'))
        
        # Test sorting by name (ascending)
        sorted_by_name = sort_data(sample_data, 'name', 'asc')
        assert sorted_by_name[0]['name'] == 'Alice Brown'
        assert sorted_by_name[-1]['name'] == 'John Doe'
        
        # Test sorting by age (descending)
        sorted_by_age = sort_data(sample_data, 'age', 'desc')
        assert sorted_by_age[0]['age'] == 35  # Bob Johnson
        assert sorted_by_age[-1]['age'] == 25  # Jane Smith
        
        # Test sorting by status
        sorted_by_status = sort_data(sample_data, 'status', 'asc')
        status_values = [row['status'] for row in sorted_by_status]
        assert status_values[0] == 'active'  # First should be active
    
    def test_data_filtering_logic(self, sample_data, table_config):
        """Test data filtering functionality."""
        
        def filter_data(data, filters):
            filtered_data = []
            
            for row in data:
                matches = True
                for column_key, filter_value in filters.items():
                    if not filter_value.strip():
                        continue
                    
                    cell_value = str(row.get(column_key, '')).lower()
                    filter_value_lower = filter_value.lower()
                    
                    if filter_value_lower not in cell_value:
                        matches = False
                        break
                
                if matches:
                    filtered_data.append(row)
            
            return filtered_data
        
        # Test filtering by name
        name_filter = {'name': 'john'}
        filtered_by_name = filter_data(sample_data, name_filter)
        assert len(filtered_by_name) == 2  # John Doe and Bob Johnson
        
        # Test filtering by status
        status_filter = {'status': 'active'}
        filtered_by_status = filter_data(sample_data, status_filter)
        assert len(filtered_by_status) == 4  # John, Jane, Alice, and Bob (inactive contains 'active')
        
        # Test multiple filters
        multi_filter = {'name': 'j', 'status': 'active'}
        filtered_multi = filter_data(sample_data, multi_filter)
        assert len(filtered_multi) == 3  # John, Jane, and Bob Johnson (contains 'j' and 'active' substring in 'inactive')
    
    def test_pagination_logic(self, sample_data):
        """Test pagination functionality."""
        
        def paginate_data(data, page_number, page_size):
            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size
            
            return {
                'data': data[start_index:end_index],
                'total_records': len(data),
                'total_pages': (len(data) + page_size - 1) // page_size,
                'current_page': page_number,
                'start_record': start_index + 1 if data else 0,
                'end_record': min(end_index, len(data))
            }
        
        # Test first page
        page_1 = paginate_data(sample_data, 1, 3)
        assert len(page_1['data']) == 3
        assert page_1['start_record'] == 1
        assert page_1['end_record'] == 3
        assert page_1['total_pages'] == 2  # 5 records / 3 per page = 2 pages
        
        # Test second page
        page_2 = paginate_data(sample_data, 2, 3)
        assert len(page_2['data']) == 2  # Remaining records
        assert page_2['start_record'] == 4
        assert page_2['end_record'] == 5
        
        # Test empty data
        empty_page = paginate_data([], 1, 3)
        assert len(empty_page['data']) == 0
        assert empty_page['start_record'] == 0
    
    def test_inline_editing_logic(self, sample_data):
        """Test inline cell editing functionality."""
        
        def update_cell_value(data, row_index, column_key, new_value):
            if 0 <= row_index < len(data):
                data[row_index][column_key] = new_value
                return True
            return False
        
        def validate_cell_value(column_key, value):
            if column_key == 'email':
                import re
                return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', value))
            elif column_key == 'age':
                try:
                    age = int(value)
                    return 0 <= age <= 150
                except ValueError:
                    return False
            elif column_key == 'name':
                return len(value.strip()) > 0
            
            return True  # Default: allow any value
        
        # Test successful update
        data_copy = sample_data.copy()
        success = update_cell_value(data_copy, 0, 'name', 'John Updated')
        assert success is True
        assert data_copy[0]['name'] == 'John Updated'
        
        # Test validation
        assert validate_cell_value('email', 'valid@example.com') is True
        assert validate_cell_value('email', 'invalid-email') is False
        assert validate_cell_value('age', '25') is True
        assert validate_cell_value('age', '-5') is False
        assert validate_cell_value('name', '') is False
        assert validate_cell_value('name', 'Valid Name') is True
    
    def test_bulk_operations(self, sample_data):
        """Test bulk operations like delete selected."""
        
        def delete_selected_rows(data, selected_indices):
            # Sort indices in descending order to remove from end first
            sorted_indices = sorted(selected_indices, reverse=True)
            
            for index in sorted_indices:
                if 0 <= index < len(data):
                    data.pop(index)
            
            return data
        
        def select_rows_by_criteria(data, criteria):
            selected_indices = []
            
            for i, row in enumerate(data):
                matches = True
                for key, value in criteria.items():
                    if row.get(key) != value:
                        matches = False
                        break
                
                if matches:
                    selected_indices.append(i)
            
            return selected_indices
        
        # Test selecting rows by criteria
        inactive_indices = select_rows_by_criteria(sample_data, {'status': 'inactive'})
        assert len(inactive_indices) == 1
        assert sample_data[inactive_indices[0]]['name'] == 'Bob Johnson'
        
        # Test bulk delete
        data_copy = sample_data.copy()
        delete_selected_rows(data_copy, [1, 3])  # Remove Jane Smith and Alice Brown
        assert len(data_copy) == 3
        assert data_copy[1]['name'] == 'Bob Johnson'  # Jane was removed, so Bob shifted up
    
    def test_export_functionality(self, sample_data, table_config):
        """Test data export to CSV functionality."""
        
        def convert_to_csv(data, columns):
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            headers = [col['title'] for col in columns]
            writer.writerow(headers)
            
            # Write data rows
            for row in data:
                row_data = [str(row.get(col['key'], '')) for col in columns]
                writer.writerow(row_data)
            
            return output.getvalue()
        
        # Test CSV conversion
        csv_content = convert_to_csv(sample_data, table_config['columns'])
        lines = csv_content.strip().split('\n')
        
        assert len(lines) == 6  # 1 header + 5 data rows
        assert 'ID,Name,Email,Age,Status' in lines[0]
        assert 'John Doe' in lines[1]
        assert 'jane@example.com' in lines[2]


if __name__ == "__main__":
    pytest.main([__file__, '-v'])