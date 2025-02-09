"""This provide summary statistics of the TAFs, i.e., the core of our analysis once we've got
all the data"""
import concurrent.futures
import contextlib
import csv
import datetime
import multiprocessing
import os.path
import time
import zipfile
from collections import namedtuple

import analyzer.jobs
import artaf_util
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
    :param aerodrome: The aerodrome, as a four-letter identifier, for which the tafs are supposed to
    be
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


class HourlyHistogramKeeper:  # pylint: disable=too-many-instance-attributes
    """A keeper of histograms of hourly data. Its function its defined by its HourlyHistogramJob.
    Within the job we have the parameters:
    name: A name for the job
    ascending_group_by: a dictionary from field names to functions transforming an HourlyGroup
    into some key, with a guarantee that this will only appear in ascending order, e.g., dates
    order_group_by: a dictionary from names to functions transforming an HourlyGroup into some kind
    of keys.
    values: A dictionary from names to functions transforming a HourlyItem into some value
    """

    def __init__(self, job, callback, callback_info):
        self.job = job
        self.name = self.job.name
        self.ascending_group_by = list(self.job.ascending_group_by.items())
        self.other_group_by = list(self.job.other_group_by.items())
        self.values = list(self.job.values.items())
        self.callback = callback
        self.callback_info = callback_info

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
            self.flush()
            self.current_ascending_group = ascending_group

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

    def flush(self):
        """Write out accumulated statistics."""
        if len(self.counts) > 0:
            self.counts = dict(sorted(list(self.counts.items()), key=lambda x: str(x[0])))
            self.callback(self.current_ascending_group, self.counts, self.callback_info)
        self.counts = {}


class ParallelContext:
    """This is a placeholder class for HourlyHistogramProcessor that can get pickled and passed
    to different processes in parallel processing."""

    def __init__(self, jobs, output_queue):
        self.output_queue = output_queue
        self.jobs = jobs

    def receive_output(self, ascending_group, counts, job_index):
        """Remote access to HourlyHistogramProcessor.receive_output"""
        self.output_queue.put(("receive_output", (ascending_group, counts, job_index)))

    def progress(self, station_processed_hours, station_processed_errors):
        """Remote access to HourlyHistogramProcessor.progress"""
        self.output_queue.put(("progress", (station_processed_hours,
                                            station_processed_errors)))

    def write_error(self, message_text, error, hint):
        """Remote access to HourlyHistogramProcessor.write_error"""
        self.output_queue.put(("write_error", (message_text, error, hint)))


class HourlyHistogramProcessor:  # pylint: disable=too-many-instance-attributes
    """Automates the parsing and processing of TAFs"""

    def __init__(self, jobs, output_dir, progress_callback=None, parallel=False):
        """
        Make a new processor
        :param jobs: A list of HourlyHistogramJob objects
        :param output_dir: the directory in which to write output
        :param progress_callback: a function(hours_parsed, errors_encountered) to display progress
        :param parallel: Process in parallel
        """
        self.jobs = jobs
        self.output_dir = output_dir
        self.out_files = None
        self.error_file = None
        self.out_writers = None
        self.error_writer = None
        self.processed_hours = 0
        self.processed_errors = 0
        self.progress_callback = progress_callback
        self.output_queue = None
        self.parallel = parallel

    def process(self, stations, year_from, year_to):
        """
        Process TAFs
        :param stations: A list of stations to process
        :param year_from: Process from year
        :param year_to: Process to year
        """
        os.makedirs(self.output_dir, exist_ok=True)
        with contextlib.ExitStack() as exit_stack:
            self._initialize_output_files(exit_stack)

            self.processed_hours = 0
            self.processed_errors = 0

            # map() is a generator -- list forces evaluation
            evaluations = [(s, year_from, year_to) for s in stations]
            if self.parallel:
                with (concurrent.futures.ProcessPoolExecutor() as executor,
                      multiprocessing.Manager() as manager):
                    self.output_queue = manager.Queue()
                    context = ParallelContext(self.jobs, self.output_queue)
                    futures = [executor.submit(self._process_station, e, context) for e in
                               evaluations]
                    while True:
                        if all(f.done() for f in futures) and self.output_queue.empty():
                            break
                        if not self.output_queue.empty():
                            method, payload = self.output_queue.get()
                            getattr(self, method)(*payload)
                        else:
                            time.sleep(0.1)
                    list((f.result() for f in futures))
            else:
                context = self
                for e in evaluations:
                    self._process_station(e, context)

    def _initialize_output_files(self, exit_stack):
        self.out_files = [
            exit_stack.enter_context(
                artaf_util.open_compressed_text_zip_write(
                    os.path.join(self.output_dir, f"hist {job.name}.csv.zip"),
                    f"hist {job.name}.csv", "ascii", zipfile.ZIP_DEFLATED))
            for job in self.jobs]
        self.error_file = exit_stack.enter_context(
            artaf_util.open_compressed_text_zip_write(
                os.path.join(self.output_dir, "errors.csv.zip"),
                "errors.csv", "ascii", zipfile.ZIP_DEFLATED))
        self.out_writers = [csv.writer(f) for f in self.out_files]
        header_keepers = [HourlyHistogramKeeper(j, None, None) for j in self.jobs]
        for i in range(len(self.jobs)):
            ascending_group_headers, other_group_headers = header_keepers[i].get_field_names()
            self.out_writers[i].writerow(
                ascending_group_headers + other_group_headers +
                ["variable", "previous", "current", "final", "count"])
        self.error_writer = csv.writer(self.error_file)
        self.error_writer.writerow(["taf", "error", "info"])

    def receive_output(self, ascending_group, counts, job_index):
        """
        Receive output to be written into output files
        """
        for (other_group, field_name, prev, curr, final), ncount in counts.items():
            new_row = list(ascending_group) + list(other_group) + \
                      [field_name, prev, curr, final, ncount]
            self.out_writers[job_index].writerow(new_row)

    def progress(self, station_processed_hours, station_processed_errors):
        """Receive a progress message to be displayed"""
        self.processed_hours += station_processed_hours
        self.processed_errors += station_processed_errors
        if self.progress_callback is not None:
            self.progress_callback(self.processed_hours, self.processed_errors)

    def write_error(self, message_text, error, hint):
        """Receive a parse error to be logged"""
        self.error_writer.writerow([message_text, error, hint])

    @staticmethod
    def _process_station(params, context):
        station, year_from, year_to = params
        tafs = meteostore.get_tafs([station], year_from, year_to, read_only=True)
        station, station_tafs = next(tafs)
        parsed_tafs = meteoparse.parse_tafs(station_tafs)
        expanded_tafs = meteoparse.regularize_tafs(parsed_tafs)
        arranged_forecasts = arrange_by_hour_forecast(expanded_tafs, station.station)
        station_processed_hours = 0
        station_processed_errors = 0
        keepers = [HourlyHistogramKeeper(
            context.jobs[i], context.receive_output, i) for i in range(len(context.jobs))]
        for hourly_data in arranged_forecasts:
            if isinstance(hourly_data, HourlyGroup):
                for k in keepers:
                    k.process_hourly_group(hourly_data)
                station_processed_hours += 1
                if station_processed_hours % 10000 == 0:
                    context.progress(station_processed_hours, station_processed_errors)
                    station_processed_errors = 0
                    station_processed_hours = 0
            elif isinstance(hourly_data, meteoparse.TafParseError):
                context.write_error(str(hourly_data.message_text), str(hourly_data.error),
                                    str(hourly_data.hint))
                station_processed_errors += 1
            else:
                raise TypeError("Unexpected message type encountered.")
        for k in keepers:
            k.flush()
        context.progress(station_processed_hours, station_processed_errors)


if __name__ == "__main__":
    my_jobs = analyzer.jobs.DEFAULT_JOBS


    def progress(hours, errors):
        """Display progress"""
        print(f"\rProcessed {hours:,} station hours, encountered {errors:,} errors...",
              end="", flush=True)


    processor = HourlyHistogramProcessor(my_jobs, os.path.join("output", "tmp"),
                                         progress_callback=progress)
    processor.process(meteostore.get_station_list()[:3], 2023, 2024)
    print(f"\rProcessed {processor.processed_hours:,} station hours, encountered "
          f"{processor.processed_errors:,} errors...")
    print("Done.")
