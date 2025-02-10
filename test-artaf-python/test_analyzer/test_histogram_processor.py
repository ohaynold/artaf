"""Test analyzer.HourlyHistogramProcessor"""
import os.path
import zipfile

import analyzer.analyzer
import meteostore
from test_artaf_util import make_temp_directory


class TestHourlyHistogramProcessor:  # pylint: disable=too-few-public-methods
    """Test analyzer.HourlyHistogramProcessor"""

    @staticmethod
    def _nada_callback(processed_hours, _):
        """Just a function to pass as a callback that does nothing to exercise the callback
        functionality"""
        assert processed_hours == int(processed_hours)

    def test_parallel(self):
        """Really more of an integration test for the parallel processing mechanism.
        Make sure that results are identical when processed in parallel and in one thread."""
        stations = [s for s in meteostore.get_station_list() if s.station == "KENW"]
        year = 2023
        read_records = 1000
        # If TAFs aren't here, download them as test data set
        meteostore.download_tafs(stations, year, year)
        with make_temp_directory() as temp_directory:
            # Process in a single thread
            flat_temp_directory = os.path.join(temp_directory, "flat")
            processor_flat = analyzer.analyzer.HourlyHistogramProcessor(
                analyzer.jobs.DEFAULT_JOBS, flat_temp_directory,
                parallel=False, progress_callback=self._nada_callback)
            processor_flat.show_progress_after = read_records
            processor_flat._abort_after = read_records + 1  # pylint: disable=protected-access
            processor_flat.process(stations, year, year)

            # Process parallel
            parallel_temp_directory = os.path.join(temp_directory, "parallel")
            processor_parallel = analyzer.analyzer.HourlyHistogramProcessor(
                analyzer.jobs.DEFAULT_JOBS, parallel_temp_directory,
                parallel=True, progress_callback=self._nada_callback)
            processor_parallel.show_progress_after = read_records
            processor_parallel._abort_after = read_records + 1  # pylint: disable=protected-access
            processor_parallel.process(stations, year, year)

            # Ensure that records are identical other than order of lines
            with (zipfile.ZipFile(os.path.join(flat_temp_directory, "hist YearlyStations.csv.zip"),
                                  "r") as flat_zip,
                  flat_zip.open("hist YearlyStations.csv") as flat_file):
                flat_lines = flat_file.read().decode("ascii").split("\n")
            with (zipfile.ZipFile(
                    os.path.join(parallel_temp_directory, "hist YearlyStations.csv.zip"),
                    "r") as parallel_zip,
                parallel_zip.open("hist YearlyStations.csv") as parallel_file):
                parallel_lines = parallel_file.read().decode("ascii").split("\n")
            assert flat_lines[0] == parallel_lines[0]
            assert len(flat_lines) == len(parallel_lines)
            assert list(sorted(flat_lines[1:])) == list(sorted(parallel_lines[1:]))
