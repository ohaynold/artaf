"""Here we provide the functionality to break TAFs down into a simple-to use sequence of
lines, each representing one forecast for one hour"""

import datetime
from collections import namedtuple

import meteostore
import meteoparse.tafparser

HourlyTafLine = namedtuple(
    "HourlyTafLine",
   ["aerodrome", "issued_at", "issued_in",  "amendment",
               "hour_starting", "wind_speed", "wind_gust"]
   )

ONE_HOUR = datetime.timedelta(seconds=3600)

def regularize_taf(taf):
    """
    Break a TAF down into a flat list of hourly prognoses
    :param taf: A meteoparse.ParsedForecast, or an error
    :return: A list of HourlyTafLine or an error passed through
    """
    if taf.from_lines is None:
        return []
    res = []
    for f in taf.from_lines:
        hour_starting = f.valid_from
        while hour_starting < f.valid_until:
            if hour_starting in [x.hour_starting for x in res]:
                return [meteoparse.tafparser.TafParseError(error="Overlapping hours",
                                                           message_text=taf,
                                                           hint=None)]
            res.append(HourlyTafLine(
                taf.aerodrome, taf.issued_at, taf.issued_in, taf.amendment,
                hour_starting, f.conditions.wind_speed, f.conditions.wind_gust
            ))
            hour_starting += ONE_HOUR
    return res

def regularize_tafs(tafs):
    """
    Parse a sequence of TAFs into regularized plain lines, each with one hourly forecast.
    Errors are passed through unchanged.
    :param tafs: A sequence of  meteoparse.ParsedForecast and/or errors
    """
    for taf in tafs:
        if isinstance(taf, meteoparse.tafparser.ParsedForecast):
            yield from regularize_taf(taf)
        else:
            # Pass on errors unmodified
            yield taf

if __name__ == "__main__":
    for station, raw_tafs in meteostore.get_tafs(meteostore.get_station_list()[:10], 2023, 2024):
        raw_tafs = meteoparse.tafparser.parse_tafs(raw_tafs)
        expanded = regularize_tafs(raw_tafs)
        for line in expanded:
            if isinstance(line, HourlyTafLine):
                print(line)
    print("Done.")
