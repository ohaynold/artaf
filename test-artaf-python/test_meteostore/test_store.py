"""Test meteostore.store"""

import datetime

import pytest
import pytz

import meteostore


class TestStore():
    """Test such functionality in meteostore.store as is practicable for unit testing. We're not
    making Web requests to Iowa State just for this purpose, and we're not setting up mock
    requests answers either as the main risk really is something in the remote service changing."""

    def test_cleanup_datetime_date(self):
        """A date should turn into midnight"""
        res = meteostore.store.cleanup_datetime(datetime.date(2024, 1, 1))
        assert res == datetime.datetime(2024, 1, 1, 0, 0)

    def test_cleanup_datetime_datetime(self):
        """A datetime should turn into midnight"""
        res = meteostore.store.cleanup_datetime(datetime.datetime(2024, 1, 1, 2, 15))
        assert res == datetime.datetime(2024, 1, 1, 2, 15)

    def test_cleanup_datetime_timezone(self):
        """A datetime with a time zone should be rejected"""
        with pytest.raises(ValueError):
            meteostore.store.cleanup_datetime(datetime.datetime(2024, 1, 1, 2, 15,
                                                                tzinfo=pytz.UTC))

    def test_cleanup_datetime_wrong_type(self):
        """An object that's not a date should be rejected"""
        with pytest.raises(AttributeError):
            meteostore.store.cleanup_datetime("today")

    def test_get_tafs_year_check(self):
        """Check that we're refusing to download for the present year"""
        current_year = datetime.datetime.now().year
        stations = [s for s in meteostore.get_station_list() if s.station == "KORD"]
        with pytest.raises(IndexError):
            # List to force the generator to yield, which raises
            list(meteostore.get_tafs(stations, 2024, current_year))


    def test_get_tafs(self):
        """Test TAF retrieval. We should have something for O'Hare"""
        stations = [s for s in meteostore.get_station_list() if s.station == "KORD"]
        res = meteostore.get_tafs(stations, 2024, 2024)
        count = 0
        for _, tafs in res:
            for _ in tafs:
                count += 1
        assert 3300 < count < 3400
