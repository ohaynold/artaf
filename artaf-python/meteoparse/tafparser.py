import collections
import datetime
import os
import os.path
from enum import Enum

import lark

import meteostore


class Amendment_Type(Enum):
    CORRECTED = 1
    AMENDED = 2


ParsedForecast = collections.namedtuple(
    "ParsedForecast",
    ["aerodrome", "issued_at", "issued_in", "valid_from", "valid_until", "amendment",
     "from_lines"])

WeatherConditions = collections.namedtuple(
    "WeatherConditions",
    ["wind_speed"])

FromLine = collections.namedtuple(
    "FromLine",
    ["valid_from", "valid_until", "conditions"]
)


def next_or_none(generator):
    for a in generator:
        return a
    return None


class TafTreeTransformer(lark.Transformer):
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

    @staticmethod
    def find_branches(args, target):
        return [x for x in args if isinstance(x, lark.Tree) and x.data == target]

    @staticmethod
    def find_branch(args, target):
        branches = [x for x in args if isinstance(x, lark.Tree) and x.data == target]
        if len(branches) == 0:
            return None
        if len(branches) == 1:
            return branches[0]
        raise IndexError("Got more than one branch where I expected one.")

    @staticmethod
    def find_leaf(tree, target):
        branches = [x for x in tree.children if isinstance(x, lark.Token) and x.type == target]
        if len(branches) == 0:
            return None
        if len(branches) == 1:
            return branches[0].value
        raise IndexError("Got more than one leaf where I expected one.")

    def start(self, args):
        # TODO: ABE is shared between KABE and PABE. Maybe really have to key by center and aerodrome for PILs or re-sort after loading
        issued_in = str(next(self.find_branch(args, "preamble").find_data("preamble_issued_in")).children[0])
        aerodrome = str(next(self.find_branch(args, "header").find_data("header_issued_for")).children[0])
        issued_at = str(next(self.find_branch(args, "header").find_data("header_issued_at")).children[0])
        valid_from = str(next(self.find_branch(args, "header").find_data("header_valid_from")).children[0])
        valid_until = str(next(self.find_branch(args, "header").find_data("header_valid_until")).children[0])
        amendment = self.find_leaf(self.find_branch(args, "header"), "HEADER_AMENDMENT")

        taf_content = self.find_branch(args, "taf_content")
        if taf_content:
            from_line_times = [valid_from]
            from_lines = [taf_content.children[0]]
            if len(taf_content.children) > 1:
                for line in taf_content.children[1:]:
                    from_line_times.append(line.children[0])
                    from_lines.append(line.children[1])
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

    def from_group_content(self, args):
        conditions = self.find_branch(args, "from_conditions")
        wind_group = next(conditions.find_data("wind_group"))
        wind_speed = self.find_leaf(wind_group, "WIND_SPEED")
        return WeatherConditions(wind_speed=wind_speed)
        # TODO: Add other elements of group

    def WIND_SPEED(self, arg):
        return arg.update(value=int(arg.value))

    def DAY_HOUR_MINUTE(self, args):
        s = args.value
        day = int(s[0:2])
        hour = int(s[2:4])
        minute = int(s[4:6])
        return self.make_datetime_from_day_hour_minute(day, hour, minute)

    def DAY_HOUR(self, args):
        s = args.value
        day = int(s[0:2])
        hour = int(s[2:4])
        if hour == 24:
            increment_day = True
            hour = 0
        else:
            increment_day = False
        res = self.make_datetime_from_day_hour_minute(day, hour, 0)
        if increment_day:
            res += datetime.timedelta(days=1)
        return res

    def HEADER_AMENDMENT(self, tok):
        if tok == "COR":
            return tok.update(value=Amendment_Type.CORRECTED)
        if tok == "AMD":
            return tok.update(value=Amendment_Type.AMENDED)
        return IndexError("Unknown amendment type.")


_parser = None
LARK_DIR = os.path.join("artaf-python", "meteoparse", "lark")


def parse_taf(message_time, message):
    global _parser
    if _parser is None:
        with open(os.path.join(LARK_DIR, "taf.lark"), "r") as lark_grammar:
            _parser = lark.Lark(lark_grammar, parser="lalr")
    try:
        tree = _parser.parse(message)
        transformer = TafTreeTransformer(message_time)
        tree = transformer.transform(tree)
        # print(tree)
        return True
    except lark.exceptions.UnexpectedInput as e:
        print("\n============================")
        print(message)
        print(e)
        print(e.get_context(message))
        return False
    except lark.exceptions.VisitError as e:
        print("\n============================")
        print(message)
        print(e)
        return False


if __name__ == "__main__":
    tafs_parsed = 0
    tafs_failed = 0
    for station, raw_tafs in meteostore.get_tafs(meteostore.get_station_list(), 2010, 2024):
        for message_time, message in raw_tafs:
            if not parse_taf(message_time, message):
                tafs_failed += 1
            tafs_parsed += 1
            if tafs_parsed % 1_000 == 0:
                print("\r Parsed {} TAFs, failed {}, failure rate {}.     ".format(tafs_parsed, tafs_failed,
                                                                                   tafs_failed / tafs_parsed), end="",
                      flush=True)
