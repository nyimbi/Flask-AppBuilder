"""
Full Application Generator for Flask-AppBuilder

Generates complete, production-ready Flask-AppBuilder applications with:
- Modern project structure and configuration
- Authentication and authorization setup
- Automatic navigation generation
- Docker and deployment support
- Testing framework setup
- Documentation generation
- CI/CD pipeline configuration
- Performance monitoring
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from pathlib import Path
from jinja2 import Environment, BaseLoader, Template

from .database_inspector import EnhancedDatabaseInspector
from .model_generator import EnhancedModelGenerator, ModelGenerationConfig
from .view_generator import BeautifulViewGenerator, ViewGenerationConfig

logger = logging.getLogger(__name__)


@dataclass
class AppGenerationConfig:
    """Configuration for application generation."""
    app_name: str
    app_title: str = ""
    app_description: str = ""
    author_name: str = ""
    author_email: str = ""
    version: str = "1.0.0"

    # Feature flags
    enable_auth: bool = True
    enable_oauth: bool = True
    enable_ldap: bool = False
    enable_api: bool = True
    enable_websockets: bool = True
    enable_caching: bool = True
    enable_celery: bool = True
    enable_monitoring: bool = True
    enable_logging: bool = True

    # Deployment
    enable_docker: bool = True
    enable_kubernetes: bool = False
    enable_ci_cd: bool = True
    cloud_provider: str = "generic"  # aws, gcp, azure, generic

    # Security
    security_level: str = "medium"  # basic, medium, high
    enable_2fa: bool = False
    enable_audit: bool = True

    # Database
    database_type: str = "postgresql"
    enable_migrations: bool = True
    enable_seeds: bool = True

    # Frontend
    enable_modern_ui: bool = True
    enable_pwa: bool = False
    theme: str = "modern"

    # Testing
    enable_testing: bool = True
    enable_e2e_tests: bool = True
    enable_load_tests: bool = False


class FullAppGenerator:
    """
    Complete application generator that creates production-ready Flask-AppBuilder apps.

    Features:
    - Complete project structure generation
    - Integration of enhanced models and views
    - Authentication and authorization setup
    - Modern configuration management
    - Docker and deployment support
    - Testing framework integration
    - Documentation generation
    - CI/CD pipeline setup
    - Performance monitoring
    - Security best practices
    """

    def __init__(
        self,
        inspector: EnhancedDatabaseInspector,
        config: AppGenerationConfig,
        output_dir: str
    ):
        """
        Initialize the app generator.

        Args:
            inspector: Enhanced database inspector instance
            config: Application generation configuration
            output_dir: Output directory for generated application
        """
        self.inspector = inspector
        self.config = config
        self.output_dir = Path(output_dir)
        self.jinja_env = Environment(loader=BaseLoader())

        # Component generators
        self.model_generator = EnhancedModelGenerator(
            inspector,
            ModelGenerationConfig(
                generate_pydantic=config.enable_api,
                generate_validation=True,
                security_features=config.security_level != "basic"
            )
        )

        self.view_generator = BeautifulViewGenerator(
            inspector,
            ViewGenerationConfig(
                use_modern_widgets=config.enable_modern_ui,
                generate_api_views=config.enable_api,
                enable_real_time=config.enable_websockets,
                security_enabled=config.security_level != "basic"
            )
        )

        # Generation state
        self.generated_files: Dict[str, str] = {}
        self.project_structure: Dict[str, Any] = {}

        logger.info(f"Full app generator initialized for: {config.app_name}")

    def generate_complete_app(self) -> Dict[str, Any]:
        """
        Generate complete Flask-AppBuilder application.

        Returns:
            Dictionary with generation results and file paths
        """
        logger.info("Starting complete application generation...")

        # Create project structure
        self._create_project_structure()

        # Generate core components
        self._generate_core_files()
        self._generate_models()
        self._generate_views()
        self._generate_authentication()
        self._generate_navigation()
        self._generate_api()

        # Generate supporting infrastructure
        self._generate_configuration()
        self._generate_database_setup()
        self._generate_static_assets()
        self._generate_templates()

        # Generate development and deployment files
        self._generate_development_files()
        if self.config.enable_docker:
            self._generate_docker_files()
        if self.config.enable_ci_cd:
            self._generate_ci_cd_files()
        if self.config.enable_testing:
            self._generate_test_files()

        # Generate documentation
        self._generate_documentation()

        # Write all files to disk
        self._write_files_to_disk()

        result = {
            'status': 'success',
            'app_name': self.config.app_name,
            'output_dir': str(self.output_dir),
            'files_generated': len(self.generated_files),
            'project_structure': self.project_structure,
            'next_steps': self._generate_next_steps()
        }

        logger.info(f"Application generation complete: {result['files_generated']} files generated")
        return result

    def _create_project_structure(self):
        """Create the project directory structure."""
        structure = {
            'app': {
                'models': {},
                'views': {},
                'api': {},
                'templates': {
                    'layouts': {},
                    'forms': {},
                    'lists': {},
                    'charts': {}
                },
                'static': {
                    'css': {},
                    'js': {},
                    'img': {},
                    'fonts': {}
                },
                'translations': {},
                'utils': {}
            },
            'migrations': {'versions': {}},
            'tests': {
                'unit': {},
                'integration': {},
                'e2e': {}
            },
            'docs': {},
            'config': {},
            'scripts': {},
            'docker': {}
        }

        self.project_structure = structure

        # Create directories
        for path in self._flatten_structure(structure):
            full_path = self.output_dir / path
            full_path.mkdir(parents=True, exist_ok=True)

    def _generate_core_files(self):
        """Generate core application files."""
        # Main app.py
        self.generated_files['app.py'] = self._generate_main_app()

        # __init__.py files
        self.generated_files['app/__init__.py'] = self._generate_app_init()
        self.generated_files['app/models/__init__.py'] = self._generate_models_init()
        self.generated_files['app/views/__init__.py'] = self._generate_views_init()
        self.generated_files['app/api/__init__.py'] = self._generate_api_init()

        # Requirements and setup
        self.generated_files['requirements.txt'] = self._generate_requirements()
        self.generated_files['setup.py'] = self._generate_setup_py()
        self.generated_files['pyproject.toml'] = self._generate_pyproject_toml()

        # Environment files
        self.generated_files['.env.example'] = self._generate_env_example()
        self.generated_files['.gitignore'] = self._generate_gitignore()

    def _generate_models(self):
        """Generate model files."""
        models = self.model_generator.generate_all_models()

        self.generated_files['app/models/models.py'] = models['models.py']
        if models.get('schemas.py'):
            self.generated_files['app/models/schemas.py'] = models['schemas.py']
        if models.get('validators.py'):
            self.generated_files['app/models/validators.py'] = models['validators.py']

    def _generate_views(self):
        """Generate view files."""
        views_result = self.view_generator.generate_all_views()
        views = views_result['views']

        # Generate view files
        for table_name, table_views in views.items():
            for view_type, view_code in table_views.items():
                filename = f"app/views/{table_name}_{view_type}.py"
                self.generated_files[filename] = view_code

        # Generate supporting files
        supporting_files = views_result.get('supporting_files', {})
        for filename, content in supporting_files.items():
            if filename.endswith('.py'):
                self.generated_files[f'app/views/{filename}'] = content
            elif filename.endswith('.js'):
                self.generated_files[f'app/static/js/{filename}'] = content
            elif filename.endswith('.css'):
                self.generated_files[f'app/static/css/{filename}'] = content
            elif filename.endswith('.html'):
                self.generated_files[f'app/templates/{filename}'] = content

    def _generate_authentication(self):
        """Generate authentication configuration."""
        if not self.config.enable_auth:
            return

        # Custom security manager
        self.generated_files['app/security.py'] = self._generate_security_manager()

        # OAuth configuration
        if self.config.enable_oauth:
            self.generated_files['app/oauth.py'] = self._generate_oauth_config()

        # LDAP configuration
        if self.config.enable_ldap:
            self.generated_files['app/ldap.py'] = self._generate_ldap_config()

    def _generate_navigation(self):
        """Generate navigation menu based on database structure."""
        database_analysis = self.inspector.analyze_database()

        # Group tables by category
        categories = {}
        for table_name, table_info in database_analysis['tables'].items():
            category = table_info.category
            if category not in categories:
                categories[category] = []
            categories[category].append(table_info)

        self.generated_files['app/navigation.py'] = self._generate_navigation_config(categories)

    def _generate_api(self):
        """Generate API configuration and documentation."""
        if not self.config.enable_api:
            return

        # API blueprint
        self.generated_files['app/api/api.py'] = self._generate_api_blueprint()

        # OpenAPI/Swagger configuration
        self.generated_files['app/api/swagger.py'] = self._generate_swagger_config()

        # API authentication
        self.generated_files['app/api/auth.py'] = self._generate_api_auth()

    def _generate_configuration(self):
        """Generate configuration files."""
        # Main config
        self.generated_files['config/config.py'] = self._generate_main_config()

        # Environment-specific configs
        self.generated_files['config/development.py'] = self._generate_dev_config()
        self.generated_files['config/production.py'] = self._generate_prod_config()
        self.generated_files['config/testing.py'] = self._generate_test_config()

    def _generate_database_setup(self):
        """Generate database setup and migration files."""
        # Migration configuration
        self.generated_files['migrations/alembic.ini'] = self._generate_alembic_config()
        self.generated_files['migrations/env.py'] = self._generate_migration_env()
        self.generated_files['migrations/script.py.mako'] = self._generate_migration_template()

        # Database initialization
        self.generated_files['scripts/init_db.py'] = self._generate_db_init_script()

        # Seed data
        if self.config.enable_seeds:
            self.generated_files['scripts/seed_data.py'] = self._generate_seed_data()

    def _generate_static_assets(self):
        """Generate static assets."""
        # Custom CSS
        self.generated_files['app/static/css/custom.css'] = self._generate_custom_css()

        # Custom JavaScript
        self.generated_files['app/static/js/custom.js'] = self._generate_custom_js()

        # Favicon and icons
        self.generated_files['app/static/img/favicon.ico'] = "# Favicon placeholder"

        # Service Worker for PWA
        if self.config.enable_pwa:
            self.generated_files['app/static/js/service-worker.js'] = self._generate_service_worker()
            self.generated_files['app/static/manifest.json'] = self._generate_web_manifest()

    def _generate_templates(self):
        """Generate custom templates."""
        # Base template
        self.generated_files['app/templates/base.html'] = self._generate_base_template()

        # Custom login template
        if self.config.enable_auth:
            self.generated_files['app/templates/login.html'] = self._generate_login_template()

        # Dashboard template
        self.generated_files['app/templates/dashboard.html'] = self._generate_dashboard_template()

    def _generate_development_files(self):
        """Generate development support files."""
        # Development server
        self.generated_files['run_dev.py'] = self._generate_dev_server()

        # Pre-commit hooks
        self.generated_files['.pre-commit-config.yaml'] = self._generate_pre_commit_config()

        # IDE configuration
        self.generated_files['.vscode/settings.json'] = self._generate_vscode_settings()
        self.generated_files['.vscode/launch.json'] = self._generate_vscode_launch()

    def _generate_docker_files(self):
        """Generate Docker configuration."""
        self.generated_files['Dockerfile'] = self._generate_dockerfile()
        self.generated_files['docker-compose.yml'] = self._generate_docker_compose()
        self.generated_files['docker-compose.dev.yml'] = self._generate_docker_compose_dev()
        self.generated_files['.dockerignore'] = self._generate_dockerignore()

        # Kubernetes manifests
        if self.config.enable_kubernetes:
            self.generated_files['k8s/deployment.yaml'] = self._generate_k8s_deployment()
            self.generated_files['k8s/service.yaml'] = self._generate_k8s_service()
            self.generated_files['k8s/ingress.yaml'] = self._generate_k8s_ingress()

    def _generate_ci_cd_files(self):
        """Generate CI/CD pipeline configuration."""
        # GitHub Actions
        self.generated_files['.github/workflows/ci.yml'] = self._generate_github_actions()
        self.generated_files['.github/workflows/deploy.yml'] = self._generate_deploy_workflow()

        # GitLab CI (alternative)
        self.generated_files['.gitlab-ci.yml'] = self._generate_gitlab_ci()

    def _generate_test_files(self):
        """Generate testing framework files."""
        # Test configuration
        self.generated_files['pytest.ini'] = self._generate_pytest_config()
        self.generated_files['conftest.py'] = self._generate_conftest()

        # Unit tests
        self.generated_files['tests/unit/test_models.py'] = self._generate_model_tests()
        self.generated_files['tests/unit/test_views.py'] = self._generate_view_tests()

        # Integration tests
        self.generated_files['tests/integration/test_api.py'] = self._generate_api_tests()

        # E2E tests
        if self.config.enable_e2e_tests:
            self.generated_files['tests/e2e/test_user_flows.py'] = self._generate_e2e_tests()

    def _generate_documentation(self):
        """Generate project documentation."""
        # Main README
        self.generated_files['README.md'] = self._generate_readme()

        # API documentation
        self.generated_files['docs/API.md'] = self._generate_api_docs()

        # Development guide
        self.generated_files['docs/DEVELOPMENT.md'] = self._generate_dev_docs()

        # Deployment guide
        self.generated_files['docs/DEPLOYMENT.md'] = self._generate_deployment_docs()

        # Architecture documentation
        self.generated_files['docs/ARCHITECTURE.md'] = self._generate_architecture_docs()

    def _write_files_to_disk(self):
        """Write all generated files to disk."""
        for file_path, content in self.generated_files.items():
            full_path = self.output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

        logger.info(f"Written {len(self.generated_files)} files to {self.output_dir}")

    def _flatten_structure(self, structure: Dict[str, Any], parent: str = "") -> List[str]:
        """Flatten nested structure dictionary to list of paths."""
        paths = []
        for key, value in structure.items():
            current_path = f"{parent}/{key}" if parent else key
            paths.append(current_path)
            if isinstance(value, dict):
                paths.extend(self._flatten_structure(value, current_path))
        return paths

    def _generate_main_app(self) -> str:
        """Generate main app.py file."""
        template = '''
"""
{{ config.app_title or config.app_name }} Flask-AppBuilder Application

{{ config.app_description }}

Generated: {{ timestamp }}
Version: {{ config.version }}
Author: {{ config.author_name }} <{{ config.author_email }}>
"""

import os
from flask import Flask
from flask_appbuilder import AppBuilder, SQLA

from app.config import Config
{% if config.enable_auth %}
from app.security import CustomSecurityManager
{% endif %}
{% if config.enable_api %}
from app.api import init_api
{% endif %}
{% if config.enable_websockets %}
from flask_socketio import SocketIO
{% endif %}
{% if config.enable_caching %}
from flask_caching import Cache
{% endif %}
{% if config.enable_monitoring %}
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
{% endif %}

# Initialize extensions
db = SQLA()
appbuilder = None
{% if config.enable_websockets %}
socketio = SocketIO()
{% endif %}
{% if config.enable_caching %}
cache = Cache()
{% endif %}
{% if config.enable_monitoring %}
limiter = Limiter(key_func=get_remote_address)
{% endif %}


def create_app(config_name=None):
    """Application factory pattern."""
    app = Flask(__name__)

    # Configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(Config.get_config(config_name))

    # Initialize extensions
    db.init_app(app)
    {% if config.enable_caching %}
    cache.init_app(app)
    {% endif %}
    {% if config.enable_monitoring %}
    limiter.init_app(app)
    {% endif %}
    {% if config.enable_websockets %}
    socketio.init_app(app, cors_allowed_origins="*")
    {% endif %}

    # Initialize AppBuilder
    global appbuilder
    {% if config.enable_auth %}
    appbuilder = AppBuilder(app, db.session, security_manager_class=CustomSecurityManager)
    {% else %}
    appbuilder = AppBuilder(app, db.session)
    {% endif %}

    # Import views and register them
    from app.views import register_views
    register_views(appbuilder)

    {% if config.enable_api %}
    # Initialize API
    init_api(appbuilder)
    {% endif %}

    return app


def main():
    """Main entry point for development server."""
    app = create_app('development')
    {% if config.enable_websockets %}
    socketio.run(app, debug=True, host='0.0.0.0', port=8080)
    {% else %}
    app.run(debug=True, host='0.0.0.0', port=8080)
    {% endif %}


if __name__ == '__main__':
    main()
        '''.strip()

        template_obj = self.jinja_env.from_string(template)
        return template_obj.render(
            config=self.config,
            timestamp=datetime.now().isoformat()
        )

    def _generate_next_steps(self) -> List[str]:
        """Generate next steps for the user."""
        steps = [
            f"cd {self.output_dir}",
            "python -m venv venv",
            "source venv/bin/activate  # On Windows: venv\\Scripts\\activate",
            "pip install -r requirements.txt",
            "cp .env.example .env",
            "# Edit .env with your database connection details",
            "python scripts/init_db.py",
            "python app.py"
        ]

        if self.config.enable_docker:
            steps.extend([
                "",
                "# Or using Docker:",
                "docker-compose up --build"
            ])

        return steps

    # Template generation methods would continue here...
    # I'll include a few key ones to show the pattern:

    def _generate_requirements(self) -> str:
        """Generate requirements.txt file."""
        requirements = [
            "Flask-AppBuilder>=4.0.0",
            "Flask>=2.0.0",
            "SQLAlchemy>=2.0.0",
            "alembic>=1.8.0",
            "marshmallow>=3.0.0",
            "python-dotenv>=0.19.0"
        ]

        if self.config.enable_api:
            requirements.extend([
                "flask-restx>=1.0.0",
                "flask-cors>=3.0.0"
            ])

        if self.config.enable_websockets:
            requirements.extend([
                "flask-socketio>=5.0.0",
                "redis>=4.0.0"
            ])

        if self.config.enable_caching:
            requirements.append("flask-caching>=2.0.0")

        if self.config.enable_monitoring:
            requirements.extend([
                "flask-limiter>=2.0.0",
                "prometheus-flask-exporter>=0.20.0"
            ])

        if self.config.enable_testing:
            requirements.extend([
                "pytest>=7.0.0",
                "pytest-flask>=1.2.0",
                "pytest-cov>=4.0.0"
            ])

        return '\n'.join(sorted(requirements))

    def _generate_readme(self) -> str:
        """Generate README.md file."""
        return f'''
# {self.config.app_title or self.config.app_name}

{self.config.app_description}

## Features

- 🚀 **Modern Flask-AppBuilder Application** - Built with the latest Flask-AppBuilder features
- 🔐 **Authentication & Authorization** - Secure user management with role-based access
- 📊 **Advanced Data Views** - Modern widgets, charts, calendars, and reports
- 🌐 **REST API** - Complete RESTful API with OpenAPI documentation
- 📱 **Responsive Design** - Mobile-first responsive interface
- 🔄 **Real-time Updates** - WebSocket support for live data updates
- ⚡ **Performance Optimized** - Caching, pagination, and query optimization
- 🐳 **Docker Ready** - Complete Docker and Kubernetes support
- 🧪 **Testing Framework** - Comprehensive unit, integration, and E2E tests
- 📚 **Auto-generated Documentation** - Complete API and user documentation

## Quick Start

### Prerequisites

- Python 3.8+
- {self.config.database_type.title()} database
{'- Docker & Docker Compose (optional)' if self.config.enable_docker else ''}

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd {self.config.app_name}
```

2. Set up virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database connection details
```

5. Initialize database:
```bash
python scripts/init_db.py
```

6. Run the application:
```bash
python app.py
```

The application will be available at: http://localhost:8080

### Default Login
- **Username**: admin
- **Password**: admin

⚠️ **Important**: Change the default admin password after first login!

## Development

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
# Create migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade
```

### Code Quality
```bash
# Format code
black .
isort .

# Lint code
flake8
```

## Deployment

### Docker Deployment
```bash
docker-compose up -d
```

### Production Deployment
See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions.

## API Documentation

When running, visit:
- **Swagger UI**: http://localhost:8080/swagger-ui
- **API Docs**: http://localhost:8080/api/docs

## Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- 📧 Email: {self.config.author_email}
- 📚 Documentation: [docs/](docs/)
- 🐛 Issues: GitHub Issues

---

Generated by Flask-AppBuilder Enhanced Generator
Version: {self.config.version} | Generated: {datetime.now().strftime('%Y-%m-%d')}
        '''.strip()

    # Additional generation methods would continue here...
    # This shows the pattern for the comprehensive app generator

    def _generate_dockerfile(self) -> str:
        """Generate Dockerfile."""
        return f'''
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "app.py"]
        '''.strip()

    # More template methods would be implemented following this pattern...