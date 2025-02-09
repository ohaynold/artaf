"""Test meteoparse.regularize_tafs"""
import datetime

import meteoparse

TEST_TAFS_NORMAL = [
    (datetime.datetime(2024, 1, 1, 0, 20, 0),
     """000 
     FTUS41 KTST 010020
     TAFTST
     TAF
     KTST 010020Z 0100/0106 03005KT P6SM SKC
         FM010300 03010KT P6SM OVC010="""
     ),
    (datetime.datetime(2024, 1, 1, 6, 20, 0),
     """000 
     FTUS41 KTST 010020
     TAFTST
     TAF
     KTST 010020Z 0106/0112 03015KT P6SM SKC
         FM010900 03020KT P6SM OVC010="""
     ),
]

TEST_TAFS_ERROR = [
    (datetime.datetime(2024, 1, 1, 0, 20, 0),
     """000 
     FTUS41 KTST 010020
     TAFTST
     TAF
     KTST 010020Z 0100/0106 03005KT P6SM SKC
         FM010300 03010KT P6SM OVC010="""
     ),
    (datetime.datetime(2024, 1, 1, 6, 20, 0),
     """000 
     FTUS41 KTST 010020
     TAFTST
     TAF
     KTST 010020Z 0106/0112 03015KT P6SM SKY_DARK
         FM010900 03020KT P6SM OVC010="""
     ),
]

TEST_TAFS_ODD_START = [
    (datetime.datetime(2024, 1, 1, 0, 20, 0),
     """000 
     FTUS41 KTST 010020
     TAFTST
     TAF
     KTST 010020Z 0100/0106 03005KT P6SM SKC
         FM010320 03010KT P6SM OVC010="""
     ),
    (datetime.datetime(2024, 1, 1, 6, 20, 0),
     """000 
     FTUS41 KTST 010020
     TAFTST
     TAF
     KTST 010020Z 0106/0112 03015KT P6SM SKC
         FM010900 03020KT P6SM OVC010="""
     ),
]

TEST_TAFS_NIL = [
    (datetime.datetime(2024, 1, 1, 0, 20, 0),
     """000 
     FTUS41 KTST 010020
     TAFTST
     TAF
     KTST 010020Z 0100/0106 03005KT P6SM SKC
         FM010320 03010KT P6SM OVC010="""
     ),
    (datetime.datetime(2024, 1, 1, 6, 20, 0),
     """000 
     FTUS41 KTST 010020
     TAFTST
     TAF
     KTST 010020Z 0106/0112 NIL="""
     ),
]


class TestRegularizeTafs:
    """Test whether regularize_tafs properly arranges TAFs in hourly intervals"""

    def test_regularize_tafs(self):
        """Test a boring case of properly aligned from lines"""
        parsed_tafs = meteoparse.parse_tafs(TEST_TAFS_NORMAL)
        regularized = list(meteoparse.regularize_tafs(parsed_tafs))
        assert len(regularized) == 2
        assert len(regularized[0].from_lines) == 6
        for i in range(6):
            assert regularized[0].from_lines[i].valid_from.hour == i
            # See that wind is as we set it in the TAF
            assert regularized[0].from_lines[i].conditions.wind.speed == (5 if i < 3 else 10)

    def test_regularize_tafs_pass_error(self):
        """Test passing on an error from an improper TAF"""
        parsed_tafs = meteoparse.parse_tafs(TEST_TAFS_ERROR)
        regularized = list(meteoparse.regularize_tafs(parsed_tafs))
        assert len(regularized) == 2
        assert isinstance(regularized[1], meteoparse.TafParseError)

    def test_regularize_tafs_odd_hour(self):
        """Test a TAF with the validity not starting on a full hour"""
        parsed_tafs = meteoparse.parse_tafs(TEST_TAFS_ODD_START)
        regularized = list(meteoparse.regularize_tafs(parsed_tafs))
        assert len(regularized) == 2
        assert len(regularized[0].from_lines) == 6
        for i in range(5):
            assert regularized[0].from_lines[i].valid_from.hour == i
            # See that wind is as we set it in the TAF -- 3 is now still at 5 knots
            assert regularized[0].from_lines[i].conditions.wind.speed == (5 if i <= 3 else 10)

    def test_regularize_tafs_nil(self):
        """Test a TAF with no content"""
        parsed_tafs = meteoparse.parse_tafs(TEST_TAFS_NIL)
        regularized = list(meteoparse.regularize_tafs(parsed_tafs))
        assert regularized[1].from_lines is None
