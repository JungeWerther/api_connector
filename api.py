import regex
import json
from dotenv import load_dotenv
import os
import inspect
from connection import Supabase, Connection
import regex
from datetime import date, time, timedelta, datetime
from glom import glom, Coalesce, T, S, Flatten

# TODO: implement caching as variable

load_dotenv()

class Wrapper():
    def __init__(self, start=None, end=None, mode=None):
        pass
        
class APIConfig():
    """
    Class that loads and apiconfig file, then starts a connection.
    """
    
    def __init__(self, path: str, config="apiconfig.json", key=None, **kwargs) -> dict:
        self.path = path
        self.config = self.load_config(config)
        self.connection = Connection(self.config, key)
        self.connection.config.add_attributes(**kwargs)
    
    def load_config(self, config):
        with open(config, "r") as f:
            return self.extract_config(json.load(f))

    def extract_config(self, config):
        for source in config["sources"]:
            if source["name"] is not None:
                if self.path == source["name"]:
                    return source
        for source in config["sources"]:
            if source["base_url"] is not None:
                if regex.have_same_base_url(self.path, source["base_url"]):
                    return source
            else:
                raise ValueError("base_url must be defined")
            
        raise ValueError("no config found for path " + self.path)
    

class Jsonic():
    def __init__(self):
        pass

    def __repr__(self):
        return json.dumps(self.obj, indent=4)
    
    def json(self):
        """Quick and dirty way to get a json representation of the object."""
        repr = {}
        args = inspect.getargspec(self.__init__).args
        for arg in args:
            if hasattr(self, arg):
                repr[arg] = getattr(self, arg)
        
        return repr
        
class Basket(Jsonic):
    def __init__(self, id, basket_date):
        self.id = id
        self.basket_date = basket_date


class Item(Jsonic):
    def __init__(self, id, basket_id, bo_type, bo_id, badge_type_id, booking_price, sales_price, sales_vat, prepaid_badge_amount, promo_discount, scanned_at):
        self.id = id
        self.basket_id = basket_id
        self.bo_type = bo_type
        self.bo_id = bo_id
        self.badge_type_id = badge_type_id
        self.booking_price = booking_price
        self.sales_price = sales_price
        self.sales_vat = sales_vat
        self.prepaid_badge_amount = prepaid_badge_amount
        self.promo_discount = promo_discount
        self.scanned_at = scanned_at

class Detail(Jsonic):
    def __init__(self, detail_id, item_id, name, amount, vat_pct, ledger):
        self.detail_id = detail_id
        self.item_id = item_id
        self.name = name
        self.amount = amount
        self.vat_pct = vat_pct
        self.ledger = ledger

class Transaction(Jsonic):
    def __init__(self, id, basket_id, created_at, payment_type_id, payment_type_name, psp_reference, till_id, selling_point_name):
        self.id = id
        self.basket_id = basket_id
        self.created_at = created_at
        self.payment_type_id = payment_type_id
        self.payment_type_name = payment_type_name
        self.psp_reference = None
        self.till_id = till_id
        self.selling_point_name = selling_point_name

def get_last_updated(schema):
    temp_client = Supabase()
    temp_client.options.schema = "public"
    data, _ = temp_client.table("updates").select("updated_at").eq("schema", schema).execute()
    print(data)
    if len(data[1]) > 0:
        return data[1][0]["updated_at"]
    else:
        # raise ValueError("no last updated found for " + schema)
        print(f"Warning: no last_updated found for {schema}")
    
class SupaSchema():
    def __init__(self, schema="public", last_updated=None):
        self.schema = schema
        
        self.client = Supabase()

        if last_updated is None:
            self.last_updated = get_last_updated(self.schema) if schema != "public" else None
        else:
            self.last_updated = last_updated

        self.client.options.schema = self.schema
    
    def return_table_columns(self, table):
        """Returns a list of column names for a given table."""
        assert self.schema == "information_schema" 
        data, _ = self.client.table("columns").select("*").eq("table_schema", self.schema).eq("table_name", table).execute()
        return data
        
    
    def upsert(self, table, data):
        """Upsert data into table. If id is specified, it will be used to check for duplicates."""

        print("upserting into", table, "in", self.client.options.schema, "with", len(data), "items")

        seen = set()
        unique = []
        for datum in data:

            try:
                json_datum = datum.json()
            except:
                json_datum = datum

            # print("[JSON_DATUM]", json_datum)
            if all(key in json_datum.keys() for key in ["rel_id", "bill_id"]):
                if (json_datum["rel_id"], json_datum["bill_id"]) not in seen:
                    seen.add((json_datum["rel_id"], json_datum["bill_id"]))
                    unique.append(json_datum)
                else:
                    print("duplicate", json_datum)
                    continue

            elif all(key in json_datum.keys() for key in ["article_id", "id"]):
                if (json_datum["article_id"], json_datum["id"]) not in seen:
                    seen.add((json_datum["article_id"], json_datum["id"]))
                    unique.append(json_datum)
                else:
                    print("duplicate", json_datum)
                    continue

            # if the id gets specified, it must be unique
            elif "id" in json_datum.keys():
                if json_datum["id"] not in seen:
                    seen.add(json_datum["id"])
                    unique.append(json_datum)
                else:
                    print("duplicate", json_datum)
                    continue
            
            # case JL
            elif "detail_id" in json_datum.keys() and "item_id" in json_datum.keys():
                if (json_datum["detail_id"], json_datum["item_id"]) not in seen:
                    seen.add((json_datum["detail_id"], json_datum["item_id"]))
                    unique.append(json_datum)
                else:
                    print("duplicate", json_datum)
                    continue
            
            # here we require that id is generated by db
            else:
                unique.append(json_datum)

        return self.client.table(table).upsert(unique).execute()

class Updater():
    def __init__(self, schema, date):
        self.record = schema
        self.schema = SupaSchema()
        self.date = date
        self.row = self.format_record()
        self.update()

    def update(self):
        self.schema.client.table("updates").upsert(self.row).execute()

    def format_record(self):
        match self.record:
            case "mice":
                return {
                    "name": "Mice",
                    "description": "Mice Operations. Zaalverhuur en catering.",
                    "schema": "mice_operations",
                    "updated_at": self.date
                }
            case "jewellabs":
                return {
                    "name": "Jewellabs",
                    "description": "Jewellabs. Ticketing.",
                    "schema": "jewellabs",
                    "updated_at": self.date
                }
            case "untill":
                return {
                    "name": "Untill",
                    "description": "Untill. Kassasystem.",
                    "schema": "untill",
                    "updated_at": self.date
                }
            case "nostradamus":
                return {
                    "name": "Nostradamus",
                    "description": "Nostradamus. Personeelsadministratie.",
                    "schema": "nostradamus",
                    "updated_at": self.date
                }
            case _:
                raise ValueError("no record found for " + self.record)

class Nostradamus():
    """
    mode: 
        "departments" | 
        "teams" | 
        "staff" | 
        "hours" | 
        "freedays" | 
        "planning" | 
        "turnover (not active)" | 
        "functions" | 
        "project (not active)" | 
        "salary"
    """
    def __init__(self, start=None, end=None, mode="hours"):
        self.schema = SupaSchema("nostradamus")
        self.client = self.schema.client
        self.start = start
        self.end = end


        self.mode: str["departments" | 
                       "teams" | 
                       "staff" | 
                       "hours" | 
                       "freedays" | 
                       "planning" | 
                       "turnover (not active)" | 
                       "functions" | 
                       "project (not active)" | 
                       "salary"] = mode

        key = os.environ.get("ND")

        JL = APIConfig(
            f"nostradamus", 
            element=self.mode,
            key=key,
            start=self.start,
            debug=True
            )

        JL.connection.run()
        self.process(JL.connection.config.obj)

    def process(self, data):
        for response in data:
            match self.mode:
                case "staff":
                    filtered = self.filter_staff(response)
                    self.schema.upsert("staff", filtered["staff"])
                case "departments":
                    filtered = self.filter_departments(response)
                    self.schema.upsert("departments", filtered["departments"])
                case "teams":
                    filtered = self.filter_teams(response)
                    self.schema.upsert("teams", filtered["teams"])
                case "hours":
                    filtered = self.filter_hours(response)
                    self.schema.upsert("hours", filtered["hours"])
                case "freedays":
                    filtered = self.filter_freedays(response)
                    self.schema.upsert("freedays", filtered["freedays"])
                case "planning":
                    filtered = self.filter_planning(response)
                    self.schema.upsert("planning", filtered["planning"])
                case "turnover":
                    filtered = self.filter_turnover(response)
                    self.schema.upsert("turnover", filtered["turnover"])
                case "functions":
                    filtered = self.filter_functions(response)
                    self.schema.upsert("functions", filtered["functions"])
                case "project":
                    filtered = self.filter_projects(response)
                    self.schema.upsert("projects", filtered["projects"])
                case "salary":
                    filtered = self.filter_salary(response)
                    self.schema.upsert("salary", filtered["salary"])
                case _:
                    self.schema.upsert(self.mode, response["response"])
    
    
    def filter_departments(self, data):
        spec = {
            "departments": ("response", [
                {
                    "department_id": "department_id",
                    "department_name": "department_name"
                }
            ])
        }
        return glom(data, spec)
    
    def filter_teams(self, data):
        spec = {
            "teams": ("response", [
                {
                    "department_id": "department_id",
                    "team_id": "team_id",
                    "team_name": "team_name"
                }
            ])
        }
        return glom(data, spec)
    
    def filter_staff(self, data):
        spec = {
            "staff": ("response", [{
                "card_id": "card_id",
                "card_accountant_number": "card_accountant_number",
                "card_start": self.coalesce_empty_to_null("card_start"),
                "card_end": self.coalesce_empty_to_null("card_end"),
                "card_contract_hours": "card_contract_hours",
                "card_hourly_salary": "card_hourly_salary",
                "card_salary_rate": "card_salary_rate",
                "card_department": self.coalesce_empty_to_null("card_department"),
                "card_function": self.coalesce_empty_to_null("card_function"),
                "card_contract_number": self.coalesce_empty_to_null("card_contract_number"),
                "card_contract_profile": self.coalesce_empty_to_null("card_contract_profile"),
                "card_date_of_birth": self.coalesce_empty_to_null("card_date_of_birth"),
                "card_gender": self.coalesce_empty_to_null("card_gender")
            }])
        }
        return glom(data, spec)
    
    def coalesce_null_date_to_null(self, key):
        return lambda x: None if x[key] == "0000-00-00 00:00:00" else x[key]

    def filter_hours(self, data):
        spec = {
            "hours": ("response", [{
                "card_id": self.coalesce_empty_to_null("card_id"),
                "hour_id": "hour_id",
                "hour_department_id": self.coalesce_empty_to_null("hour_department_id"),
                "hour_team_id": self.coalesce_empty_to_null("hour_team_id"),
                "hour_date": "hour_date",
                "hour_hours": "hour_hours",
                "hour_enter": self.coalesce_null_date_to_null("hour_enter"),
                "hour_exit": self.coalesce_null_date_to_null("hour_exit"),
                "hour_state": self.coalesce_empty_to_null("hour_state"),
                "hour_type": self.coalesce_empty_to_null("hour_type"),
                "project_id": self.coalesce_empty_to_null("project_id")
            }])
        }
        return glom(data, spec)
    
    def filter_freedays(self, data):
        spec = {
            "freedays": ("response", [{
                "card_id": "card_id",
                "freeday_id": "freeday_id",
                "freeday_start": "freeday_start",
                "freeday_end": "freeday_end",
                "freeday_days": "freeday_days",
                "freeday_type": "freeday_type",
                "freeday_hours": "freeday_hours"
            }])}
        return glom(data, spec)
    
    def filter_planning(self, data):
        spec = {
            "planning": ("response", [{
                "card_id": self.coalesce_empty_to_null("card_id"),
                "planning_workplace_id": self.coalesce_empty_to_null("planning_workplace_id"),
                "planning_team_id": self.coalesce_empty_to_null("planning_team_id"),
                "planning_date": "planning_date",
                "planning_start": self.adjust_time("planning_date", "planning_start"),
                "planning_hours": "planning_hours",
                "planning_end": self.adjust_time("planning_date", "planning_end"),
                "planning_department_id": self.coalesce_empty_to_null("planning_department_id"),
                "planning_costs": "planning_costs"
            }])}
        return glom(data, spec)
        
    def adjust_time(self, date_field, time_field):
        return lambda x: datetime.combine(datetime.strptime(x[date_field], "%Y-%m-%d") + timedelta(days=int(x[time_field].split(':')[0])//24), datetime.strptime('00:'+x[time_field].split(':')[1]+':'+x[time_field].split(':')[2],'%H:%M:%S').replace(hour=int(x[time_field].split(':')[0])%24).time()).isoformat()

    def filter_turnover(self, data):
        spec = {
            "turnover": ("response", [{
                "article_id": "article_id",
                "article_name": "article_name",
                "articles_value": "articles_value",
                "articles_sold": "articles_sold",
                "articles_turnover": "articles_turnover",
                "date": "date"
            }])}
        return glom(data, spec)

    def filter_functions(self, data):   
        spec = {
            "functions": ("response", [{
                "function_id": "function_id",
                "function_name": "function_name",
                "department_id": "department_id",
                "function_state": "function_state"
            }])}
        return glom(data, spec)
    
    def filter_projects(self, data):
        spec = {
            "projects": ("response", [{
                "id": "id",
                "project_code": "project_code",
                "project_name": "project_name",
                "project_start": "project_start",
                "project_end": "project_end",
                "project_turnover_expectation": "project_turnover_expectation",
                "project_turnover_realisation": "project_turnover_realisation",
                "budget_type": "budget_type",
                "prognosis": "prognosis",
                "project_labourcost_percentage": "project_labourcost_percentage",
                "project_labourcost_amount": "project_labourcost_amount",
                "project_state": "project_state",
                "project_params": "project_params",
                "project_external_reference": "project_external_reference",
                "label": "label",
                "label_colour": "label_colour",
                "label_text_colour": "label_text_colour",
                "project_origin": "project_origin",
                "project_location": "project_location",
                "project_visitors": "project_visitors"
            }])}
        return glom(data, spec)

    def filter_salary(self, data):
        spec = {
            "salary": ("response", [{
                "id": "id",
                "card_id": "card_id",
                "cao_id": "coa_id", # ATTENTION: typo in API
                "salary_start_date": "salary_start_date",
                "salary_end_date": "salary_end_date",
                "salary_level": "salary_level",
                "salary_wage_group": "salary_wage_group",
                "salary_use_wage": "salary_use_wage",
                "salary_base": "salary_base",
                "salary_extra": "salary_extra",
                "salary_bonus": "salary_bonus",
                "salary_total": "salary_total",
                "salary_holiday_days_percentage": "salary_holiday_days_percentage",
                "salary_holiday_legal_percentage": "salary_holiday_legal_percentage",
                "salary_holiday_extralegal_percentage": "salary_holiday_extralegal_percentage",
                "salary_holiday_money_percentage": "salary_holiday_money_percentage",
                "salary_rate": "salary_rate"
            }])}
        return glom(data, spec)

    def coalesce_empty_to_null(self, key):
        return lambda x: None if key not in x.keys() or x[key] == "" else x[key]
        

class Untill():
    """
    mode in ["article" | "department" | "transaction"]
    """
    def __init__(self, start=None, end=None, mode: str = "transaction"):
        self.schema = SupaSchema("untill", last_updated="2023-01-01")
        self.client = self.schema.client

        self.last_updated = self.schema.last_updated

        dates = getdates(self.last_updated)
        datetimes = dates_to_datetimes(dates)[0:3]

        self.start = date_to_datetime(start)
        self.end = date_to_datetime(end)

        # attention: transaction trumps bill. RUN department > article > transaction
        self.mode: str["article" | "department" | "transaction"] = mode
        
        key = os.environ.get("UNTILL")
        user = os.environ.get("UNTILL_USER")
        password = os.environ.get("UNTILL_PASSWORD")

        JL = APIConfig(
            f"untill_{self.mode}", 
            key=key,
            from_date=self.start if start is not None else datetimes[0],
            till_date=self.end if end is not None else datetimes[-1],
            user=user,
            password=password,
            dbname="NAT-POS2",
            domain="http://92.64.72.50:443",
            debug=True
            )
        
        # testapi.untill.com/shield

        JL.connection.run()

        res = self.process(JL.connection.config.obj)

        match self.mode:
            # bill is depreciated!
            case "bill":
                self.schema.upsert("bill", res["bills"])

                # first, we need to add a rel_id to each item and flatten the list (wasn't sure how to do this in glom yet). 
                lst = []
                for items in res["items"]:
                    for i, item in enumerate(items):
                        item["rel_id"] = i
                        lst.append(item)
                        
                self.schema.upsert("item", lst)
        
            case "article":
                self.schema.upsert("article", res["articles"])
                self.schema.upsert("price", [entry for prices in res["prices"] for entry in prices])

            case "department":
                self.schema.upsert("department", res["departments"])
                
            case "transaction":
                self.schema.upsert("transaction", res["transactions"])
                self.schema.upsert("item", res["items"])

    def process(self, data):
        match self.mode:
            case "article":
                spec = { 
                    "articles": [
                        {
                            'id': 'id',
                            'name': 'name',
                            'active': 'active',
                            'department_id': 'departmentId'
                            # 'dailyStockActive': 'dailyStockActive',
                            # 'dailyStockQuantity': 'dailyStockQuantity',

                        }
                    ],
                    "prices": [
                        (
                            'prices', [
                                {
                                    'id': 'priceId',
                                    'article_id': 'articleId',
                                    'name': 'priceName',
                                    'amount': 'amount',
                                    'vat_rate': Coalesce('vat', default=None),
                                }
                            ]
                        )
                    ]
                }
        
            case "bill":
                spec = {
                    "bills": [
                        {
                            "date": "openDateTime",
                            "id": "billNumber",
                            "table_num": "tableNumber",
                            "covers": "covers",
                            # "user_id": "userId",
                        }
                    ],
                    "items": [
                        (
                            S(bill_id=Coalesce("billNumber", default=None)),
                            "items", [
                                {
                                    "article_id": "articleId",
                                    "quantity": "quantity",
                                    "price": "price",
                                    "bill_id": S["bill_id"]
                                }
                            ]
                        )
                    ]
                }
            
            case "department":
                spec = {
                    "departments": [
                        {
                            "id": "id",
                            "name": "name",
                        }
                    ]
                }
            
            case "transaction":
                spec = {
                    "transactions": [{
                        "id": "id",
                        "table_num": "tableNumber",
                        "covers": "covers",
                        "date": "openDateTime",
                        "tip": ("bills.*.tip", sum),  
                        "amount": ("bills.*", [("payments.*.amount", sum)], sum)
                    }],
                    "items": ([(
                        S(transaction_id=Coalesce("id", default=None)),
                        ("orders.*", [
                            ("items.*", [
                                {
                                    "id": "id", 
                                    "article_id": ("articleId", lambda x: x if x != 0 else None),
                                    "quantity": "quantity",
                                    "price": "price",
                                    "vat": "vat",
                                    "returned": Coalesce("returned", default=None),
                                    "transaction_id": S["transaction_id"]
                            }
                            ])
                        ], Flatten())
                    )], Flatten())
                }
            case _:
                raise SyntaxError("no spec found for " + self.mode)
            
        res = glom(data[0], spec)
        # print(res)
        return res

class Zaalcapaciteit():
    def __init__(self):
        self.schema = SupaSchema("public", last_updated="2023-11-20")
        self.client = self.schema.client

        self.mode = ""
        
        JL = APIConfig(
            f"zaalcapaciteit_{self.mode}"
            )
        
        JL.connection.run()

        data = self.process(JL.connection.config.obj[0])
        self.schema.upsert("zaalcapaciteit", data["locations"])

    def process(self, data):
        return data

class Mice():
    """ 
    mode: str[client | location | event]
    """
    def __init__(self, start=None, end=None, mode="event"):
        self.schema = SupaSchema("mice_operations")
        self.client = self.schema.client
        self.start = start
        self.end = end
        self.mode = mode

        if self.start is None:
            raise ValueError("class Mice requires start parameter")

        key = os.environ.get("MC")
        JL = APIConfig(
            f"Mice_{self.mode}",
            key=key,
            debug=False,
            updated_after=self.start
            )

        # run a first time to get the number of pages. Already process (why not?)
        JL.connection.config.page = str(1)
        JL.connection.run()

        success = JL.connection.config.obj[0]["page"]["status"] == "success"
        if not success: raise ValueError("first run failed")
        
        # upon success, process the data
        else:
            num_pages = JL.connection.config.obj[0]["page"]["total_pages"]
            self.process(JL.connection.config.obj)
            
            if num_pages > 1:
                
                # a bit ugly, but works. Otherwise does not get overwritten in config syntax when calling run() twice...
                del JL.connection.config.obj
                JL.connection.config.page = [str(num) for num in range(2, num_pages+1)]
                JL.connection.run()

                self.process(JL.connection.config.obj)

            Updater("mice", getdates()[-1])

    def insert_empty(self, table, id, keys):
        data = {key: None for key in keys}
        data["id"] = id
        self.client.table(table).insert(data).execute()

    def process(self, data):

        client_keys = ["id", "name", "postalcode", "country"]
        
        final_location_keys = ["id", "name", "subtitle", "product_name", "disabled", "description", "content", "sort", "price", "vat_rate"] + ["category_id"]
        location_keys = ["id", "name", "subtitle", "product_name", "disabled", "description", "content", "sort", "price", "vat_rate"] + ["category"]
        
        # self.insert_empty("client", 30011, client_keys)
        # self.insert_empty("location", 2686, final_location_keys)

        for response in data:
            match self.mode:
                case "event":
                    filtered = self.filter_event(response)
                    self.schema.upsert("event", filtered["events"])
                    self.schema.upsert("product", filtered["products"])
                    
                case "client":
                    filtered = self.filter_keys(response["data"], client_keys)                
                    self.schema.upsert("client", filtered)

                case "location":
                    filtered = self.filter_location(response)
                    self.schema.upsert("location", filtered["locations"])
                    # filtered = self.filter_keys(response["data"], location_keys)
                    # flattened = self.flatten_dict_underscore(filtered, ["category"])
                    # self.schema.upsert("location", flattened)

    def coalesce_zero_to_null(self, key):
        return lambda x: None if x[key] == 0 else x[key]
    
    def filter_location(self, data):
        spec = {
            "locations": (
                "data", [{
                "id": "id",
                "name": "name",
                "subtitle": "subtitle",
                "product_name": "product_name",
                "disabled": "disabled",
                "description": "description",
                "content": "content",
                "sort": "sort",
                "price": "price",
                "vat_rate": "vat_rate",
                "category_id": Coalesce("category.id", default=None),
                "category_name": Coalesce("category.name", default=None),
            }]),
        }
        return glom(data, spec)
        

    def filter_event(self, data):
        # event_keys = ["id", "name", "client_id", "booking_id", "status", "planner_id", "location_id", "event_type_id", "datetime_start", "datetime_end", "guests", "total_billed_amount", "total_billed_amount_excl_vat", "products"]
        # product_keys = ["id", "object_id", "object_category_id", "event_id", "amount", "amount_pp", "name", "price", "price_excl_vat", "total_price", "total_price_excl_vat", "cost_price", "vat", "vat_rates"]
        # Coalesce 0 to null: "client_id", "booking_id", "location_id", "event_type_id"
        spec = {
            "events": (
                "data", [{
                "id": "id",
                "name": "name",
                "client_id": self.coalesce_zero_to_null("client_id"),
                "booking_id": self.coalesce_zero_to_null("booking_id"),
                "status": "status",
                "planner_id": "planner_id",
                "location_id": self.coalesce_zero_to_null("location_id"),
                "event_type_id": self.coalesce_zero_to_null("event_type_id"),
                "datetime_start": "datetime_start",
                "datetime_end": "datetime_end",
                "guests": "guests",
                "total_billed_amount": "total_billed_amount",
                "total_billed_amount_excl_vat": "total_billed_amount_excl_vat"
            }]),
            "products": (
                "data", ([(
                    S(event_id=Coalesce("id", default=None)), (
                    "products.*", [{
                        "id": "id",
                        "object_id": "object_id",
                        "object_category_id": "object_category_id",
                        "event_id": S["event_id"],
                        "amount": Coalesce("amount", default=None),
                        "amount_pp": "amount_pp",
                        "name": "name",
                        "price": "price",
                        "price_excl_vat": "price_excl_vat",
                        "total_price": "total_price",
                        "total_price_excl_vat": "total_price_excl_vat",
                        "cost_price": "cost_price",
                        "vat": "vat",
                        "vat_rates_rate": ("vat_rates.*", lambda t: [q["rate"] if q["price"] != 0 else None for q in t][0] if t != [] else None)
                    }]),
                )], Flatten())

            )
        }
        return glom(data, spec)

        # print(data)
    def assign_null_to_zero(self, data, keys):
        for item in data:
            for key in keys:
                if key in item.keys():
                    if item[key] == 0:
                        item[key] = None
        return data
    
    def filter_keys(self, data, keys):
        return [{key: item[key] for key in keys} for item in data]
    
    def return_tuple_extrapolate(self, data, keys):
        """to extract nested items that get their own table.
        In the case of products, also assign event_id. TODO implement generally.
        """
        keylist = []
        for item in data:
            for key in keys:
                for linked_item in item[key]:
                    linked_item["event_id"] = item["id"]
                    keylist.append(linked_item)
                del item[key]
        return data, keylist

    def flatten_single_list_dict_underscore(self, data, keys, selection=None):
        """to flatten a list of dicts with just one item in the list."""
        for item in data:
            for key in keys:
                
                # we expect just one item in the list
                if len(item[key]) == 1:
                    for nested_item in item[key]:
                        for index in nested_item.keys():
                            if selection is None or index in selection:
                                item[f"{key}_{index}"] = nested_item[index]
                    del item[key]
                
                # if there are more, we might filter out some null-criterium
                elif len(item[key]) > 1:  
                    count_filtered = 0                     
                    for nested_item in item[key]:
                        if nested_item["price"] == 0:
                            continue
                        else:
                            for index in nested_item.keys():
                                if selection is None or index in selection:
                                    item[f"{key}_{index}"] = nested_item[index]
                                    count_filtered += 1
                    
                    # but we gotta make sure not more than one criterium meets the filter
                    if count_filtered > 1:
                        print(item)
                        raise ValueError("list has more than one item")
                    else:
                        del item[key]
                
                # make sure we assign a null value if there is no item
                else:
                    for sel in selection:
                        item[f"{key}_{sel}"] = None
                    del item[key]
        
        return data
    
    def flatten_dict_underscore(self, data, keys):
        for item in data:
            for key in keys:
                for index in item[key].keys():
                    item[f"{key}_{index}"] = item[key][index]
                del item[key]
        return data
    
class Jewellabs():
    """Available modes: ["sales"|"show"|"product"|"production"|"badge_type"|"theatre"]
    TODO: fix bug here with non-sales loop...
    """
    def __init__(self, 
                 start=None, 
                 end=None, 
                 mode: str = "sales"
                 ):

        self.start = start
        self.end = end
        self.schema = SupaSchema("jewellabs", last_updated=start)
        self.client = self.schema.client

        self.baskets = []
        self.items = []
        self.transactions = []
        self.details = []

        # production > show | product | badge_type > sales
        self.mode = mode

        self.last_updated = self.schema.last_updated
        self.dates = daterange(start, end)


        JL = APIConfig(
            f"jewellabs_{self.mode}", 
            key=os.environ.get("JL"),
            password=os.environ.get("JL_PASSWORD"),
            user=os.environ.get("JL_USER"),
            updated_after=self.last_updated,
            start=self.start,
            debug=True
            )

        
        if self.mode == "sales":
            if len(self.dates) > 20: raise ValueError("too many dates to process")
            JL.connection.config.date = self.dates
        
        
        JL.connection.run()

        match self.mode:
            case "sales":
                self.sales_process(JL.connection.config.obj)

                self.schema.upsert("basket", self.baskets)
                self.schema.upsert("item", self.items)
                self.schema.upsert("transaction", self.transactions)
                self.schema.upsert("detail", self.details)

            case "show" | "production" | "badge_type" | "product" | "theatre":
                res = self.process(JL.connection.config.obj)

        match self.mode:
            case "show":
                self.schema.upsert("show", res["shows"])

            case "production":
                self.schema.upsert("production", res["productions"])
            
            case "badge_type":
                self.schema.upsert("badge_type", res["badge_types"])
            
            case "product":
                self.schema.upsert("product", res["products"])

            case "theatre":
                self.schema.upsert("theatre", res["theatres"])
            case _:
                pass

        Updater("jewellabs", self.dates[-1])

    def process(self, data):
        match self.mode:
            case "product":
                spec = {
                    "products": ([(
                    "products.*", [
                        {
                            "id": "id",
                            "name": "name",
                            "invoice_name": "invoice_name",
                            "ledger": Coalesce("ledger", default=None),
                            "default_price": "default_price",
                            "default_vat": "default_vat",
                            "product_type_id": "product_type_id",
                            "product_type_code": "product_type_code",
                            "is_deleted": "is_deleted",
                        }
                    ])], Flatten())
                }
            
            case "production":
                spec = {
                    "productions": ([(
                    "productions.*", [
                        {
                         "id": "id",
                         "name": "name",
                         "duration": "duration",
                         "last_play_date": "last_play_date",
                         "production_type_id": "production_type_id",
                         "genre_code": "genre_code",
                         "category_code": "category_code",
                         "is_deleted": "is_deleted",
                        }
                    ]
                )], Flatten())
                }

            case "show":
                spec = {
                    "shows": ([(
                    "shows.*", [
                        {
                            "id": "id",
                            "name": "name",
                            "starts_at": "starts_at",
                            "pre_show_duration": "pre_show_duration",
                            "post_show_duration": "post_show_duration",
                            "theatre_id": "theatre_id",
                            "genre_id": "genre_id",
                            "ticket_product_id": "ticket_product_id",
                            "category_id": "category_id",   
                            "duration": "duration",
                            "production_id": "production_id",
                            "is_for_cineville": "is_for_cineville",
                            "start_date": "start_date",
                            "category_code": "category_code",
                            "director": Coalesce("director", default=None),
                            "spoken_languages": "spoken_languages",
                            "subtitle_languages": "subtitle_languages",
                            "is_deleted": "is_deleted",
                        }
                    ] )], Flatten()
                )}
            
            case "badge_type":
                spec = {
                    "badge_types": ([(
                    "badge_types.*", [
                        {
                            "id": "id",
                            "code": "code",
                            "name": "name",
                            "entity_id": "entity_id",
                        }
                    ])], Flatten()
                )}
            
            case "theatre":
                spec = {
                    "theatres": ([(
                    "theatres.*", [
                        {
                            "id": "id",
                            "name": "name",
                            "code": "code",
                            "maccsbox_code": Coalesce("maccsbox_code", default=None),
                        }
                    ])], Flatten())
                }

            case _:
                raise SyntaxError("no spec found for " + self.mode)
            
        res = glom(data, spec)
        return res

    def sales_process(self, data):
        for over in data:

            for date, date_baskets in over.items():
                
                for basket_id, basket in date_baskets.items():
                    
                    self.baskets.append(Basket(basket_id, regex.remove_date_literal(date)))
                    
                    for ticket_id, ticket in basket["tickets"].items():
                        self.items.append(Item(ticket_id, basket_id, ticket["bo_type"], ticket["bo_id"], ticket["badge_type_id"], ticket["booking_price"]/100, ticket["sales_price"]/100, ticket["sales_vat"]/100, ticket["prepaid_badge_amount"]/100, ticket["promo_discount"]/100, ticket["scanned_at"]))
                        for detail_id, detail in ticket["details"].items():
                            self.details.append(Detail(detail_id, ticket_id, detail["name"], detail["amount"]/100, detail["vat_pct"], detail["ledger"]))
                    
                    for item_id, item in basket["items"].items():
                        self.items.append(Item(item_id, basket_id, item["bo_type"], item["bo_id"], item["badge_type_id"], item["booking_price"]/100, item["sales_price"]/100, item["sales_vat"]/100, item["prepaid_badge_amount"]/100, item["promo_discount"]/100, item["scanned_at"]))
                        for detail_id, detail in item["details"].items():
                            self.details.append(Detail(detail_id, item_id, detail["name"], detail["amount"]/100, detail["vat_pct"], detail["ledger"]))

                    for transaction_id, transaction in basket["transactions"].items():
                        self.transactions.append(Transaction(transaction_id, basket_id, transaction["created_at"], transaction["payment_type_id"], transaction["payment_type_name"], transaction["psp_reference"], transaction["till_id"], transaction["selling_point_name"]))

# DONE: absolve from manual. Need to log the dates in a file or query Supa.
def getdates(last_updated=None):
    today = date.today()
    start_date = date(year=today.year, month=1, day=1) if last_updated is None else date.fromisoformat(last_updated)
    dates = []
    cur = start_date
    while cur < today:
        dates.append(cur.isoformat())
        cur += timedelta(days=1)
    return dates

def daterange(start=None, end=None):
    """Default: YTD"""
    today = date.today()
    start_date = date(year=today.year, month=1, day=1) if start is None else date.fromisoformat(start)
    end_date = date.fromisoformat(end) if end is not None else today
    dates = []
    cur = start_date
    while cur < end_date:
        dates.append(cur.isoformat())
        cur += timedelta(days=1)
    return dates

def dates_to_datetimes(dates):
    return [date_to_datetime(date) for date in dates]

def date_to_datetime(date):
    return date + "T00:00:00Z"