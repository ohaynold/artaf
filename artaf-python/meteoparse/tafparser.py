"""This is the parser for TAFs. Function parse_taf() does all the work. We're using Lark as our parser
generator, in the LALR mode for speed. In addition to the grammar in lark/taf.lark, class
 TafTreeTransformer does the remaining heave lifting of building Pythonic output objects."""

import collections
import datetime
import os
import os.path
from enum import Enum

import lark

import meteostore
from meteoparse.tree_accessor import lark_tree_accessor


class AmendmentType(Enum):
    CORRECTED = 1
    AMENDED = 2


ParsedForecast = collections.namedtuple(
    "ParsedForecast",
    ["aerodrome", "issued_at", "issued_in", "valid_from", "valid_until", "amendment",
     "from_lines"])

WeatherConditions = collections.namedtuple(
    "WeatherConditions",
    ["wind_speed", "wind_gust", "cloud_layers"])

FromLine = collections.namedtuple(
    "FromLine",
    ["valid_from", "valid_until", "conditions"]
)


# noinspection PyMethodMayBeStatic,PyPep8Naming
class TafTreeTransformer(lark.Transformer):
    """
    To be used within Lark to transform abstract syntax trees into ParsedForecast objects.
    """

    # noinspection PyTypeChecker
    def __init__(self, issue_date):
        super().__init__(self)
        self.issue_date = issue_date

    def make_datetime_from_day_hour_minute(self, day, hour, minute):
        if day >= self.issue_date.day:
            return datetime.datetime(self.issue_date.year, self.issue_date.month, day, hour, minute)
        elif self.issue_date.month < 12:
            return datetime.datetime(self.issue_date.year, self.issue_date.month + 1, day, hour, minute)
        else:
            return datetime.datetime(self.issue_date.year + 1, 1, day, hour, minute)

    # noinspection GrazieInspection
    def start(self, branches):
        tree = lark_tree_accessor(branches)

        # Extract header information
        issued_in = tree.preamble.preamble_issued_in.AERODROME.value
        header = tree.header
        aerodrome = header.header_issued_for.AERODROME.value
        issued_at = header.header_issued_at.DAY_HOUR_MINUTE.value
        valid_from = header.header_valid_from.DAY_HOUR.value
        valid_until = header.header_valid_until.DAY_HOUR.value
        amendment = header.HEADER_AMENDMENT.value if hasattr(header, "HEADER_AMENDMENT") else None

        # Copy the from lines with the actual forecasts and for simplicity give each one a start and an
        # end datetime.
        if hasattr(tree, "taf_content"):
            taf_content = tree.taf_content
            from_line_times = [valid_from]
            from_lines = [taf_content[0]]
            if len(taf_content) > 1:
                for line in taf_content[1:]:
                    from_line_times.append(line[0].value)
                    from_lines.append(line[1])
            from_line_times.append(valid_until)
            new_from_line = [
                FromLine(conditions=from_lines[i], valid_from=from_line_times[i], valid_until=from_line_times[i + 1])
                for i in range(len(from_lines))]
        else:
            new_from_line = None

        res = ParsedForecast(aerodrome=aerodrome, issued_at=issued_at, issued_in=issued_in,
                             valid_from=valid_from, valid_until=valid_until, amendment=amendment,
                             from_lines=new_from_line)

        return res

    def from_group_content(self, branches):
        """
        Parse from groups. This is where most of the interesting weather information is and likely the right
        place to come if you want to extend functionality.
        :param branches: A list of lark.Tree or lark.Token objects
        :return: WeatherCondition tuple
        """
        from_conditions = lark_tree_accessor(branches).from_conditions
        wind_group = from_conditions.wind_group
        wind_speed = wind_group.WIND_SPEED.value
        wind_gust = wind_group.wind_gust_group.WIND_SPEED.value if hasattr(wind_group, "wind_gust_group") else None
        cloud_layers_group = from_conditions.clouds['cloud_layer']
        return WeatherConditions(wind_speed=wind_speed, wind_gust=wind_gust, cloud_layers=cloud_layers_group)
        # TODO: Unroll TEMPO and PROB changes
        # TODO: Add other elements of group

    def WIND_SPEED(self, token):
        return token.update(value=int(token.value))

    def DAY_HOUR_MINUTE(self, token):
        s = token.value
        day = int(s[0:2])
        hour = int(s[2:4])
        minute = int(s[4:6])
        return token.update(value=self.make_datetime_from_day_hour_minute(day, hour, minute))

    def DAY_HOUR(self, token):
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
        if token == "COR":
            return token.update(value=AmendmentType.CORRECTED)
        if token == "AMD":
            return token.update(value=AmendmentType.AMENDED)
        return IndexError("Unknown amendment type.")


_parser = None
LARK_DIR = os.path.join("artaf-python", "meteoparse", "lark")


# noinspection PyShadowingNames
def parse_taf(message_time, message):
    # The parser is expensive to generate, so we memoize it
    global _parser
    if _parser is None:
        with open(os.path.join(LARK_DIR, "taf.lark"), "r") as lark_grammar:
            _parser = lark.Lark(lark_grammar, parser="lalr")

    try:
        tree = _parser.parse(message)
        transformer = TafTreeTransformer(message_time)
        tree = transformer.transform(tree)
        # print(tree)
        return tree
    except lark.exceptions.UnexpectedInput as e:
        # TODO: Remember that something went wrong
        return None
    except lark.exceptions.VisitError as e:
        # TODO: Remember that something went wrong
        return None


def parse_tafs(taf_sequence):
    """
    Parse a sequence of raw TAFs and make a sequence of ParsedForecast tuples out of them
    :param taf_sequence: a sequence of datetime.datetime, str tuples with the time and content of the raw TAF
    :return: a sequence of ParsedForecast tuples
    """
    for taf_date, taf_text in taf_sequence:
        res = parse_taf(taf_date, taf_text)
        # TODO: Register errors
        if res is not None:
            # taf_date is no longer needed because now the TAF itself is augmented with full dates
            yield res


if __name__ == "__main__":
    tafs_parsed = 0
    for station, raw_tafs in meteostore.get_tafs(meteostore.get_station_list(), 2010, 2024):
        for taf in parse_tafs(raw_tafs):
            print(taf)
            tafs_parsed += 1
            if tafs_parsed % 1000 == 0:
                print("\r Parsed {:,} TAFs.".format(tafs_parsed),
                      end="",
                      flush=True)
    print("Done.")
