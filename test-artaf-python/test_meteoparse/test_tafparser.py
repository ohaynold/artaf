"""Test the TAF parser.

For testing the parser, it is simplest to go all the way from a TAF message to the
parsed output instead of building a framework to set up as method as it would during parsing."""

import datetime
import math
import pytest

import meteoparse.tafparser

# pragma pylint: disable=trailing-whitespace
SAMPLE_TAF_START = """000 
FTUS41 KTST 010020
TAFTST
TAF
KTST 010020Z 0100/0200 """
# pragma pylint: enable=trailing-whitespace

def parse_oneliner_taf(conditions_string):
    """
    Make and parse a simple one-liner TAF with the same conditions forecast for a day.
    Useful to test parsing of weather phenomena.
    :param conditions_string: Conditions for the one-liner, e.g., "09005KT P6SM SKC"
    :return: the parsed TAF
    """
    taf = SAMPLE_TAF_START + conditions_string + "="

    message_time = datetime.datetime(2024, 1, 1, 0, 20, 0)
    parsed = meteoparse.tafparser.parse_taf(message_time, taf)
    return parsed

class TestParseTafsWinds:
    """Test whether winds get parsed correctly."""

    def test_winds_valid_heading(self):
        """Test that only wind headings of 000 to 360 are accepted"""

        # Note that the range() ends before 360; i.e., the highest number tested is 359.
        # We will test a heading of 360 a bit farther down.
        for heading in range(0, 360):
            parsed = parse_oneliner_taf(f"{heading:03d}05KT P6SM SKC")
            wind = parsed.from_lines[0].conditions.wind
            assert wind.direction == heading

        # We will test a heading of 360 here, which should get auto-converted to a heading of 0.
        # Also note that this same functionality is validated in test_winds_from_north.
        parsed = parse_oneliner_taf("36005KT P6SM SKC")
        wind = parsed.from_lines[0].conditions.wind
        assert wind.direction == 0

        # All other headings should fail. We're blindly trusting that the regex will catch anything
        # in excess of three digits.
        for heading in range(361, 1000):
            parsed_incorrect = parse_oneliner_taf(f"{heading:03d}05KT P6SM SKC")
            assert isinstance(parsed_incorrect, meteoparse.tafparser.TafParseError)

    def test_winds_speed_heading(self):
        """Test that the speed and direction are correct in the Wind object."""
        parsed = parse_oneliner_taf("09005KT P6SM SKC")
        wind = parsed.from_lines[0].conditions.wind
        assert wind.speed == 5
        assert wind.direction == 90

    def test_winds_variable(self):
        """Test that Variable winds are captured correctly for a VRB wind."""
        parsed = parse_oneliner_taf("VRB05KT P6SM SKC")
        wind = parsed.from_lines[0].conditions.wind
        assert wind.speed == 5
        assert wind.is_variable_direction
        assert wind.direction is None

    def test_winds_gust(self):
        """Test that wind gusts are correctly stored in a Wind object."""
        parsed = parse_oneliner_taf("09005G10KT P6SM SKC")
        wind = parsed.from_lines[0].conditions.wind
        assert wind.speed == 5
        assert wind.speed_with_gust == 10
        assert wind.direction == 90

    def test_winds_from_north(self):
        """Test that the Wind object automatically corrects a wind heading
        of 360 to 0 degrees."""
        parsed = parse_oneliner_taf("36005KT P6SM SKC")
        wind = parsed.from_lines[0].conditions.wind
        assert wind.direction == 0

    def test_winds_cartesian(self):
        """Test that the Cartesian coordinates for given wind headings are correct."""

        # This is partly an exercise for myself to remember how the unit circle
        # works, but I do see a little bit of value in verifying that the
        # cartesian() method still spits out the right numbers; i.e. that math
        # is still math.
        #
        # See https://www.youtube.com/watch?v=3QtRK7Y2pPU for more details
        # re: the persistence of math.

        windspeed = 5

        winds_cartesian_components = (
            {"heading": 0,   "north": 1.0,              "east": 0.0},
            {"heading": 45,  "north": math.sqrt(2)/2,   "east": math.sqrt(2)/2},
            {"heading": 90,  "north": 0.0,              "east": 1.0},
            {"heading": 135, "north": -math.sqrt(2)/2,  "east": math.sqrt(2)/2},
            {"heading": 180, "north": -1.0,             "east": 0.0},
            {"heading": 225, "north": -math.sqrt(2)/2,  "east": -math.sqrt(2)/2},
            {"heading": 270, "north": 0.0,              "east": -1.0},
            {"heading": 315, "north": math.sqrt(2)/2,   "east": -math.sqrt(2)/2},
        )

        for wind in winds_cartesian_components:
            wind_parsed = parse_oneliner_taf(f"{wind['heading']:03d}{windspeed:02d}KT P6SM SKC")
            (north_coord, east_coord) = wind_parsed.from_lines[0].conditions.wind.cartesian()
            assert north_coord == pytest.approx(windspeed * wind['north'])
            assert east_coord == pytest.approx(windspeed * wind['east'])

class TestParseTafsVisibility:
    """Test whether visibility conditions get parsed correctly"""

    def test_visibility_exactly(self):
        """Test an exact visibility (that is, not an excess)"""
        parsed = parse_oneliner_taf("09005KT 6SM SKC")
        visibility = parsed.from_lines[0].conditions.visibility
        assert visibility.visibility_miles == 6.0
        assert visibility.is_excess is False

    def test_visibility_excess(self):
        """Test a visibility measured in excess of a specific distance"""
        parsed = parse_oneliner_taf("09005KT P6SM SKC")
        visibility = parsed.from_lines[0].conditions.visibility
        assert visibility.visibility_miles == 6.0
        assert visibility.is_excess is True


class TestParseTafsClouds:
    """Test whether clouds get parsed correctly"""

    def test_clouds_skc(self):
        """Test SKC clouds"""
        parsed = parse_oneliner_taf("09005KT P6SM SKC")
        assert len(parsed.from_lines[0].conditions.clouds) == 1
        layer = parsed.from_lines[0].conditions.clouds[0]
        assert layer.is_sky_clear
        assert layer.cloud_base is None
        assert str(layer.coverage) == "SKC"
        assert float(layer.coverage) == 0.0
        assert not layer.is_cumulonimbus

    def test_clouds_vv(self):
        """Test VV clouds"""
        parsed = parse_oneliner_taf("09005KT P6SM VV005")
        assert len(parsed.from_lines[0].conditions.clouds) == 1
        layer = parsed.from_lines[0].conditions.clouds[0]
        assert not layer.is_sky_clear
        assert layer.cloud_base == 500
        assert str(layer.coverage) == "VV"
        assert float(layer.coverage) == 1.0
        assert not layer.is_cumulonimbus

    def test_clouds_one_layer(self):
        """Test ordinary cloud layers, one at a time"""
        for message, base, coverage in [
            ("FEW010", 1000, 0.125),
            ("SCT015", 1500, 0.375),
            ("BKN050", 5000, 0.6875),
            ("OVC100", 10000, 0.9375),
        ]:
            parsed = parse_oneliner_taf("09005KT P6SM " + message)
            assert len(parsed.from_lines[0].conditions.clouds) == 1
            layer = parsed.from_lines[0].conditions.clouds[0]
            assert not layer.is_sky_clear
            assert layer.cloud_base == base
            assert str(layer.coverage) == message[:3]
            assert float(layer.coverage) == coverage
            assert not layer.is_cumulonimbus

    def test_clouds_cb(self):
        """Test cumulonimbus"""
        parsed = parse_oneliner_taf("09005KT P6SM BKN050CB")
        assert len(parsed.from_lines[0].conditions.clouds) == 1
        layer = parsed.from_lines[0].conditions.clouds[0]
        assert not layer.is_sky_clear
        assert layer.cloud_base == 5000
        assert str(layer.coverage) == "BKN"
        assert float(layer.coverage) == 0.6875
        assert layer.is_cumulonimbus

    def test_clouds_multilayer(self):
        """Test several cloud layers"""
        test_clouds = [
            ("FEW010", 1000, 0.125),
            ("SCT015", 1500, 0.375),
            ("BKN050", 5000, 0.6875),
            ("OVC100", 10000, 0.9375),
        ]
        message = "09005KT P6SM  " + (" ".join([m for m, _, _ in test_clouds]))
        parsed = parse_oneliner_taf(message)
        assert len(parsed.from_lines[0].conditions.clouds) == len(test_clouds)
        for layer, (cloud_string, base, coverage) in \
                zip(parsed.from_lines[0].conditions.clouds, test_clouds):
            assert not layer.is_sky_clear
            assert layer.cloud_base == base
            assert str(layer.coverage) == cloud_string[:3]
            assert float(layer.coverage) == coverage
            assert not layer.is_cumulonimbus

    def test_clouds_invalid_coverage(self):
        """A nonsense cloud coverage type should fail"""
        parsed = parse_oneliner_taf("09005KT P6SM INV005")
        assert isinstance(parsed, meteoparse.tafparser.TafParseError)

    def test_clouds_invalid_order(self):
        """Cloud layers in non-ascending order should fail"""
        # Make sure it works in the correct order
        parsed_correct = parse_oneliner_taf("09005KT P6SM BKN010 FEW020 OVC030")
        assert parsed_correct.from_lines[0].conditions.clouds[0].cloud_base == 1000
        # Make sure it gives an error in the incorrect order
        parsed_incorrect = parse_oneliner_taf("09005KT P6SM BKN010 OVC030 FEW020")
        assert isinstance(parsed_incorrect, meteoparse.tafparser.TafParseError)

    def test_clouds_plain_english(self):
        """Test that the cloud layers are correctly translated to plain English"""
        test_clouds = [
            ("FEW010CB", "Few 1000 feet, cumulonimbus"),
            ("SCT020", "Scattered 2000 feet"),
            ("BKN030", "Broken 3000 feet"),
            ("OVC040", "Overcast 4000 feet")
        ]
        parsed = parse_oneliner_taf(f"09005KT P6SM {' '.join([cloud[0] for cloud in test_clouds])}")
        english_strings = [cloud[1] for cloud in test_clouds]

        for (layer, plain_english) in \
            zip(parsed.from_lines[0].conditions.clouds, english_strings):
            assert str(layer) == plain_english
