"""Helper functions for meteostore."""

import csv
import os.path
from collections import namedtuple

StationDesc = namedtuple("StationDesc",
                         ["station", "name", "latitude", "longitude", "center"])

STATION_PATH = os.path.join("config", "stations.csv")


def get_station_list():
    """
    Get a list of stations to consider from the configuration file stations.csv.
    :return: List of StationDesc tuples
    """
    with open(STATION_PATH, "r", encoding="ascii") as station_file:
        reader = csv.DictReader(station_file)
        stations = sorted(reader, key=lambda r: r["station"])
        return [StationDesc(l["station"], l["name"], l["latitude"], l["longitude"], l["center"])
                for l in stations]
