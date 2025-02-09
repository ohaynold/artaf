"""meteostore handles the download, storage, and service on demand of raw TAFs.
We obtain our TAFs from Iowa Environmental Mesonet at Iowa State, https://mesonet.agron.iastate.edu/
TAFs are stored in compressed archives and can be transparently iterated through with get_tafs()."""

__all__ = ["download_taf_stations", "download_tafs", "StationDesc", "get_station_list", "get_tafs"]

from meteostore.download_stations import download_taf_stations
from meteostore.store import download_tafs, get_tafs
from meteostore.util import StationDesc, get_station_list
