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

parser = lark.Lark(r"""
    taf: preamble header (taf_content | taf_nil_content) (amd_limitation)? close
    taf_optional_content: taf_content
                        | taf_nil_content
    taf_content: from_group_content from_groups 
    from_groups: ("\n" from_group)*
    taf_nil_content: sp "NIL"
    amd_limitation: /\n {5,6}AMD [^=]*/ 

    preamble: /\d{3} \n[A-Z]{4}\d{2} / (preamble_issued_at)? /( \d{6}( [A-Z]{3})?)?\nTAF[A-Z]{3}\n/
    preamble_issued_at: aerodrome

    header: "TAF" (sp header_amendment)? "\n" header_issued_for sp header_issued "Z " header_valid_from "/" header_valid_until
    header_issued_for: aerodrome
    header_issued: day_hour_minute
    header_valid_from: day_hour
    header_valid_until: day_hour
    !header_amendment: "AMD"
                    | "COR"

    from_group: "     FM" day_hour_minute from_group_content
    from_group_content: from_conditions (prob_group | tempo_group)*
    prob_group: sp /PROB(\d){2}/ sp day_hour "/" day_hour optional_conditions
    tempo_group: "\n      TEMPO " day_hour "/" day_hour optional_conditions

    close: "=" ("\n")*

    from_conditions: wind_group visibility_group conditions_phenomena sp clouds (sp wind_shear_group)?
    optional_conditions: wind_group? visibility_group? conditions_nsw_or_phenomena (sp clouds)? (sp wind_shear_group)?
    conditions_phenomena: (sp phenomenon)*
    conditions_nsw_or_phenomena:  (sp "NSW")|conditions_phenomena

    wind_group: sp wind_direction wind_speed ("G"wind_speed)? "KT"
    wind_shear_group: "WS" hundreds_feet "/" wind_direction wind_speed "KT"
    wind_direction: wind_direction_degrees
                  | wind_direction_variable
    wind_direction_degrees: /\d{3}/
    wind_direction_variable: "VRB"
    # Three digit wind speeds are somewhat common, but some are clearly erroneous, so we can't really
    # be lenient.
    wind_speed: /\d{2}/

    visibility_group: sp visibility_exceeding? visibility_range "SM"
    visibility_exceeding: "P"
    visibility_range: /\d{1,2}/
                    | /(\d )?\d\/\d/ 

    phenomenon: /[\+-]?([A-Z]{2})+/

    clouds: clouds_sky_clear
          | clouds_vertical_visibility
          | cloud_layer (sp cloud_layer)*
    clouds_sky_clear: "SKC"
    clouds_vertical_visibility: "VV" hundreds_feet cloud_layer_cumulonimbus?
    cloud_layer: cloud_layer_coverage hundreds_feet cloud_layer_cumulonimbus?
    !cloud_layer_coverage: "FEW" | "BKN" | "OVC" | "SCT"
    cloud_layer_cumulonimbus: "CB"

    day_hour_minute : /\d{6}/
    aerodrome: /[A-Z]{4}/
    day_hour: /\d{4}/
    hundreds_feet: /\d{3}/

    sp: " " | "\n      "
""", start="taf")

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

def parse_taf(message_time, message):
    try:
        tree = parser.parse(message)
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
