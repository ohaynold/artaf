#!/usr/bin/env -S bash

. ./pythoncheck.sh
. ./activatevenv.sh

export PYTHONPATH=$PWD/artaf-python/:$PWD/test-artaf-python/:$PYTHONPATH

echo "*** Linting the Python code... ***"
pylint test-artaf-python artaf-python

echo "*** Running Python unit tests... ***"
coverage run -m pytest
coverage html

echo "*** Checking the Citation ***"
cffconvert --validate

echo "*** Finished... ***"
