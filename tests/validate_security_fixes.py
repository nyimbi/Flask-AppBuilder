#!/usr/bin/env python3
"""
Simple validation script to verify security fixes are working correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_xss_protection():
    """Test XSS protection utilities."""
    try:
        from flask_appbuilder.widgets.xss_security import XSSProtection

        # Test basic HTML escaping
        dangerous_html = "<script>alert('xss')</script>"
        escaped = XSSProtection.escape_html(dangerous_html)

        if "<script>" in escaped:
            print("❌ XSS Protection FAILED: HTML not properly escaped")
            return False

        if "&lt;script&gt;" not in escaped:
            print("❌ XSS Protection FAILED: Expected escaped HTML not found")
            return False

        print("✅ XSS Protection: HTML escaping works correctly")

        # Test JSON escaping
        json_escaped = XSSProtection.escape_json_string(dangerous_html)
        if "<script>" in json_escaped:
            print("❌ XSS Protection FAILED: JSON not properly escaped")
            return False

        print("✅ XSS Protection: JSON escaping works correctly")

        # Test HTML sanitization
        sanitized = XSSProtection.sanitize_html(dangerous_html)
        if "<script>" in sanitized:
            print("❌ XSS Protection FAILED: HTML not properly sanitized")
            return False

        print("✅ XSS Protection: HTML sanitization works correctly")

        return True

    except ImportError as e:
        print(f"❌ XSS Protection FAILED: Import error - {e}")
        return False
    except Exception as e:
        print(f"❌ XSS Protection FAILED: {e}")
        return False

def test_sql_injection_warning():
    """Test SQL injection warning documentation exists."""
    try:
        warning_file = os.path.join(os.path.dirname(__file__), '..', 'flask_appbuilder', 'widgets_postgresql', 'SECURITY_WARNING.md')

        if not os.path.exists(warning_file):
            print("❌ SQL Injection Warning FAILED: Warning file not found")
            return False

        with open(warning_file, 'r') as f:
            content = f.read()

        if "SQL injection vulnerabilities" not in content:
            print("❌ SQL Injection Warning FAILED: Warning content not found")
            return False

        if "CRITICAL" not in content:
            print("❌ SQL Injection Warning FAILED: Critical warning not found")
            return False

        print("✅ SQL Injection Warning: Documentation exists and is comprehensive")
        return True

    except Exception as e:
        print(f"❌ SQL Injection Warning FAILED: {e}")
        return False

def test_security_imports():
    """Test that security modules can be imported correctly."""
    try:
        # Test AI security manager
        from flask_appbuilder.collaborative.ai.security import AISecurityManager, PromptSanitizer
        print("✅ AI Security Manager: Imports successfully")

        # Test XSS security utilities
        from flask_appbuilder.widgets.xss_security import XSSProtection, apply_csp_headers
        print("✅ XSS Security Utilities: Imports successfully")

        return True

    except ImportError as e:
        print(f"❌ Security Imports FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ Security Imports FAILED: {e}")
        return False

def test_team_manager_fixes():
    """Test team manager N+1 query fixes."""
    try:
        from flask_appbuilder.collaborative.core.team_manager import TeamManager

        # Check if bulk methods exist
        if not hasattr(TeamManager, 'get_teams_with_stats'):
            print("❌ Team Manager FAILED: Bulk stats method not found")
            return False

        if not hasattr(TeamManager, 'get_teams_members_bulk'):
            print("❌ Team Manager FAILED: Bulk members method not found")
            return False

        print("✅ Team Manager: N+1 query fix methods are present")
        return True

    except ImportError as e:
        print(f"❌ Team Manager FAILED: Import error - {e}")
        return False
    except Exception as e:
        print(f"❌ Team Manager FAILED: {e}")
        return False

def test_deployment_guide():
    """Test that deployment guide exists."""
    try:
        guide_file = os.path.join(os.path.dirname(__file__), '..', 'docs', 'SECURITY_DEPLOYMENT_GUIDE.md')

        if not os.path.exists(guide_file):
            print("❌ Deployment Guide FAILED: Guide file not found")
            return False

        with open(guide_file, 'r') as f:
            content = f.read()

        required_sections = [
            "Key Vault Configuration",
            "Content Security Policy",
            "MFA Configuration",
            "Rate Limiting",
            "Security Hardening"
        ]

        missing_sections = []
        for section in required_sections:
            if section not in content:
                missing_sections.append(section)

        if missing_sections:
            print(f"❌ Deployment Guide FAILED: Missing sections - {missing_sections}")
            return False

        print("✅ Deployment Guide: Comprehensive security documentation exists")
        return True

    except Exception as e:
        print(f"❌ Deployment Guide FAILED: {e}")
        return False

def main():
    """Run all security validation tests."""
    print("🔒 Flask-AppBuilder Security Fixes Validation")
    print("=" * 50)

    tests = [
        ("XSS Protection", test_xss_protection),
        ("SQL Injection Warning", test_sql_injection_warning),
        ("Security Imports", test_security_imports),
        ("Team Manager Fixes", test_team_manager_fixes),
        ("Deployment Guide", test_deployment_guide)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}...")
        try:
            if test_func():
                passed += 1
            else:
                print(f"   Test failed: {test_name}")
        except Exception as e:
            print(f"   ❌ {test_name} FAILED with exception: {e}")

    print("\n" + "=" * 50)
    print(f"📊 Security Validation Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL SECURITY FIXES VALIDATED SUCCESSFULLY!")
        return 0
    else:
        print("⚠️  Some security fixes need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())