#!/bin/sh
# Create temp Python virtual environment
# to fix https://github.com/cpp-linter/cpp-linter-action/issues/111
# This script can be decommissioned when
# resolve https://github.com/cpp-linter/clang-tools-pip/issues/15

create_venv(){
    python3 -m venv $PYTHON_VENV_PATH
}

activate_venv(){
    if [ "$RUNNER_OS"  = "Windows" ];then
        $PYTHON_VENV_PATH\Scripts\activate.bat
    else
        source $PYTHON_VENV_PATH/bin/activate
    fi
}

#=============#
# MAIN starts #
#=============#

# https://stackoverflow.com/a/29835459
SCRIPT_PATH="$(
  CDPATH='' \
  cd -- "$(
    dirname -- "$0"
  )" && (
    pwd -P
  )
)"
readonly SCRIPT_PATH

if [ "$RUNNER_OS"  = "Windows" ];then
    readonly PYTHON_VENV_PATH="${SCRIPT_PATH}\venv"
else
    readonly PYTHON_VENV_PATH="${SCRIPT_PATH}/venv"
fi

create_venv
activate_venv

python3 -m pip install -r "${SCRIPT_PATH}/requirements.txt"
