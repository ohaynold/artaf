""" This is a script to run the data download and processing in logical order. It should
be executed with the project directory as the working directory."""
import argparse
import collections
import os.path

import coverage
import yaml

import meteoparse
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


RunConfig = collections.namedtuple("RunConfig", ["stations", "year_from", "year_to", "coverage"])


def process_arguments():
    """
    Process command line arguments and load the appropriate configuration to run
    :return: List of aerodromes, year to start with, year to end with
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="select a configuration to run in", default="default")
    parser.add_argument("--run_coverage",
                        help="produce a code coverage report from a linear run, not tests",
                        action="store_true")
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
    return RunConfig(stations=stations, year_from=year_from, year_to=year_to, coverage=arguments.run_coverage)


def placeholder_analysis(raw_tafs):
    """
    This is just a placeholder to do some minimal analysis and exercise our data store and parser
    :param raw_tafs: TAFs as a generator given by get_tafs()
    """
    records = 0
    wind_speed_sum = 0
    wind_gust_sum = 0
    clouds_count = dict(few=0, sct=0, bkn=0, ovc=0)
    ceiling_sum = 0
    ceiling_count = 0
    for _, date_records in raw_tafs:
        for parsed_taf in meteoparse.parse_tafs(date_records):
            if parsed_taf.from_lines:
                records += 1
                wind_speed_sum += parsed_taf.from_lines[0].conditions.wind_speed
                wind_gust_sum += parsed_taf.from_lines[0].conditions.wind_gust \
                    if parsed_taf.from_lines[0].conditions.wind_gust is not None \
                    else parsed_taf.from_lines[0].conditions.wind_speed

                for cloud_layer in parsed_taf.from_lines[0].conditions.cloud_layers:
                    clouds_count[cloud_layer.CLOUD_LAYER_COVERAGE.lower()] += 1
                    if cloud_layer.CLOUD_LAYER_COVERAGE in ["BKN", "OVC"]:
                        ceiling_sum += int(cloud_layer.CLOUDS_ALTITUDE)
                        ceiling_count += 1

                if records % 1000 == 0:
                    print(
                        "\rRead {:,} TAFs with an avg. wind speed of {:.1f} knots, gusting {:.1f}...   " \
                            .format(records, wind_speed_sum / records, wind_gust_sum / records),
                        end="", flush=True)
                    # print(
                    #    "\rThere are {:,} TAFs forecasting cloud ceilings with an average cloudbase of {:03.0f}   " \
                    #        .format(ceiling_count, ceiling_sum/ceiling_count),
                    #    end="", flush=True)
    print("\rFinished reading {:,} TAFs with an avg. wind speed of {:.1f} knots, gusting {:.1f}...    "
          .format(records, wind_speed_sum / records, wind_gust_sum / records))


class CoverageRunner:
    def __init__(self, active):
        self.active = active
        self.coverage = None
        if self.active:
            import coverage

    def __enter__(self):
        if self.active:
            self.coverage = coverage.Coverage()
            self.coverage.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.active:
            self.coverage.stop()
            self.coverage.save()
            report_dir = os.path.join("test_results", "execution_coverage")
            self.coverage.html_report(directory=report_dir)


def process_data():
    """
    Execute everything in the right order.
    """

    run_config = process_arguments()

    with CoverageRunner(active=run_config.coverage):
        print("Getting TAFs...")
        raw_tafs = meteostore.get_tafs(run_config.stations, run_config.year_from, run_config.year_to)

        # Just a placeholder to do something with our TAFs
        print("Evaluating TAFs (a placeholder for now)...")
        placeholder_analysis(raw_tafs)

        print("Success!")


if __name__ == "__main__":
    process_data()
