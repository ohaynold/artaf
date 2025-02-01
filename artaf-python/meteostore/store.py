"""This is the main functionality of meteostore, downloading, storing, and retrieving TAFs."""
import contextlib
import datetime
import os
import os.path
import re
import zipfile
from collections import namedtuple
from artaf_util import safe_open_write

import pytz
import requests

from meteostore import util

DATA_PATH = os.path.join("data", "raw")


def cleanup_datetime(d):
    """
    Helper function to take any date-like object and turn it into a naive datetime in UTC.
    If the input object already is a datetime, it must be naive and in UTC.
    :param d: input date, a datetime.date or naive datetime.datetime
    :return: naive datetime.datetime
    """
    for a in ["year", "month", "day"]:
        if not hasattr(d, a):
            raise AttributeError("I need at least a date with year, month, day.")
    if hasattr(d, "tzinfo") and d.tzinfo is not None:
        raise ValueError("I need a naive UTC date without timezone information.")
    if hasattr(a, "hour"):
        return datetime.datetime(d.year, d.month, d.day, d.hour, d.minute)
    return datetime.datetime(d.year, d.month, d.day)


def get_iowa_state_nws_archive(pil, start_time, end_time, center=None, fmt="text"):
    """
    Download a NWS weather product from the Iowa Environmental Mesonet archive at Iowa State.
    :param pil: NWS PIL
    :param start_time: A date or datetime specifying the start time from which to download the
    product.
    :param end_time: A date or datetime specifying the end time to which to download the product.
    :param center: Can be used to specify the desired center if the same PIL gets published by more
    than one.
    :param fmt: Can be "text", "html", or "zip", for the desired output format.
    :return: The downloaded weather product, as a string for text or html formats and as bytes for
    zip format.
    """

    start_time = cleanup_datetime(start_time)
    end_time = cleanup_datetime(end_time)
    base_url = "https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py"
    # noinspection SpellCheckingInspection
    params = {"pil": pil,
              "sdate": start_time.strftime("%Y-%m-%dT%H:%MZ"),
              "edate": end_time.strftime("%Y-%m-%dT%H:%MZ"),
              "fmt": fmt,
              "limit": "9999",
              "order": "asc"
              }
    if center:
        params["center"] = center

    r = requests.get(base_url, params, timeout=60)
    r.raise_for_status()

    if fmt in ["text", "html"]:
        return r.content.decode(r.encoding)
    return r.content


def ensure_stations_years_sane(stations, from_year, to_year):
    """
    Make sure that we can download for a given set of stations and years as far as obvious
    sanity checks go.
    :param stations: List of stations as StationDesc tuples
    :param from_year: Year from which to download, inclusive
    :param to_year: Year to which to download, inclusive
    :return:
    """
    # Make sure dates are sane
    from_year = int(from_year)
    to_year = int(to_year)
    assert from_year <= to_year
    utcnow = datetime.datetime.now().astimezone(pytz.utc).replace(tzinfo=None)
    if datetime.date(to_year + 1, 1, 3) > utcnow.date():
        raise IndexError("I can only download a yearly archive once the year is over.")
    # Make sure stations are sane
    station_codes = [(s.station, s.center) for s in stations]
    for station, center in station_codes:
        assert len(station) == 4 and station.isalpha() and station.isupper()
        assert len(center) == 4 and center.isalpha() and center.isupper()
    return station_codes, from_year, to_year


def _prepare_taf_download(station_codes, file_path, tmp_dir_path, tmp_file_path, force_refresh):
    """A helper function for download_tafs() to recover from a possible previous failed download
    and to create and clean up the directory structure"""
    if os.path.exists(file_path) and force_refresh:
        os.unlink(file_path)
    if os.path.exists(tmp_file_path):
        os.unlink(tmp_file_path)
    if os.path.exists(file_path):
        # If the output file exists and is complete, we're done
        with zipfile.ZipFile(file_path, "r") as old_zip_file:
            if set(old_zip_file.namelist()) >= set((s + ".zip" for s, _ in station_codes)):
                return True
            # If the output file already exists but is incomplete, we'll have to recover
            # We expand the files into the temporary directory
            if not os.path.exists(tmp_dir_path):
                os.mkdir(tmp_dir_path)
            for sub_file in old_zip_file.namelist():
                with open(os.path.join(tmp_dir_path, sub_file), "wb") as out_file, \
                        old_zip_file.open(sub_file, "r") as in_file:
                    out_file.write(in_file.read())
    # Ensure temporary directory exists and is clear of temporary files
    if not os.path.exists(tmp_dir_path):
        os.mkdir(tmp_dir_path)
    for filename in os.listdir(tmp_dir_path):
        if filename.endswith("~"):
            os.unlink(os.path.join(tmp_dir_path, filename))
    return False


def _finish_download(year, file_path, tmp_dir_path, tmp_file_path):
    """A helper function for download_tafs() to package up downloaded data and clean up after
    itself"""
    # Now we collect the temporary directory into a ZIP file -- normally we don't compress
    # collections of compressed files, but it turns out that ZIP as delivered from Iowa State is
    # horribly inefficient for many small files. At the same time, I don't want to modify the
    # original files. Thus, we just compress them again. This may take a little while.
    print(f"\rPackaging TAFs for {year}...          ", end="", flush=True)
    with zipfile.ZipFile(tmp_file_path, "w", zipfile.ZIP_LZMA) as new_zip_file:
        for filename in sorted(os.listdir(tmp_dir_path)):
            with open(os.path.join(tmp_dir_path, filename), "rb") as in_file:
                new_zip_file.writestr(filename, in_file.read())
    os.rename(tmp_file_path, file_path)
    # Now we can get rid of the temporary directory
    for filename in os.listdir(tmp_dir_path):
        os.unlink(os.path.join(tmp_dir_path, filename))
    os.rmdir(tmp_dir_path)


def download_tafs(stations, from_year, to_year, force_refresh=False):
    """
    Download all TAFs not yet loaded into our data cache.
    :param stations: List of stations as StationDesc tuples
    :param from_year: Year from which to download, inclusive
    :param to_year: Year to which to download, inclusive
    :param force_refresh: If true, delete old datastore files
    """
    station_codes, from_year, to_year = ensure_stations_years_sane(stations, from_year, to_year)

    os.makedirs(DATA_PATH, exist_ok=True)
    new_downloads = 0

    for year in range(from_year, to_year + 1):
        file_path = os.path.join(DATA_PATH, "TAF" + str(year) + ".zip")
        tmp_dir_path = os.path.join(DATA_PATH, "TAF" + str(year) + "~")
        tmp_file_path = file_path + "~"

        if _prepare_taf_download(station_codes, file_path, tmp_dir_path, tmp_file_path,
                                 force_refresh):
            # We're already done
            continue

        # Download TAFs for all the stations we don't already have
        for station, center in station_codes:
            # This means quite a few open and close operations, but we want to
            sub_file_name = station + ".zip"
            if os.path.exists(os.path.join(tmp_dir_path, sub_file_name)):
                continue

            print(f"\rDownloading {station} TAFs for {year}...", end="", flush=True)
            data = get_iowa_state_nws_archive("TAF" + station[-3:],
                                              datetime.date(year, 1, 1),
                                              datetime.date(year + 1, 1, 1),
                                              center=center,
                                              fmt="zip")
            with safe_open_write(os.path.join(tmp_dir_path, sub_file_name), "wb") as out_file:
                out_file.write(data)

            new_downloads += 1

        _finish_download(year, file_path, tmp_dir_path, tmp_file_path)

    if new_downloads:
        print(f"\rDownloaded {new_downloads} missing TAFs.            ")


_taf_file_re = re.compile(r"TAF[A-Z]{3}_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2}).txt")

TimeTafRecord = namedtuple("TimeTafRecord", ["time", "text"])


# noinspection PyShadowingNames
def _get_tafs_station(station, data_files):
    """
    A helper function for get_tafs that returns a generator of TimeTafRecords for the
    given station and years. Should not be called outside of get_tafs().
    :param station: The station for which records are to be returned
    :param data_files: A dictionary of years and the corresponding ZIP files
    """
    previous_taf_date = None
    for data_file in data_files.values():
        with data_file.open(station.station + ".zip", "r") as inner_file:
            with zipfile.ZipFile(inner_file, "r") as inner_zip:
                for file_name in sorted(inner_zip.namelist()):
                    match = _taf_file_re.fullmatch(file_name)
                    date_parts = [int(x) for x in match.groups()]
                    taf_date = datetime.datetime(date_parts[0], date_parts[1], date_parts[2],
                                                 date_parts[3], date_parts[4])
                    # There is an oddity in Iowa State's archives whereby a few files are
                    # included twice
                    if taf_date == previous_taf_date:
                        continue
                    assert previous_taf_date is None or taf_date > previous_taf_date
                    previous_taf_date = taf_date
                    taf_content = inner_zip.read(file_name).decode("ascii")
                    yield TimeTafRecord(taf_date, taf_content)


StationTafRecord = namedtuple("StationTafRecord", ["station", "tafs"])


# noinspection PyShadowingNames
def get_tafs(stations, from_year, to_year):
    """
    Get TAFs for the given times and places from the store. Download if need be.
    The result is a generator of StationTafRecords which in turn contain
    generators of TimeTafRecords in their tafs field. Results are in chronological order
    for each station.
    :param stations: A list of meteostore.StationDesc tuples
    :param from_year: Year from which to serve data, inclusive
    :param to_year: Year to which to serve data, inclusive
    """
    stations = list(stations)
    download_tafs(stations, from_year, to_year)
    years = list(range(from_year, to_year + 1))
    # ExitStack will provide context management for all the files we're opening, i.e., close them
    # for us once we're finished or raise and exception
    with contextlib.ExitStack() as stack:
        data_files = {
            year: stack.enter_context(
                zipfile.ZipFile(os.path.join(DATA_PATH, "TAF" + str(year) + ".zip"), "r"))
            for year in years}
        for a_station in stations:
            yield StationTafRecord(a_station, _get_tafs_station(a_station, data_files))


if __name__ == "__main__":
    selected_stations = util.get_station_list()
    i = 0
    my_start_time = datetime.datetime.now()
    for _, taf_records in get_tafs(selected_stations, 2024, 2024):
        for date, content in taf_records:
            i += 1
    my_end_time = datetime.datetime.now()
    print(
        f"I have {i} TAFs. This took me {((my_end_time - my_start_time).total_seconds())} seconds.")
