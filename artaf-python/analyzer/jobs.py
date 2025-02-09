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
    return hourly_item.conditions.wind.speed


def get_wind_speed_with_gust(hourly_item):
    "Extract wind speed including gust, if any"
    return hourly_item.conditions.wind.speed_with_gust


def get_wind_gust_spread(hourly_item):
    "Extract the difference between gust and constant wind"
    return hourly_item.conditions.wind.speed_with_gust - hourly_item.conditions.wind.speed


def get_wind_north(hourly_item):
    "Extract the northerly wind component, rounded to an integer"
    north, _ = hourly_item.conditions.wind.cartesian()
    if north is None:
        return ""
    return int(round(north, 0))


def get_wind_east(hourly_item):
    "Extract the northerly wind component, rounded to an integer"
    _, east = hourly_item.conditions.wind.cartesian()
    if east is None:
        return ""
    return int(round(east, 0))


def get_clouds_lowest_base(hourly_item):
    "Extract altitude of lowest cloud layers, independent of coverage"
    lowest_layer = hourly_item.conditions.clouds[0]
    # the highest cloud altitude we care about
    max_altitude = 18_000
    if lowest_layer.is_sky_clear:
        return max_altitude
    return min(lowest_layer.cloud_base, max_altitude)


def get_visibility(hourly_item):
    """Extract visibility in statute miles"""
    return float(hourly_item.conditions.visibility)


def get_clouds_ceiling(hourly_item):
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
                                       "wind_speed_with_gust": get_wind_speed_with_gust,
                                       "wind_gust_spread": get_wind_gust_spread,
                                       "wind_north": get_wind_north,
                                       "wind_east": get_wind_east,
                                       "clouds_lowest_base": get_clouds_lowest_base,
                                       "clouds_ceiling": get_clouds_ceiling,
                                       "visibility": get_visibility
                                   }
                                   )]
