from itertools import product

def flatten_dict(**d):
        """Flatten a dictionary (one level)."""

        keys, values = zip(*d.items())
        for instance in product(*(x if isinstance(x, list) else [x] for x in values)):
            yield dict(list(zip(keys, instance)))