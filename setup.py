from setuptools import setup, find_packages
setup(
    name="terranet",
    version="0.1",
    packages=find_packages(),
    scripts=['bin/tn.py'],

    author="Me",
    author_email="me@example.com",
    description="This is an Example Package",
    keywords="hello world example examples",
    install_requires=[
        "configparser",
        "jinja2",
        "whichcraft",
        "future",
        "mininet",
        "ipmininet"
    ],
    include_package_data=True,
    package_data={
        'terranet': ['templates/*.j2']
    },
)
