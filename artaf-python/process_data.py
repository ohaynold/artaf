""" This is a script to run the data download and processing in logical order. It should
be executed with the project directory as the working directory."""
import argparse
import os.path

import yaml

import meteostore

CONFIG_PATH = os.path.join("config", "config.yaml")


def get_config(config_name):
    """
    Load the configuration with the given name from config/config.yaml.
    We first load the configuration "general" and then override with values from the specified configuration.
    :param config_name: Name of the configuration to be loaded
    :return: A dictionary with configuration parameters
    """
    with open(CONFIG_PATH, "r") as config_file:
        config_raw = yaml.safe_load(config_file)
    config = config_raw["general"] if config_raw["general"] else {}
    if config_raw[config_name]:
        config.update(config_raw[config_name])
    return config


def process_arguments():
    """
    Process command line arguments and load the appropriate configuration to run
    :return: List of aerodromes, year to start with, year to end with
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="select a configuration to run in", default="default")
    arguments = parser.parse_args()
    config_name = arguments.config
    config = get_config(config_name)
    year_from = config["year_from"]
    year_to = config["year_to"]
    stations = meteostore.get_station_list()
    if "aerodromes" in config:
        stations = list(filter(lambda station: station.station in config["aerodromes"], stations))
    print("Running in configuration {} for years from {} through {} with {} aerodromes.".format(
        arguments.config, year_from, year_to, len(stations)))
    return stations, year_from, year_to


def process_data():
    """
    Execute everything in the right order.
    """

    stations, year_from, year_to = process_arguments()

    print("Getting TAFs...")
    raw_tafs = meteostore.get_tafs(stations, year_from, year_to)

    # Just a placeholder to do something with our TAFs
    records = 0
    for _, date_records in raw_tafs:
        for _ in date_records:
            records += 1
    print("I have read {} TAFs.".format(records))

    print("Success!")


if __name__ == "__main__":
    process_data()
