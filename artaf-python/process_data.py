""" This is a script to run the data download and processing in logical order. It should
be executed with the project directory as the working directory."""

import meteostore


def process_data():
    """
    Execute everything in the right order.
    """
    print("Getting TAFs...")
    stations = meteostore.download_taf_stations()
    meteostore.download_tafs(stations, 2024, 2024)
    print("Success!")


if __name__ == "__main__":
    process_data()
