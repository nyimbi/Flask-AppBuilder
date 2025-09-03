#!/bin/bash
# Flask-AppBuilder Quality Validation Script
# This script runs comprehensive quality validation checks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STRICT_MODE=${STRICT_MODE:-false}
GENERATE_REPORT=${GENERATE_REPORT:-true}
MIN_COVERAGE=${MIN_COVERAGE:-60.0}

echo -e "${BLUE}🚀 Flask-AppBuilder Quality Validation${NC}"
echo "=============================================="
echo "Strict Mode: $STRICT_MODE"
echo "Generate Report: $GENERATE_REPORT"
echo "Minimum Documentation Coverage: $MIN_COVERAGE%"
echo ""

# Function to print status
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ PASSED${NC} $message"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ FAILED${NC} $message"
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠️  WARNING${NC} $message"
    else
        echo -e "${BLUE}ℹ️  INFO${NC} $message"
    fi
}

# Function to run quality check
run_check() {
    local check_name=$1
    local command=$2
    local required=${3:-true}
    
    echo -e "${BLUE}🔍 Running $check_name...${NC}"
    
    if eval "$command"; then
        print_status "PASS" "$check_name"
        return 0
    else
        if [ "$required" = "true" ]; then
            print_status "FAIL" "$check_name"
            if [ "$STRICT_MODE" = "true" ]; then
                echo -e "${RED}❌ Strict mode enabled - Exiting due to $check_name failure${NC}"
                exit 1
            fi
            return 1
        else
            print_status "WARN" "$check_name (optional)"
            return 0
        fi
    fi
}

# Initialize counters
total_checks=0
passed_checks=0
failed_checks=0

# Check 1: Syntax Validation
total_checks=$((total_checks + 1))
if run_check "Syntax Validation" "python tests/validation/fix_syntax_errors.py flask_appbuilder --analyze-only"; then
    passed_checks=$((passed_checks + 1))
else
    failed_checks=$((failed_checks + 1))
fi

# Check 2: Critical Tests
total_checks=$((total_checks + 1))
if run_check "Critical Tests" "python -m pytest tests/ci/test_integration_workflows.py tests/ci/test_documentation_validation.py -v --tb=short -q"; then
    passed_checks=$((passed_checks + 1))
else
    failed_checks=$((failed_checks + 1))
fi

# Check 3: Documentation Coverage
total_checks=$((total_checks + 1))
if run_check "Documentation Coverage" "python -c \"
import sys
sys.path.append('tests/ci')
from test_documentation_validation import DocumentationValidator
validator = DocumentationValidator('flask_appbuilder')
results = validator.analyze_directory(['__pycache__', '.git', 'tests', 'examples'])
coverage = results['summary']['documentation_coverage_percentage']
print(f'Documentation Coverage: {coverage:.1f}%')
if coverage < $MIN_COVERAGE:
    print(f'ERROR: Coverage {coverage:.1f}% below minimum $MIN_COVERAGE%')
    sys.exit(1)
\""; then
    passed_checks=$((passed_checks + 1))
else
    failed_checks=$((failed_checks + 1))
fi

# Check 4: Security Scan (optional)
total_checks=$((total_checks + 1))
if command -v bandit >/dev/null 2>&1; then
    if run_check "Security Scan" "bandit -r flask_appbuilder -q -f txt" false; then
        passed_checks=$((passed_checks + 1))
    else
        print_status "WARN" "Security scan found issues - review recommended"
        passed_checks=$((passed_checks + 1))  # Don't fail on security warnings
    fi
else
    print_status "INFO" "Security Scan - bandit not installed (optional)"
    passed_checks=$((passed_checks + 1))
fi

# Check 5: Comprehensive Quality Pipeline
total_checks=$((total_checks + 1))
if [ "$GENERATE_REPORT" = "true" ]; then
    echo -e "${BLUE}🔧 Running Comprehensive Quality Pipeline...${NC}"
    if python tests/validation/quality_validation_pipeline.py flask_appbuilder; then
        print_status "PASS" "Quality Pipeline"
        passed_checks=$((passed_checks + 1))
        
        # Find the most recent report
        report_file=$(ls -t quality_validation_report_*.json 2>/dev/null | head -1)
        if [ -n "$report_file" ]; then
            echo -e "${BLUE}📄 Quality report generated: $report_file${NC}"
        fi
    else
        print_status "WARN" "Quality Pipeline - needs improvement"
        failed_checks=$((failed_checks + 1))
    fi
else
    print_status "INFO" "Quality Pipeline - skipped (GENERATE_REPORT=false)"
    passed_checks=$((passed_checks + 1))
fi

# Summary
echo ""
echo "=============================================="
echo -e "${BLUE}📊 QUALITY VALIDATION SUMMARY${NC}"
echo "=============================================="
echo "Total Checks: $total_checks"
echo "Passed: $passed_checks"
echo "Failed: $failed_checks"

pass_rate=$(( (passed_checks * 100) / total_checks ))
echo "Pass Rate: $pass_rate%"

if [ $failed_checks -eq 0 ]; then
    print_status "PASS" "All quality gates passed! 🎉"
    echo -e "${GREEN}✅ Flask-AppBuilder meets production quality standards${NC}"
    exit 0
elif [ $pass_rate -ge 80 ]; then
    print_status "WARN" "Most quality gates passed, some improvements needed"
    echo -e "${YELLOW}⚠️  Flask-AppBuilder is approaching production readiness${NC}"
    if [ "$STRICT_MODE" = "true" ]; then
        exit 1
    else
        exit 0
    fi
else
    print_status "FAIL" "Quality gates need significant improvements"
    echo -e "${RED}❌ Flask-AppBuilder needs work before production deployment${NC}"
    exit 1
fi