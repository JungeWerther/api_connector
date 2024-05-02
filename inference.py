# The idea behind this file is to automate schema inference from a list of dictionaries
# It's working well for almost all cases, except when the type 
# of a key is a dictionary in one case, and some other type in another case.
# then, we'll return Any. --> such data is structurally incoherent,
# and needs manual cleaning!
# 
# Ideally we also want:
# DONE: to support dynamic keys. Using the collapse_dynamic flag, we can collapse
# --> I think the best way is to vectorize all keynames.
# TODO: lists nested in lists (?) srsly? who the hell designs apis like that?
# DONE: type resolution (except directly nested lists)
# TODO: add regex-based castability checks i.e. 
        # "1" -> Castable(int)
        # "1.0" -> Castable(number)
        # "1.0.0" -> str
        # "22-04-2021" -> Castable(datetime)
    # then if we reduce the type to the largest denominator,
    # we can cast the values to the correct type.
    # Which means we can auto-infer database schemas.




from typing import Set, Type, List, Dict, Any, Union, Optional, get_type_hints, get_origin, get_args, TypeVar, Generic
from pydantic import BaseModel
import json
from helpers import flatten_dict
from functools import reduce, lru_cache


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
                },
                {
                    "z": 1.0, 
                    "q": "22-04-2022"
                
                }], 
            "c": True
        }
    }
]
    
class ComplexType():
    def __init__(self, structure=None):
        if structure is None:
            structure = {}
        
        # Structure is a dict mapping keys to either types 
        # or ComplexType instances (nested dictionaries)
        self.structure = structure
    
    def __repr__(self):
        return json.dumps(
            self.structure,
            indent=4,
            default=lambda x: str(x) if not isinstance(x, ComplexType) else x.structure
            )
    
    def update_with(self, other):
        """Recursively update this type with another, performing union operations at each level."""
        
        for key, value in other.structure.items():
            if key in self.structure:
                if isinstance(self.structure[key], ComplexType) and isinstance(value, ComplexType):
                    self.structure[key].update_with(value)
                else:
                    self.structure[key] = self.union_types(self.structure[key], value)
            else:
                self.structure[key] = value

    def items(self):
        return self.structure.items()

    def values(self):
        return self.structure.values()
    
    @staticmethod
    def is_ext_subclass(type1: type, type2: type) -> bool:
        """Check if type1 is a subclass of type2, including external subclasses."""
        
        try:
            if issubclass(type1, type2) or type1 == int and type2 == float:
                return type2
        except:
            pass
    
    @staticmethod
    def coalesce_types(type1: type, type2: type) -> type:
        """Coalesce two non-generic types"""

        if ComplexType.is_ext_subclass(type1, type2):
            return type2
        if ComplexType.is_ext_subclass(type2, type1):
            return type1
        
        return type1 | type2  
    
    @staticmethod
    @lru_cache
    def union_types(type1: type, type2: type) -> type:
        """Union two types, which could be basic types or ComplexType instances."""

        # note len(types) > 1. Also no type has Union as origin.
        if type1 == type2: return type1

        types = get_args(type1 | type2) #all types
        merged_type = ComplexType.merge_types(*types)
        return merged_type
        
    
    
    @staticmethod
    def flatten_types(types: tuple[type]) -> set[type]:
        """Flatten types, including nested Unions, into a set of unique types."""
        
        flat_types = set()
        for t in types:
            if get_origin(t) is Union:
                flat_types.update(
                    ComplexType.flatten_types(
                        get_args(t)
                        ))
            else:
                flat_types.add(t)
        return flat_types
    
    @staticmethod
    def merge_parameterized_types(types: set[type]) -> list[type]:
        """Merge parameterized types by combining their type arguments."""
        
        origin_args_map = {}
        for t in types:
            origin = get_origin(t)
            if origin not in origin_args_map:
                origin_args_map[origin] = []
            origin_args_map[origin].extend(
                get_args(t)
                )
        
        merged_types = []
        for origin, args in origin_args_map.items():
            flat_args = ComplexType.flatten_types(args)
            merged_types.append(
                ComplexType.union_helper(flat_args)
                )
           
        return merged_types

    @staticmethod
    def union_helper(sequence: list[type] | set[type]) -> type:
        """Helper function for unioning a sequence of types."""
        if len(sequence) > 1:
            return reduce(lambda x, y: ComplexType.coalesce_types(x,y), sequence)
        return next(iter(sequence))
    
    @staticmethod
    @lru_cache
    def merge_types(*types: tuple[type]) -> type:
        """Merge given types into a unified type representation."""
        
        flat_types = ComplexType.flatten_types(types)
        non_param_types = {t for t in flat_types if get_origin(t) is None}
        param_types = {t for t in flat_types if get_origin(t) is not None}
        
        # Merge non-parameterized types
        if non_param_types:
            merged_non_param = ComplexType.union_helper(non_param_types)
        else:
            merged_non_param = None
        
        # Merge parameterized types
        merged_param = ComplexType.merge_parameterized_types(param_types)
        
        # Combine all merged types
        all_merged = [t for t in [merged_non_param] + merged_param if t is not None]
        return ComplexType.union_helper(all_merged)

class Hypothesis():
    def __init__(self, v=None, collapse_dynamic=False):
        self.current = ComplexType()
        if v is not None:
            self.update(v)
        if collapse_dynamic:
            self.collapse_nested_dicts()
    
    def handle_kv(self, k, v):
        if k not in self.current.structure:
                    self.current.structure[k] = ComplexType()

        if not isinstance(
            self.current.structure[k], 
            ComplexType
            ):
            self.current.structure[k] = Any
        
        else:
            # Recursively update the nested dictionary
            self.current.structure[k].update_with(Hypothesis(v).current)
        
    def collapse_nested_dicts(self):
        """Collapse nested dictionaries into a list of dictionaries.
        BUG: converts str -> type because the type of a type is type.
        Needs fixing in hypothesis logic (ignore casing type to type but return id)
        """
        def transform(item):
            # Base case for recursion: if item is not a dictionary, return it as is
            
            if isinstance(item, list):
                return [transform(i) for i in item]
            
            if not isinstance(item, dict | ComplexType):
                return item
            
            # Check if all values in the dictionary are dictionaries themselves
            if all(isinstance(v, dict | ComplexType) for v in item.values()):
                # Transform the dictionary into a list of its values (nested dictionaries)
                h = Hypothesis()
                for v in item.values():
                    h.update(v)
                
                # h.current.structure.update({"ps_key__": str})
                return {"{ps_key__}": h.current}
            else:
                # If not all values are dictionaries, recursively apply transform to each value
                return {k: transform(v) for k, v in item.items()}
    
        # Start the transformation process from the root of the structure
        self.current.structure = transform(self.current.structure)
    
    def handle_listitem(self, k, v):
        list_hypothesis = Hypothesis()
        list_types = []
        for elem in v:
            if isinstance(elem, dict):
                list_hypothesis.update(elem)
            else:
                list_types.append(type(elem))
        
        no_hyp = list_hypothesis.current.structure == {}
        no_list = list_types == []
        
        if no_hyp and no_list:
            print(list_hypothesis.current, list_types)
            list_type_representation = [Any]
        elif no_hyp:
            list_type_representation = list[reduce(
                lambda x, y: ComplexType.union_types(x, y),
                list_types
            )] 

        elif no_list:
            list_type_representation = [list_hypothesis.current]
        else: 
            list_type_representation = (
            list_hypothesis.current.union_types(
                list_types, 
                list_hypothesis.current
            ))

        if k in self.current.structure:
            # If the key already exists, union the new types with the existing ones
            self.current.structure[k] = self.current.union_types(self.current.structure[k], list_type_representation)

        else:
            # If the key doesn't exist, simply set the types
            self.current.structure[k] = list_type_representation

    def update(self, item: dict, current_complex_type=None):
        
        # first, determine the union of the current schema and the new item
        if current_complex_type is None:
            current_complex_type = self.current

        for k, v in item.items():
            if isinstance(v, dict):
                self.handle_kv(k, v)
                
            elif isinstance(v, list):
                self.handle_listitem(k, v)
            
            else:
                new_type = type(v)
                if k in self.current.structure:
                    self.current.structure[k] = self.current.union_types(
                        self.current.structure[k], 
                        new_type
                        )
                else:
                    self.current.structure[k] = new_type

      
if __name__ == "__main__":


    # hypothesis = Hypothesis()
    # hypothesis.update({"name": "Alice", "age": 30, "address": {"street": "123 Main St", "city": "Anytown"}})
    # print("[HYPOTHESIS]", hypothesis.current)
    # hypothesis.update({"name": "Bob", "age": "unknown", "address": {"street": 1, "city": "Othertown", "zip": 12345}})
    # print("[HYPOTHESIS]", hypothesis.current)

    # TODO: implement proper unit test framework.
    hypothesis = Hypothesis()
    for item in input:
        hypothesis.update(item)
        print("[HYPOTHESIS]", hypothesis.current)

    hypothesis = Hypothesis({
        "data": [{
            "a1": 1,
            "a2": "c1"
        },
        {
            "a1": "b2",
            "a3": "c2"
        }
    ]
    })

    print("[HYPOTHESIS]", hypothesis.current)

    h = Hypothesis(
        {"results":[{"name":"WEBHOOKS","features":{"Webhooks":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/webhooks/v3","stage":"LATEST"}}},{"name":"EVENTS","features":{"Events":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/events/v3/events","stage":"DEVELOPER_PREVIEW"}}},{"name":"COMMUNICATION-PREFERENCES","features":{"Communications-status":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/communication-preferences/v3","stage":"DEVELOPER_PREVIEW"}}},{"name":"AUTH","features":{"Oauth":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/oauth/v1","stage":"LATEST"}}},{"name":"BUSINESS-UNITS","features":{"Business Units":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/business-units/v3","stage":"STABLE"}}},{"name":"ANALYTICS","features":{"Custom Behavioral Events":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/events/v3/send","stage":"DEVELOPER_PREVIEW"}}},{"name":"CMS","features":{"Domains":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/cms/v3/domains","stage":"DEVELOPER_PREVIEW"},"Source Code":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/cms/v3/source-code","stage":"DEVELOPER_PREVIEW"},"Blog-posts":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/cms/v3/blogs/blog-posts","stage":"DEVELOPER_PREVIEW"},"Authors":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/cms/v3/blogs/authors","stage":"DEVELOPER_PREVIEW"},"Url-redirects":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/cms/v3/url-redirects","stage":"DEVELOPER_PREVIEW"},"Performance":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/cms/v3/performance","stage":"DEVELOPER_PREVIEW"},"Hubdb":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/cms/v3/hubdb","stage":"DEVELOPER_PREVIEW"},"Tags":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/cms/v3/blogs/tags","stage":"DEVELOPER_PREVIEW"},"Audit-logs":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/cms/v3/audit-logs","stage":"DEVELOPER_PREVIEW"},"Site-search":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/cms/v3/site-search","stage":"DEVELOPER_PREVIEW"}}},{"name":"MARKETING","features":{"Marketing-events-beta":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/marketing/v3/marketing-events-beta","stage":"LATEST"},"Transactional":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/marketing/v3/transactional","stage":"LATEST"}}},{"name":"AUTOMATION","features":{"Actions":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/automation/v4/actions","stage":"LATEST"}}},{"name":"CONVERSATIONS","features":{"Visitor Identification":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/conversations/v3/visitor-identification","stage":"LATEST"}}},{"name":"CRM","features":{"Crm Extensions":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/extensions/sales-objects/v1/object-types","stage":"LATEST"},"Products":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/objects/products","stage":"LATEST"},"Crm Associations":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v4/associations","stage":"STABLE"},"Pipelines":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/pipelines","stage":"LATEST"},"Accounting":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/extensions/accounting","stage":"LATEST"},"Companies":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/objects/companies","stage":"LATEST"},"Calling":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/extensions/calling","stage":"LATEST"},"Quotes":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/objects/quotes","stage":"LATEST"},"Deals":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/objects/deals","stage":"LATEST"},"Imports":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/imports","stage":"LATEST"},"Schemas":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/schemas","stage":"LATEST"},"Properties":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/properties","stage":"LATEST"},"Associations":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/associations","stage":"LATEST"},"Owners":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/owners","stage":"LATEST"},"Timeline":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/timeline","stage":"LATEST"},"Contacts":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/objects/contacts","stage":"LATEST"},"Feedback Submissions":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/objects/feedback_submissions","stage":"DEVELOPER_PREVIEW"},"Objects":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/objects","stage":"LATEST"},"Videoconferencing":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/extensions/videoconferencing","stage":"LATEST"},"Tickets":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/objects/tickets","stage":"LATEST"},"Line Items":{"openAPI":"https://api.hubspot.com/api-catalog-public/v1/apis/crm/v3/objects/line_items","stage":"LATEST"}}}]}
        , collapse_dynamic=True
        )
    print("[HYPOTHESIS]", h.current)
