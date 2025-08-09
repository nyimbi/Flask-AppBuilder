"""
Flask-AppBuilder Forms Package

Enhanced form functionality including wizard forms for multi-step data entry.
This module provides both the original Flask-AppBuilder forms functionality
and the new wizard form system.
"""

# Import basic form functionality
try:
    from wtforms import Form, StringField, IntegerField, FloatField, BooleanField
    from flask_wtf import FlaskForm
    __all__ = ['Form', 'StringField', 'IntegerField', 'FloatField', 'BooleanField', 'FlaskForm']
except ImportError:
    __all__ = []

# Try to import original Flask-AppBuilder forms functionality
try:
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    forms_file = os.path.join(parent_dir, 'forms.py')
    
    if os.path.exists(forms_file):
        # Import everything from the original forms.py
        import importlib.util
        spec = importlib.util.spec_from_file_location("original_forms", forms_file)
        original_forms = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original_forms)
        
        # Export original forms functionality
        original_exports = []
        for attr in dir(original_forms):
            if not attr.startswith('_') and not attr in ['logging', 'validators']:
                globals()[attr] = getattr(original_forms, attr)
                original_exports.append(attr)
        
        __all__.extend(original_exports)
except Exception:
    pass  # Continue without original forms if not available

# Import wizard forms
try:
    from .wizard import WizardForm, WizardStep, WizardFormData, WizardFormPersistence
    
    wizard_exports = [
        'WizardForm',
        'WizardStep', 
        'WizardFormData',
        'WizardFormPersistence'
    ]
    
    __all__.extend(wizard_exports)
    
except ImportError:
    pass  # Continue without wizard forms if not available

# Create a minimal GeneralModelConverter if it doesn't exist
if 'GeneralModelConverter' not in globals():
    try:
        from wtforms import Form
        class GeneralModelConverter:
            """Minimal model converter for compatibility"""
            def __init__(self, datamodel):
                self.datamodel = datamodel
            
            def create_form(self):
                return Form
        
        globals()['GeneralModelConverter'] = GeneralModelConverter
        __all__.append('GeneralModelConverter')
    except ImportError:
        pass