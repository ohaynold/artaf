"""Test process_data. Not much to do since the runtime starting doesn't lend itself very
productively to unit testing and is better exercised simply by running it."""

import process_data


class TestProcessData: # pylint: disable=too-few-public-methods
    """Test process_data. Not much to do since the runtime starting doesn't lend itself very
    productively to unit testing and is better exercised simply by running it."""

    def test_get_config(self):
        """We expect there to be a configuration named full_set with at least ten years"""
        config = process_data.get_config("full_set")
        assert config["year_to"] - config["year_from"] > 10
