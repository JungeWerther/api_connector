"""Parsing methods for different data types."""

import xmltodict
import csv

def parse_xml(xml: str) -> dict:
    """Parses xml string to dict"""
    obj = xmltodict.parse(xml)
    return obj

def parse_html(html: str) -> dict:
    """Returns html as string"""
    return html

def parse_csv(text: str) -> list:
    return list(
        csv.DictReader(text.splitlines())
    )