"""
Enhanced Mixin Library for Flask-AppBuilder

This package integrates and extends the appgen mixins with Flask-AppBuilder,
providing a comprehensive suite of model mixins for advanced functionality.

Key Features:
- Direct integration with Flask-AppBuilder's User model
- Enhanced security and permissions
- Widget integration for complex data types
- View mixins for automatic CRUD enhancement
- Migration tools and compatibility helpers

Categories:
- Core Mixins: Base functionality (audit, versioning, soft delete)
- Data Mixins: Advanced data handling (encryption, caching, search)
- Business Mixins: Workflow, approval, multi-tenancy
- Content Mixins: Documents, comments, internationalization
- System Mixins: Replication, rate limiting, scheduling
- Integration Mixins: Flask-AppBuilder specific enhancements
"""

import logging
import sys
import os
from typing import Dict, List, Any, Optional, Type
from sqlalchemy.ext.declarative import declared_attr

# Add appgen mixins to path
appgen_mixins_path = '/Users/nyimbiodero/src/pjs/appgen/src/mixins'
if appgen_mixins_path not in sys.path:
    sys.path.insert(0, appgen_mixins_path)

# Import all appgen mixins
try:
    from tree_mixin import TreeMixin
    from base_mixin import BaseModelMixin
    from audit_log_mixin import AuditLogMixin
    from soft_delete_mixin import SoftDeleteMixin
    from versioning_mixin import VersioningMixin
    from encryption_mixin import EncryptionMixin
    from cache_mixin import CacheMixin
    from searchable_mixin import SearchableMixin
    from workflow_mixin import WorkflowMixin
    from approval_workflow_mixin import ApprovalWorkflowMixin
    from multi_tenancy_mixin import MultiTenancyMixin
    from internationalization_mixin import InternationalizationMixin
    from commentable_mixin import CommentableMixin
    from doc_mixin import DocMixin
    from import_export_mixin import ImportExportMixin
    from metadata_mixin import MetadataMixin
    from geo_location_mixin import GeoLocationMixin
    from project_mixin import ProjectMixin
    from scheduling_mixin import SchedulingMixin
    from rate_limit_mixin import RateLimitMixin
    from polymorphic_mixin import PolymorphicMixin
    from currency_mixin import CurrencyMixin
    from archive_mixin import ArchiveMixin
    from statemachine_mixin import StateMachineMixin
    from replication_mixin import ReplicationMixin
    from version_control_mixin import VersionControlMixin
    from full_text_search_mixin import FullTextSearchMixin
    from slug_mixin import SlugMixin
    
    APPGEN_MIXINS_AVAILABLE = True
    log = logging.getLogger(__name__)
    log.info("Successfully imported appgen mixins")
    
except ImportError as e:
    APPGEN_MIXINS_AVAILABLE = False
    log = logging.getLogger(__name__)
    log.warning(f"Could not import appgen mixins: {e}")
    
    # Create placeholder classes to prevent import errors
    class TreeMixin: pass
    class BaseModelMixin: pass
    class AuditLogMixin: pass
    class SoftDeleteMixin: pass
    class VersioningMixin: pass
    class EncryptionMixin: pass
    class CacheMixin: pass
    class SearchableMixin: pass
    class WorkflowMixin: pass
    class ApprovalWorkflowMixin: pass
    class MultiTenancyMixin: pass
    class InternationalizationMixin: pass
    class CommentableMixin: pass
    class DocMixin: pass
    class ImportExportMixin: pass
    class MetadataMixin: pass
    class GeoLocationMixin: pass
    class ProjectMixin: pass
    class SchedulingMixin: pass
    class RateLimitMixin: pass
    class PolymorphicMixin: pass
    class CurrencyMixin: pass
    class ArchiveMixin: pass
    class StateMachineMixin: pass
    class ReplicationMixin: pass
    class VersionControlMixin: pass
    class FullTextSearchMixin: pass
    class SlugMixin: pass

# Import Flask-AppBuilder integration enhancements
from .fab_integration import *
from .view_mixins import *
from .widget_integration import *
from .migration_tools import *

# Mixin registry for documentation and discovery
MIXIN_REGISTRY = {
    'core': {
        'BaseModelMixin': {
            'class': BaseModelMixin,
            'description': 'Base functionality with audit fields, soft delete, and versioning',
            'features': ['audit_trail', 'soft_delete', 'versioning', 'completion_tracking'],
            'flask_appbuilder_ready': True
        },
        'AuditLogMixin': {
            'class': AuditLogMixin,
            'description': 'Detailed audit logging of all model changes',
            'features': ['change_tracking', 'user_attribution', 'custom_logs'],
            'flask_appbuilder_ready': True
        },
        'SoftDeleteMixin': {
            'class': SoftDeleteMixin,
            'description': 'Soft delete functionality to avoid data loss',
            'features': ['soft_delete', 'restore', 'filtered_queries'],
            'flask_appbuilder_ready': True
        },
        'VersioningMixin': {
            'class': VersioningMixin,
            'description': 'Version control for model instances',
            'features': ['version_history', 'rollback', 'branching'],
            'flask_appbuilder_ready': True
        }
    },
    'data': {
        'EncryptionMixin': {
            'class': EncryptionMixin,
            'description': 'Field-level encryption for sensitive data',
            'features': ['field_encryption', 'key_management', 'migration_tools'],
            'flask_appbuilder_ready': True
        },
        'CacheMixin': {
            'class': CacheMixin,
            'description': 'Caching functionality for improved performance',
            'features': ['instance_caching', 'query_caching', 'cache_invalidation'],
            'flask_appbuilder_ready': True
        },
        'SearchableMixin': {
            'class': SearchableMixin,
            'description': 'Full-text search capabilities',
            'features': ['text_indexing', 'ranked_search', 'highlighting'],
            'flask_appbuilder_ready': True
        },
        'MetadataMixin': {
            'class': MetadataMixin,
            'description': 'Flexible metadata storage',
            'features': ['schema_less_data', 'dynamic_fields', 'metadata_search'],
            'flask_appbuilder_ready': True
        },
        'ImportExportMixin': {
            'class': ImportExportMixin,
            'description': 'Data import and export functionality',
            'features': ['csv_export', 'excel_support', 'json_import', 'validation'],
            'flask_appbuilder_ready': True
        }
    },
    'business': {
        'WorkflowMixin': {
            'class': WorkflowMixin,
            'description': 'State-based workflow management',
            'features': ['state_machine', 'transitions', 'workflow_actions'],
            'flask_appbuilder_ready': True
        },
        'ApprovalWorkflowMixin': {
            'class': ApprovalWorkflowMixin,
            'description': 'Multi-step approval processes',
            'features': ['approval_steps', 'parallel_approvals', 'conditional_logic'],
            'flask_appbuilder_ready': True
        },
        'MultiTenancyMixin': {
            'class': MultiTenancyMixin,
            'description': 'Multi-tenant data isolation',
            'features': ['tenant_scoping', 'data_isolation', 'shared_resources'],
            'flask_appbuilder_ready': True
        },
        'StateTrackingMixin': {
            'class': StateTrackingMixin,
            'description': 'Model state management and transitions',
            'features': ['status_tracking', 'audit_trail', 'transition_validation'],
            'flask_appbuilder_ready': True
        },
        'ProjectMixin': {
            'class': ProjectMixin,
            'description': 'Comprehensive project management',
            'features': ['project_tracking', 'team_management', 'gantt_charts'],
            'flask_appbuilder_ready': True
        },
        'SchedulingMixin': {
            'class': SchedulingMixin,
            'description': 'Task and event scheduling',
            'features': ['recurring_events', 'timezone_support', 'dependencies'],
            'flask_appbuilder_ready': True
        }
    },
    'content': {
        'DocMixin': {
            'class': DocMixin,
            'description': 'Document management and processing',
            'features': ['file_handling', 'metadata_extraction', 'content_analysis'],
            'flask_appbuilder_ready': True
        },
        'CommentableMixin': {
            'class': CommentableMixin,
            'description': 'Advanced commenting system',
            'features': ['nested_comments', 'moderation', 'voting'],
            'flask_appbuilder_ready': True
        },
        'InternationalizationMixin': {
            'class': InternationalizationMixin,
            'description': 'Multi-language content support',
            'features': ['translation_management', 'fallback_languages', 'bulk_operations'],
            'flask_appbuilder_ready': True
        },
        'SlugMixin': {
            'class': SlugMixin,
            'description': 'URL-friendly slug generation',
            'features': ['automatic_slugs', 'uniqueness', 'seo_friendly'],
            'flask_appbuilder_ready': True
        }
    },
    'system': {
        'ReplicationMixin': {
            'class': ReplicationMixin,
            'description': 'Data replication across databases',
            'features': ['multi_database', 'conflict_resolution', 'sync_status'],
            'flask_appbuilder_ready': False
        },
        'RateLimitMixin': {
            'class': RateLimitMixin,
            'description': 'Rate limiting for API operations',
            'features': ['request_throttling', 'per_user_limits', 'redis_backend'],
            'flask_appbuilder_ready': True
        },
        'StateMachineMixin': {
            'class': StateMachineMixin,
            'description': 'Advanced state machine with visualization',
            'features': ['state_transitions', 'event_handling', 'mermaid_diagrams'],
            'flask_appbuilder_ready': True
        },
        'VersionControlMixin': {
            'class': VersionControlMixin,
            'description': 'Git-like version control for data',
            'features': ['branching', 'merging', 'diff_tracking'],
            'flask_appbuilder_ready': False
        }
    },
    'specialized': {
        'TreeMixin': {
            'class': TreeMixin,
            'description': 'Hierarchical tree structures',
            'features': ['parent_child', 'tree_traversal', 'depth_queries'],
            'flask_appbuilder_ready': True
        },
        'PolymorphicMixin': {
            'class': PolymorphicMixin,
            'description': 'Polymorphic inheritance support',
            'features': ['table_inheritance', 'polymorphic_queries', 'dynamic_types'],
            'flask_appbuilder_ready': False
        },
        'CurrencyMixin': {
            'class': CurrencyMixin,
            'description': 'Currency handling and conversion',
            'features': ['exchange_rates', 'currency_math', 'formatting'],
            'flask_appbuilder_ready': True
        },
        'GeoLocationMixin': {
            'class': GeoLocationMixin,
            'description': 'Geolocation and spatial operations',
            'features': ['coordinates', 'distance_calculations', 'geocoding'],
            'flask_appbuilder_ready': True
        },
        'ArchiveMixin': {
            'class': ArchiveMixin,
            'description': 'Data archiving and lifecycle management',
            'features': ['automatic_archiving', 'retention_policies', 'restore_capability'],
            'flask_appbuilder_ready': True
        }
    }
}

# Convenience functions for mixin discovery
def get_all_mixins() -> Dict[str, Dict]:
    """Get all available mixins organized by category."""
    return MIXIN_REGISTRY

def get_flask_appbuilder_ready_mixins() -> Dict[str, Dict]:
    """Get mixins that are ready for Flask-AppBuilder integration."""
    ready_mixins = {}
    for category, mixins in MIXIN_REGISTRY.items():
        ready_category = {}
        for name, info in mixins.items():
            if info.get('flask_appbuilder_ready', False):
                ready_category[name] = info
        if ready_category:
            ready_mixins[category] = ready_category
    return ready_mixins

def get_mixin_by_name(name: str) -> Optional[Type]:
    """Get a mixin class by name."""
    for category, mixins in MIXIN_REGISTRY.items():
        if name in mixins:
            return mixins[name]['class']
    return None

def get_mixins_by_feature(feature: str) -> List[Dict]:
    """Get all mixins that provide a specific feature."""
    matching_mixins = []
    for category, mixins in MIXIN_REGISTRY.items():
        for name, info in mixins.items():
            if feature in info.get('features', []):
                matching_mixins.append({
                    'name': name,
                    'category': category,
                    'class': info['class'],
                    'info': info
                })
    return matching_mixins

def create_enhanced_model(base_class, mixins: List[str], **kwargs):
    """
    Create an enhanced model class with specified mixins.
    
    Args:
        base_class: The base SQLAlchemy model class
        mixins: List of mixin names to include
        **kwargs: Additional attributes for the model
    
    Returns:
        Enhanced model class with mixins applied
    """
    mixin_classes = []
    for mixin_name in mixins:
        mixin_class = get_mixin_by_name(mixin_name)
        if mixin_class:
            mixin_classes.append(mixin_class)
    
    # Create dynamic class with all mixins
    class_name = f"Enhanced{base_class.__name__}"
    enhanced_class = type(class_name, tuple(mixin_classes + [base_class]), kwargs)
    
    return enhanced_class

# Export commonly used mixins
__all__ = [
    # Core mixins
    'BaseModelMixin',
    'AuditLogMixin', 
    'SoftDeleteMixin',
    'VersioningMixin',
    
    # Data mixins
    'EncryptionMixin',
    'CacheMixin',
    'SearchableMixin',
    'MetadataMixin',
    'ImportExportMixin',
    
    # Business mixins
    'WorkflowMixin',
    'ApprovalWorkflowMixin',
    'MultiTenancyMixin',
    'ProjectMixin',
    'SchedulingMixin',
    
    # Content mixins
    'DocMixin',
    'CommentableMixin',
    'InternationalizationMixin',
    'SlugMixin',
    
    # System mixins
    'ReplicationMixin',
    'RateLimitMixin',
    'StateMachineMixin',
    'VersionControlMixin',
    
    # Specialized mixins
    'TreeMixin',
    'PolymorphicMixin',
    'CurrencyMixin',
    'GeoLocationMixin',
    'ArchiveMixin',
    
    # Integration classes
    'FABIntegratedModel',
    'EnhancedModelView',
    'MixinWidgetMapping',
    'MigrationHelper',
    
    # Utility functions
    'get_all_mixins',
    'get_flask_appbuilder_ready_mixins',
    'get_mixin_by_name',
    'get_mixins_by_feature',
    'create_enhanced_model',
    
    # Registry
    'MIXIN_REGISTRY',
    'APPGEN_MIXINS_AVAILABLE'
]