import os
from setuptools import setup, find_packages

# https://packaging.python.org/guides/single-sourcing-package-version/
# 4th option
with open(os.path.join(os.getcwd(), 'VERSION')) as version_file:
    version = version_file.read().strip()

setup(
    name='terranet',
    version=version,
    packages=find_packages(),
    author='butjar',
    author_email='',
    description='Terranet: mmWave Distribution Network Emulator',
    keywords='terranet terragraph wifi wifi6 60GHz mmWave',
    install_requires=[
        'collectd',
        'configparser',
        'Flask',
        'influxdb',
        'netns',
        'proxy',
        'ryu',
        'whichcraft',
    ],
    include_package_data=True,
    package_data={
        'terranet': ['examples/.komondor/**/*']
    },
    scripts=['terranet/examples/simple_terranet.py',
             'terranet/examples/hybrid_handover.py'],
)
