#!/usr/bin/env -S sh

LOG_FILE="install.log"
TEST_REQS_FILE="test-artaf-python/requirements.txt"
VENV_DIR="venv"

. ./pythoncheck.sh
. ./activatevenv.sh
if [[ $VIRTUAL_ENV_PROMPT != "venv" ]]; then
    answer="a"
    while [[ "YyNn" != *"$answer"* ]] ; do
        read -r -p "No Python virtual environment loaded, try running install.sh first. Continue anyway? [y/N]: " answer
        answer=${answer:-N}

        if [[ "Nn" == *"$answer"* ]]; then
            exit
        fi
    done
fi

export PYTHONPATH=artaf-python:test-artaf-python:$PYTHONPATH

echo "*** Linting the Python code... ***"
pylint test-artaf-python artaf-python

echo "*** Running Python unit tests... ***"
coverage run -m pytest
coverage html

echo "*** Finished... ***"
