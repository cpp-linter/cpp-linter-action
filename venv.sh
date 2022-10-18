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

activate(){
    if [[ "$RUNNER_OS"  == "Windows" ]];then
        ./venv/Scripts/activate
    else
        source ./venv/bin/activate
    fi
    export CPP_LINTER_VENV_EXE=`python -c "import sys; print(sys.executable)"`
}

create(){
    python3 -m venv venv
    activate
    $CPP_LINTER_VENV_EXE -m pip install -r requirements.txt
}

delete(){
    rm -rf venv
}

#=============#
# MAIN starts #
#=============#
cd $GITHUB_ACTION_PATH
param=$1
case "$param" in
    *create*)   create ;;
    *activate*) activate ;;
    *delete*)   delete ;;
    *)          usage ;;
esac
