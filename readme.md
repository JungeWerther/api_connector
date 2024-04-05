# Features
## Function calling
Prepend an underscore ("_<function_name>") to the key of your key-value pair to execute an associated function with arguments defined by its associated value. 

Functions only get called if they are a method of the Callables class.

## String substitution
So you can keep your API-keys encrypted-at-rest.

## Nested requests with a single JSON definition.
Imagine you are connecting with an API that requires you to get a new access token using an existing refresh token, which is subsequently used to obtain data. Then you could do something like:

```
{
    "_request": {
        "_request": {
            "url": "{refresh_url}"
            "method": "GET",
            "headers": {
                "Content-Type": "application/json",
                "refresh-token": "{refresh_token}"
            },
        "_extract": {
            "path": "data.access_token"
        }
        "url": "{data_url}",
        "method": "GET",
        "headers": {
            "Content-Type": "application/json",
            "access-token": "{_extract}"
        }
        }
    }
}
```