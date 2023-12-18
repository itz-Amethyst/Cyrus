import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from dateutil import parser
from pydantic import BaseModel
from sqlalchemy.orm import InstanceState

DATETIME_AWARE = "%m/%d/%Y %I:%M:%S %p %z"
DATE_ONLY = "%m/%d/%Y"

ONE_HOUR_IN_SECONDS = 3600
ONE_DAY_IN_SECONDS = ONE_HOUR_IN_SECONDS * 24
ONE_WEEK_IN_SECONDS = ONE_DAY_IN_SECONDS * 7
ONE_MONTH_IN_SECONDS = ONE_DAY_IN_SECONDS * 30
ONE_YEAR_IN_SECONDS = ONE_DAY_IN_SECONDS * 365

SERIALIZE_OBJ_MAP = {
    str(datetime): parser.parse,
    str(date): parser.parse,
    str(Decimal): Decimal,
}


#! Improve Required
def CustomJsonEncoder( obj ):
    result = {}
    if isinstance(obj , dict):
        for key , value in obj.items():
            if not isinstance(value , InstanceState):
                if isinstance(value , datetime):
                    result[key] = value.strftime(DATETIME_AWARE)
                elif isinstance(value , Enum):
                    result[key] = value.value
                else:
                    result[key] = value
        return result
    elif isinstance(obj , list):
    # If it's a list, apply serialization to each element
        return [CustomJsonEncoder(element) for element in obj]
    elif isinstance(obj, datetime):
        return {"val": obj.strftime(DATETIME_AWARE), "_spec_type": str(datetime)}
    elif isinstance(obj, date):
        return {"val": obj.strftime(DATE_ONLY), "_spec_type": str(date)}
    elif isinstance(obj, Decimal):
        return {"val": str(obj), "_spec_type": str(Decimal)}
    elif isinstance(obj, BaseModel):
        return obj.dict()
    elif isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, Enum):
        return str(obj.value)
    else:
        return obj


def object_hook(obj):
    if "_spec_type" not in obj:
        return obj
    _spec_type = obj["_spec_type"]
    if _spec_type not in SERIALIZE_OBJ_MAP:  # pragma: no cover
        raise TypeError(f'"{obj["val"]}" (type: {_spec_type}) is not JSON serializable')
    return SERIALIZE_OBJ_MAP[_spec_type](obj["val"])


def serialize_json(json_dict):
    if isinstance(json_dict, dict):
        data = CustomJsonEncoder(obj = json_dict)
        return json.dumps(data)

    else:
        data_main= []
        for obj in json_dict:
            data = CustomJsonEncoder(obj = obj.__dict__)
            data_main.append(data)

        return json.dumps(data_main)


def deserialize_json(json_str):
    return json.loads(json_str, object_hook=object_hook)
