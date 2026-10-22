# Copyright (c) 2021, Nordic Semiconductor ASA
#
# SPDX-License-Identifier: Apache-2.0

import setuptools

long_description = '''

Stack size
===========

This tool is there to estimate stack usage in an RTOS type thread.

I takes the .ci file output from GCC's -callgraph-info=cu,da options to build a calltree of a firmware with a given stack use for each function.

Given a config file a list of threads and associtated stack sizes a report will be generated to each threads stack utilization.

For function calls not know at compile-time via function pointers a list of dynamic calls can complete this missing parts of the runtime callgraph to get better results in the estimation.
'''

version = '0.0.1'

setuptools.setup(
    author='Paul Würtz',
    author_email='paulwuertz@posteo.de',
    name='szuncover',
    version=version,
    description='Python library for stack-size estimation',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url='https://github.com/zephyrproject-rtos/zephyr',
    packages=setuptools.find_packages(where='szuncover'),
    package_dir={'': 'szuncover'},
    classifiers=[
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
    ],
    install_requires=[
        'PyYAML>=6.0',
    ],
    python_requires='>=3.6',
)
