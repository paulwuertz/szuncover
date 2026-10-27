import json
import logging
from dataclasses import dataclass

logger = logging.getLogger()


@dataclass
class ThreadConfig:
    thread_entry_name: str
    stack_size: int
    # TODO only functions so far, so cannot deduce from variable symbol atm...
    # stack_variable_name

    @classmethod
    def from_dict(cls, data: dict) -> "ThreadConfig":
        return cls(
            thread_entry_name=data.get("thread_entry_name"), stack_size=data.get("stack_size")
        )


@dataclass
class DynamicCallResolutions:
    caller: str
    callees: list[str | None]

    @classmethod
    def from_dict(cls, data: dict) -> "DynamicCallResolutions":
        return cls(caller=data.get("caller"), callees=data.get("callees"))


@dataclass
class SZuncoverConfig:
    threads: list[ThreadConfig]
    dynamic_calls: list[DynamicCallResolutions]

    @classmethod
    def from_dict(cls, data: dict) -> "SZuncoverConfig":
        # Handle nested Address if present in the raw data
        raw_threads = data.get("threads")
        raw_dynamic_calls = data.get("dynamic_calls")
        threads_obj = (
            [ThreadConfig.from_dict(raw_thread) for raw_thread in raw_threads]
            if raw_threads
            else None
        )
        dynamic_calls_obj = (
            [
                DynamicCallResolutions.from_dict(raw_dynamic_call)
                for raw_dynamic_call in raw_dynamic_calls
            ]
            if raw_dynamic_calls
            else None
        )

        return cls(
            threads=threads_obj,
            dynamic_calls=dynamic_calls_obj,
        )


def load_config(conf_path: str) -> SZuncoverConfig | None:
    try:
        with open(conf_path) as file:
            config_content = file.read()
            return load_config_from_str(config_content)
    except BaseException:
        logger.exception("Error loading szuncover config file")
        return None


def load_config_from_str(config: str) -> SZuncoverConfig | None:
    raw_data = json.loads(config)
    return SZuncoverConfig.from_dict(raw_data)
