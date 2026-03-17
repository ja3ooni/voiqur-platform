#!/usr/bin/env python3
"""
Simple test for data protection system.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    # Try to import the module directly
    from security import data_protection as dp
    print("Module imported successfully")
    print("Available classes:", [name for name in dir(dp) if not name.startswith('_')])
    
    # Try to access the class
    if hasattr(dp, 'DataProtectionSystem'):
        print("DataProtectionSystem class found")
        system = dp.DataProtectionSystem()
        print("DataProtectionSystem instance created successfully")
    else:
        print("DataProtectionSystem class NOT found")
        
except Exception as e:
    print(f"Error importing: {e}")
    import traceback
    traceback.print_exc()