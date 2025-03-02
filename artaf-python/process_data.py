""" This is a script to run the data download and processing in logical order. It should
be executed with the project directory as the working directory."""
import argparse
import collections
import os
import os.path

import yaml

import analyzer
import meteostore

CONFIG_PATH = os.path.join("config", "config.yaml")


def get_config(config_name):
    """
    Load the configuration with the given name from config/config.yaml.
    We first load the configuration "general" and then override with values from the specified
    configuration.
    :param config_name: Name of the configuration to be loaded
    :return: A dictionary with configuration parameters
    """
    with open(CONFIG_PATH, "r", encoding="ascii") as config_file:
        config_raw = yaml.safe_load(config_file)
    config = config_raw["general"] if config_raw["general"] else {}
    if config_raw[config_name]:
        config.update(config_raw[config_name])
    return config


RunConfig = collections.namedtuple(
    "RunConfig",
    ["stations", "year_from", "year_to", "config_name", "parallel"])


def process_arguments():  # pragma: no cover
    """
    Process command line arguments and load the appropriate configuration to run
    :return: List of aerodromes, year to start with, year to end with
    """
    parser = argparse.ArgumentParser(prog="runme.sh [or] process_data.py")
    parser.add_argument("--config", help="select a configuration to run in",
                        default="full_set")
    arguments = parser.parse_args()
    config_name = arguments.config
    config = get_config(config_name)
    year_from = config["year_from"]
    year_to = config["year_to"]
    parallel = config["parallel"]
    stations = meteostore.get_station_list()
    if "aerodromes" in config:
        stations = list(filter(lambda station: station.station in config["aerodromes"], stations))
    print(f"Running in configuration {arguments.config} for years from {year_from} through "
          f"{year_to} with {len(stations)} aerodromes.")
    return RunConfig(stations=stations, year_from=year_from, year_to=year_to,
                     config_name=config_name, parallel=parallel)


def process_data():  # pragma: no cover
    """
    Execute everything in the right order.
    """

    run_config = process_arguments()

    print("Getting TAFs...")
    meteostore.download_tafs(run_config.stations, run_config.year_from, run_config.year_to)

    print("Parsing and analyzing TAFs...")

    def progress(tafs, hours, errors):
        """Display progress"""
        print(f"\rRead {tafs:,} TAFs, {hours:,} st. hours, "
              f"saw {errors:,} errors...",
              end="", flush=True)

    processor = analyzer.HourlyHistogramProcessor(
        analyzer.DEFAULT_JOBS,
        os.path.join("data", "histograms", run_config.config_name),
        progress_callback=progress,
        parallel=run_config.parallel)
    processor.process(run_config.stations, run_config.year_from, run_config.year_to)
    print(f"\rProcessed {processor.processed_hours:,} station hours, encountered "
          f"{processor.processed_errors:,} errors...")

    with open(".current_data_set", "w", encoding="ascii") as current_data_set_file:
        current_data_set_file.write(run_config.config_name)

    print("Success!")


if __name__ == "__main__":
    process_data()
