# Inference
The `Inference` class in inference.py automatically infers the schema of data coming from an API. The following background is in order:

## Assumptions
When we deal with data coming from a single source, though it may not always be clean, if it is in any way structured, it will always conform to either one of the following:

1. It is a dictionary
1. It is a list of dictionaries
1. It is a dictionary containing a list of dictionaries

Note that lists of lists are pretty much unusable from a data perspective. Indeed, how are we supposed to know which list corresponds to what? If there is any way that data arriving in such a structure is meaningful, we should be able to simply flatten such structures in 99% of cases. But let us focus on the more prevalent cases first.

In any case we can treat API responses as directed acyclic graphs (DAG). Our goal is to 'rip apart' this graph into a list of 'singular' structures which do not contain any 'aggregates'.

By *aggregate* is meant:
1. list of dictionaries with the same type. (When we are dealing with `lists`, it is **required** that items are of the same type).
2. dictionary with dynamic keynames but values that are **all** of the same type (and dictionaries (?)).

If we assign types to all nested data structures, 
```
{
    "data": [
        {
            "a1": "b1",
            "a2": "c1"
        },
        {
            "a1": 1,
            "a3": "c2"
        }, ...
    ]
}
```
then we can call `Hypothesis({...})` to obtain
```
{
    "data": [
        {
            "a1": int | str,
            "a2": str,
            "a3": str
        }
    ]
}
```
Once more, if we have data like
```
input = [
    {
        "name": "John",
        "age": 30,
        "city": "New York"
    },
    {
        "name": "Hans",
        "age": 45,
        "city": "New York",
        "cool": {
            "too": "cool",
            "for": 4
        }
    },
    {
        "name": "Mary",
        "age": 25,
        "city": "New York",
        "hobbies": 1
    },
    {
        "name": "Peter",
        "age": 45,
        "city": "New York",
        "hobbies": ["reading", "writing"]
    },
    {
        "name": "Johnny Depp",
        "age": 47,
        "city": "Amsterdam",
        "hobbies": [1, "yes"]
    },
    {
        "name": "Markus",
        "age": 12,
        "city": "Berlin",
        "cool": {
            "too": "cool",
            "for": "for",
            "what": "school"
        }
    },
    {
        "name": "Markovich",
        "age": 12,
        "city": {
            "name": "Berlin",
            "zip": 12345
        },
        "test": {
            "a": "stringy", 
            "b": [{
                "z": 1, 
                "q": "2"
                }], 
            "c": True
        }
    }
]
```

We can run 
```
hypothesis = Hypothesis()
for item in input:
    hypothesis.update(item)
print(hypothesis.current)
```
to get the reduced form
```
{
    "name": "<class 'str'>",
    "age": "<class 'int'>",
    "city": "typing.Any",
    "cool": {
        "too": "<class 'str'>",
        "for": "int | str",
        "what": "<class 'str'>"
    },
    "hobbies": "int | list[str | int]",
    "test": {
        "a": "<class 'str'>",
        "b": [
            {
                "z": "<class 'int'>",
                "q": "<class 'str'>"
            }
        ],
        "c": "<class 'bool'>"
    }
}
```
We are essentially 'intersecting' all the records in a list to a type which will validate all records.

Why is this useful? Because it allows us to incrementally validate data. If we validate all incoming data in a stream to the output of `Hypothesis.current`, we can easily notify users of our application when an API definition has changed, for example.

Lists nested in lists **currently stop the recursive process**. So you will just get a Type `list`.

So, now, at any moment, we have the type that is used by that key. So how do we deal with the dynamic keyname case? Since there is no logical way to destinguish
