#!/usr/bin/env -S sh

LOG_FILE="install.log"
TEST_REQS_FILE="test-artaf-python/requirements.txt"
VENV_DIR="venv"

. ./pythoncheck.sh

echo "" > $LOG_FILE

if [[ -d "./$VENV_DIR" ]]; then
    read -r -p 'A Python virtual environment exists; delete it and start fresh? [Y/n] ' answer
    answer=${answer:-Y}

    if [[ $answer == "Y" || $answer == "y" ]]; then
        rm -r $VENV_DIR && echo "Deleted old Python virtual environment in '$VENV_DIR' directory" > $LOG_FILE
        python_command -m venv $VENV_DIR && echo "Created new Python virtual environment in '$VENV_DIR' directory" >> $LOG_FILE
    fi
else
    python_command -m venv $VENV_DIR && echo "Created new Python virtual environment in '$VENV_DIR' directory" > $LOG_FILE
fi

. ./activatevenv.sh

notifyerror(){
    echo "There was a problem installing $1. See \"install.log\" for details."
    exit;
}

echo "Installing required packages:" && awk -F "==" '{print "    "$1}' $TEST_REQS_FILE
[[ $(pip install -r $TEST_REQS_FILE --log $LOG_FILE) ]] || notifyerror "a requirement"

echo "Done! To run the program, run runme.sh"
