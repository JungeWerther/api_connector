"""Helper functions for the Connect module."""

from itertools import product
from datetime import datetime

def get_date_format(date_str):
    """Naive function to determine the format of a date string. Can be improved"""
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H",

        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H",
        
        "%Y-%m-%d",

        "%Y/%m/%dT%H:%M:%S.%fZ",
        "%Y/%m/%dT%H:%M:%S.%f",
        "%Y/%m/%dT%H:%M:%S",
        "%Y/%m/%dT%H:%M",
        "%Y/%m/%dT%H",

        "%Y/%m/%d %H:%M:%S.%f%z",
        "%Y/%m/%d %H:%M:%S.%f",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d %H",

        "%Y/%m/%d"
          ]:
        try:
            datetime.strptime(date_str, fmt)
            return fmt
        except ValueError as e:
            continue
    
def date_format(date_source: str, target_expression: str) -> str:
    """Convert a date to a string with a specific format."""
    try:
        date_obj = datetime.fromisoformat(date_source)
    except: 
        date_obj = datetime.strptime(date_source, get_date_format(date_source))

    print(date_obj)
    formatted_date = date_obj.strftime(get_date_format(target_expression))
    print(formatted_date)
    return formatted_date

def flatten_dict(**d):
    """Flatten a dictionary (one level)."""

    keys, values = zip(*d.items())
    for instance in product(*(x if isinstance(x, list) else [x] for x in values)):
        yield dict(list(zip(keys, instance)))
