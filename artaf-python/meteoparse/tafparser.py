"""This is the parser for TAFs. Function parse_taf() does all the work. We're using Lark as our
parser generator, in the LALR mode for speed. In addition to the grammar in lark/taf.lark, class
TafTreeTransformer does the remaining heave lifting of building Pythonic output objects."""

import collections
import csv
import datetime
import os
import os.path
from enum import Enum

import lark

import meteostore
from meteoparse.tree_accessor import TreeAccessor


class AmendmentType(Enum):
    """Type of a TAF amendment"""
    CORRECTED = 1
    AMENDED = 2


ParsedForecast = collections.namedtuple(
    "ParsedForecast",
    ["aerodrome", "issued_at", "issued_in", "valid_from", "valid_until", "amendment",
     "from_lines"])

WeatherConditions = collections.namedtuple(
    "WeatherConditions",
    ["wind_speed", "wind_gust", "clouds"])

FromLine = collections.namedtuple(
    "FromLine",
    ["valid_from", "valid_until", "conditions"]
)

TafParseError = collections.namedtuple(
    "TafParseError",
    ["error", "message_text", "hint"]
)


# The case of the methods is given by the conventions expected by Lark
# noinspection PyMethodMayBeStatic,PyPep8Naming
# pragma pylint: disable=invalid-name
class TafTreeTransformer(lark.Transformer):
    """
    This is the Lark transformer called on Lark's parse results. For an explanation of how it works,
    see https://lark-parser.readthedocs.io/en/latest/visitors.html

    The method names correspond to the rules and terminals in taf.lark. See for more references
    there.
    """

    # noinspection PyTypeChecker
    def __init__(self, issue_date):
        super().__init__(self)
        self.issue_date = issue_date

    def make_datetime_from_day_hour_minute(self, day, hour, minute):
        """Turns a DDHHMM time specification as found in TAFs into a proper datetime"""
        if day >= self.issue_date.day:
            return datetime.datetime(self.issue_date.year, self.issue_date.month, day, hour, minute)
        if self.issue_date.month < 12:
            return datetime.datetime(self.issue_date.year, self.issue_date.month + 1,
                                     day, hour, minute)
        return datetime.datetime(self.issue_date.year + 1, 1, day, hour, minute)

    def start(self, branches):
        """Transform the topmost node of the AST, i.e., the entire TAF"""
        tree = TreeAccessor(branches)

        # Extract header information we need for parsing -- we'll extract the others
        # when we construct the output tuple below
        header = tree.header
        valid_from = header.header_valid_from.DAY_HOUR.value
        valid_until = header.header_valid_until.DAY_HOUR.value

        # Copy the from lines with the actual forecasts and for simplicity give each one a start
        # and an end datetime so that they don't have to be inferred later on.
        if hasattr(tree, "taf_content"):
            taf_content = tree.taf_content
            from_line_times = [valid_from]
            from_lines = [taf_content[0]]
            if len(taf_content) > 1:
                for line in taf_content[1:]:
                    from_line_times.append(line[0].value)
                    from_lines.append(line[1])
            from_line_times.append(valid_until)
            new_from_lines = [
                FromLine(conditions=from_lines[i], valid_from=from_line_times[i],
                         valid_until=from_line_times[i + 1])
                for i in range(len(from_lines))]
        else:
            # We got a NIL TAF
            new_from_lines = None

        res = ParsedForecast(
            aerodrome=header.header_issued_for.AERODROME.value,
            issued_at=header.header_issued_at.DAY_HOUR_MINUTE.value,
            issued_in=tree.preamble.preamble_issued_in.AERODROME.value,
            valid_from=valid_from,
            valid_until=valid_until,
            amendment=header.HEADER_AMENDMENT.value
            if hasattr(header, "HEADER_AMENDMENT") else
            None,
            from_lines=new_from_lines)

        return res

    def from_group_content(self, branches):
        """
        Parse from groups. This is where most of the interesting weather information is and likely
        the right place to come if you want to extend functionality.
        :param branches: A list of lark.Tree or lark.Token objects
        :return: WeatherCondition tuple
        """
        from_conditions = TreeAccessor(branches).from_conditions
        wind_group = from_conditions.wind_group
        wind_speed = wind_group.WIND_SPEED.value
        wind_gust = wind_group.wind_gust_group.WIND_SPEED.value \
            if hasattr(wind_group, "wind_gust_group") \
            else None

        cloud_layers_group = from_conditions['clouds'][0].children

        # See the clouds work beautifully by uncommenting these lines
        # for cloud_layer in cloud_layers_group:
        #    print(cloud_layer)

        return WeatherConditions(wind_speed=wind_speed, wind_gust=wind_gust,
                                 clouds=cloud_layers_group)
        # TODO: Unroll TEMPO and PROB changes
        # TODO: Add other elements of group

    def WIND_SPEED(self, token):
        """Wind speed as an integer in knots"""
        return token.update(value=int(token.value))

    def DAY_HOUR_MINUTE(self, token):
        """Date and time from DDHHMM specification, always in UTC"""
        s = token.value
        day = int(s[0:2])
        hour = int(s[2:4])
        minute = int(s[4:6])
        return token.update(value=self.make_datetime_from_day_hour_minute(day, hour, minute))

    def DAY_HOUR(self, token):
        """Date and time from DDHH specification, always in UTC"""
        s = token.value
        day = int(s[0:2])
        hour = int(s[2:4])

        # Sometimes midnight in this format gets encoded as 24:00 of the preceding day
        if hour == 24:
            increment_day = True
            hour = 0
        else:
            increment_day = False

        res = self.make_datetime_from_day_hour_minute(day, hour, 0)

        if increment_day:
            res += datetime.timedelta(days=1)
        return token.update(value=res)

    def HEADER_AMENDMENT(self, token):
        """Header amendment AMD or COR"""
        if token == "COR":
            return token.update(value=AmendmentType.CORRECTED)
        if token == "AMD":
            return token.update(value=AmendmentType.AMENDED)
        return IndexError("Unknown amendment type.")

    # We don't need to parse the clear sky token as it can only carry one value
    def CLOUDS_SKY_CLEAR(self, token):  # pylint: disable=unused-argument
        """Cloud layer with sky clear"""
        return CloudLayer(None, CloudCoverage("SKC"), False)

    def clouds_vertical_visibility(self, token):
        """Parses as VV group as a CloudLayer"""
        return CloudLayer(
            int(token[0].value) * 100,
            CloudCoverage("VV"),
            False
        )

    def cloud_layer(self, branches):
        """Produces a list of CloudLayer objects for the TAF"""
        cloud_layer = TreeAccessor(branches)

        cb = hasattr(cloud_layer, "CLOUD_LAYER_CUMULONIMBUS")

        cloud_layer_obj = CloudLayer(
            int(cloud_layer.CLOUDS_ALTITUDE.value) * 100,
            cloud_layer.CLOUD_LAYER_COVERAGE.value,
            cb
        )

        return cloud_layer_obj


# Was disabled above to allow for Lark transformer method names
# pragma pylint: enable=invalid-name


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


LARK_DIR = os.path.join("artaf-python", "meteoparse", "lark")


# noinspection PyShadowingNames
def parse_taf(message_time, message):
    """
    Parse a TAF
    :param message_time: Datetime of the TAF in UTC. Knowledge of the current date is presumed in
    TAFs' abbreviated notation.
    :param message: Raw test of the TAF
    :return: ParsedForecast with the TAF's content, or TafParseError with what went wong
    """
    # The parser is expensive to generate, so we memoize it
    if parse_taf.parser is None:
        with open(os.path.join(LARK_DIR, "taf.lark"), "r", encoding="ascii") as lark_grammar:
            parse_taf.parser = lark.Lark(lark_grammar, parser="lalr")

    try:
        tree = parse_taf.parser.parse(message)
        # We cannot use the faster option of passing the transformer as an argument to lark.Lark
        # above since it needs to be instantiated with message_time
        transformer = TafTreeTransformer(message_time)
        tree = transformer.transform(tree)
        return tree
    except (lark.exceptions.UnexpectedInput, lark.exceptions.VisitError) as e:
        hint = e.get_context(message) \
            if isinstance(e, lark.exceptions.UnexpectedInput) \
            else None
        return TafParseError(e, message, hint)


parse_taf.parser = None


def parse_tafs(taf_sequence):
    """
    Parse a sequence of raw TAFs and make a sequence of ParsedForecast tuples out of them
    :param taf_sequence: a sequence of datetime.datetime, str tuples with the time and content of
    the raw TAF
    :return: a sequence of ParsedForecast tuples and/or TafParseError for TAFs that failed to parse
    """
    for taf_date, taf_text in taf_sequence:
        res = parse_taf(taf_date, taf_text)
        # taf_date is no longer needed because now the TAF itself is augmented with full dates
        yield res


if __name__ == "__main__":
    # Why does pylint think this is a constant?
    tafs_parsed = 0  # pylint: disable=invalid-name
    tafs_error = 0  # pylint: disable=invalid-name
    LOG_DIR = os.path.join("data", "logs")
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "parse_errors.csv"), "w", encoding="ascii") as error_log_file:
        error_log = csv.writer(error_log_file)
        error_log.writerow(["TAF", "Exception", "Hint"])
        for station, raw_tafs in meteostore.get_tafs(meteostore.get_station_list(), 2010, 2024):
            for taf in parse_tafs(raw_tafs):
                if isinstance(taf, ParsedForecast):
                    pass
                elif isinstance(taf, TafParseError):
                    error_log.writerow([taf.message_text, taf.error, taf.hint])
                    # print("ERROR-----------------------------------------")
                    # print(taf)
                    # print("----------------------------------------------")
                    tafs_error += 1
                tafs_parsed += 1
                if tafs_parsed % 1000 == 0:
                    print(
                        f"\r Parsed {tafs_parsed:,} TAFs with {tafs_error / tafs_parsed * 100:.4f}%"
                        f"errors.",
                        end="", flush=True)
    print("Done.")
