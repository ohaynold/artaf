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
    return hourly_item.conditions.clouds[0].coverage_altitude

DEFAULT_JOBS = [HourlyHistogramJob(name="YearlyStations",
                                   ascending_group_by={
                                       "aerodrome": get_aerodrome,
                                       "year": get_year
                                   },
                                   other_group_by={},
                                   values={
                                       "wind_speed": get_wind_speed,
                                       "lowest_cloud_altitude": get_lowest_cloud_altitude
                                   }
                                   )]
