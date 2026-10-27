import logging

from pydantic import BaseModel
from pydantic_core import from_json

logger = logging.getLogger()


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


def load_config(conf_path: str) -> SZuncoverConfig | None:
    try:
        return SZuncoverConfig.parse_file(path=conf_path)
    except BaseException:
        logger.exception("Error loading szuncover config file")
        return None


def load_config_from_str(config: str) -> SZuncoverConfig | None:
    return SZuncoverConfig.model_validate(from_json(config, allow_partial=True))
