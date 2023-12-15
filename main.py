from api import daterange, Jewellabs, Mice, Untill, Nostradamus, Zaalcapaciteit
from dotenv import load_dotenv
from datetime import timedelta, datetime
from time import sleep

def iter_date_range(start, end):
    """
    Takes a start date iso datestring and end date and returns an iterator of groups of 5 days. 
    Returns iterator that yields isoformat tuples of strings indicating only the first and last date of the group.
    """
    start = datetime.strptime(start, "%Y-%m-%d")
    end = datetime.strptime(end, "%Y-%m-%d")
    delta = end - start
    for i in range(delta.days):
        if i % 3 == 0:
            yield (start + timedelta(days=i)).strftime("%Y-%m-%d"), (start + timedelta(days=i+3)).strftime("%Y-%m-%d")

# Jewellabs(start="2022-01-02", end="2022-01-15")
# Mice()  
# Untill()
# Nostradamus()
# Zaalcapaciteit()

for start, end in iter_date_range("2023-12-13", "2023-12-14"):
    Jewellabs(start=start, end=end)
    sleep(1)
