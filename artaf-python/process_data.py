""" This is a script to run the data download and processing in logical order. It should
be executed with the project directory as the working directory."""
import os.path

import meteostore
import yaml

def get_config(config_name):
    CONFIG_PATH = os.path.join("config", "config.yaml")
    with open(CONFIG_PATH, "r") as config_file:
        config_raw = yaml.parse(config_file)
    config = config_raw["general"]
    config.update(config_raw[config_name])
    return config

def process_data():
    """
    Execute everything in the right order.
    """
    print("Getting TAFs...")
    stations = meteostore.download_taf_stations()
    meteostore.download_tafs(stations, 2024, 2024)
    print("Success!")


if __name__ == "__main__":
    print(get_config("default"))
    # process_data()
