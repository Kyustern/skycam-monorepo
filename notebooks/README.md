# Notebooks Environment Guide

## Overview

This directory contains Jupyter notebooks for analyzing TURRET captured data. All notebooks require a specific Python environment to run correctly.

## Python Environment

A virtual environment is provided at `./notebooks/venv` containing all required dependencies for running the analysis notebooks.

**Python Version:** 3.14.4

## Activating the Environment

Before running or testing any notebooks, you must activate the virtual environment.

### Linux/macOS

```bash
# Navigate to the notebooks directory
cd /home/leon/DEV/DOCKER/TURRET/notebooks

# Source the activation script
source venv/bin/activate

# Verify activation (prompt should show (venv))
echo $VIRTUAL_ENV
```

### Windows (PowerShell)

```powershell
# Navigate to the notebooks directory
cd C:\path\to\DEV\DOCKER\TURRET\notebooks

# Activate the environment
.\venv\Scripts\Activate.ps1
```

### Windows (Command Prompt)

```cmd
cd C:\path\to\DEV\DOCKER\TURRET\notebooks
venv\Scripts\activate.bat
```

## Running Jupyter Notebooks

Once the environment is activated, you can launch Jupyter:

```bash
# Launch Jupyter Lab (recommended)
jupyter lab

# Or launch classic Jupyter Notebook
jupyter notebook
```

This will open a browser window where you can navigate to and open the notebooks.

## Alternative: Running from Any Directory

If you want to run Jupyter from outside the notebooks directory:

```bash
# Navigate to your preferred directory
cd /path/to/your/directory

# Source the environment and launch Jupyter with the notebooks path
source /home/leon/DEV/DOCKER/TURRET/notebooks/venv/bin/activate
jupyter lab --notebook-dir=/home/leon/DEV/DOCKER/TURRET/notebooks
```

Or use the full path to Jupyter:

```bash
/home/leon/DEV/DOCKER/TURRET/notebooks/venv/bin/jupyter lab
```

## Verifying the Environment

To check that the environment is active and working:

```bash
# Check Python version
python --version

# Check installed packages
pip list

# Check Jupyter is available
which jupyter
```

## Deactivating the Environment

When you're done working with the notebooks:

```bash
# Deactivate the virtual environment
deactivate

# Or simply close your terminal
```

## Environment Management

### Adding New Packages

If you need to add a new package to the environment:

```bash
# Activate the environment first
source venv/bin/activate

# Install the package
pip install package-name

# Optionally, save to requirements.txt
pip freeze > requirements.txt
```

### Recreating the Environment

If the environment becomes corrupted or you need to rebuild it:

```bash
# Remove the old environment
rm -rf venv

# Create new environment
python -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install -r requirements.txt
```

## Directory Structure

```
notebooks/
├── README.md                    # This file
├── venv/                       # Python virtual environment
│   ├── bin/                    # Executables (jupyter, python, pip)
│   ├── lib/                    # Python packages
│   └── pyvenv.cfg              # Environment configuration
├── kalman-tuning/              # Kalman filter analysis notebooks
│   ├── kalman-tuning.ipynb     # Main analysis notebook
│   ├── requirements.md         # Notebook requirements specification
│   └── requirements.txt        # Python package dependencies (if created)
└── ...                         # Additional notebook directories
```

## Tips

1. **Always activate the environment** before running notebooks or scripts
2. **Use the environment's Python** for any related scripts: `venv/bin/python script.py`
3. **Keep dependencies updated** by occasionally running `pip install -U package-name`
4. **Document new dependencies** in the appropriate requirements file
5. **Test in the environment** before committing analysis code

## Troubleshooting

### "ModuleNotFoundError" Errors

If you see `ModuleNotFoundError: No module named 'pandas'` or similar:

1. Verify the environment is activated: `echo $VIRTUAL_ENV`
2. Check the Python path: `which python` should point to `.../notebooks/venv/bin/python`
3. If not active, source the activation script again

### Jupyter Not Starting

If Jupyter fails to start:

1. Verify the environment is activated
2. Try running: `venv/bin/jupyter lab` with the full path
3. Check for port conflicts (default is 8888)
4. Try a different port: `jupyter lab --port 8889`

### Kernel Connection Issues

If the notebook kernel keeps dying:

1. Restart the kernel and try again
2. Verify all required packages are installed: `pip list`
3. Check for version conflicts between packages
4. Try recreating the environment from scratch

## Current Environment Contents

The environment currently includes:
- Jupyter Lab and Notebook
- IPython kernel
- Standard data science stack (to be installed as needed)

For the full list of installed packages, run:

```bash
source venv/bin/activate
pip list
```
