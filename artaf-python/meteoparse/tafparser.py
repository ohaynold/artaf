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
        cloud_layers_group = from_conditions.clouds['cloud_layer']
        # TODO: I imagine this has to change, now that the clouds() method gets auto-called by lark.
        # TODO: I have no idea how the pieces all fit together though.
        return WeatherConditions(wind_speed=wind_speed, wind_gust=wind_gust,clouds=cloud_layers_group)
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

    def clouds(self, branches):
        """Produces a list of cloud-shaped objects"""
        cloud_layers = TreeAccessor(branches)
        cloud_layers_list = []

        if hasattr(cloud_layers, "CLOUDS_SKY_CLEAR"):
            cloud_layers_list.append(CloudLayer(
                0,
                CloudCoverage("SKC"),
                False))
        elif hasattr(cloud_layers, "clouds_vertical_visibility"):
            cloud_layers_list.append(CloudLayer(
                int(cloud_vv[0].CLOUDS_ALTITUDE.value) * 100,
                CloudCoverage("VV"),
                False
            ))
        else:
            for cloud_layer in cloud_layers["cloud_layer"]:

                cb = hasattr(cloud_layer, "CLOUD_LAYER_CUMULONIMBUS")

                cloud_layers_list.append(CloudLayer(
                    int(cloud_layer.CLOUDS_ALTITUDE.value) * 100,
                    CloudCoverage(cloud_layer.CLOUD_LAYER_COVERAGE),
                    cb
                ))

        return cloud_layers_list


class CloudLayer:
    """
    Represents the cloud layer with altitude in feet, cloud coverage as a
    CloudCoverage object, and whether the cloud is cumulonimbus as a boolean.
    """
    def __init__(self, altitude, coverage, cb):
        self.coverage_altitude = altitude
        self.coverage_obj = CloudCoverage(coverage)
        self.coverage_cb = cb

    def altitude(self):
        """Return the cloud layer's altitude in feet"""
        return self.coverage_altitude

    def coverage(self):
        """Return the cloud layer's coverage as a CloudCoverage object"""
        return self.coverage_obj

    def is_cumulonimbus(self):
        """Return True if cumulonimbus, False if not"""
        return self.coverage_cb


class CloudCoverage:
    """Represents a cloud layer coverage as either a string or float."""

    def __init__(self, coverage):
        self.coverage_string = coverage

    def __repr__(self):
        return self.coverage_string

    def __str__(self):
        return self.coverage_string

    def __float__(self):
        match self.coverage_string:
            case "SKC":
                return 0.0
            case "FEW":
                return 0.25
            case "SCT":
                return .375
            case "BKN":
                return .6875
            case "OVC":
                return 1.0
            case "VV":
                # I picked this arbitrarily. I don't know if there's a number
                # that makes more sense to represent a VV condition.
                return 1.1


# Was disabled above to allow for Lark transformer method names
# pragma pylint: enable=invalid-name


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
