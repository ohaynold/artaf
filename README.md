# artaf

## Autoregressive Behavior of Aviation Weather Forecasts

# Team members

- Oliver M. Haynold
- Neal Ylitalo

# Purpose

Pilots rely on [Terminal Aerodrome Forecasts](https://en.wikipedia.org/wiki/Terminal_aerodrome_forecast) or TAFs
published typically every six hours for about 700 airports in the United States. Although these forecasts rely on
computer models, they still involve significant human judgment and are prepared by meteorologists. In the verbal
discussions accompanying the formal forecasts, the meteorologists sometimes make mention of "not yet" including or
changing something they foresee  since there isn't enough certainty yet.

The purpose of this program is to see if we can find evidence of the meteorologists being too conservative (or too
aggressive) in incorporating new information as it becomes available. That is to say, we'd like to see whether there is
[autoregressive behavior](https://en.wikipedia.org/wiki/Autoregressive_model) in changes of the forecast for the same
parameter at the same time and place. Put simply, if the meteorologist makes his forecast worse than it was, is that
reason to believe he'll make it even worse in the next update? (*E.g.*, if in the evening before I want to go flying,
the forecast for 9 AM the next morning goes from a cloud base of 5000 ft to 4000 ft, is that reason to assume that by
the morning, the forecast will be 3000 ft, in which case I'll probably stay home?)

# Results

The report generated by running the software is [published at Zenodo](https://doi.org/10.5281/zenodo.14954569).

# Setup

To set up the project, clone the repository. You will also need all of the following: 

1. A ``bash`` shell
   - On Windows, you can use Git Bash [included with git](https://git-scm.com/downloads/win)
2. [Python 3.10 or newer](https://www.python.org/downloads/)
   - (advanced use: PyPy for a speed gain)
3. [R 4.4 or newer](https://cran.r-project.org/).
4. [Rtools 4.4 or newer](https://cran.r-project.org/bin/windows/Rtools/rtools44/rtools.html)
   The following packages may be required, depending on your setup and the availability of binary
   packages:
   -  openssl dev package (required for compiling some R packages)
      - deb: libssl-dev (Debian, Ubuntu, etc)
      - rpm: openssl-devel (Fedora, CentOS, RHEL)
      - brew: openssl@1.1 (Mac OSX)
   - udunits2 dev package 
      - deb: libudunits2-dev (Debian, Ubuntu, ...)
      - rpm: udunits2-devel (Fedora, EPEL, ...)
      - brew: udunits (OSX)
   - GDAL dev package 
     - deb: libgdal-dev (Debian, Ubuntu, etc.)

5. [Quarto 1.6 or newer](https://quarto.org/docs/get-started/).
6. A common [(La)TeX](https://www.tug.org/texlive/) distribution. (Alternatively, you could change the output file format from PDF to another format.)
   - ``xelatex`` - provided in Debian by texlive-xetex

On Debian or Debian-based GNU/Linux distributions, you may also need to first install the ``python3-venv`` package via your 
package manager.

After you install the prerequisites, all that's required to set it up is to run the following command in your shell:

```commandline
./install.sh
```

# How to run

We provide the shell script [`runme.sh`](runme.sh) that runs the entire analysis  all in the correct order. 
It downloads TAFs and then analyzes them (for now just by converting into a flat
file for statistical analysis). Thus, you should get the paper we published from a simple

```commandline
./runme.sh
```

On the first run, or whenever the directory `data/raw` does not exist, the script will obtain an [entire data set
from Zenodo](https://zenodo.org/records/14954564). This a download of about 1.5 GB. Otherwise, for incremental updates
to the data set, it will obtain individual TAFs from [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu/). 

If you want to run on a very small dataset just to see that it functions, pass the command line arguments
``--config tiny_data``. If you want to avoid the 1.5 GB download, create an empty directory `data/raw` first.

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

## Testing

The script `./run_tests.sh` will run the various function tests we provide and create test results as well as a
coverage report. Some of the tests require some test data, so if you run this on a clean install, running the tests
will also download the entire dataset from Zenodo, which may take a little while. If you only want to run the tests,
but have no interest in the data set, you can `mkdir -p data/raw`, in which case only the small data set used for
testing will be downloaded.
