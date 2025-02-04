""" This is a script to run the data download and processing in logical order. It should
be executed with the project directory as the working directory."""
import argparse
import collections
import csv
import io
import os.path
import zipfile

import yaml

import meteoparse
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


RunConfig = collections.namedtuple("RunConfig",
                                   ["stations", "year_from", "year_to", "config_name"])


def process_arguments():
    """
    Process command line arguments and load the appropriate configuration to run
    :return: List of aerodromes, year to start with, year to end with
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="select a configuration to run in",
                        default="full_set")
    arguments = parser.parse_args()
    config_name = arguments.config
    config = get_config(config_name)
    year_from = config["year_from"]
    year_to = config["year_to"]
    stations = meteostore.get_station_list()
    if "aerodromes" in config:
        stations = list(filter(lambda station: station.station in config["aerodromes"], stations))
    print(f"Running in configuration {arguments.config} for years from {year_from} through "
          f"{year_to} with {len(stations)} aerodromes.")
    return RunConfig(stations=stations, year_from=year_from, year_to=year_to,
                     config_name=config_name)


def process_data():
    """
    Execute everything in the right order.
    """

    run_config = process_arguments()

    print("Getting TAFs...")
    raw_tafs = meteostore.get_tafs(run_config.stations, run_config.year_from,
                                   run_config.year_to)

    print("Parsing and regularizing TAFs...")

    output_dir = "data"
    lines_written = 0
    errors = 0
    output_path = os.path.join(output_dir, f"TAF Lines {run_config.config_name}.csv.zip")
    error_path = os.path.join(output_dir, f"TAF Errors {run_config.config_name}.csv.zip")
    with (
        zipfile.ZipFile(output_path, "w", zipfile.ZIP_LZMA) as out_zip_file,
        out_zip_file.open("TAF Lines.csv", "w") as out_bin_file,
        io.TextIOWrapper(out_bin_file, encoding="ascii", newline="\n") as out_file,
        zipfile.ZipFile(error_path, "w", zipfile.ZIP_LZMA) as err_zip_file,
        err_zip_file.open("TAF Errors.csv", "w") as out_err_file,
        io.TextIOWrapper(out_err_file, encoding="ascii", newline="\n") as err_file
    ):
        writer = csv.writer(out_file)
        writer.writerow(["aerodrome","issue_time","issue_place","amendment",
                         "hour_starting", "wind_speed","wind_gust"])
        error_writer = csv.writer(err_file)
        error_writer.writerow(["raw_message", "error", "info"])
        for station, taf_messages in raw_tafs:
            parsed_tafs = meteoparse.parse_tafs(taf_messages)
            hourly_lines = meteoparse.regularize_tafs(parsed_tafs)
            for line in hourly_lines:
                if isinstance(line, meteoparse.HourlyTafLine):
                    clean_line = [line.aerodrome, line.issued_at.strftime("%Y-%m-%dT%H:%M"),
                                  line.issued_in,
                                  line.amendment.name if line.amendment is not None else None,
                                  line.hour_starting.strftime("%Y-%m-%dT%H:%M"),
                                  line.wind_speed, line.wind_gust]
                    writer.writerow(clean_line)
                    lines_written += 1
                    if lines_written % 10_000 == 0:
                        print(f"\rProcessing {station.station}, wrote {lines_written:,} hourly TAF "
                              f"lines, {errors} errors...",
                              flush=True, end="")
                elif isinstance(line, meteoparse.TafParseError):
                    error_writer.writerow([line.message_text, line.error, line.hint])
                    errors += 1
                else:
                    raise TypeError("Unexpected parser output")
    print(f"\rWrote {lines_written:,} hourly TAF lines, {errors} errors.                          ")
    print(f"Output written to {output_path}.")

    print("Success!")


if __name__ == "__main__":
    process_data()
