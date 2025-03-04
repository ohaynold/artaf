#!/usr/bin/env -S bash

LOG_FILE="install.log"
REQS_FILE="artaf-python/requirements.txt"
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

echo "Installing pip..."
python_command -m pip install --upgrade pip >>$LOG_FILE 2>&1

# Make sure that the first pip in $PATH is in our new virtual environment
[[ $(which pip) == "$VIRTUAL_ENV"* ]] || notifyerror "pip"

echo "Installing required packages:" && awk -F "==" '{print "    "$1}' $REQS_FILE
[[ $(pip install -r $REQS_FILE --log $LOG_FILE) ]] || notifyerror "a requirement"

echo "Installing R environment..."
Rscript renv/restore.R >>$LOG_FILE 2>&1


echo "Done! To run the program, run runme.sh"
