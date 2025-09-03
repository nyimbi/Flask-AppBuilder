#!/usr/bin/env python3
"""
Basic functionality test for security modules.

This test verifies that the security modules are properly integrated
and functional, without requiring full Flask app setup.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_input_validation():
    """Test that input validation module works."""
    try:
        from flask_appbuilder.security.input_validation import InputValidator
        
        # Test string sanitization
        malicious_input = "<script>alert('xss')</script>Hello"
        sanitized = InputValidator.sanitize_string(malicious_input)
        print(f"✅ Input validation: '{malicious_input}' -> '{sanitized}'")
        
        # Should not contain script tags
        assert '<script>' not in sanitized
        print("✅ XSS protection working")
        
        # Test email validation
        valid_email = "test@example.com"
        invalid_email = "not-an-email"
        
        assert InputValidator.validate_email(valid_email) == True
        assert InputValidator.validate_email(invalid_email) == False
        print("✅ Email validation working")
        
        return True
    except ImportError as e:
        print(f"❌ Input validation module not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Input validation test failed: {e}")
        return False

def test_security_headers():
    """Test that security headers module can be imported."""
    try:
        from flask_appbuilder.security.security_headers import SecurityHeaders
        print("✅ Security headers module available")
        
        # Test that it can be instantiated
        headers = SecurityHeaders()
        print("✅ Security headers can be instantiated")
        return True
    except ImportError as e:
        print(f"❌ Security headers module not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Security headers test failed: {e}")
        return False

def test_rate_limiting():
    """Test that rate limiting module can be imported."""
    try:
        from flask_appbuilder.security.rate_limiting import SecurityRateLimiter
        print("✅ Rate limiting module available")
        
        # Test that it can be instantiated
        limiter = SecurityRateLimiter()
        print("✅ Rate limiting can be instantiated")
        return True
    except ImportError as e:
        print(f"❌ Rate limiting module not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False

def test_enhanced_field():
    """Test that enhanced field with security validation works."""
    try:
        from flask_appbuilder.fields import SecurityEnhancedStringField
        print("✅ Enhanced string field available")
        
        # Test field instantiation with proper binding
        from wtforms import Form
        
        class TestForm(Form):
            test_field = SecurityEnhancedStringField("Test Field", max_length=100)
            
        form = TestForm()
        field = form.test_field
        print("✅ Enhanced string field can be instantiated")
        
        # Test form data processing
        field.process_formdata(["<script>alert('test')</script>Hello"])
        print(f"✅ Field processed data: '{field.data}'")
        
        # Should not contain script tags
        assert '<script>' not in field.data
        print("✅ Field XSS protection working")
        
        return True
    except ImportError as e:
        print(f"❌ Enhanced field not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Enhanced field test failed: {e}")
        return False

def main():
    """Run all security module tests."""
    print("🔒 Testing Flask-AppBuilder Security Module Integration")
    print("=" * 60)
    
    tests = [
        ("Input Validation", test_input_validation),
        ("Security Headers", test_security_headers),
        ("Rate Limiting", test_rate_limiting),
        ("Enhanced Field", test_enhanced_field),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}:")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n🎯 Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All security modules integrated successfully!")
    else:
        print("⚠️  Some security modules need fixes")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)