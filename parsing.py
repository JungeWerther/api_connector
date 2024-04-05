"""Parsing methods for different data types."""

import xmltodict

def parse_xml(xml: str) -> dict:
    """Parses xml string to dict"""
    obj = xmltodict.parse(xml)
    return obj

def parse_html(html: str) -> str:
    """Returns html as string"""
    return html
