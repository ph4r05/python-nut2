import os

from setuptools import find_packages, setup

__version__ = "3.1.0"

README = open(os.path.join(os.path.dirname(__file__), "README.rst")).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name="ph4-nut2",
    version=__version__,
    include_package_data=True,
    install_requires=[
        "telnetlib3>=2.0.4",
    ],
    packages=find_packages(),
    license="GPL3",
    description="A Python abstraction class to access NUT servers.",
    long_description=README,
    url="https://github.com/ph4r05/python-nut2",
    author="Ryan Shipp, Dusan Klinec",
    author_email="python@rshipp.com, ph4r05@gmail.com",
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Power (UPS)",
        "Topic :: System :: Systems Administration",
    ],
)
