#!/bin/bash
# Launch the Pseudotime Pipeline GUI.
# Tries Neuroimaging conda env first, then falls back to any Python with tkinter.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 1. Prefer the Neuroimaging conda env by direct path ───────────────────────
CONDA_PYTHON=""
for base in "$HOME/anaconda3" "$HOME/miniconda3" "/opt/anaconda3" "/opt/miniconda3"; do
    candidate="$base/envs/Neuroimaging/bin/python"
    if [ -x "$candidate" ]; then
        CONDA_PYTHON="$candidate"
        break
    fi
done

# ── 2. Try conda activate as a fallback ───────────────────────────────────────
if [ -z "$CONDA_PYTHON" ]; then
    CONDA_BASE="$(conda info --base 2>/dev/null)"
    if [ -n "$CONDA_BASE" ]; then
        # shellcheck disable=SC1091
        source "$CONDA_BASE/etc/profile.d/conda.sh"
        conda activate Neuroimaging 2>/dev/null && CONDA_PYTHON="$(which python)"
    fi
fi

# ── 3. Last resort: system python3 ────────────────────────────────────────────
if [ -z "$CONDA_PYTHON" ]; then
    echo "WARNING: Neuroimaging conda env not found — using system python3."
    echo "         Some imports (scipy, matplotlib) may fail."
    CONDA_PYTHON="$(which python3)"
fi

echo "Python: $CONDA_PYTHON"
echo "Starting Pseudotime Pipeline GUI…"
"$CONDA_PYTHON" "$DIR/app.py"
