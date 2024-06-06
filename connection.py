# system
# import uuid
import os
import inspect
import json
import time
import getpass

# data
import csv
import hashlib

# requests
import requests
from requests import Response, Session

# custom
from . import regex, parsing
from .errors import add_error, ErrorHandlingMeta
from .helpers import flatten_dict
from .inference import Hypothesis

# supabase-py
from gotrue import SyncMemoryStorage
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from storage3.types import CreateOrUpdateBucketOptions

# Default file size limit = 26MB
DEFAULT_FILE_SIZE_LIMIT = 26000000

# TODO: implement caching strategy when referencing data in config.
# Right now, we're just unpacking a list and returning it itself.
# This could introduce bugs if the data contains the {var} syntax. (??)
# One strategy could be to protect the data keyword.
# We should also definitely consider only 'pulling up' lists with the flatten_dict helper function..
# ..if the var is not key_callable.

class Supabase(Client):
    """Supabase client class. Inherits from supabase.Client."""

    def __init__(self, schema="public"):
        self.url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

        super().__init__(
            self.url,
            self.key
            )

        self.options.schema = schema
        self.schema = schema

    def create_client(self, options=None):
        """Create a new client with the same key and url."""
        return create_client(self.url, self.key, options or self.options)

class AnyClient():
    """Client class for any supabase client. Inherits from supabase.Client."""
    def __init__(self, token: str=None, schema: str=None):
        self.url: str = self.get_supabase_url()
        self.key: str = token
        self.client: Client = create_client(
            self.url,
            self.key,
            ClientOptions(
                schema=schema,
                storage=SyncMemoryStorage()
                )
            )

    def get_supabase_url(self):
        return (
            os.environ.get("SUPABASE_URL") or
            os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
        )

class AnonClient(AnyClient):
    """AnonClient class. To use ANONKEY jwt. Inherits from AnyClient."""
    def __init__(self, schema: str):
        super().__init__(
            os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY"),
            schema
            )

class ServiceRoleClient(AnyClient):
    """
    ServiceRoleClient class. Inherits from AnyClient. 
    Bypasses RLS on underlying database. Use with care.
    """
    def __init__(self, schema: str):
        super().__init__(
            self.get_service_role_key(),
            schema
            )

    def get_service_role_key(self):
        """Get the service role key from the environment."""
        return (
            os.environ.get("SUPABASE_SERVICE_ROLE")
        )

class Callables(metaclass=ErrorHandlingMeta):
    """Class to define explicit methods callable from config.
    Important: you need to add type hints and return signatures.
    """
    def __init__(self, config=None, debug=False):
        self.config = config
        self.debug = debug

    def caller(self, func, **kwargs):
        """Flatten kwargs and call func on each instance. Return aggregate"""
        q = []
        for p in flatten_dict(**kwargs):
            q.append(func(**p))

        return q

    def censor(self, value: str):
        """Censor data in self.data"""

        if hasattr(self.config, "key"):
            res = regex.censor(value, str(self.config.key))
            if res != value:
                return res

        if hasattr(self.config, "password"):
            res = regex.censor(value, self.config.password[0])
            if res != value:
                return res

        return value[:100] + " ... " if len(value) > 100 else value

    @add_error("Unable to parse response (hint: change the Content-Type)", 472)
    def parse_doctype(self, res: Response, doctype: str) -> dict | str:
        """Parse a doctype from a string"""
        print("Parsing doctype:", doctype)
        print("Response:", res.text[:100])
        match doctype:
            case "application/xml":
                return parsing.parse_xml(res.text)
            case "application/json":
                return res.json()
            case "text/csv":
                r = csv.DictReader(res.text.splitlines())
                return {"response": list(r)}
            case "application/html":
                # the xml parser also works for html
                return parsing.parse_html(res.text)
            case _:
                return res.json()

    @add_error("Error calling function", 472)
    def _request(self,
            url=None,
            base_url=None,
            headers=None,
            method=None,
            rel_url="",
            auth=None,
            session: Session=None,
            sleep=0,
            debug=False,
            ) -> dict | str | list:
        """send a request with the specified parameters
        TODO: implement POST, PUT methods.
        """

        print("Requesting:", url)
        try:
            auth = (auth["user"], auth["password"]) if auth is not None else None
        except Exception as e:
            raise SyntaxError("auth must be a dict with keys 'user' and 'password'") from e

        if url is None:
            if base_url is not None:
                url = base_url + rel_url
            else:
                raise SyntaxError("Both url and base_url undefined")

        if debug:
            print("Requesting:", url)

        if method is None:
            print("Warning: method not defined. defaulting to GET")
            method = "GET"

        if headers is None:
            print("Warning: headers not set. defaulting to Content-type: application/json.")
            headers = {
                "Content-Type": "application/json"
            }

        # If there is no session, or if session config has changed in the meantime, 
        # create a new session.
        if session is None or (
            session.auth != auth or
            session.headers != headers
            ):
            session = self.new_session(auth, headers)

        # sleep if specified
        if sleep > 0:
            time.sleep(sleep)

        if method == "GET":
            print("GET request")
            try:
                res = session.get(url)
            except Exception as e:                
                raise e
        
            if res is None:
                print("No response from server")
            else:
                print("Response:")
                print(type(res))
        
        elif method == "POST":
            print("POST request")
            res = session.post(url)
        else:
            raise ValueError(f"{method} needs implementation")

        if debug:
            print(
                "\n Response Headers: \n",
                res.headers
                )
            with open("./debug.html", "wt") as f:
                f.write(res.text)
        
        return self.parse_doctype(res, headers["Content-Type"])

    def _transform(self, data: list, spec: dict) -> dict | str | list:
        """Transform data according to a glom spec"""
        return parsing.transform(data, spec)
    
    def new_session(self, auth, headers):
        """Create a new session"""

        s = requests.Session()
        s.auth = auth
        s.headers.update(headers)

        setattr(self.config, "session", s)
        return s

    def _fromFile(self, path):
        """Read a file and return its contents as a json object. Disabled in production."""
        try:
            with open(path, "r") as f:
                obj = json.loads(f.read())
            if self.debug: print("Reading:", path)
        except:
            if path is not None:
                raise ValueError("Unable to read file:", path)
            else:
                raise SyntaxError("'path' undefined")

        return obj

    def _test(self, base_url, rel_url="") -> str:
        """Test function. Can you pass base_url and rel_url to get url?"""
        url = base_url + rel_url
        return url

class Config():
    """Class used as target for configuration settings. Define special methods here."""
    def __init__(self, **kwargs):

        # initialize config with any passed kwargs
        # for k, v in kwargs.items():
        #     setattr(self, k, v)

        # does this work?
        self.add_attributes(**kwargs)

    def add_attributes(self, **kwargs):
        """Add attributes to config"""
        for k, v in kwargs.items():
            setattr(self, k, v)

class Writeables(metaclass=ErrorHandlingMeta):
    """Class to define explicit methods callable from config"""
    def __init__(self, config=None, debug=False):
        self.config = config
        self.debug = debug
        self.decoded = getattr(self.config, "decoded", None)
        self.metadata = getattr(self.config, "metadata", None)

    def toSupa_(self, data, table: str=None, schema: str = None, overwrite: bool=False) -> None:
        """
        Upsert data to supabase table. You need a supabase session cookie. 
        Let me know if you have any trouble here, I can help.
        """

        # TODO: add hypothesis object to request metadata in metadata table.
        # hypothesis = Hypothesis(data).current
        # print(json.dumps(data, indent=2))
        # print("Hypothesis:", hypothesis)

        if overwrite: print("[WARNING] overwrite needs implementation")
        if self.decoded is None: raise ValueError("invalid session")

        client = AnyClient(self.decoded.token, schema="etl").client
        user_tld = client.from_("organization").select("tld").single().execute().data["tld"]
        newclient = AnyClient(self.decoded.token, schema=user_tld).client

        try:

            res = newclient.from_("metadata").insert({
                "user_id": self.decoded.sub or None,
                "run_id": self.metadata["run_id"] or None,
                "data": json.dumps(data)
                }, returning="representation").execute()

            return res
            # retu rn newclient.from_(table).insert({
            #     "metaId": res.data[0]["id"],
            #     "html": data
            #     }).execute()
        except:
            print("Table does not exist. Creating...")
            print("TODO: implement type-safe RPC call to create table.")
            raise SyntaxError("Table does not exist....")
            # tables = newclient.rpc("create_table", {"name": table})

    # def toStorage_(self, data, bucket: str, folder: str, filename: str, overwrite: bool):
    #    TODO: implement
    #     """Upsert data to supabase table. Needs implementation."""

    #     if self.decoded is None: raise ValueError("invalid session")
    #     client = AnyClient(self.decoded.token, schema="storage").client
    #     print("client", client)

    #     raise ValueError("Not implemented")
    #     # if bucket in client.storage.list_buckets():
        #     print("bucket exists")
        # else:
        #     print(f"bucket '{bucket}' does not exist. creating...")
        #     id = uuid.uuid4().__str__()

        #     res = client.storage.create_bucket(
        #         id, 
        #         bucket,
        #         CreateOrUpdateBucketOptions(
        #             public=False,
        #             file_size_limit=DEFAULT_FILE_SIZE_LIMIT,
        #             allowed_mime_types=[
        #             "application/json", 
        #             "application/xml", 
        #             "text/csv", 
        #             "application/html",
        #             "application/pdf",
        #             "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        #             "application/vnd.ms-powerpoint",
        #             "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        #             "application/vnd.visio",
        #             "application/vnd.ms-excel",
        #             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",    
        #             "application/msword"
        #             "image/*",
        #             "video/*",
        #             "audio/*",
        #             "text/*",
        #             ]))
        # print(res)

    # def toFile_(self, data, path):
    #     """Write data that is currently cached in self.config.data to file. Disabled in production
    #     """
    #     raise ValueError("File storage is disabled")
    #     with open(path, "wt") as f:
    #         json.dump(data, f, indent=2)
    
    @add_error(f"Error calling function {__name__}", 472)
    def caller(self, func, **kwargs):
        """Flatten kwargs and call func on each instance. Return aggregate"""
        return func(**kwargs)

class DataOBJ():
    """Data Object.
    -> Used for logging raw response data
    """
    def __init__(self, data=None, func=None, callables_obj: Callables=None, **kwargs):
        self.data = data
        self.func = func
        self.kwargs = kwargs

        if func is not None and callables_obj is not None:
            self.censor = callables_obj.censor
            self.config = callables_obj.config
            self.path = "./response_cache/" + self.to_file_path()

            if self.path_exists():
                print("reading cache stored at:", self.path, "\n")
                self.data = callables_obj._fromFile(self.path)
            else:
                print("[FUNCTION]", func.__name__)

                self.data = callables_obj.caller(func, **kwargs)

            if hasattr(self.config, "cache"):
                if not self.config.cache:
                    pass
                else: self.save_snapshot(self.path)
                # uncomment if you want to enable cache by default
                # else: self.save_snapshot(self.path)

    def __repr__(self) -> str:
        return "data: " + self.data_truncated() + "\n"

    def data_truncated(self):
        """Return a truncated string representation of the data object."""
        lines = json.dumps(self.data, indent=2).split('\n')
        res = '\n'.join(lines[:10]) + "\n...\n" + '\n'.join(lines[-10:]) if len(lines) > 20 else '\n'.join(lines)
        return res 

    def save_snapshot(self, path):
        """Save a snapshot of the data object to a file."""
        with open(path, "wt") as f:
            json.dump(self.data, f)

    def path_exists(self):
        """Check if a file exists at the path."""
        return os.path.exists(self.path)

    def to_file_path(self):
        """Return a file path for the data object"""
        return self.hash_string(
            regex.list_to_file_path(
                [self.func.__name__] + 
                [self.censor(str(val)) for val in self.kwargs.values()]
                )
        ) + ".json"

    def hash_string(self, string):
        """Hash a string with sha256. Return hexdigest."""
        return hashlib.sha256(string.encode()).hexdigest()

class Connection():
    """Connection Class. This is the main class that traverses the configuration file."""

    def __init__(self,
        spec=None,
        debug: bool=False,
        **kwargs
        ):

        self.debug = debug
        self.spec = spec
        self.data = None

        # initialize configuration class with passed kwargs.
        self.config = Config(**kwargs)

        # instantiate Callables class instance with permanent access to config.
        self.functions = Callables(self.config)

        # instantiate Writeables class instance with permanent access to config.
        self.writeables = Writeables(self.config)

    def get_key(self):
        """Get the key from the user"""
        return getpass.getpass("Enter your key: ")

    def run(self):
        """Traverses the configuration file"""
        return self.traverse_config()

    def traverse_config(self):
        """Traverses the passed configuration"""

        for key, value in self.spec.items():
            self.evaluate(key, value)

    def key_callable(self, key):
        """
        Criterium for a function to be callable from config. 
        Must start with _ and exist as a function in self.functions
        """
        return (key in dir(self.functions)) and key[0]=="_" and key[1]!="_"

    def key_writeable(self, key):
        """
        Criterium for a function to be a writer function callable from config. 
        Must end with _ and exist as a function in self.writeables.functions
        """
        return (key in dir(self.writeables)) and key[-1]=="_" and key[-2]!="_"

    def get_callables(self):
        """Return a list of callable functions in self.functions"""
        return [f for f in dir(self.functions) if self.key_callable(f)]
    
    def get_writeables(self):
        """Return a list of writeable functions in self.writeables"""
        return [f for f in dir(self.writeables) if self.key_writeable(f)]
    
    def get_callable_signature(self, func_name):
        """Return the signature of a callable function"""
        return inspect.signature(getattr(self.functions, func_name))
    
    def get_writeable_signature(self, func_name):
        """Return the signature of a writeable function"""
        return inspect.signature(getattr(self.writeables, func_name))
    
    def get_callable_return_type(self, func_name):
        """DEPRECIATED: Return the return type of a callable function"""
        return inspect.getfullargspec(getattr(self.functions, func_name)).annotations.get("return", None)
    
    def get_writeable_return_type(self, func_name):
        """DEPRECTIATED: Return the return type of a writeable function"""
        return inspect.getfullargspec(getattr(self.writeables, func_name)).annotations.get("return", None)
    
    def get_callable_description(self, func_name):
        """Return the description of a callable function"""
        return inspect.getdoc(getattr(self.functions, func_name))
    
    def get_writeable_description(self, func_name):
        """Return the description of a writeable function"""
        return inspect.getdoc(getattr(self.writeables, func_name))
    
    def trimargs(self, func):
        """Returns a list of arguments that can be passed to func."""    

        print("Trimming args for:", func.__name__)

        # get function arguments
        try:
            args = inspect.getfullargspec(func).args
        except:
            args = inspect.getfullargspec(func).args

        # store evaluated args in iargs
        iargs = {}
        for arg in args:
            if arg == 'self':
                continue
            if arg == 'data':
                continue

            # look in self.config (the variable store) and append only those args that have a definite value
            if hasattr(self.config, arg):
                iargs[arg] = getattr(self.config, arg)
            else:
                print("[WARNING] No", arg, "defined in config. Skipping.")

        # return args that can be passed to func.
        return iargs
    
    def val_data(self, value: str):
        """
        Check if value corresponds to an escaped callable. 
        If so, we can return the value as is. 
        Otherwise, we need to evaluate the value.
        """
        match value:
            case str():
                esc = regex.return_escapable_variables(value)
                if len(esc) == 1 and self.key_callable(esc[0]): return True
                else: return False
            case _:
                return False

    @add_error("Value Error. One of your values is not a string, bool, int, or float.", 475)
    def set_function_attribute(self, key, value):
        """Set a function as an attribute in self.config"""
        print(
            "Setting:", key, 
              "-->", type(value).__name__ + ":", 
              self.functions.censor(json.dumps(value))
              )
        
        self.config.__setattr__(key, value)    

    @add_error(f"Error evaluating function spec. Check your syntax.", 471)
    def evaluate(self,
                 key,
                 value,
                 path=[],
                 in_function_call: bool=False
                 ):
        """
        DFS on each configuration key.
        Initializes (key, value) pairs as class attributes on self.config. 
        Callable functions must be designated with _<function_name> in config. 
        BE CAREFUL when adding functions in case you're exposing config to UI in production. 
        Config can execute ANY function in self.functions = Callables().
        """

        # traverse dict recursively, while keeping track of path
        match value:
            case dict():

                # Ouch! what to do here... 
                # we absolutely need this for our auto-flatten feature, 
                # but it seems inefficient to calculate the cross product of all values, 
                # if most database SDKs support bulk-uploads...
                value = list(flatten_dict(**{
                    k: self.evaluate(k, v, path + [k], in_function_call)
                    for k, v in value.items()
                }))

            case list():
                for index, item in enumerate(value):
                    if isinstance(item, dict):
                        for k, v in item.items():
                            self.evaluate(
                                    k, v, path + [index] + [k], in_function_call
                                    )

            case str():

                # locate all the {escaped} variables in the string
                variables = regex.return_escapable_variables(value)

                # loop over variables that need to be unpacked
                for variable in variables:

                    # if the variable is already defined in self.config, unpack it into a list of possible values.
                    if hasattr(self.config, variable):
                        value: list = self.unpack(value, variable)
                    
                    # otherwise, infer value(s) from dataobj.
                    # using path as a key
                    # and set to variable with specified name in config.
                    else:    
                        print("Traversing data with path:", path, "to find", variable, "- data:")
                        
                        extracted_data = self.locate_in_dict(path, self.data.data)
                        print("Type of extracted data:", str(type(extracted_data)))
                        
                        self.config.__setattr__(
                            variable, extracted_data
                            )
                        
            case bool() | int() | float():
                pass
            case _:
                print("[ERROR] value:", value, "type:", type(value))
                raise ValueError(
                    "Invalid value type in spec. Must be dict, list, str, bool, int, or float."
                    )

        # Define non-callable keys specified in config as attributes in self.config:
        self.set_function_attribute(key, value)

        # handle callables
        if self.key_callable(key):            
            # TODO: match function arguments with passed kwargs in self.config.<funcName>
            # We need to pass qargs in case we want to use top-level flags like debug, cache, etc.
            # qargs = self.trimargs(func)

            func = getattr(self.functions, key)
            iargs = getattr(self.config, key)

            # self.config.<funcName> is a dictionary of arguments now, to be passed to the function.
            # print("iargs", iargs)

            match iargs:
                case dict():
                    self.data = DataOBJ(
                        func=func,
                        callables_obj=self.functions,
                        **iargs
                        )
                case list():
                    # TODO: decide whether we want to permit some calls to fail.
                    self.data = DataOBJ(
                        data=[
                            j for i in iargs for j in DataOBJ(
                                func=func,
                                callables_obj=self.functions,
                                **i).data
                            ])
                
            self.set_function_attribute(key, self.data.data)
            # self.config.__setattr__(key, self.data.data)    
            # print("Setting:", key, "-->", type(self.data.data).__name__ + ":", self.functions.censor(json.dumps(self.data.data)))

            # after calling a function, we want our value (as defined in config) 
            # to be equivalent to the data in the DataOBJ.
            in_function_call = True
            path=[]

        # handle writeables
        if self.key_writeable(key):
            func = getattr(self.writeables, key)
            iargs = getattr(self.config, key)

            match iargs:
                case dict():
                    do = self.writeables.caller(func, **iargs)
                    
                    print(do)
                case list():
                    for i in iargs:
                        do = self.writeables.caller(func, **i)
        
                        print(do)
        
        return value


    def unpack(self, value: str | list, variable: str | list) -> list:
        """
        Returns the cross product between two str | list items, 
        replacing {escapable} parts of value with variables of the same key.
        Always returns list.
        """
        lst = []
        print("unpacking:", value, "with", variable)

        # for each value
        if isinstance(value, list):
            for v in value:
                lst += self.unpack(v, variable)

        # apply variable
        else:

            # access self.'variable' through var
            var = getattr(self.config, variable)
            
            if isinstance(var, list):
                for item in var:
                    try:
                        # TODO: NEEDS UNIT TEST
                        lst.append(item)
                    except:
                        raise SyntaxError("""Unable to replace variable with value""")
            else:
                try:
                    lst.append(value.replace(f'{{{variable}}}', var))
                except:
                    raise ValueError(f"variable {variable} could not be replaced with {var}")

        return lst

    @add_error("""
               Syntax Error: could not find non-secret variable. 
               If you use the brackets syntax '{name}', 
               you need to define a variable with key 'name' first.
               """, 471)
    def locate_in_dict(self, path: list, dictionary: dict):
        """Locates a value in a nested dictionary."""

        data = []

        if path == []: return dictionary
        if dictionary is None: return None

        print("path:", path, "type", str(type(dictionary)))
        if type(path[0]) == str: print(dictionary.keys())

        if len(path) == 1:
            print("needs handling I think")

        match path[0]:
            # if path is an integer, it cannot be other than that the value is a list.
            case int():

                # so we just want to keep traversing (this snippet also flattens (?))
                for item in dictionary:
                    res = self.locate_in_dict(path[1:], item)
                    if not isinstance(res, list): data.append(res)
                    else: data += res

                return data
            
            # if path is a string, it can be either a key or a variable.
            case str():
                esc_vars = regex.return_escapable_variables(path[0])

                # if esc_vars is not empty, we have a variable.
                if esc_vars != []:
                    
                    ls = []
                    for k, v in dictionary.items():
                        res = self.locate_in_dict(path[1:], v)    
                        
                        if isinstance(res, list):
                            pass
                        elif isinstance(res, dict):
                            res[esc_vars[0]] = k
                        elif isinstance(res, str):
                            print("res", res[:5], "\n")
                    
                        ls.append(res)
                    
                    return {esc_vars[0] + "s": ls} 
                
                # if esc_vars is empty, we have a key.
                elif esc_vars == []:
                    return self.locate_in_dict(path[1:], dictionary[path[0]])
                else:
                    raise SyntaxError(f"Something went wrong. Compare your data at at \n{path}")
