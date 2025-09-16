# Flask-AppBuilder Tech Stack

## Core Technologies
- **Python**: 3.8+ with modern typing (`str | None`, `list[str]`, `dict[str, Any]`)
- **Flask**: 2.3+ with factory pattern support
- **SQLAlchemy**: 2.0.42+ with modern query patterns using `session.execute(select())`
- **Flask-SQLAlchemy**: 3.1.1+ with compatibility layers

## Database Support
- **Primary**: PostgreSQL, MySQL, SQLite, MSSQL, Oracle, DB2
- **Alternative**: MongoDB via MongoEngine
- **Graph**: Apache AGE extension for PostgreSQL
- **Multi-DB**: Vertical partitioning support

## Frontend Technologies
- **Templates**: Jinja2 templates in `flask_appbuilder/templates/appbuilder/`
- **CSS**: Bootstrap themes with customization
- **JavaScript**: Static assets in `flask_appbuilder/static/appbuilder/`
- **Internationalization**: Flask-Babel with translations

## Security & Auth
- **Authentication**: OAuth, OpenID, Database, LDAP, REMOTE_USER
- **Authorization**: Role-based permissions with auto-generation
- **Session**: Flask-Login integration
- **API**: OpenAPI/Swagger documentation

## Development Tools
- **Testing**: nose2 with coverage reporting
- **Linting**: flake8 (Google import order style, 90 char limit)
- **Formatting**: black
- **Type Checking**: mypy (selective modules)
- **CLI**: `flask fab` commands (modern) vs `fabmanager` (deprecated)