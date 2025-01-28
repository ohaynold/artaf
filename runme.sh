#!/usr/bin/env -S sh

# This script runs the analysis in the logical order. It should be executed with the
# project directory as the working directory.
#
# To run on a tiny dataset for testing, pass command line arguments --config tiny_data

python3 artaf-python/process_data.py "$@"
