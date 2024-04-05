# Features
## Function calling
Prepend an underscore ("_<function_name>") to the key of your key-value pair to execute an associated function with arguments defined by its associated value. By convention, use the ("<function_name>_") syntax when putting data somewhere else. 

Functions only get called if they are a method of the Callables or Writables class.

## Variable substitution
So you can keep your API-keys encrypted-at-rest, and send different types of requests in a single definition. Lists passed as arguments are automatically handled. For example:

```
{
  "_request": {
      "url": ["https://example.com", "https://pearstop.com"],
      "method": "GET",
      "headers": {
        "Content-Type": "application/html"
       }
     },
  "toSupa_": {
      "data": "{_request}",
      "table": "html",
      "overwrite": false
    }
}
```

will send two GET requests, one to example.com and one to pearstop.com. The result is stored inside a separate object that you can call upon by specifying "{_<function_name>}" as a value. **In fact, all keynames are accessible as variables**, which is very useful in case you want to make your api-connectors more readable.

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
                }
            },

        "_extract": {
            "from": "{_request}"
            "key": "access_token"
            },

        "url": "{data_url}",
        "method": "GET",
        "headers": {
            "Content-Type": "application/json",
            "access-token": "{_extract}"
            }
        }
    }

```