from setuptools import setup, find_packages
from codecs import open
from os import path

setup(
    name='cm_tools',
    version='0.0.1a1',
    packages=find_packages(),
    description='CLI tools for working with CloudMan clusters',
    url='https://github.com/simonalpha/cm_tools',
    author='Simon Belluzzo',
    author_email='simon@belluzzo.id.au',
    install_requires=['boto<2.35.0', 'bioblend', 'docopt'],
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
    ],
    entry_points={
        'console_scripts': [
            'cm-launcher = cm_tools:cm_launch_from_cli',
        ]
    }
)
