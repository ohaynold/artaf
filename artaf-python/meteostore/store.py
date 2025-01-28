import datetime
import os
import os.path
import zipfile

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
    Download a NWS weather product from Iowa State's archive.
    :param pil: NWS PIL
    :param start_time: A date or datetime specifying the start time from which to download the product.
    :param end_time: A date or datetime specifying the end time to which to download the product.
    :param center: Can be used to specify the desired center if the same PIL gets published by more than one.
    :param fmt: Can be "text", "html", or "zip", for the desired output format.
    :return: The downloaded weather product, as a string for text or html formats and as bytes for zip format.
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

    r = requests.get(base_url, params)
    r.raise_for_status()

    if fmt in ["text", "html"]:
        return r.content.decode(r.encoding)
    else:
        return r.content


def download_tafs(stations, from_year, to_year, force_refresh=False):
    """
    Download all TAFs not yet loaded into our data cache.
    :param stations: List of stations as StationDesc tuples
    :param from_year: Year from which to download, inclusive
    :param to_year: Year to which to download, inclusive
    :param force_refresh: If true, delete old datastore files
    """
    # Make sure dates are sane
    from_year = int(from_year)
    to_year = int(to_year)
    assert from_year <= to_year
    utcnow = datetime.datetime.now().astimezone(pytz.utc).replace(tzinfo=None)
    if datetime.date(to_year + 1, 1, 3) > utcnow.date():
        raise IndexError("I can only download a yearly archive once the year is over.")

    # Make sure stations are sane
    station_codes = [s.station for s in stations]
    for station in station_codes:
        assert len(station) == 4 and station.isalpha() and station.isupper()

    os.makedirs(DATA_PATH, exist_ok=True)
    new_downloads = 0

    for year in range(from_year, to_year + 1):
        file_path = os.path.join(DATA_PATH, "TAF" + str(year) + ".zip")
        tmp_file_path = file_path + "~"
        copy_file_path = file_path + "#"

        if os.path.exists(file_path) and force_refresh:
            os.unlink(file_path)
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
        if os.path.exists(copy_file_path):
            os.unlink(copy_file_path)

        stations_already_loaded = set()
        if os.path.exists(file_path):
            # If the output file exists and is complete, we're done
            with zipfile.ZipFile(file_path, "r") as old_zip_file:
                if set(old_zip_file.namelist()) >= set(station_codes):
                    continue
                # If the output file already exists but is incomplete, we'll have to recover
                # Compression is ZIP_STORED since this contains even more ZIP files
                with zipfile.ZipFile(tmp_file_path, "x", zipfile.ZIP_STORED) as out_zip:
                    for sub_file in old_zip_file.namelist():
                        with out_zip.open(sub_file, "w") as out_file, \
                                old_zip_file.open(sub_file, "r") as in_file:
                            out_file.write(in_file.read())
                        stations_already_loaded.add(sub_file)

        # Download TAFs for all the stations we don't already have
        for station in station_codes:
            # This means quite a few open and close operations, but we want to
            sub_file_name = station + ".zip"
            if sub_file_name in stations_already_loaded:
                continue
            pil = "TAF" + station[-3:]
            print("\rDownloading {} TAFs for {}...".format(station, year), end="", flush=True)
            data = get_iowa_state_nws_archive(pil,
                                              datetime.date(year, 1, 1),
                                              datetime.date(year + 1, 1, 1),
                                              fmt="zip")
            with zipfile.ZipFile(tmp_file_path, "a",zipfile. ZIP_STORED) as out_zip, \
                    out_zip.open(sub_file_name, "w") as out_file:
                out_file.write(data)

            # We copy the written archive into another temporary file and then rename
            # that to the output file. This means a lot of copying, but ensures that
            # program abort during a long downloading operation leaves us with a clean
            # archive.
            with open(tmp_file_path, "rb") as tmp_file, \
                    open(copy_file_path, "wb") as copy_file:
                copy_file.write(tmp_file.read())
            os.rename(copy_file_path, file_path)

            new_downloads += 1

    if new_downloads:
        print("\rDownloaded {} missing TAFs.            ".format(new_downloads))


if __name__ == "__main__":
    selected_stations = util.get_station_list()
    download_tafs(selected_stations, 2024, 2024)
