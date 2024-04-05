# system
import os
import inspect
import json
import time
import getpass
import requests

# data
from itertools import product
import csv
import hashlib
import uuid

# custom
from Connect import regex, parsing

# supabase-py
from gotrue import SyncMemoryStorage
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from storage3.types import CreateOrUpdateBucketOptions

# Default file size limit = 26MB
DEFAULT_FILE_SIZE_LIMIT = 26000000

class Supabase(Client):
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
        return create_client(self.url, self.key, options or self.options)

class AnyClient():
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
    def __init__(self, schema: str):
        super().__init__(
            os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY"), 
            schema
            )
        
class ServiceRoleClient(AnyClient):
    def __init__(self, schema: str):
        super().__init__( 
            self.get_service_role_key(), 
            schema
            )
        
    def get_service_role_key(self):
        return (
            os.environ.get("SUPABASE_SERVICE_ROLE")
        )
    

class Callables():
    """Class to define explicit methods callable from config"""
    def __init__(self, config=None, debug=False):
        self.config = config
        self.debug = debug
    
    def flatten_dict(self, **d):
        """Flatten a dictionary (one level)."""

        keys, values = zip(*d.items())
        for instance in product(*(x if isinstance(x, list) else [x] for x in values)):
            yield dict(list(zip(keys, instance)))
            
    def caller(self, func, **kwargs):
        """Flatten kwargs and call func on each instance. Return aggregate"""
        q = []
        for p in self.flatten_dict(**kwargs):
            # print("[CALLING]", func.__name__, "with parameters:", p)
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
        return value
    
    def _request(self, 
            url=None, 
            base_url=None, 
            headers=None, 
            method=None, 
            rel_url="", 
            auth=None, 
            session=None, 
            sleep=0,
            debug=False,
            ):
        """send a request with the specified parameters
        TODO: implement POST, PUT methods.
        """
        
        try:
            auth = (auth["user"], auth["password"]) if auth is not None else None
        except:
            raise SyntaxError("auth must be a dict with keys 'user' and 'password'")
        
        if url is None:
            if base_url is not None:
                url = base_url + rel_url
            else:
                raise SyntaxError("Both url and base_url undefined")
            
        if debug: print("Requesting:", url)
        
        if method is None:
            print("Warning: method not defined. defaulting to GET")
            method = "GET"
        
        if headers is None:
            print("Warning: headers not set. defaulting to Content-type: application/json.")
            headers = {
                "Content-Type": "application/json"
            }

        # If there is no session, or if session config has changed in the meantime, create a new session.
        if session is None or (
            session.auth != auth or 
            session.headers != headers
            ):
            session = self.new_session(auth, headers)

        # sleep if specified
        if sleep > 0:
            time.sleep(sleep)

        if method == "GET":
            res = session.get(url)
        elif method == "POST":
            res = session.post(url)
        else:
            raise ValueError(f"{method} needs implementation")
        
        if debug: 
            print(
                "\n Response Headers: \n", 
                res.headers
                )
            with open("./debug.html", "w") as f:
                f.write(res.text)
        
        if headers["Content-Type"] == "application/xml":
            return parsing.parse_xml(res.text)
        elif headers["Content-Type"] == "application/json":
            return res.json()
        elif headers["Content-Type"] == "text/csv":
            r = csv.DictReader(res.text.splitlines())
            return {"response": [q for q in r]}
        elif headers["Content-Type"] == "application/html":
            # the xml parser also works for html
            return parsing.parse_html(res.text)
        else:
            return res.json()
        
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

    def _test(self, base_url, rel_url="", timeout=0):
        url = base_url + rel_url
        return(url)


# TODO: figure out kwargs situation. (?)
class Config():
    """Class used as target for configuration settings. Define special methods here."""
    def __init__(self, **kwargs):
        
        # initialize config with any passed kwargs   
        for k in kwargs.keys():
            self.__setattr__(k, kwargs[k])
    
    def add_attributes(self, **kwargs):
        """Add attributes to config"""
        for k in kwargs.keys():
            self.__setattr__(k, kwargs[k])

class Writeables():
    """Class to define explicit methods callable from config"""
    def __init__(self, config=None, debug=False):
        self.config = config
        self.debug = debug
        self.decoded = self.config.decoded or None
        self.metadata = self.config.metadata or None

    def toSupa_(self, data, table: str, overwrite: bool=False):
        """Upsert data to supabase table. Needs implementation."""
        print("toSupa")
        if self.decoded is None: raise ValueError("invalid session")
        client = AnyClient(self.decoded.token, schema="etl").client
        user_tld = client.from_("organization").select("tld").single().execute().data["tld"]
        
        print("user_tld", user_tld)
        newclient = AnyClient(self.decoded.token, schema=user_tld).client
        
        try:
            res = newclient.from_("metadata").insert({
                "connectionId": self.metadata["connectionId"] or None,
                "userId": self.decoded.sub or None,
                "runId": self.metadata["runId"] or None
                }, returning="representation").execute()
            
            print("[DATA]", data[0])

            print("[META]", res.data)
            tables = newclient.from_(table).insert({
                "metaId": res.data[0]["id"],
                "html": data[0]
                }).execute()
        except:
            print("Table does not exist. Creating...")
            print("TODO: implement type-safe RPC call to create table.")
            # tables = newclient.rpc("create_table", {"name": table})

    def toStorage_(self, data, bucket: str, folder: str, filename: str, overwrite: bool):
        """Upsert data to supabase table. Needs implementation."""

        if self.decoded is None: raise ValueError("invalid session")
        client = AnyClient(self.decoded.token, schema="storage").client
        print("client", client)

        raise ValueError("Not implemented")
        if bucket in client.storage.list_buckets():
            print("bucket exists")
        else:
            print(f"bucket '{bucket}' does not exist. creating...")
            id = uuid.uuid4().__str__()

            res = client.storage.create_bucket(
                id, 
                bucket,
                CreateOrUpdateBucketOptions(
                    public=False,
                    file_size_limit=DEFAULT_FILE_SIZE_LIMIT,
                    allowed_mime_types=[
                        "application/json", 
                        "application/xml", 
                        "text/csv", 
                        "application/html",
                        "application/pdf",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        "application/vnd.ms-powerpoint",
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        "application/vnd.visio",
                        "application/vnd.ms-excel",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",    
                        "application/msword"
                        "image/*",
                        "video/*",
                        "audio/*",
                        "text/*",
                        ]))
        print(res)
    
    def toFile_(self, data, path):
        """Write data that is currently cached in self.config.data to file. Disabled in production"""
        raise ValueError("File storage is disabled")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        return("asd")
    
    def caller(self, func, data, **kwargs):
        """Flatten kwargs and call func on each instance. Return aggregate"""
        return func(data, **kwargs)

class DataOBJ():
    """Data Object.
    -> Used for logging raw response data
    """
    def __init__(self, func, callables_obj, **kwargs):
        self.func = func
        self.kwargs = kwargs
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
        lines = json.dumps(self.data, indent=2).split('\n')
        res = '\n'.join(lines[:10]) + "\n...\n" + '\n'.join(lines[-10:]) if len(lines) > 20 else '\n'.join(lines)
        return res 

    def save_snapshot(self, path):
        with open(path, "w") as f:
            json.dump(self.data, f)

    def path_exists(self):
        return os.path.exists(self.path)
    
    def to_file_path(self):
        return self.hash_string(
            regex.list_to_file_path([self.func.__name__] + [self.censor(str(val)) for val in self.kwargs.values()])
        ) + ".json"
        
    def hash_string(self, string):
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
        """Criterium for a function to be callable from config. Must start with _ and exist as a function in self.functions"""
        return (key in dir(self.functions)) and key[0]=="_"

    def value_writeable(self, value):
        """Criterium for a function to be a writer function callable from config. Must end with _ and exist as a function in self.writeables.functions"""
        return (value in dir(self.writeables)) and value[-1]=="_"

    def trimargs(self, func):
        """Returns a list of arguments that can be passed to func."""    

        print("Trimming args for:", func.__name__)
        
        # get function arguments
        try:
            args = inspect.getfullargspec(func).args
        except:
            args = inspect.getargspec(func).args


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
        BE CAREFUL when adding functions in case you're exposing config to UI in production. Config can execute ANY function in self.functions = Callables().
        """

        # call function if callable, store result in self.config (GLOBAL data source for each action).
        if self.key_callable(key):
            func = getattr(self.functions, key)
            iargs = self.trimargs(func)

            self.data = DataOBJ(func, self.functions, **iargs)
        
            # after calling a function, we want our value (as defined in config) 
            # to be isomorphic to the data in the DataOBJ.
            in_function_call = True
            path=[]

        # traverse dict recursively, while keeping track of path
        match value:
            case dict():
                for k, v in value.items():
                    q = self.evaluate(k, v, path + [k], in_function_call)
                    
                    # updated nested dictionary values
                    value[k] = q[0] if isinstance(q, list) else q
            case list():
                for index, item in enumerate(value):
                    if isinstance(item, dict):
                        for k, v in item.items():
                            self.evaluate(
                                    k, v, path + [index] + [k], in_function_call
                                    )
                               
            case str():
                
                # TODO: abstract extracted_data
                # value is the function name in Writeables here if true.

                if self.value_writeable(value):
                    func = getattr(self.writeables, value)
                    
                    # extracted_data is the data we need to store.
                    extracted_data = self.locate_in_dict(path, getattr(self.config, regex.return_escapable_variables(key)[0]))
                    
                    print("func:", func)
                    iargs = self.trimargs(func)
                    print(iargs)
                    
                    do = self.writeables.caller(func, extracted_data, **iargs)
                
                else:

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
                            
                            # newdata = copy.copy(self.data.data)
                            extracted_data = self.locate_in_dict(path, self.data.data)
                            print("Type of extracted data:", str(type(extracted_data)))
                            
                            self.config.__setattr__(
                                variable, extracted_data
                                )

        
        # Define non-callable keys specified in config as attributes in self.config:
        if not in_function_call: 
            self.config.__setattr__(key, value)    
            print("Setting:", key, "-->", type(value).__name__ + ":", self.functions.censor(json.dumps(value)))
            
        return value

    
    def unpack(self, value: str | list, variable: str | list) -> list:
        """
        Returns the cross product between two str | list items, replacing {escapable} parts of value with variables of the same key.
        Always returns list.
        """
        lst = []

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
                        lst.append(value.replace(f'{{{variable}}}', item))
                    except:
                        raise SyntaxError("--> is the variable you're trying to unpack into surely undefined? Try prepending del object.{variable} before your run()")
            else:
                try:
                    lst.append(value.replace(f'{{{variable}}}', var))
                except:
                    raise ValueError(f"variable {variable} could not be replaced with {var}")
                
        return lst

    def locate_in_dict(self, path, dictionary):
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
                        # cascade key to value with new key specified in config file (here path[0])
                    
                        ls.append(res)
                    
                    return {esc_vars[0] + "s": ls} 
                
                # if esc_vars is empty, we have a key.
                elif esc_vars == []:
                    
                    # TODO: implement error handling try:
                    return self.locate_in_dict(path[1:], dictionary[path[0]])
                    # except:
                        # raise SyntaxError(f"Invalid path. Config is not compatible with output. Compare your data at at \n{path}")

                else:
                    raise SyntaxError(f"Oops! something went wrong. Probably a bug! Compare your data at at \n{path}")