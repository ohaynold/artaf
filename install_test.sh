#!/usr/bin/env -S sh

LOG_FILE="install.log"
TEST_REQS_FILE="test-artaf-python/requirements.txt"
VENV_DIR="venv"

. ./pythoncheck.sh

echo "" > $LOG_FILE

. ./activatevenv.sh

notifyerror(){
    echo "There was a problem installing $1. See \"install.log\" for details."
    exit;
}

echo "Installing required packages:" && awk -F "==" '{print "    "$1}' $TEST_REQS_FILE
[[ $(pip install -r $TEST_REQS_FILE --log $LOG_FILE) ]] || notifyerror "a requirement"

echo "Done! To run the program, run runme.sh"
