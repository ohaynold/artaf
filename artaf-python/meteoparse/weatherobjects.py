"""Objects for convenient representations of weather phenomena"""

import math


class CloudLayer:
    """
    Represents the cloud layer with altitude in feet, cloud coverage as a
    CloudCoverage object, and whether the cloud is cumulonimbus as a boolean.
    """

    def __init__(self, altitude, coverage, cb):
        self.cloud_base = altitude

        # This allows for a CloudLayer to be created with either a string or a
        # pre-made CloudCoverage object. I don't know if it's better to force it
        # one way or the other or to allow the flexibility.
        if isinstance(coverage, CloudCoverage):
            self.coverage = coverage
        else:
            self.coverage = CloudCoverage(coverage)

        self.is_cumulonimbus = cb

    def __str__(self):
        human_readable_altitude = f"{self.cloud_base} feet" if self.cloud_base != 0 else ""
        return (f"{self.coverage.in_english()} {human_readable_altitude}"
                f"{', cumulonimbus' if self.is_cumulonimbus else ''}")

    @property
    def is_sky_clear(self):
        """Is the sky clear?"""
        return self.coverage.coverage_string == "SKC"


class CloudCoverage:
    """Represents a cloud layer coverage as either a string or float."""

    def __init__(self, cloud_coverage):
        self.coverage_string = cloud_coverage

    def __str__(self):
        return self.coverage_string

    def __float__(self):
        # Definitions in AC 00-45H, section 5.11.2.9.1
        if self.coverage_string == "SKC":
            coverage_float = 0.0  # exactly no clouds -- the slightest whiff is FEW
        elif self.coverage_string == "FEW":
            coverage_float = 0.125  # 0 - 2 oktas
        elif self.coverage_string == "SCT":
            coverage_float = .375  # 3 - 4 oktas
        elif self.coverage_string == "BKN":
            coverage_float = .6875  # 5- 7 oktas
        elif self.coverage_string == "OVC":
            coverage_float = 0.9375  # 7-8 oktas
            # there is no encoding parallelling SKC for exactly 100%
        elif self.coverage_string == "VV":
            coverage_float = 1.0  # Sky not visible anywhere
        else:
            raise ValueError(f"Unexpected type of cloud coverage: '{self.coverage_string}'")

        return coverage_float

    def in_english(self):
        """Return a natural language string representation of the cloud coverage"""
        english_string = "Unknown"
        if self.coverage_string == "SKC":
            english_string = "Sky clear"
        if self.coverage_string == "FEW":
            english_string = "Few"
        if self.coverage_string == "SCT":
            english_string = "Scattered"
        if self.coverage_string == "BKN":
            english_string = "Broken"
        if self.coverage_string == "OVC":
            english_string = "Overcast"
        if self.coverage_string == "VV":
            english_string = "Vertical visibility"
        return english_string


class Visibility:  # pylint: disable=too-few-public-methods
    """A visibility in statute miles. is_excess indicates that the visibility is higher than
    the number given."""

    # This class definition makes it exclusively useful for TAFs published in USA and Canada. If you
    # want to analyze TAFs produced in other countries, they use meters instead of statute miles;
    # you'll need to write another method or rewrite this one.

    def __init__(self, visibility_miles, is_excess):
        self.visibility_miles = float(visibility_miles)
        self.is_excess = bool(is_excess)

    def __float__(self):
        return self.visibility_miles


class Wind:
    """Wind with the possibility of a given or variable direction and of gusts.
    Direction is in degrees and speeds are in knots"""

    def __init__(self, direction, speed, gust):
        self.direction = int(direction) if direction is not None else None
        # Question for Oliver: why do you translate a heading of 360 to 0? I suspect it's to
        # standardize otherwise inconsistent representations of wind from exactly north, but I think
        # an explicit explanation would be helpful.
        if self.direction == 360:
            self.direction = 0
        self.speed = int(speed)
        self.gust = int(gust) if gust is not None else None
        if self.direction:
            assert 0 <= self.direction < 360
        if self.gust is not None:
            assert self.gust > self.speed

    @property
    def is_variable_direction(self):
        """Test if the wind is coming from a variable direction"""
        return self.direction is None

    @property
    def speed_with_gust(self):
        """Give the wind speed including gusts, if any"""
        return self.gust if self.gust is not None else self.speed

    def cartesian(self, with_gust=False):
        """Gives the wind in Cartesian coordinates"""

        if self.direction is None:
            return (None, None)
        speed = self.speed_with_gust if with_gust else self.speed
        direction_radians = math.radians(self.direction)
        # Rounding is to compensate for floating point error at wind headings
        # of 90, 180, and 270 degrees. 360 is not a factor because it gets auto-
        # corrected to 0 when the object is created.
        #
        # Whether 10 decimal places is sufficient, I will leave to others to
        # decide. --Neal
        #
        # This method incorporates the windspeed in its calculations. If there's another application
        # that warrants producing Cartesian coordinates for the pure wind heading sans windspeed,
        # then writing another method would likely be appropriate.
        north = speed * round(math.cos(direction_radians), 10)
        east = speed * round(math.sin(direction_radians), 10)
        return north, east
