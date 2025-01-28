import csv
import datetime
import io
import zipfile
import re
import os.path
import os
from multiprocessing.managers import Token
import meteostore

import lark
from enum import Enum

class Amendment_Type(Enum):
    NO_AMENDMENT = 0
    CORRECTED = 1
    AMENDED = 2


class TafTreeTransformer(lark.Transformer):
    def __init__(self, issue_date):
        super().__init__(self)
        self.issue_date = issue_date

    def header(self, args):
        amendment = list(filter(lambda x: x is Token and x.type == "header_amendment", args))
        if len(amendment) == 0:
            return Amendment_Type.NO_AMENDMENT
        else:
            return amendment[0]

    def header_amendment(self, args):
        s = args[0].value
        if s == "COR":
            return lark.Token(args[0].type, Amendment_Type.CORRECTED)
        elif s == "AMD":
            return lark.Token(args[0].type, Amendment_Type.AMENDED)
        else:
            raise ValueError("Impermissible amendment type '{}'.".format(s))

    def day_hour_minute(self, args):
        s = args[0].value
        day = int(s[0:2])
        hour = int(s[2:4])
        minute = int(s[4:6])
        return self.make_datetime_from_day_hour_minute(day, hour, minute)

    def make_datetime_from_day_hour_minute(self, day, hour, minute):
        if day >= self.issue_date.day:
            return datetime.datetime(self.issue_date.year, self.issue_date.month, day, hour, minute)
        elif self.issue_date.month < 12:
            return datetime.datetime(self.issue_date.year, self.issue_date.month + 1, day, hour, minute)
        else:
            return datetime.datetime(self.issue_date.year + 1, 1, day, hour, minute)

    def day_hour(self, args):
        s = args[0].value
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

_parser = None
LARK_DIR = os.path.join("artaf-python","meteoparse","lark")

def parse_taf(message_time, message):
    global _parser
    if _parser is None:
        with open(os.path.join(LARK_DIR, "taf.lark"), "r") as lark_grammar:
            _parser = lark.Lark(lark_grammar)
    try:
        tree = _parser.parse(message)
        transformer = TafTreeTransformer(message_time)
        tree = transformer.transform(tree)
        # print(tree.pretty())
        return True
    except Exception as e:
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
            tafs_parsed +=1
            if tafs_parsed % 1_000 == 0:
                print("\r Parsed {} TAFs, failed {}, failure rate {}.     ".format(tafs_parsed, tafs_failed, tafs_failed/tafs_parsed), end="", flush=True)
