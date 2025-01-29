import collections
import datetime
import os
import os.path
from enum import Enum

import lark

import meteostore


class AmendmentType(Enum):
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


class TreeAccessor:
    def __init__(self, tree):
        self.tree = tree

    def __getitem__(self, item):
        if isinstance(item, slice):
            res = []
            for a in self.tree.children[item]:
                if isinstance(a, lark.Tree):
                    res.append(TreeAccessor(a))
                else:
                    res.append(a)
            return res
        if isinstance(item, int):
            res = self.tree.children[item]
            if isinstance(res, lark.Tree):
                return TreeAccessor(res)
            else:
                return res
        res = []
        for child in self.tree.children:
            if isinstance(child, lark.Tree):
                if child.data == item:
                    res.append(TreeAccessor(child))
            elif isinstance(child, lark.Token):
                if child.type == item:
                    res.append(child)
            else:
                raise TypeError("Unexpected type hanging in our Lark tree.")
        return res

    def __getattr__(self, item):
        candidates = self[item]
        if len(candidates) != 1:
            raise AttributeError("Expected to find exactly one selected child node.")
        return candidates[0]

    def __len__(self):
        return len(self.tree.children)


class BranchesAccessor:
    def __init__(self, branches):
        self.branches = branches

    def __getitem__(self, item):
        res = []
        for child in self.branches:
            if isinstance(child, lark.Tree):
                if child.data == item:
                    res.append(TreeAccessor(child))
            elif isinstance(child, lark.Token):
                if child.type == item:
                    res.append(child)
            else:
                raise TypeError("Unexpected type hanging in our Lark tree.")
        return res

    def __getattr__(self, item):
        candidates = self[item]
        if len(candidates) != 1:
            raise AttributeError("Expected to find exactly one selected child node.")
        return candidates[0]


def lark_tree_accessor(item):
    if isinstance(item, lark.Tree):
        return TreeAccessor(item)
    elif isinstance(item, list):
        return BranchesAccessor(item)
    else:
        raise TypeError("Unexpected type hanging in our Lark tree.")


# noinspection PyMethodMayBeStatic,PyPep8Naming
class TafTreeTransformer(lark.Transformer):
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

    @staticmethod
    def find_leaf(tree, target):
        branches = [x for x in tree.children if isinstance(x, lark.Token) and x.type == target]
        if len(branches) == 0:
            return None
        if len(branches) == 1:
            return branches[0].value
        raise IndexError("Got more than one leaf where I expected one.")

    def start(self, args):
        tree = lark_tree_accessor(args)
        issued_in = tree.preamble.preamble_issued_in.AERODROME.value
        header = tree.header
        aerodrome = header.header_issued_for.AERODROME.value
        issued_at = header.header_issued_at[0]
        valid_from = header.header_valid_from[0]
        valid_until = header.header_valid_until[0]
        amendment = header.HEADER_AMENDMENT.value if hasattr(header, "HEADER_AMENDMENT") else None

        if hasattr(tree, "taf_content"):
            taf_content = tree.taf_content
            from_line_times = [valid_from]
            from_lines = [taf_content[0]]
            if len(taf_content) > 1:
                for line in taf_content[1:]:
                    from_line_times.append(line[0])
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

    def from_group_content(self, args):
        from_conditions = lark_tree_accessor(args).from_conditions
        wind_speed = from_conditions.wind_group.WIND_SPEED.value
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
            return tok.update(value=AmendmentType.CORRECTED)
        if tok == "AMD":
            return tok.update(value=AmendmentType.AMENDED)
        return IndexError("Unknown amendment type.")


_parser = None
LARK_DIR = os.path.join("artaf-python", "meteoparse", "lark")


# noinspection PyShadowingNames
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
        # print("\n============================")
        # print(message)
        # print(e)
        # print(e.get_context(message))
        return False
    except lark.exceptions.VisitError as e:
        print("\n============================")
        print(message)
        print(e)
        return False


if __name__ == "__main__":
    tafs_parsed = 0
    tafs_failed = 0
    for station, raw_tafs in meteostore.get_tafs(meteostore.get_station_list(), 2009, 2009):
        for message_time, message in raw_tafs:
            if not parse_taf(message_time, message):
                tafs_failed += 1
            tafs_parsed += 1
            if tafs_parsed % 1_000 == 0:
                print("\r Parsed {} TAFs, failed {}, failure rate {}.     ".format(tafs_parsed, tafs_failed,
                                                                                   tafs_failed / tafs_parsed), end="",
                      flush=True)
