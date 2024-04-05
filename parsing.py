"""Parsing methods for different data types"""

import xmltodict

def parse_xml(xml: str) -> dict:
    """Parses xml string to dict"""
    try:
        obj = xmltodict.parse(xml)
    except:
        print("Warning: Could not parse xml. Check returned xml string in response cache.")
    return obj

def parse_html(html: str) -> str:
    """Returns html as string"""
    return html
