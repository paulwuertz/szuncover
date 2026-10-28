import unittest

from szuncover.config import load_config_from_str

from .test_ctx import *


class Test_Config(unittest.TestCase):
    def test_parse_graph_minimal(self):
        test_config_str = """
        {
            "threads": [
                { "thread_entry_name": "a", "stack_size": 128 },
                { "thread_entry_name": "b", "stack_size": 256 },
                { "thread_entry_name": "c", "stack_size": 1024 }
            ],
            "dynamic_calls": [
                { "caller": "a", "callees": [ "c" ] },
                { "caller": "b", "callees": [ null ] }
            ]
        }
        """
        test_conf = load_config_from_str(test_config_str)
        # thread entry size
        self.assertEqual(len(test_conf.threads), 3, "3 threads defined in conf")
        # test one entry
        self.assertEqual(test_conf.threads[1].thread_entry_name, "b", "thread entry name correct")
        self.assertEqual(test_conf.threads[1].stack_size, 256, "thread entry name correct")
        # dynamic_calls entry size
        self.assertEqual(len(test_conf.dynamic_calls), 2, "len fns define dynamic calls")
        self.assertEqual(test_conf.dynamic_calls[0].caller, "a", "dynamic caller name")
        self.assertEqual(len(test_conf.dynamic_calls[0].callees), 1, "fns dynamic call len matches")
