from distutils.core import setup
from glob import glob

with open('README.rst') as fd:
    long_description = fd.read()

locale_files = [path[len('naval/'):] for path in glob('naval/locale/*/*/*.[mp]o')]
test_files = [path[len('naval/'):] for path in glob('naval/test/*.py')]
package_data = {'naval': ['locale/naval.pot'] + locale_files + test_files}

setup(
    name = 'naval',
    version = '0.6.0',
    packages = ['naval'],
    package_data = package_data,
    include_package_data = True,
    install_requires = ['postpone>=0.2.0', 'validators>=0.9', 'future'],
    author = 'Benjamin Le Forestier',
    author_email = 'benjamin@leforestier.org',
    url = 'https://github.com/leforestier/naval',
    keywords = ["validation", "validator", "dictionary", "dict", "json", "schema", "rest", "html", "form", "translation", "i18n"],
    description = "Validation library with error messages in multiple languages and a readable syntax.",
    long_description = long_description,
    classifiers = [
        'Environment :: Web Environment',
        'Environment :: Other Environment',
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]  
)
