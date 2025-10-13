# TaskRouterX Startup Script (cross-platform)
# - Creates/activates venv on Unix or Windows (Git Bash)
# - Installs deps with the venv's pip
# - Starts FastAPI (Uvicorn) and the frontend server
# - Cleans up on Ctrl+C / exit

set -euo pipefail

# -------------------------
# Pretty headers
# -------------------------
print_header() {
  echo ""
  echo "======================================================================"
  echo " $1"
  echo "======================================================================"
}

# -------------------------
# Pick a Python executable
# -------------------------
pick_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
  elif command -v python >/dev/null 2>&1; then
    echo "python"
  elif command -v py >/dev/null 2>&1; then
    # Windows launcher
    echo "py -3"
  else
    echo ""
  fi
}

# -------------------------
# Cleanup on exit
# -------------------------
API_PID=""
FRONTEND_PID=""
cleanup() {
  print_header "Shutting down services..."
  # Kill the specific background processes if they exist
  if [ -n "${API_PID}" ] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
  fi
  if [ -n "${FRONTEND_PID}" ] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  # Try a gentle group kill as a fallback (safe if nothing else running)
  kill 0 2>/dev/null || true
  echo "Cleanup complete."
}
trap cleanup EXIT

# -------------------------
# 1) Virtual environment
# -------------------------
print_header "Step 1: Setting up Python virtual environment..."

PY_CMD="$(pick_python)"
if [ -z "$PY_CMD" ]; then
  echo "No Python found on PATH. Please install Python 3.10+ and re-run."
  exit 1
fi

if [ ! -d "venv" ]; then
  eval $PY_CMD -m venv venv
  echo "Virtual environment created."
else
  echo "Virtual environment already exists."
fi

# Activate venv (Unix or Windows layout)
if [ -f "venv/bin/activate" ]; then
  # macOS/Linux/WSL
  # shellcheck source=/dev/null
  . venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
  # Windows Git Bash / MSYS2
  # shellcheck source=/dev/null
  . venv/Scripts/activate
else
  echo "Found venv but couldn't locate activate script (bin/activate or Scripts/activate)."
  exit 1
fi
echo "Virtual environment activated."

# Resolve venv python explicitly (robust on all platforms)
if [ -x "venv/bin/python" ]; then
  VENV_PY="venv/bin/python"
elif [ -x "venv/Scripts/python.exe" ]; then
  VENV_PY="venv/Scripts/python.exe"
else
  # Fallback to whichever 'python' is now on PATH after activation
  VENV_PY="python"
fi

# -------------------------
# 2) Install dependencies
# -------------------------
print_header "Step 2: Installing dependencies from requirements.txt..."
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r requirements.txt
echo "Dependencies installed successfully."

# -------------------------
# 3) (DB init handled in API)
# -------------------------
# No separate step needed if your app initializes on startup.

# -------------------------
# 4) Start Backend (Uvicorn)
# -------------------------
print_header "Step 3: Starting FastAPI backend server on port 8000..."
# Use module form to ensure we use the venv's uvicorn
"$VENV_PY" -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!
echo "Backend API server started with PID: $API_PID"

# Give the API a moment to boot
sleep 2

# -------------------------
# 5) Start Frontend server
# -------------------------
print_header "Step 4: Starting frontend server on port 3000..."
"$VENV_PY" frontend/server.py &
FRONTEND_PID=$!
echo "Frontend server started with PID: $FRONTEND_PID"

# -------------------------
# Final info
# -------------------------
print_header "TaskRouterX is now running!"
echo "- Interactive Dashboard: http://localhost:3000"
echo "- Backend API (Swagger): http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services."

# Keep the script alive so trap can catch Ctrl+C and clean up
wait