#!/bin/sh
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

init(){
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
}

create(){
    python3 -m venv $PYTHON_VENV_PATH
}

activate(){
    if [ "$RUNNER_OS"  = "Windows" ];then
        cd $SCRIPT_PATH
        venv\Scripts\activate.bat
    else
        cd $SCRIPT_PATH
        source venv/bin/activate
    fi
}

delete(){
    rm -rf venv
}

install-deps(){
    python3 -m pip install -r "${SCRIPT_PATH}/requirements.txt"
}

#=============#
# MAIN starts #
#=============#

param=$1
case "$param" in
    *create*)
        init
        create
        ;;
    *activate*)
        init
        activate
        ;;
    *delete*)
        delete
        ;;
    *install-deps*)
        init
        install-deps
        ;;
    *)
        usage
        ;;
esac
