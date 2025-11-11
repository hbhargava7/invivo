#!/usr/bin/env bash

# Use conda
source ~/miniforge3/etc/profile.d/conda.sh

# Create the Conda environment
conda env create -f environment.yml -v

# Activate the environment
conda activate invivo

# Install dependencies, workaround to prevent installation from stopping if any one fails
cat requirements.txt | sed -e '/^\s*#.*$/d' -e '/^\s*$/d' | xargs -n 1 pip install --no-cache-dir


# Install FlowTx itself.
pip install -e .
