# Suggested Commands for Flask-AppBuilder Development

## Testing Commands
```bash
# Run all tests
nose2 -c setup.cfg -F -v --with-coverage --coverage flask_appbuilder -A '!mongo' tests

# Run MongoDB tests
nose2 -c setup.cfg -F -v --with-coverage --coverage flask_appbuilder -A 'mongo' tests

# Run single test
nose2 tests.test_<module_name>

# Tox environments
tox -e api-sqlite
tox -e mysql
tox -e postgres
tox -e mongodb
```

## Code Quality Commands
```bash
# Linting (Google import order style, 90 char limit)
flake8

# Code formatting
black --check setup.py flask_appbuilder tests
black setup.py flask_appbuilder tests

# Type checking
mypy
```

## Framework CLI Commands
```bash
# Modern CLI (preferred)
flask fab <command>

# Legacy CLI (deprecated in 2.2.X)
fabmanager <command>
```

## Documentation Commands
```bash
# Build documentation
cd docs && make html
```

## Development Workflow
1. Run tests before changes
2. Make changes following code style
3. Run linting and formatting
4. Run tests again
5. Update documentation if needed