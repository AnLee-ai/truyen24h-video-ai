# Root Cause Analysis & Impact Assessment Rule

Every time an error or bug occurs, the assistant MUST:
1. Identify the CORE ROOT CAUSE and all surrounding contributing factors.
2. Evaluate potential conflicts and ensure the proposed fix does NOT introduce downstream bugs or break existing architecture.
3. Validate fixes empirically using test scripts (`python -m unittest tests/test_full_system_integrity.py`).
