#!/usr/bin/env python
"""
Test runner script for the Language Police Bot project.

This script provides convenient commands to run different types of tests:
- Unit tests
- Integration tests
- Coverage reports
- Performance tests
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle the output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(command, shell=True, capture_output=False)
    return result.returncode == 0

def run_unit_tests():
    """Run unit tests."""
    return run_command(
        "python -m pytest tests/ -v --tb=short -m 'not integration'",
        "Unit Tests"
    )

def run_integration_tests():
    """Run integration tests."""
    return run_command(
        "python -m pytest tests/ -v --tb=short -m 'integration'",
        "Integration Tests"
    )

def run_all_tests():
    """Run all tests."""
    return run_command(
        "python -m pytest tests/ -v --tb=short",
        "All Tests"
    )

def run_tests_with_coverage():
    """Run tests with coverage report."""
    success = run_command(
        "python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing",
        "Tests with Coverage"
    )
    
    if success:
        print("\nCoverage report generated in htmlcov/index.html")
    
    return success

def run_specific_test_file(test_file):
    """Run a specific test file."""
    return run_command(
        f"python -m pytest tests/{test_file} -v --tb=short",
        f"Specific Test File: {test_file}"
    )

def run_performance_tests():
    """Run performance-focused tests."""
    return run_command(
        "python -m pytest tests/ -v --tb=short -k 'performance or benchmark'",
        "Performance Tests"
    )

def main():
    """Main test runner function."""
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py [command]")
        print("\nAvailable commands:")
        print("  unit          - Run unit tests only")
        print("  integration   - Run integration tests only")
        print("  all           - Run all tests")
        print("  coverage      - Run tests with coverage report")
        print("  performance   - Run performance tests")
        print("  file <name>   - Run specific test file")
        print("\nExamples:")
        print("  python run_tests.py unit")
        print("  python run_tests.py coverage")
        print("  python run_tests.py file test_rankings_chat_top.py")
        return
    
    command = sys.argv[1].lower()
    
    # Change to project directory
    project_dir = Path(__file__).parent.parent
    os.chdir(project_dir)
    
    success = False
    
    if command == "unit":
        success = run_unit_tests()
    elif command == "integration":
        success = run_integration_tests()
    elif command == "all":
        success = run_all_tests()
    elif command == "coverage":
        success = run_tests_with_coverage()
    elif command == "performance":
        success = run_performance_tests()
    elif command == "file" and len(sys.argv) > 2:
        test_file = sys.argv[2]
        success = run_specific_test_file(test_file)
    else:
        print(f"Unknown command: {command}")
        return
    
    if success:
        print(f"\n✅ {command.title()} tests completed successfully!")
    else:
        print(f"\n❌ {command.title()} tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()