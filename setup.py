#!/usr/bin/env python

from setuptools import find_packages, setup

from mteor import __version__

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='mteor',
    version=__version__,
    author='Daichi Narushima',
    author_email='dnarsil+github@gmail.com',
    description='Automated Trader using MetaTrader 5',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/dceoy/mteor',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'docopt', 'MetaTrader5', 'numpy', 'pandas', 'scipy', 'statsmodels'
    ],
    entry_points={'console_scripts': ['mteor=mteor.cli:main']},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Office/Business :: Financial :: Investment'
    ],
    python_requires='>=3.6'
)
