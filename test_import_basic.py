#!/usr/bin/env python3
"""
Basic import test script for Flask-AppBuilder components.
This script tests imports in isolation to identify remaining issues.
"""

import sys
import traceback

def test_import(module_name, description=""):
    """Test importing a specific module"""
    try:
        __import__(module_name)
        print(f"✅ {module_name} - {description}")
        return True
    except Exception as e:
        print(f"❌ {module_name} - {description}")
        print(f"   Error: {e}")
        return False

def main():
    """Test core Flask-AppBuilder imports"""
    print("Testing Flask-AppBuilder module imports...\n")
    
    # Test basic Python modules first
    test_import("flask", "Flask web framework")
    test_import("sqlalchemy", "SQLAlchemy ORM")
    
    print("\n--- Testing Flask-AppBuilder Core Modules ---")
    
    # Test individual components in dependency order
    modules_to_test = [
        ("flask_appbuilder.const", "Constants"),
        ("flask_appbuilder._compat", "Compatibility layer"),
        ("flask_appbuilder.models.sqla", "SQLAlchemy models"),
        ("flask_appbuilder.security.decorators", "Security decorators"),
        ("flask_appbuilder.baseviews", "Base view classes"),
        ("flask_appbuilder.forms", "Form classes"),
        ("flask_appbuilder.widgets", "Widget classes"),
        ("flask_appbuilder.filters", "Filter classes"),
        ("flask_appbuilder.menu", "Menu classes"),
        ("flask_appbuilder.fieldwidgets", "Field widgets"),
        ("flask_appbuilder.validators", "Form validators"),
        ("flask_appbuilder.views", "View classes"),
        ("flask_appbuilder.api", "API classes"),
        ("flask_appbuilder.base", "AppBuilder main class"),
        ("flask_appbuilder", "Main Flask-AppBuilder module"),
    ]
    
    success_count = 0
    total_count = len(modules_to_test)
    
    for module, description in modules_to_test:
        if test_import(module, description):
            success_count += 1
    
    print(f"\n--- Import Test Results ---")
    print(f"Successful imports: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 All imports successful! Ready to run comprehensive tests.")
        return 0
    else:
        print("⚠️  Some imports failed. Fix remaining issues before running tests.")
        return 1

if __name__ == "__main__":
    sys.exit(main())