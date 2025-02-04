# artaf

## Autoregressive Behavior of Aviation Weather Forecasts

# Team members

- Oliver M. Haynold
- Neal Ylitalo

# Purpose

Pilots rely on [Terminal Aerodrome Forecasts](https://en.wikipedia.org/wiki/Terminal_aerodrome_forecast) or TAFs
published typically every six hours for about 700 airports in the United States. AAlthough these forecasts rely on
computer models, they still involve significant human judgment and are prepared by meteorologists. In the verbal
discussions accompanying the formal forecasts, the meteorologists sometimes make mention of "not yet" including or
changing something they foresee since they're not certain enough yet to find doing so worthwhile.

The purpose of this program is to see if we can find evidence of the meteorologists being too conservative (or too
aggressive) in incorporating new information as it becomes available. That is to say, we'd like to see whether there is
[autoregressive behavior](https://en.wikipedia.org/wiki/Autoregressive_model) in changes of the forecast for the same
parameter at the same time and place. Put simply, if the meteorologist makes his forecast worse than it was, is that
reason to believe he'll make it even worse in the next update? (*E.g.*, if in the evening before I want to go flying,
the forecast for 9 AM the next morning goes from a cloud base of 5000 ft to 4000 ft, is that reason to assume that by
the morning, the forecast will be 3000 ft, in which case I'll probably stay home?)

# Results

For now as a mere promise of the future (since the R code isn't quite ready for checkin yet), here is a [summary report
of the data](output/Statistics.md).

# Setup

To set up the project, clone the repository. You will need Python 3.10 or newer (or PyPy for a speed gain).

On Debian or Debian-based GNU/Linux distributions, you may need to first install the python3-venv package via your 
package manager.

Automated setup instructions, assuming python3 and bash are available:

```commandline
./install.sh
```

# How to run

We provide the shell script [runme.sh](runme.sh) that runs the entire analysis (as far as it's developed
as of now) all in the correct order. It downloads TAFs and then analyzes them (for now just by converting into a flat
file for statistical analysis).

If you want to run on a very small dataset just to see that it functions, pass the command line arguments
``--config tiny_data``. Note that we don't provide automated dependency management yet, so you
may have to install the required modules by hand. If you're running the full dataset, we will download about
20 million TAFs, so give it a little time and disk space. The full dataset will take about three hours to
download and 800 MB of storage.

## Options

```
options:
  -h, --help       show this help message and exit
  --config CONFIG  select a configuration to run in
```

## Configurations provided

These configurations can be accessed with `--config`:

- *full_set*, run by default if no configuration is given, is the full dataset from 2010
- *tiny_data* is a test dataset of two years and ten aerodromes

You can add your own configurations to [config/config.yaml](config/config.yaml).