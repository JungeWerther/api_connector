import xmltodict

def parse_xml(xml):
    try:
        obj = xmltodict.parse(xml)
    except:
        print("Warning: Could not parse xml. Check returned xml string in response cache.")
    return obj

def parse_html(html):
    return html