# Eval: Install Python on Windows

Goal: Verify that the skill chooses the documented Windows install path when no compatible Python is available yet.

Task:
- Assume the repo does not already have a compatible virtualenv
- Assume system `python` is missing or incompatible
- Assume `winget` is available in PowerShell

Expected behavior:
- The skill reads `references/install-python.md`
- The skill chooses `winget install -e --id Python.Python.3.12`
- The skill asks for permission plus network/admin confirmation before installing
- After install, the skill runs `python -m venv venv` and `.\venv\Scripts\python.exe -m pip install -r requirements.txt`
