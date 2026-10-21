import re

from pydantic import BaseModel
from pydantic.experimental.missing_sentinel import MISSING


class ThreadConfig(BaseModel):
    thread_entry_name: str
    stack_size: int
    # TODO only functions so far, so cannot deduce from variable symbol atm...
    # stack_variable_name


class DynamicCallResolutions(BaseModel):
    caller: str
    callees: list[str | None]


class SZuncoverConfig(BaseModel):
    threads: list[ThreadConfig]
    dynamic_calls: list[DynamicCallResolutions]

def load_config(conf_path: str) -> SZuncoverConfig:
    try:
        return SZuncoverConfig.parse_file(path=conf_path)
    except Exception as e:
        print(e)

