#!/bin/bash
set -e

echo "========================================="
echo " VERCEL BUILD ENVIRONMENT DIAGNOSTIC "
echo "========================================="
echo ""

echo "--- 1. WHO AM I AND WHERE AM I? ---"
echo "User: $(whoami)"
echo "Current Directory: $(pwd)"
echo ""

echo "--- 2. WHAT IS MY ENVIRONMENT? (Node or Python?) ---"
env | sort
echo ""

echo "--- 3. WHAT FILES ARE IN MY CURRENT DIRECTORY? ---"
ls -la
echo ""

echo "--- 4. DO PYTHON & PIP EXIST? ---"
echo "Python version:"
python --version || echo "Python command not found."
echo ""
echo "Python3 version:"
python3 --version || echo "Python3 command not found."
echo ""
echo "Pip version:"
pip --version || echo "Pip command not found."
echo ""
echo "Pip3 version:"
pip3 --version || echo "Pip3 command not found."
echo ""

echo "========================================="
echo "         DIAGNOSTIC COMPLETE"
echo "========================================="

exit 0