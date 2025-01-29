# artaf
Autoregressive Behavior of Aviation Weather Forecasts

# Team members
- Oliver M. Haynold
- Neal Ylitalo

# Set up
To set up the project, clone the repository. You will need the following packages installed:

- yaml (provided by PyYAML)
- requests
- pytz
- coverage (if you want to run a coverage report with `--run-coverage`)

# How to run
We provide the shell script [runme.sh](runme.sh) that runs the entire analysis (as far as it's developed
as of now) all in the correct order. It downloads TAFs and then analyzes them (for now just by counting).
If you want to run on a very small dataset just to see that it functions, pass the command line arguments
``--config tiny_data``. Note that for now we don't provide automated dependency management yet, so you
may have to install the required modules by hand. If you're running the full dataset, we will download about
30 million TAFs, so give it a little time and disk space.

## Options

```
options:
  -h, --help       show this help message and exit
  --config CONFIG  select a configuration to run in
  --run_coverage   produce a code coverage report from a linear run, not tests
```

## Configurations provided
These configurations can be accessed with `--config`
- *default*, run by default if no configuration is given, is the full dataset from 2010
- *tiny_data* is a test dataset of two years and ten aerodromes