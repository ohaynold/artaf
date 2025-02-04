"""This provide summary statistics of the TAFs, i.e., the core of our analysis once we've got
all the data"""

import datetime
from collections import namedtuple

import meteoparse.tafparser
import meteostore

ONE_HOUR = datetime.timedelta(seconds=3600)

HourlyGroup = namedtuple("HourlyGroup", ["hour_starting", "items"])
HourlyItem = namedtuple("HourlyItem", ["issued_at", "amendment", "conditions"])


def arrange_by_hour_forecast(tafs):
    """
    Rearrange a stream of TAFs, in ascening order and for the same station, so as to have all the
    forecasts for a given hour together, in the order they were issues.
    :param tafs: A sequence of TAFs and/or errors
    """
    hourly_cache = {}
    for taf in tafs:
        if isinstance(taf, meteoparse.tafparser.ParsedForecast):
            # Cache this TAF
            if not taf.from_lines:
                continue
            for from_line in taf.from_lines:
                if from_line.valid_from not in hourly_cache:
                    hourly_cache[from_line.valid_from] = []
                hourly_cache[from_line.valid_from].append(HourlyItem(taf.issued_at,
                                                                     taf.amendment,
                                                                     from_line.conditions))

            first_hour_available = min(hourly_cache.keys())
            if len(hourly_cache) > 0 and first_hour_available < taf.issued_at - ONE_HOUR:
                yield HourlyGroup(first_hour_available, hourly_cache[first_hour_available])
                del hourly_cache[first_hour_available]
        elif isinstance(taf, meteoparse.TafParseError):
            yield taf
        else:
            raise TypeError("Unexpected parser output")


if __name__ == "__main__":
    for station, raw_tafs in meteostore.get_tafs(meteostore.get_station_list()[:10], 2023, 2024):
        raw_tafs = meteoparse.parse_tafs(raw_tafs)
        expanded = meteoparse.regularize_tafs(raw_tafs)
        arranged = arrange_by_hour_forecast(expanded)
        for line in arranged:
            if isinstance(line, HourlyGroup):
                print(line)
    print("Done.")
