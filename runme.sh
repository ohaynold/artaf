#!/usr/bin/env -S sh

# This script runs the analysis in the logical order. It should be executed with the
# project directory as the working directory.
#
# To run on a tiny dataset for testing, pass command line arguments --config tiny_data

. ./activatevenv.sh
if [[ $VIRTUAL_ENV_PROMPT != "venv" ]]; then
    answer="a"
    while [[ "YyNn" != *"$answer"* ]] ; do
        read -p "No Python virtual environment loaded, try running install.sh first. Continue anyway? [yN]: " answer
        answer=${answer:-N}

        if [[ "Nn" == *"$answer"* ]]; then
            exit
        fi
    done
fi

python3 artaf-python/process_data.py "$@"
