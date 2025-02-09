"""Test the TAF parser.

For testing the parser, it is simplest to go all the way from a TAF message to the
parsed output instead of building a framework to set up as method as it would during parsing."""

import datetime

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
