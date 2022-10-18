#!/bin/bash
# Create temp Python virtual environment
# to fix https://github.com/cpp-linter/cpp-linter-action/issues/111
# This script can be decommissioned when
# resolve https://github.com/cpp-linter/clang-tools-pip/issues/15

usage() {
cat << EOF

Usage: sh $0 [param]
Create and activate Python virtual environment

Parameters:
    create: Create Python virtual environment
    activate: Activate Python virtual environment
    delete: Delete Python virtual environment

Examples:
    $ sh $0 create
    $ sh $0 activate
    $ sh $0 delete
EOF
exit 0
}

# a global var used to set the env var of the same name
CPP_LINTER_VENV_EXE=""


activate(){
    if [[ "$RUNNER_OS"  == "Windows" ]];then
        "$GITHUB_ACTION_PATH/venv/Scripts/activate"
        CPP_LINTER_VENV_EXE="$GITHUB_ACTION_PATH/venv/Scripts/python.exe" | tr "\\\\" "/"
    else
        source "$GITHUB_ACTION_PATH/venv/bin/activate"
        CPP_LINTER_VENV_EXE="$GITHUB_ACTION_PATH/venv/bin/python"
    fi
    echo "path to venv exe: $CPP_LINTER_VENV_EXE"
    export CPP_LINTER_VENV_EXE=$CPP_LINTER_VENV_EXE
    echo "{CPP_LINTER_VENV_EXE}={$CPP_LINTER_VENV_EXE}" >> $GITHUB_ENV
}

create(){
    python3 -m venv "$GITHUB_ACTION_PATH/venv"
    activate
    "$CPP_LINTER_VENV_EXE" -m pip install -r "$GITHUB_ACTION_PATH/requirements.txt"
}

delete(){
    rm -rf "$GITHUB_ACTION_PATH/venv"
}

#=============#
# MAIN starts #
#=============#
param=$1
case "$param" in
    *create*)   create ;;
    *activate*) activate ;;
    *delete*)   delete ;;
    *)          usage ;;
esac
