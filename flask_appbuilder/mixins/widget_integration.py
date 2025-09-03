"""
Widget Integration System for Mixin-Enhanced Models

This module automatically maps appropriate widgets to model fields based on
the mixins used, providing optimal UI components for enhanced functionality.
"""

import logging
from typing import Dict, List, Any, Optional, Type, Union
from flask_appbuilder.widgets import (
    ModernTextWidget, ModernTextAreaWidget, JSONEditorWidget, 
    ArrayEditorWidget, TagInputWidget, DateTimeRangeWidget,
    ColorPickerWidget, FileUploadWidget, ValidationWidget
)
from flask_appbuilder.fieldwidgets import (
    Select2Widget, Select2ManyWidget, DatePickerWidget, DateTimePickerWidget
)

log = logging.getLogger(__name__)


class MixinWidgetMapping:
    """
    Intelligent widget mapping system that selects optimal widgets
    based on model mixins and field characteristics.
    """
    
    # Widget mappings for different mixin types
    MIXIN_WIDGET_MAP = {
        'MetadataMixin': {
            'metadata': JSONEditorWidget(show_tree_view=True, auto_format=True),
            'metadata_json': JSONEditorWidget(show_tree_view=True, auto_format=True)
        },
        
        'SearchableMixin': {
            'search_vector': ModernTextAreaWidget(readonly=True, show_stats=False),
            'searchable_content': ModernTextAreaWidget(
                auto_resize=True,
                show_stats=True,
                full_screen=True
            )
        },
        
        'InternationalizationMixin': {
            'translatable_fields': ArrayEditorWidget(
                item_type='text',
                sortable=False,
                max_items=20
            )
        },
        
        'WorkflowMixin': {
            'current_state': Select2Widget(),
            'workflow_data': JSONEditorWidget(show_tree_view=True),
            'state_history': ArrayEditorWidget(
                item_type='text',
                sortable=False,
                readonly=True
            )
        },
        
        'ApprovalWorkflowMixin': {
            'approval_status': Select2Widget(),
            'approval_history': ArrayEditorWidget(
                item_type='text',
                readonly=True,
                sortable=False
            )
        },
        
        'DocMixin': {
            'doc': FileUploadWidget(
                allowed_types=['application/pdf', 'image/*', 'text/*'],
                show_preview=True,
                max_file_size=50*1024*1024  # 50MB
            ),
            'doc_binary': FileUploadWidget(
                show_preview=False,
                max_file_size=100*1024*1024  # 100MB
            ),
            'keywords': TagInputWidget(
                max_tags=20,
                tag_colors=True,
                allow_duplicates=False
            ),
            'doc_text': ModernTextAreaWidget(
                auto_resize=True,
                show_stats=True,
                full_screen=True
            ),
            'doc_context': ModernTextAreaWidget(
                auto_resize=True,
                markdown_preview=True
            )
        },
        
        'CommentableMixin': {
            'comment_text': ModernTextAreaWidget(
                rich_text=True,
                auto_resize=True,
                show_stats=True
            )
        },
        
        'SchedulingMixin': {
            'start_time': DateTimeRangeWidget(
                include_time=True,
                predefined_ranges=True
            ),
            'end_time': DateTimeRangeWidget(
                include_time=True,
                predefined_ranges=True
            ),
            'recurrence_pattern': JSONEditorWidget(
                show_tree_view=False,
                auto_format=True
            )
        },
        
        'GeoLocationMixin': {
            'coordinates': ModernTextWidget(
                icon_prefix='fa-map-marker',
                validation_rules=[
                    {'type': 'pattern', 'options': {'pattern': r'^-?\d+\.?\d*,-?\d+\.?\d*$'}}
                ]
            )
        },
        
        'CurrencyMixin': {
            'amount': ModernTextWidget(
                icon_prefix='fa-dollar',
                validation_rules=[
                    {'type': 'number'},
                    {'type': 'minValue', 'options': {'min': 0}}
                ]
            ),
            'currency': Select2Widget()
        },
        
        'ProjectMixin': {
            'project_data': JSONEditorWidget(show_tree_view=True),
            'project_tags': TagInputWidget(
                max_tags=15,
                tag_colors=True
            ),
            'milestones': ArrayEditorWidget(
                item_type='text',
                sortable=True
            )
        },
        
        'VersioningMixin': {
            'version_data': JSONEditorWidget(
                readonly=True,
                show_tree_view=True
            )
        },
        
        'EncryptionMixin': {
            'encrypted_fields': ArrayEditorWidget(
                readonly=True,
                item_type='text'
            )
        },
        
        'SlugMixin': {
            'slug': ModernTextWidget(
                icon_prefix='fa-link',
                readonly=True,
                show_counter=True
            )
        },
        
        'TreeMixin': {
            'parent_id': Select2Widget(),
            'tree_path': ModernTextWidget(
                readonly=True,
                icon_prefix='fa-sitemap'
            )
        }
    }
    
    # Field type to widget mappings
    FIELD_TYPE_WIDGET_MAP = {
        'String': {
            'default': ModernTextWidget(),
            'email': ModernTextWidget(
                icon_prefix='fa-envelope',
                validation_rules=[{'type': 'email'}]
            ),
            'url': ModernTextWidget(
                icon_prefix='fa-link',
                validation_rules=[{'type': 'url'}]
            ),
            'password': ModernTextWidget(
                icon_suffix='fa-eye',
                validation_rules=[
                    {'type': 'strongPassword'}
                ]
            ),
            'color': ColorPickerWidget(
                show_palette=True,
                show_history=True
            ),
            'tags': TagInputWidget(
                max_tags=10,
                tag_colors=True
            )
        },
        
        'Text': {
            'default': ModernTextAreaWidget(
                auto_resize=True,
                show_stats=True
            ),
            'rich_text': ModernTextAreaWidget(
                rich_text=True,
                markdown_preview=True,
                auto_resize=True
            ),
            'code': ModernTextAreaWidget(
                syntax_highlighting='python',
                show_stats=True,
                full_screen=True
            ),
            'json': JSONEditorWidget(
                show_tree_view=True,
                enable_search=True
            )
        },
        
        'Integer': {
            'default': ModernTextWidget(
                validation_rules=[{'type': 'number'}]
            ),
            'percentage': ModernTextWidget(
                icon_suffix='fa-percent',
                validation_rules=[
                    {'type': 'number'},
                    {'type': 'minValue', 'options': {'min': 0}},
                    {'type': 'maxValue', 'options': {'max': 100}}
                ]
            ),
            'rating': ModernTextWidget(
                validation_rules=[
                    {'type': 'number'},
                    {'type': 'minValue', 'options': {'min': 1}},
                    {'type': 'maxValue', 'options': {'max': 5}}
                ]
            )
        },
        
        'DateTime': {
            'default': DateTimePickerWidget(),
            'range': DateTimeRangeWidget(
                include_time=True,
                predefined_ranges=True
            ),
            'date_only': DatePickerWidget(),
            'business_hours': DateTimeRangeWidget(
                include_time=True,
                business_hours_only=True
            )
        },
        
        'Boolean': {
            'default': Select2Widget(),
            'switch': ModernTextWidget()  # Would be implemented as toggle switch
        },
        
        'Enum': {
            'default': Select2Widget(),
            'multiple': Select2ManyWidget()
        }
    }
    
    @classmethod
    def get_widget_for_field(cls, model_class, field_name: str, field_type: str = None, 
                           field_info: Dict = None) -> Optional[Any]:
        """
        Get the optimal widget for a field based on model mixins and field characteristics.
        
        Args:
            model_class: The SQLAlchemy model class
            field_name: Name of the field
            field_type: Type of the field
            field_info: Additional field information
            
        Returns:
            Widget instance or None if no specific widget needed
        """
        field_info = field_info or {}
        
        # First check for mixin-specific mappings
        widget = cls._get_mixin_specific_widget(model_class, field_name)
        if widget:
            return widget
        
        # Then check for field-type specific mappings
        widget = cls._get_field_type_widget(field_name, field_type, field_info)
        if widget:
            return widget
        
        # Finally check for naming convention mappings
        widget = cls._get_convention_based_widget(field_name, field_info)
        if widget:
            return widget
        
        return None
    
    @classmethod
    def _get_mixin_specific_widget(cls, model_class, field_name: str) -> Optional[Any]:
        """Get widget based on model mixins."""
        for base in model_class.__mro__:
            mixin_name = base.__name__
            if mixin_name in cls.MIXIN_WIDGET_MAP:
                mixin_widgets = cls.MIXIN_WIDGET_MAP[mixin_name]
                if field_name in mixin_widgets:
                    return mixin_widgets[field_name]
        return None
    
    @classmethod
    def _get_field_type_widget(cls, field_name: str, field_type: str, 
                             field_info: Dict) -> Optional[Any]:
        """Get widget based on field type."""
        if not field_type or field_type not in cls.FIELD_TYPE_WIDGET_MAP:
            return None
        
        type_widgets = cls.FIELD_TYPE_WIDGET_MAP[field_type]
        
        # Check for specific subtypes based on field info
        subtype = field_info.get('subtype')
        if subtype and subtype in type_widgets:
            return type_widgets[subtype]
        
        # Check for naming conventions
        field_lower = field_name.lower()
        
        if field_type == 'String':
            if 'email' in field_lower:
                return type_widgets.get('email', type_widgets['default'])
            elif 'url' in field_lower or 'link' in field_lower:
                return type_widgets.get('url', type_widgets['default'])
            elif 'password' in field_lower:
                return type_widgets.get('password', type_widgets['default'])
            elif 'color' in field_lower:
                return type_widgets.get('color', type_widgets['default'])
            elif 'tag' in field_lower:
                return type_widgets.get('tags', type_widgets['default'])
        
        elif field_type == 'Text':
            if 'json' in field_lower:
                return type_widgets.get('json', type_widgets['default'])
            elif 'code' in field_lower or 'script' in field_lower:
                return type_widgets.get('code', type_widgets['default'])
            elif 'rich' in field_lower or 'formatted' in field_lower:
                return type_widgets.get('rich_text', type_widgets['default'])
        
        elif field_type == 'Integer':
            if 'percent' in field_lower:
                return type_widgets.get('percentage', type_widgets['default'])
            elif 'rating' in field_lower or 'score' in field_lower:
                return type_widgets.get('rating', type_widgets['default'])
        
        elif field_type == 'DateTime':
            if 'range' in field_lower or ('start' in field_lower and 'end' in field_lower):
                return type_widgets.get('range', type_widgets['default'])
            elif 'date' in field_lower and 'time' not in field_lower:
                return type_widgets.get('date_only', type_widgets['default'])
        
        return type_widgets.get('default')
    
    @classmethod
    def _get_convention_based_widget(cls, field_name: str, field_info: Dict) -> Optional[Any]:
        """Get widget based on naming conventions."""
        field_lower = field_name.lower()
        
        # Common naming patterns
        if field_lower.endswith('_json') or field_lower.endswith('_data'):
            return JSONEditorWidget(show_tree_view=True)
        
        elif field_lower.endswith('_tags') or field_lower.endswith('_keywords'):
            return TagInputWidget(max_tags=15, tag_colors=True)
        
        elif field_lower.endswith('_array') or field_lower.endswith('_list'):
            return ArrayEditorWidget(item_type='text', sortable=True)
        
        elif field_lower.endswith('_file') or field_lower.endswith('_upload'):
            return FileUploadWidget(show_preview=True)
        
        elif field_lower.endswith('_color') or field_lower.endswith('_colour'):
            return ColorPickerWidget(show_palette=True)
        
        elif field_lower.endswith('_range') or ('from' in field_lower and 'to' in field_lower):
            return DateTimeRangeWidget(include_time=True)
        
        elif field_lower.endswith('_long') or field_lower.endswith('_text') or field_lower.endswith('_description'):
            return ModernTextAreaWidget(auto_resize=True, show_stats=True)
        
        return None
    
    @classmethod
    def get_form_widget_mappings(cls, model_class) -> Dict[str, Any]:
        """
        Get complete widget mappings for a model's form fields.
        
        Args:
            model_class: The SQLAlchemy model class
            
        Returns:
            Dictionary mapping field names to widget instances
        """
        widget_mappings = {}
        
        # Get model columns
        try:
            from sqlalchemy import inspect
            inspector = inspect(model_class)
            
            for column in inspector.columns:
                field_name = column.name
                field_type = str(column.type.__class__.__name__)
                
                field_info = {
                    'nullable': column.nullable,
                    'default': column.default,
                    'primary_key': column.primary_key,
                    'foreign_key': bool(column.foreign_keys)
                }
                
                widget = cls.get_widget_for_field(
                    model_class, field_name, field_type, field_info
                )
                
                if widget:
                    widget_mappings[field_name] = widget
        
        except Exception as e:
            log.warning(f"Failed to get widget mappings for {model_class.__name__}: {e}")
        
        return widget_mappings
    
    @classmethod
    def apply_validation_rules(cls, model_class, widget_mappings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply validation rules to widgets based on model constraints.
        
        Args:
            model_class: The SQLAlchemy model class
            widget_mappings: Current widget mappings
            
        Returns:
            Updated widget mappings with validation rules
        """
        enhanced_mappings = {}
        
        try:
            from sqlalchemy import inspect
            inspector = inspect(model_class)
            
            for field_name, widget in widget_mappings.items():
                # Get column info
                column = None
                for col in inspector.columns:
                    if col.name == field_name:
                        column = col
                        break
                
                if not column:
                    enhanced_mappings[field_name] = widget
                    continue
                
                # Apply validation based on column constraints
                validation_rules = []
                
                # Required validation
                if not column.nullable:
                    validation_rules.append({'type': 'required'})
                
                # String length validation
                if hasattr(column.type, 'length') and column.type.length:
                    validation_rules.append({
                        'type': 'maxLength',
                        'options': {'max': column.type.length}
                    })
                
                # Numeric range validation
                if hasattr(column.type, 'scale') and column.type.scale:
                    validation_rules.append({'type': 'number'})
                
                # Create enhanced widget with validation
                if validation_rules and hasattr(widget, '__class__'):
                    if isinstance(widget, (ModernTextWidget, ModernTextAreaWidget)):
                        # Create new widget instance with validation
                        widget_class = widget.__class__
                        widget_kwargs = getattr(widget, '_init_kwargs', {})
                        widget_kwargs['validation_rules'] = validation_rules
                        enhanced_widget = widget_class(**widget_kwargs)
                        enhanced_mappings[field_name] = enhanced_widget
                    else:
                        enhanced_mappings[field_name] = widget
                else:
                    enhanced_mappings[field_name] = widget
        
        except Exception as e:
            log.warning(f"Failed to apply validation rules: {e}")
            enhanced_mappings = widget_mappings
        
        return enhanced_mappings


def auto_configure_model_widgets(model_class) -> Dict[str, Any]:
    """
    Automatically configure widgets for a model based on its mixins and fields.
    
    Args:
        model_class: The SQLAlchemy model class
        
    Returns:
        Dictionary of widget configurations for the model
    """
    # Get base widget mappings
    widget_mappings = MixinWidgetMapping.get_form_widget_mappings(model_class)
    
    # Apply validation rules
    widget_mappings = MixinWidgetMapping.apply_validation_rules(model_class, widget_mappings)
    
    # Log the configuration
    log.info(f"Auto-configured {len(widget_mappings)} widgets for {model_class.__name__}")
    
    return widget_mappings


def enhance_view_with_widgets(view_class, model_class):
    """
    Enhance a view class with automatically configured widgets.
    
    Args:
        view_class: The Flask-AppBuilder view class
        model_class: The SQLAlchemy model class
    """
    widget_mappings = auto_configure_model_widgets(model_class)
    
    if widget_mappings:
        # Set widget mappings on the view
        if not hasattr(view_class, 'add_form_widget'):
            view_class.add_form_widget = {}
        if not hasattr(view_class, 'edit_form_widget'):
            view_class.edit_form_widget = {}
        
        view_class.add_form_widget.update(widget_mappings)
        view_class.edit_form_widget.update(widget_mappings)
        
        log.info(f"Enhanced {view_class.__name__} with {len(widget_mappings)} widget mappings")


__all__ = [
    'MixinWidgetMapping',
    'auto_configure_model_widgets',
    'enhance_view_with_widgets'
]