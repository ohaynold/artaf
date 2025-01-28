"""This is a helper to get a list of stations. In the interest of reproducibility,
we limit this to a fixed set of stations in existence at the time we created this
analysis, stored in config/stations.csv. You can update this list at any later time
from this script"""

import csv
import sys
from collections import namedtuple

import requests

station_desc = namedtuple("station_desc",
                          ["station", "name", "latitude", "longitude"])


def get_taf_stations():
    """
    Get a list of all stations for which TAFs are issued from Iowa State's Mesonet
    :return: Alphabetically sorted list of stations as station_desc tuples
    """
    request_url = "https://mesonet.agron.iastate.edu/api/1/nws/taf_overview.json"
    request_result = requests.get(request_url)
    request_result.raise_for_status()

    json_result = request_result.json()

    # Station names have inconsistent capitalization. Most are uppercase but some
    # are not. We just make all of them uppercase for consistency.
    result = [station_desc(x["station"], x["name"].upper(), x["lat"], x["lon"])
              for x in json_result["data"]]
    result.sort(key=lambda x: x.station)

    # The number of stations shouldn't change drastically. At the time of this being
    # written it was 713.
    assert 650 < len(result) < 750

    # If KORD isn't in the dataset, then O'Hare has closed or got renamed, which
    # is unlikely.
    assert "KORD" in (x.station for x in result)

    return result


if __name__ == "__main__":
    stations = get_taf_stations()
    out_csv = csv.writer(sys.stdout)
    out_csv.writerow(["station", "name", "latitude", "longitude"])
    for s in stations:
        out_csv.writerow([s.station, s.name, s.latitude, s.longitude])
