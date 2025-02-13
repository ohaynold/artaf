"""Test the TAF parser.

For testing the parser, it is simplest to go all the way from a TAF message to the
parsed output instead of building a framework to set up as method as it would during parsing."""

import datetime
import math

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
    Make an parse a simple one-liner TAF with the same conditions forecast for a day.
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
        # If the TAF somehow gets a wind heading of 360, the Wind object should
        # translate that to a direction of 0 degrees.
        parsed = parse_oneliner_taf("36005KT P6SM SKC")
        wind = parsed.from_lines[0].conditions.wind
        assert wind.direction == 0

    def test_winds_cartesian_cardinals(self):
        """Test that the cartesian coordinates for given TAFs are correct.

        The following headings are included in the test:

        0  90  180  270
        """
        # This is partly an exercise for myself to remember how the unit circle
        # works, but I do see a little bit of value in verifying that the
        # cartesian() method still spits out the right numbers; i.e. that math
        # is still math.
        #
        # See https://www.youtube.com/watch?v=3QtRK7Y2pPU for more details
        # re: the persistence of math.

        north_parsed = parse_oneliner_taf("00005KT P6SM SKC")
        (north_component, east_component) = north_parsed.from_lines[0].conditions.wind.cartesian()
        assert north_component == 5.0
        assert east_component == 0.0

        east_parsed = parse_oneliner_taf("09005KT P6SM SKC")
        (north_component, east_component) = east_parsed.from_lines[0].conditions.wind.cartesian()
        assert north_component == 0.0
        assert east_component == 5.0

        south_parsed = parse_oneliner_taf("18005KT P6SM SKC")
        (north_component, east_component) = south_parsed.from_lines[0].conditions.wind.cartesian()
        assert north_component == -5.0
        assert east_component == 0.0

        west_parsed = parse_oneliner_taf("27005KT P6SM SKC")
        (north_component, east_component) = west_parsed.from_lines[0].conditions.wind.cartesian()
        assert north_component == 0.0
        assert east_component == -5.0

    def test_winds_cartesian_half_cardinals(self):
        """Test that the cartesian coordinates for "half-cardinal" directions are correct.
        That is, NE, SE, SW, NW."""
        # For non-cardinal directions, some rounding is required.
        digits = 5
        # The windspeed variable is established to make the formula easier to understand
        windspeed = 5

        northeast_parsed = parse_oneliner_taf(f"045{windspeed:02d}KT P6SM SKC").from_lines[0]
        (ne_north_component, ne_east_component) = northeast_parsed.conditions.wind.cartesian()
        assert round(ne_north_component, digits) == round(windspeed * math.sqrt(2)/2, digits)
        assert round(ne_east_component, digits) == round(windspeed * math.sqrt(2)/2, digits)

        southeast_parsed = parse_oneliner_taf(f"135{windspeed:02d}KT P6SM SKC").from_lines[0]
        (se_north_component, se_east_component) = southeast_parsed.conditions.wind.cartesian()
        assert round(se_north_component, digits) == round(windspeed * -math.sqrt(2)/2, digits)
        assert round(se_east_component, digits) == round(windspeed * math.sqrt(2)/2, digits)

        southwest_parsed = parse_oneliner_taf(f"225{windspeed:02d}KT P6SM SKC").from_lines[0]
        (sw_north_component, sw_east_component) = southwest_parsed.conditions.wind.cartesian()
        assert round(sw_north_component, digits) == round(windspeed * -math.sqrt(2)/2, digits)
        assert round(sw_east_component, digits) == round(windspeed * -math.sqrt(2)/2, digits)

        northwest_parsed = parse_oneliner_taf(f"315{windspeed:02d}KT P6SM SKC").from_lines[0]
        (nw_north_component, nw_east_component) = northwest_parsed.conditions.wind.cartesian()
        assert round(nw_north_component, digits) == round(windspeed * math.sqrt(2)/2, digits)
        assert round(nw_east_component, digits) == round(windspeed * -math.sqrt(2)/2, digits)

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
