"""Test meteostore.util"""

import meteostore

# There's really only one thing this function can do, so we test for a data point and for number
# of overall stations
class TestGetStationList: # pylint: disable=too-few-public-methods
    """Test meteostore.get_station_list()"""

    def test_get_station_list(self):
        """Test get_station_list()"""
        stations = meteostore.get_station_list()
        assert 650 < len(stations) < 750
        kenosha = [s for s in stations if s.station == "KENW"][0]
        assert kenosha.name == "KENOSHA"
