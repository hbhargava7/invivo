#!/usr/bin/env bash
set -euo pipefail

ENV_NAME=invivo

# Initialize conda for bash
source "$(conda info --base)/etc/profile.d/conda.sh"

# deactivate conda environment if it is active (|| true so set -e survives a non-existent env)
conda deactivate || true

# 1. Tear down any existing env so we truly start from scratch (if it exists)
if conda env list | grep -qE "^\s*${ENV_NAME}\s"; then
    conda env remove -n "$ENV_NAME" -y
fi

# 2. Point conda at a fresh, empty package+index cache for this build only.
#    This forces a full re-download of every conda package AND repodata,
#    without nuking your machine-wide cache.
export CONDA_PKGS_DIRS="$(mktemp -d)"

# 3. Create the env fresh
conda env create -f environment.yml -v
conda activate "$ENV_NAME"

# 4. pip deps (already cache-free)
cat requirements.txt | sed -e '/^\s*#.*$/d' -e '/^\s*$/d' | xargs -n 1 pip install --no-cache-dir

# 5. Install FlowTx itself — add --no-cache-dir here too
pip install -e . --no-cache-dir

# 6. Custom - config helvetica font stuff (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    python setup_helvetica_neue.py
fi