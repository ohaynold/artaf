"""This provide summary statistics of the TAFs, i.e., the core of our analysis once we've got
all the data"""

import datetime
from collections import namedtuple

import meteoparse.tafparser
import meteostore

ONE_HOUR = datetime.timedelta(seconds=3600)

HourlyGroup = namedtuple("HourlyGroup", ["aerodrome", "hour_starting", "items"])
HourlyItem = namedtuple("HourlyItem", ["issued_at", "amendment", "conditions"])


def arrange_by_hour_forecast(tafs, aerodrome):
    """
    Rearrange a stream of TAFs, in ascending order and for the same station, so as to have all the
    forecasts for a given hour together, in the order they were issues.
    :param tafs: A sequence of TAFs and/or errors
    :param tafs: The aerodrome, as a four-letter identifier, for which the tafs are supposed to be
    """
    hourly_cache = {}
    for taf in tafs:
        if isinstance(taf, meteoparse.tafparser.ParsedForecast):
            if taf.aerodrome != aerodrome:
                yield meteoparse.TafParseError(
                    "Misfiled TAF",
                    f"Expected '{aerodrome}', got '{taf.aerodrome}'.",
                    None)
            # Cache this TAF
            if not taf.from_lines:
                continue
            for from_line in taf.from_lines:
                if from_line.valid_from not in hourly_cache:
                    hourly_cache[from_line.valid_from] = []
                hourly_cache[from_line.valid_from].append(HourlyItem(taf.issued_at,
                                                                     taf.amendment,
                                                                     from_line.conditions))

            while True:
                if len(hourly_cache) == 0:
                    break
                first_hour_available = min(hourly_cache.keys())
                if not (len(hourly_cache) > 0 and first_hour_available < taf.issued_at - ONE_HOUR):
                    break
                yield HourlyGroup(aerodrome, first_hour_available, hourly_cache[
                    first_hour_available])
                del hourly_cache[first_hour_available]
        elif isinstance(taf, meteoparse.TafParseError):
            yield taf
        else:
            raise TypeError("Unexpected parser output")


HourlyHistogramJob = namedtuple("HourlyHistogramJob",
                                ["name", "ascending_group_by", "other_group_by", "values"])


class HourlyHistogramKeeper: # pylint: disable=too-many-instance-attributes
    """A keeper of histograms of hourly data. Its function its defined by its HourlyHistogramJob.
    Within the job we have the parameters:
    name: A name for the job
    ascending_group_by: a dictionary from field names to functions transforming an HourlyGroup
    into some key, with a guarantee that this will only appear in ascending order, e.g., dates
    order_group_by: a dictionary from names to functions transforming an HourlyGroup into some kind
    of keys.
    values: A dictionary from names to functions transforming a HourlyItem into some value
    """

    def __init__(self, job, callback):
        self.job = job
        self.name = self.job.name
        self.ascending_group_by = list(self.job.ascending_group_by.items())
        self.other_group_by = list(self.job.other_group_by.items())
        self.values = list(self.job.values.items())
        self.callback = callback

        self.current_ascending_group = None
        self.counts = {}

    def get_field_names(self):
        """
        Get the field names defined by the job
        :return: Field names for ascending and for other group bys.
        """
        ascending_field_names = [name for name, _ in self.ascending_group_by]
        other_field_names = [name for name, _ in self.other_group_by]
        return ascending_field_names, other_field_names

    def process_hourly_group(self, hourly_group):
        """
        Process an hourly group into the histogram.
        :param hourly_group: HourlyGroup, must be for one station and in ascending order of issue
        time
        """
        if len(hourly_group.items) < 3:
            return

        ascending_group = tuple((fun(hourly_group) for _, fun in self.ascending_group_by))
        other_groups = [tuple((fun(hourly_group) for _, fun in self.other_group_by)) for x in
                        hourly_group.items]

        if ascending_group != self.current_ascending_group:
            if len(self.counts) > 0:
                self.counts = dict(sorted(list(self.counts.items()), key=lambda x: x[0]))
                self.callback(ascending_group, self.counts)
            self.current_ascending_group = ascending_group
            self.counts = {}

        for value_name, value_fun in self.values:
            previous_value = value_fun(hourly_group.items[0])
            final_value = value_fun(hourly_group.items[-1])
            for item_index in range(1, len(hourly_group.items) - 1):
                current_value = value_fun(hourly_group.items[item_index])
                counts_key = other_groups[
                    item_index], value_name, previous_value, current_value, final_value
                if counts_key in self.counts:
                    self.counts[counts_key] += 1
                else:
                    self.counts[counts_key] = 1

                previous_value = current_value


if __name__ == "__main__":
    keeper = HourlyHistogramKeeper(
        HourlyHistogramJob(name="MonthlyStations",
                           ascending_group_by={
                               "aerodrome": lambda x: x.aerodrome,
                               "year_month": lambda x: x.hour_starting.strftime("%Y-%m")
                           },
                           other_group_by={},
                           values={
                               "wind_speed": lambda x: x.conditions.wind_speed
                           }
                           ),
        print)

    for station, raw_tafs in meteostore.get_tafs(meteostore.get_station_list()[:10], 2023, 2024):
        raw_tafs = meteoparse.parse_tafs(raw_tafs)
        expanded = meteoparse.regularize_tafs(raw_tafs)
        arranged = arrange_by_hour_forecast(expanded, station.station)
        i = 0
        for line in arranged:
            if isinstance(line, HourlyGroup):
                keeper.process_hourly_group(line)
                i += 1
                if i % 10_000 == 0:
                    print(f"\rProcessed {i} lines...", end="", flush=True)
    print("Done.")
