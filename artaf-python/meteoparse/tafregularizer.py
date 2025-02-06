"""Here we provide the functionality to break TAFs down into a simple-to use sequence of
lines, each representing one forecast for one hour"""

import datetime

import meteoparse.tafparser
import meteostore

ONE_HOUR = datetime.timedelta(seconds=3600)


def regularize_taf(taf):
    """
    Break a TAF down into a flat list of hourly prognoses
    :param taf: A meteoparse.ParsedForecast, or an error
    :return: A list of HourlyTafLine or an error passed through
    """
    if taf.from_lines is None:
        return taf
    res = taf._replace(from_lines=[])
    for f in taf.from_lines:
        hour_starting = f.valid_from
        if hour_starting != datetime.datetime(
                hour_starting.year, hour_starting.month, hour_starting.day, hour_starting.hour):
            hour_starting = datetime.datetime(
                hour_starting.year, hour_starting.month,
                hour_starting.day, hour_starting.hour) + ONE_HOUR
        while hour_starting < f.valid_until:
            if res.from_lines and hour_starting != res.from_lines[-1].valid_until:
                return meteoparse.tafparser.TafParseError(error="Non-contiguous hours",
                                                          message_text=str(taf),
                                                          hint=None)
            res.from_lines.append(f._replace(valid_from=hour_starting,
                                             valid_until=hour_starting + ONE_HOUR))
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
            yield regularize_taf(taf)
        else:
            # Pass on errors unmodified
            yield taf


if __name__ == "__main__":
    for station, raw_tafs in meteostore.get_tafs(meteostore.get_station_list()[:10], 2023, 2024):
        raw_tafs = meteoparse.tafparser.parse_tafs(raw_tafs)
        expanded = regularize_tafs(raw_tafs)
        for line in expanded:
            if isinstance(line, meteoparse.tafparser.ParsedForecast):
                print(line)
    print("Done.")
