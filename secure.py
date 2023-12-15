import getpass
import requests
import re
import xmltodict
import json
import inspect
import time

# TODO: migrate attributes to a SEPARATE UNIQUELY INSTANTIATED object or reserve a namespace. 
# Otherwise we get BIG PROBLEMS if we want to scale and some user accidently uses the key prop in api definition, for instance!

# TODO: get rid of global scope variable self.__dictionary in favour of __dictionary in the local scope of each VAR (attribute).

class Connection():
    """Connection Class"""

    def __init__(self, config=None, key=None):
        if key == None: 
            self.key = self.get_key()
        else:
            self.key = key

        self.__config = config
        self.__dictionary = None
        self.debug = True

    def get_key(self):
        """Get the key from the user"""
        
        key = getpass.getpass(prompt = "Enter your key: ")
        return key
    
    def run(self):
        
        res = self.traverse_config(self.__config)
        return res

    def traverse_config(self, pointer):
        """Traverses the passed configuration"""

        for key, value in pointer.items():
            self.evaluate(key, value)
        
    def evaluate(self, key, value, path=[], ignore=False):
        """Initializes (key, value) pairs as class attributes. Callable functions must be designated with _<function_name> in config. ABSOLUTELY BE CAREFUL"""
        
        # only call keys that are designated as functions with _ and exist as class methods.
        key_callable = (key in dir(self)) and key[0]=="_"

        # print("\npreEvaluating:", (key, value), "path:", path, "callable:", key_callable, "key[0]:", key[0], "dir_self", (key in dir(self)))

        # call function if callable, store result in self.__dictionary (GLOBAL data source for each action).
        if key_callable:
            func = getattr(self, key)
            # print(func)
            args = inspect.getargspec(func).args
            
            # store evaluated args in iargs
            iargs = []
            for arg in args:
                if arg == 'self':
                    pass
                if hasattr(self, arg):
                    iargs.append(getattr(self, arg))

            self.__dictionary = self.caller(func, iargs)

            # fetch data to self.__dictionary
            # self.__dictionary = [func(iargs)]
            
            # print(*iargs)
            # print([q for v in iargs for q in v])
            # self.__dictionary = [func(*ar)]

            ignore = True
            path=[]

        # traverse dict recursively, while keeping track of path
        if isinstance(value, dict):
            for k, v in value.items():
                self.evaluate(k, v, path + [k], ignore)
        if isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    for k, v in item.items():
                        self.evaluate(k, v, path + [index] + [k], ignore)        
        
        # unpack variables if value is a string
        if isinstance(value, str):
            
            # locate all the {escaped} variables in the string
            variables = re.findall(r'\{(.+?)\}', value)
            
            # debug statement
            # print("variables", variables)

            # loop over variables that need to be unpacked
            for variable in variables:
                
                # if the variable is already an attribute, unpack it into value.
                if hasattr(self, variable):
                    value = self.unpack(value, variable)
                        
                # otherwise, initialize attribute using the fetched data stored in self.__dictionary, using path as a key
                else:      
                    self.__setattr__(
                        variable, 
                        self.locate_in_dict(path, self.__dictionary)
                        )

        if not ignore: self.__setattr__(key, value)     

        # print("\nEvaluated:", (key, value), "path:", path, "callable:", key_callable, "key_in_dir", (key in dir(self)))
        # print("\nEvaluated:", (key), "\ndict:", self.__dict__)
    
    def caller(self, func, iargs):
        
        barg = iargs[0]
        if isinstance(barg, list):
            ls = [(ar,) for ar in barg]
        else:
            ls = [(barg,)]

        for arg in iargs[1:]:
            if isinstance(arg, list):
                ls = [(item + (a,)) for item in ls for a in arg]
            else:
                ls = [(item + (arg,)) for item in ls]
        
        print(iargs)

        if len(ls) == 1:
            result = func(*ls[0])
        else:
            result = [func(*i) for i in ls]
        
        return result

    
    def unpack(self, value: str | list, variable: str | list) -> list:
        
        lst = []
        
        if isinstance(value, list):
            for v in value:
                lst += self.unpack(v, variable)
        else:
            # access self.'variable' through var
            var = getattr(self, variable)

            if isinstance(var, list):
                for item in var:
                    lst.append(value.replace(f'{{{variable}}}', item))
            else:
                lst.append(value.replace(f'{{{variable}}}', var))
            
        return lst

    def locate_in_dict(self, path, dictionary):
        """Locates a value in a nested dictionary"""

        if path == []: return dictionary
        if dictionary is None: return None

        try:
            nextpath = dictionary[path[0]]
        except:
            raise SyntaxError(f"Invalid path. Config doesn't match output at \n{dictionary}")
        
        if len(path) == 1: 
          return nextpath  
        elif isinstance(path[0], int):
            lst = []
            for item in dictionary:
                res = self.locate_in_dict(path[1:], item)
                if not isinstance(res, list): lst.append(res)
                else: lst += res
            return lst
        else:
            return self.locate_in_dict(path[1:], nextpath)
        
    def _request(self, base_url, rel_url, headers, method, auth=None, session=None, timeout=0):
        
        if session is None or session.auth != auth or session.headers != headers:
            session = requests.Session()
            session.auth = auth
            session.headers.update(headers)
            self.session = session
        
        time.sleep(timeout)

        if method == "GET":
            res = session.get(
                url = base_url + rel_url
            )

            if self.debug == True: print(res.headers)
            
            if headers["Content-Type"] == "application/xml":
                self.xml = res.text
                # if self.debug: print(self.xml)
                try:
                    obj = xmltodict.parse(res.text)
                except:
                    raise ValueError("response is empty")
                return obj
            
            if headers["Content-Type"] == "application/json":
                self.json = res.json()
                obj = self.json
                # if self.debug: print(self.json)
                return obj
            
        else:
            raise SyntaxError(f"{method} needs implementation")
    
    def _fromFile(self, path):
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

    def _test(self, base_url, rel_url, timeout=0):
        url = base_url + rel_url
        return(url)
    

    
    # class Request():
    #     """A Request"""
    #     def __init__(self, base_url, rel_url, method, )