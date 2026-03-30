"""
Quick test runner for sales integration tests
Run this to verify all functionality is working
"""

import subprocess
import sys

print("="*70)
print("🧪 Running Sales Integration Tests")
print("="*70)
print()

# Run the test
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_sales_integration.py", "-v", "-s"],
    capture_output=False
)

sys.exit(result.returncode)
