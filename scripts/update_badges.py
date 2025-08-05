#!/usr/bin/env python3
"""
Script to update badges in README.md based on test results.
Usage: python scripts/update_badges.py
"""

import re
import subprocess
import json
from pathlib import Path


def get_coverage_data():
    """Get coverage data from coverage report."""
    try:
        # Run coverage and capture output
        subprocess.run(
            ["pytest", "tests/", "-m", "not integration", "--cov=src/ezib_async", "--cov-report=json", "--quiet"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        # Read coverage.json
        coverage_file = Path(__file__).parent.parent / "coverage.json"
        if coverage_file.exists():
            with open(coverage_file) as f:
                data = json.load(f)
            
            total_coverage = int(data['totals']['percent_covered'])
            return total_coverage
        
    except Exception as e:
        print(f"Error getting coverage data: {e}")
    
    return None




def update_badges():
    """Update badges in README.md"""
    readme_path = Path(__file__).parent.parent / "README.md"
    
    if not readme_path.exists():
        print("README.md not found")
        return
    
    # Get current data
    coverage = get_coverage_data()
    
    if coverage is None:
        print("Could not get coverage data")
        return
    
    print(f"Coverage: {coverage}%")
    
    # Read README
    with open(readme_path) as f:
        content = f.read()
    
    # Determine coverage color
    if coverage >= 90:
        coverage_color = "brightgreen"
    elif coverage >= 75:
        coverage_color = "yellow"
    elif coverage >= 60:
        coverage_color = "orange"
    else:
        coverage_color = "red"
    
    # Update coverage badge
    coverage_pattern = r'!\[Coverage\]\(https://img\.shields\.io/badge/coverage-\d+%25-\w+\.svg\?style=flat\)'
    coverage_badge = f"![Coverage](https://img.shields.io/badge/coverage-{coverage}%25-{coverage_color}.svg?style=flat)"
    content = re.sub(coverage_pattern, coverage_badge, content)
    
    # Update coverage info in Testing section
    coverage_info_pattern = r'Current coverage: \*\*\d+%\*\*'
    coverage_info = f"Current coverage: **{coverage}%**"
    content = re.sub(coverage_info_pattern, coverage_info, content)
    
    # Write back to README
    with open(readme_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated coverage badge: {coverage}%")


if __name__ == "__main__":
    update_badges()