"""
Enhanced Flask-AppBuilder Configuration Example

This example shows how to configure a Flask-AppBuilder application to use
the new advanced features including:
- Advanced Analytics BI Platform (MetricCardWidget, Dashboard Layout Manager)
- Export Enhancement System (CSV/Excel/PDF exports)
- Basic Alerting System (threshold monitoring)

Copy this configuration and adapt it to your needs.
"""

import os
from datetime import timedelta

# Base Flask configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Database configuration
SQLALCHEMY_DATABASE_URI = os.environ.get(
    'DATABASE_URL', 
    'sqlite:///app.db'  # For development - use PostgreSQL/MySQL in production
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_recycle': 3600,
    'pool_pre_ping': True
}

# Flask-AppBuilder Configuration
APP_NAME = "Enhanced Analytics Platform"
APP_THEME = "bootstrap4"  # or "cerulean", "cosmo", "cyborg", "darkly", "flatly", etc.
APP_ICON = "fa-dashboard"

# Authentication configuration
AUTH_TYPE = 1  # Database authentication
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'

# Session configuration
PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

# Security configuration
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# Enhanced Features: Register the new addon managers
ADDON_MANAGERS = [
    # Alerting System Manager
    'flask_appbuilder.alerting.manager.AlertingManager',
    
    # Export Enhancement Manager  
    'flask_appbuilder.export.manager.ExportManager',
    
    # Add other existing managers here if you have them
    # 'your_app.custom_manager.CustomManager',
]

# ===========================
# Advanced Analytics Configuration
# ===========================

# Dashboard configuration
DASHBOARD_CONFIG = {
    'default_refresh_interval': 30,  # seconds
    'max_widgets_per_dashboard': 20,
    'enable_public_dashboards': True,
    'default_layout': 'grid',
    'grid_settings': {
        'columns': 12,
        'row_height': 150,
        'margin': [10, 10]
    }
}

# Metric card configuration
METRIC_CARD_CONFIG = {
    'show_trends_by_default': True,
    'default_trend_period': '24h',
    'enable_sparklines': True,
    'decimal_precision': 2
}

# ===========================
# Export System Configuration
# ===========================

# Export configuration
EXPORT_CONFIG = {
    'enabled_formats': ['csv', 'xlsx', 'pdf'],
    'max_export_records': 100000,
    'export_timeout': 300,  # seconds
    'cleanup_after_days': 7,
    'temp_directory': '/tmp/fab_exports',
    'max_concurrent_exports': 5
}

# Export format specific settings
EXPORT_FORMAT_SETTINGS = {
    'csv': {
        'delimiter': ',',
        'quote_char': '"',
        'encoding': 'utf-8'
    },
    'xlsx': {
        'include_index': False,
        'freeze_panes': (1, 0),  # Freeze header row
        'auto_filter': True
    },
    'pdf': {
        'page_size': 'A4',
        'orientation': 'landscape',
        'margin': 0.5,
        'include_charts': True
    }
}

# ===========================
# Alerting System Configuration  
# ===========================

# Alerting configuration
ALERTING_CONFIG = {
    'enabled': True,
    'check_interval': 60,  # seconds
    'max_concurrent_checks': 10,
    'default_cooldown': 15,  # minutes
    'max_alert_history': 10000
}

# Notification settings
NOTIFICATION_CONFIG = {
    # Email notifications
    'email': {
        'enabled': True,
        'smtp_server': os.environ.get('SMTP_SERVER', 'localhost'),
        'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
        'smtp_username': os.environ.get('SMTP_USERNAME'),
        'smtp_password': os.environ.get('SMTP_PASSWORD'),
        'smtp_use_tls': True,
        'from_address': os.environ.get('SMTP_FROM', 'alerts@example.com'),
        'default_recipients': ['admin@example.com']
    },
    
    # Webhook notifications
    'webhook': {
        'enabled': False,
        'default_urls': [],
        'timeout': 30,
        'retry_attempts': 3,
        'retry_delay': 5  # seconds
    },
    
    # In-app notifications
    'inapp': {
        'enabled': True,
        'auto_dismiss': 0,  # 0 = manual dismiss
        'sound_enabled': True,
        'desktop_notifications': True
    }
}

# Metric providers configuration - Register your custom metrics here
METRIC_PROVIDERS = {
    'system': {
        'cpu_usage': 'your_app.metrics.get_cpu_usage',
        'memory_usage': 'your_app.metrics.get_memory_usage',
        'disk_usage': 'your_app.metrics.get_disk_usage'
    },
    'application': {
        'active_users': 'your_app.metrics.get_active_users',
        'total_orders': 'your_app.metrics.get_total_orders',
        'revenue_today': 'your_app.metrics.get_revenue_today'
    }
}

# ===========================
# Optional: Advanced Settings
# ===========================

# Caching (recommended for production)
CACHE_TYPE = "simple"  # Use Redis in production: "redis"
CACHE_DEFAULT_TIMEOUT = 300

# Rate limiting
RATELIMIT_ENABLED = False
RATELIMIT_STORAGE_URL = "memory://"  # Use Redis in production

# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'app.log',
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    },
    'loggers': {
        'flask_appbuilder': {
            'level': 'INFO',
            'handlers': ['wsgi'],
            'propagate': False
        },
        'flask_appbuilder.alerting': {
            'level': 'DEBUG',
            'handlers': ['wsgi', 'file'],
            'propagate': False
        }
    }
}

# ===========================
# Production Considerations
# ===========================

# For production, consider:
# 1. Use PostgreSQL or MySQL instead of SQLite
# 2. Configure proper SMTP settings for email alerts
# 3. Set up Redis for caching and session storage
# 4. Enable SSL/TLS
# 5. Configure proper logging
# 6. Set strong SECRET_KEY
# 7. Configure backup and monitoring

# Example production database URL:
# SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@host:5432/database'

# Example Redis configuration:
# CACHE_TYPE = "redis"
# CACHE_REDIS_URL = "redis://localhost:6379"
# SESSION_TYPE = "redis"
# SESSION_REDIS = redis.from_url("redis://localhost:6379")

# Security headers (recommended)
SECURITY_HEADERS = {
    'content_security_policy': {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' 'unsafe-eval'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data:",
        'font-src': "'self'"
    },
    'force_https': False,  # Set to True in production with SSL
    'session_cookie_secure': False,  # Set to True in production with SSL
    'session_cookie_httponly': True,
    'session_cookie_samesite': 'Lax'
}

# Feature flags - Enable/disable features as needed
FEATURE_FLAGS = {
    'alerting_enabled': True,
    'export_enabled': True,
    'dashboard_customization': True,
    'public_dashboards': True,
    'scheduled_exports': True,
    'webhook_notifications': False,
    'advanced_metrics': True
}