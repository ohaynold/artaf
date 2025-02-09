"""Definitions for jobs given to hourly histogram processor.

Note that if you want to use parallel processing, you can't use lambda functions in the job
defintion. Hence the little helper functions."""

from collections import namedtuple

HourlyHistogramJob = namedtuple("HourlyHistogramJob",
                                ["name", "ascending_group_by", "other_group_by", "values"])


def get_aerodrome(hourly_group):
    "Extract aerodrome"
    return hourly_group.aerodrome


def get_year(hourly_group):
    "Extract year"
    return hourly_group.hour_starting.strftime("%Y")


def get_wind_speed(hourly_item):
    "Extract wind speed"
    return hourly_item.conditions.wind_speed


def get_lowest_cloud_altitude(hourly_item):
    "Extract altitude of lowest cloud layers, independent of coverage"
    lowest_layer = hourly_item.conditions.clouds[0]
    # the highest cloud altitude we care about
    max_altitude = 18_000
    if lowest_layer.is_sky_clear:
        return max_altitude
    return min(lowest_layer.cloud_base, max_altitude)


def get_ceiling(hourly_item):
    "Extract altitude of lowest cloud layer with more than 50% coverage"
    ceiling_layers = [c for c in hourly_item.conditions.clouds if float(c.coverage) >= 0.5]
    # the highest cloud altitude we care about
    max_altitude = 18_000
    if not ceiling_layers:
        return max_altitude
    return min(ceiling_layers[0].cloud_base, max_altitude)


DEFAULT_JOBS = [HourlyHistogramJob(name="YearlyStations",
                                   ascending_group_by={
                                       "aerodrome": get_aerodrome,
                                       "year": get_year
                                   },
                                   other_group_by={},
                                   values={
                                       "wind_speed": get_wind_speed,
                                       "lowest_cloud_altitude": get_lowest_cloud_altitude,
                                       "ceiling": get_ceiling,
                                   }
                                   )]
