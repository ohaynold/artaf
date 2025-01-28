import csv
import os.path
from collections import namedtuple

StationDesc = namedtuple("station_desc",
                         ["station", "name", "latitude", "longitude"])

STATION_PATH = os.path.join("config", "stations.csv")


def get_station_list():
    """
    Get a list of stations to consider from the configuration file stations.csv.
    :return: List of StationDesc tuples
    """
    with open(STATION_PATH, "r") as station_file:
        reader = csv.DictReader(station_file)
        stations = sorted(reader, key=lambda r: r["station"])
        return [StationDesc(l["station"], l["name"], l["latitude"], l["longitude"]) for l in stations]
