# `invivo`

## Automatic analysis of in vivo study log data, built for the Lim Lab

Note: This is a work in progress. Use at your own risk and check all outputs.

by Hersh Bhargava (https://hershbhargava.com)

github: https://github.com/hbhargava/invivo

This notebook demonstrates the use of the `invivo` package to automatically analyze study log data.

## Setup

Setup is easiest with Anaconda. Make sure you have Anaconda installed (https://www.anaconda.com/download).

1) Download or clone the package from Github (https://github.com/hbhargava/invivo)
2) Open a terminal and navigate to the package directory
3) Run the script `config_conda_env.sh` to create the conda environment (installs Python and other dependencies)

    ```bash
    # may need to make the script executable
    chmod +x config_conda_env.sh

    # run the script
    ./config_conda_env.sh
    ```
4) Activate the environment

    ```bash
    conda activate invivo
    ```

5) Start your preferred Jupyter notebook server (I use VSCode/Cursor; make sure to select the `invivo` environment)