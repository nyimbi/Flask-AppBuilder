#!/usr/bin/env python3
"""
Standalone test script for wizard components that don't require Flask

Tests the core wizard functionality without external dependencies.
"""

import sys
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Type, Union, Tuple
from collections import OrderedDict


class MockSession:
    """Mock session for testing"""
    def __init__(self):
        self._data = {}
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __contains__(self, key):
        return key in self._data
    
    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]


class MockCurrentApp:
    """Mock current app for testing"""
    def __init__(self):
        self.logger = logging.getLogger('test')


# Mock globals for testing
session = MockSession()
current_app = MockCurrentApp()
current_user = None
g = None


# Now import and test wizard components
class WizardStep:
    """
    Represents a single step in a wizard form
    
    Each step contains a subset of form fields and can have its own
    validation, title, description, and conditional logic.
    """
    
    def __init__(self, 
                 name: str,
                 title: str,
                 fields: List[str],
                 description: Optional[str] = None,
                 required_fields: Optional[List[str]] = None,
                 conditional_fields: Optional[Dict[str, Any]] = None,
                 validation_rules: Optional[Dict[str, Any]] = None,
                 icon: Optional[str] = None,
                 template: Optional[str] = None):
        """
        Initialize a wizard step
        
        Args:
            name: Unique step identifier
            title: Display title for the step
            fields: List of field names included in this step
            description: Optional description text
            required_fields: Fields that must be completed to proceed
            conditional_fields: Fields shown based on other field values
            validation_rules: Custom validation rules for this step
            icon: Icon class for step indicator
            template: Custom template for this step
        """
        self.name = name
        self.title = title
        self.fields = fields or []
        self.description = description
        self.required_fields = required_fields or []
        self.conditional_fields = conditional_fields or {}
        self.validation_rules = validation_rules or {}
        self.icon = icon or 'fa-edit'
        self.template = template
        
        # Runtime state
        self.is_valid = False
        self.is_completed = False
        self.validation_errors = {}
    
    def validate_step(self, form_data: Dict[str, Any]) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Validate all fields in this step
        
        Args:
            form_data: Form data to validate
            
        Returns:
            Tuple of (is_valid, errors_dict)
        """
        errors = {}
        
        # Check required fields
        for field_name in self.required_fields:
            if field_name not in form_data or not form_data[field_name]:
                if field_name not in errors:
                    errors[field_name] = []
                errors[field_name].append(f'{field_name} is required')
        
        # Apply custom validation rules
        for field_name, rules in self.validation_rules.items():
            if field_name in form_data:
                field_value = form_data[field_name]
                field_errors = self._validate_field(field_name, field_value, rules)
                if field_errors:
                    errors[field_name] = field_errors
        
        # Check conditional field requirements
        for field_name, conditions in self.conditional_fields.items():
            if self._should_show_field(field_name, form_data, conditions):
                if field_name in self.required_fields and not form_data.get(field_name):
                    if field_name not in errors:
                        errors[field_name] = []
                    errors[field_name].append(f'{field_name} is required')
        
        self.validation_errors = errors
        self.is_valid = len(errors) == 0
        
        return self.is_valid, errors
    
    def _validate_field(self, field_name: str, value: Any, rules: Dict[str, Any]) -> List[str]:
        """Apply custom validation rules to a field"""
        errors = []
        
        if 'min_length' in rules and len(str(value)) < rules['min_length']:
            errors.append(f'{field_name} must be at least {rules["min_length"]} characters')
        
        if 'max_length' in rules and len(str(value)) > rules['max_length']:
            errors.append(f'{field_name} must be no more than {rules["max_length"]} characters')
        
        if 'pattern' in rules:
            import re
            if not re.match(rules['pattern'], str(value)):
                errors.append(f'{field_name} format is invalid')
        
        if 'custom' in rules and callable(rules['custom']):
            try:
                rules['custom'](value)
            except Exception as e:
                errors.append(str(e))
        
        return errors
    
    def _should_show_field(self, field_name: str, form_data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """Check if a conditional field should be shown based on form data"""
        for condition_field, expected_value in conditions.items():
            actual_value = form_data.get(condition_field)
            if actual_value != expected_value:
                return False
        return True
    
    def get_progress_percentage(self, form_data: Dict[str, Any]) -> float:
        """Calculate completion percentage for this step"""
        if not self.fields:
            return 100.0
        
        completed_fields = sum(1 for field in self.fields if form_data.get(field))
        return (completed_fields / len(self.fields)) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for serialization"""
        return {
            'name': self.name,
            'title': self.title,
            'fields': self.fields,
            'description': self.description,
            'required_fields': self.required_fields,
            'conditional_fields': self.conditional_fields,
            'validation_rules': self.validation_rules,
            'icon': self.icon,
            'template': self.template,
            'is_valid': self.is_valid,
            'is_completed': self.is_completed,
            'validation_errors': self.validation_errors
        }


class WizardFormData:
    """
    Manages wizard form data persistence and state
    
    Handles storing partial form data for later retrieval 
    when user returns to continue the form.
    """
    
    def __init__(self, wizard_id: str, user_id: Optional[str] = None):
        self.wizard_id = wizard_id
        self.user_id = user_id
        self.form_data = {}
        self.current_step = 0
        self.completed_steps = set()
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(days=7)  # Default 7-day expiration
        self.is_submitted = False
        self.submission_id = None
    
    def update_data(self, step_data: Dict[str, Any], step_index: int):
        """Update form data for a specific step"""
        self.form_data.update(step_data)
        if step_index not in self.completed_steps:
            self.completed_steps.add(step_index)
        self.updated_at = datetime.utcnow()
    
    def get_step_data(self, step_fields: List[str]) -> Dict[str, Any]:
        """Get form data for specific step fields"""
        return {field: self.form_data.get(field) for field in step_fields}
    
    def set_current_step(self, step_index: int):
        """Set the current active step"""
        self.current_step = step_index
        self.updated_at = datetime.utcnow()
    
    def mark_submitted(self, submission_id: Optional[str] = None):
        """Mark the wizard as submitted"""
        self.is_submitted = True
        self.submission_id = submission_id or str(uuid.uuid4())
        self.updated_at = datetime.utcnow()
        return self.submission_id
    
    def is_expired(self) -> bool:
        """Check if the wizard data has expired"""
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'wizard_id': self.wizard_id,
            'user_id': self.user_id,
            'form_data': self.form_data,
            'current_step': self.current_step,
            'completed_steps': list(self.completed_steps),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'is_submitted': self.is_submitted,
            'submission_id': self.submission_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WizardFormData':
        """Create instance from dictionary"""
        instance = cls(data['wizard_id'], data.get('user_id'))
        instance.form_data = data.get('form_data', {})
        instance.current_step = data.get('current_step', 0)
        instance.completed_steps = set(data.get('completed_steps', []))
        instance.created_at = datetime.fromisoformat(data['created_at'])
        instance.updated_at = datetime.fromisoformat(data['updated_at'])
        instance.expires_at = datetime.fromisoformat(data['expires_at'])
        instance.is_submitted = data.get('is_submitted', False)
        instance.submission_id = data.get('submission_id')
        return instance


def run_tests():
    """Run comprehensive tests on wizard components"""
    print("🧪 Running Wizard Component Tests")
    print("=" * 50)
    
    test_count = 0
    passed_count = 0
    
    # Test 1: WizardStep Creation
    test_count += 1
    try:
        step = WizardStep(
            name='personal_info',
            title='Personal Information',
            fields=['first_name', 'last_name', 'email'],
            required_fields=['first_name', 'email'],
            description='Enter your personal details'
        )
        assert step.name == 'personal_info'
        assert len(step.fields) == 3
        assert len(step.required_fields) == 2
        print("✅ Test 1: WizardStep creation - PASSED")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 1: WizardStep creation - FAILED: {e}")
    
    # Test 2: WizardStep Validation - Success
    test_count += 1
    try:
        is_valid, errors = step.validate_step({
            'first_name': 'John',
            'last_name': 'Doe', 
            'email': 'john@example.com'
        })
        assert is_valid == True
        assert len(errors) == 0
        print("✅ Test 2: WizardStep validation success - PASSED")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 2: WizardStep validation success - FAILED: {e}")
    
    # Test 3: WizardStep Validation - Missing Required Field
    test_count += 1
    try:
        is_valid, errors = step.validate_step({
            'last_name': 'Doe'  # Missing required first_name and email
        })
        assert is_valid == False
        assert 'first_name' in errors
        assert 'email' in errors
        print("✅ Test 3: WizardStep validation failure - PASSED")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 3: WizardStep validation failure - FAILED: {e}")
    
    # Test 4: WizardStep Progress Calculation
    test_count += 1
    try:
        progress = step.get_progress_percentage({'first_name': 'John', 'email': 'john@example.com'})
        expected_progress = (2 / 3) * 100  # 2 out of 3 fields completed
        assert abs(progress - expected_progress) < 0.1
        print(f"✅ Test 4: WizardStep progress calculation - PASSED ({progress:.1f}%)")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 4: WizardStep progress calculation - FAILED: {e}")
    
    # Test 5: WizardStep Serialization
    test_count += 1
    try:
        step_dict = step.to_dict()
        assert isinstance(step_dict, dict)
        assert step_dict['name'] == 'personal_info'
        assert step_dict['title'] == 'Personal Information'
        assert len(step_dict['fields']) == 3
        print("✅ Test 5: WizardStep serialization - PASSED")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 5: WizardStep serialization - FAILED: {e}")
    
    # Test 6: WizardFormData Creation
    test_count += 1
    try:
        wizard_data = WizardFormData('test_wizard_123', 'user_456')
        assert wizard_data.wizard_id == 'test_wizard_123'
        assert wizard_data.user_id == 'user_456'
        assert wizard_data.form_data == {}
        assert wizard_data.current_step == 0
        print("✅ Test 6: WizardFormData creation - PASSED")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 6: WizardFormData creation - FAILED: {e}")
    
    # Test 7: WizardFormData Update
    test_count += 1
    try:
        wizard_data.update_data({'first_name': 'John', 'email': 'john@example.com'}, 0)
        assert wizard_data.form_data['first_name'] == 'John'
        assert wizard_data.form_data['email'] == 'john@example.com'
        assert 0 in wizard_data.completed_steps
        print("✅ Test 7: WizardFormData update - PASSED")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 7: WizardFormData update - FAILED: {e}")
    
    # Test 8: WizardFormData Step Data Retrieval
    test_count += 1
    try:
        step_data = wizard_data.get_step_data(['first_name', 'email'])
        assert step_data['first_name'] == 'John'
        assert step_data['email'] == 'john@example.com'
        print("✅ Test 8: WizardFormData step data retrieval - PASSED")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 8: WizardFormData step data retrieval - FAILED: {e}")
    
    # Test 9: WizardFormData Serialization
    test_count += 1
    try:
        data_dict = wizard_data.to_dict()
        assert isinstance(data_dict, dict)
        assert data_dict['wizard_id'] == 'test_wizard_123'
        assert data_dict['user_id'] == 'user_456'
        assert len(data_dict['form_data']) == 2
        print("✅ Test 9: WizardFormData serialization - PASSED")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 9: WizardFormData serialization - FAILED: {e}")
    
    # Test 10: WizardFormData Deserialization
    test_count += 1
    try:
        restored_data = WizardFormData.from_dict(data_dict)
        assert restored_data.wizard_id == wizard_data.wizard_id
        assert restored_data.user_id == wizard_data.user_id
        assert restored_data.form_data == wizard_data.form_data
        assert restored_data.completed_steps == wizard_data.completed_steps
        print("✅ Test 10: WizardFormData deserialization - PASSED")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 10: WizardFormData deserialization - FAILED: {e}")
    
    # Test 11: WizardFormData Submission
    test_count += 1
    try:
        submission_id = wizard_data.mark_submitted()
        assert wizard_data.is_submitted == True
        assert wizard_data.submission_id is not None
        assert len(wizard_data.submission_id) > 0
        print(f"✅ Test 11: WizardFormData submission - PASSED ({submission_id})")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 11: WizardFormData submission - FAILED: {e}")
    
    # Test 12: Custom Validation Rules
    test_count += 1
    try:
        def custom_email_validator(value):
            if not value.endswith('@company.com'):
                raise Exception('Email must be from company domain')
        
        custom_step = WizardStep(
            name='custom_validation',
            title='Custom Validation Test',
            fields=['company_email'],
            required_fields=['company_email'],
            validation_rules={
                'company_email': {
                    'min_length': 5,
                    'custom': custom_email_validator
                }
            }
        )
        
        # Test valid email
        is_valid, errors = custom_step.validate_step({'company_email': 'test@company.com'})
        assert is_valid == True
        
        # Test invalid email
        is_valid, errors = custom_step.validate_step({'company_email': 'test@other.com'})
        assert is_valid == False
        
        print("✅ Test 12: Custom validation rules - PASSED")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 12: Custom validation rules - FAILED: {e}")
    
    # Test 13: Conditional Fields
    test_count += 1
    try:
        conditional_step = WizardStep(
            name='conditional_test',
            title='Conditional Fields Test',
            fields=['contact_method', 'email', 'phone'],
            conditional_fields={
                'email': {'contact_method': 'email'},
                'phone': {'contact_method': 'phone'}
            },
            required_fields=['email']  # Email is required when shown
        )
        
        # Test when email should be required
        is_valid, errors = conditional_step.validate_step({
            'contact_method': 'email',
            'phone': '123-456-7890'  # Missing required email
        })
        assert is_valid == False
        assert 'email' in errors
        
        print("✅ Test 13: Conditional fields - PASSED")
        passed_count += 1
    except Exception as e:
        print(f"❌ Test 13: Conditional fields - FAILED: {e}")
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"🏁 Test Summary: {passed_count}/{test_count} tests passed")
    
    if passed_count == test_count:
        print("🎉 ALL TESTS PASSED! Wizard components are working correctly.")
        return True
    else:
        print(f"⚠️  {test_count - passed_count} tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)