# Copyright (c) 2021, Nordic Semiconductor ASA
#
# SPDX-License-Identifier: Apache-2.0

import setuptools

long_description = """

Stack size
===========

Estimate stack usage in RTOS threads when compiling with GCC -callgraph-info=cu,da option.

From all .ci files a calltree with stack use for each function is constructed.

Given a config file a list of threads and associtated stack sizes a report will be generated to each threads stack utilization.

For dynamic function-calls not know at compile-time a list of dynamic-calls can complete this missing parts of the runtime callgraph to get better results in the estimation.
"""

version = "0.1.2"

setuptools.setup(
    author="Paul Würtz",
    author_email="paulwuertz@posteo.de",
    name="szuncover",
    version=version,
    description="Uncover stack-usages for your threads",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/paulwuertz/szuncover",
    packages=setuptools.find_packages(where="szuncover"),
    package_dir={"": "szuncover"},
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
    install_requires=[
        "pydantic>=2.13.5",
    ],
    python_requires=">=3.12",
)
