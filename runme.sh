#!/usr/bin/env -S bash

# This script runs the analysis in the logical order. It should be executed with the
# project directory as the working directory.
#
# To run on a tiny dataset for testing, pass command line arguments --config tiny_data

# Run download and evaluation
. ./pythoncheck.sh
. ./activatevenv.sh
python_command artaf-python/process_data.py "$@"

# Make the report
# (artaf-python/process_data.py writes .current_data_set)
mkdir -p output
quarto render artaf-r/Report.qmd -P data_set:$(cat .current_data_set)
mv .output/artaf-r/Report.pdf output/Haynold_Ylitalo_2025_Autoregressive.pdf

echo "Finished!"
echo "Please see the output in output/Report.pdf"
