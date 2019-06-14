from setuptools import setup, find_packages
setup(
    name="terranet",
    version="0.1",
    packages=find_packages(),
    scripts=['bin/mn_topo_generator.py'],

    author="Me",
    author_email="me@example.com",
    description="This is an Example Package",
    keywords="hello world example examples",
    install_requires=[
        "configparser",
        "jinja2",
    ],
    package_data={
        'terranet': ['templates/*.j2']
    },
)
