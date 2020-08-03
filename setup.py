import os
from setuptools import setup, find_packages

# https://packaging.python.org/guides/single-sourcing-package-version/
# 4th option
with open(os.path.join(os.getcwd(), 'VERSION')) as version_file:
    version = version_file.read().strip()

setup(
    name="terranet",
    version=version,
    packages=find_packages(),
    author="Me",
    author_email="me@example.com",
    description="This is an Example Package",
    keywords="hello world example examples",
    install_requires=[
        "configparser",
        "jinja2",
        "whichcraft",
        "future",
        "flask",
        "netns",
        "influxdb"
    ],
    include_package_data=True,
    package_data={
        'terranet': ['templates/*.j2']
    },
)
