
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
                f"{', cumulonimbus' if self.is_cumulonimbus() else ''}")

    @property
    def is_sky_clear(self):
        "Is the sky clear?"
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

