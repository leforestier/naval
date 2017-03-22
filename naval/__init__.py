"""
---------------
Examples of use
---------------

Simple validation
=================

.. code:: python

    >>> from naval import *
    >>> address_schema = Schema(
            ['house number', Type(int), Range(1, 10000)],
            ['street', Type(str), Length(min=5, max=255)],
            ['zipcode', Type(str), Regex('\d{4,5}')],
            ['country', ('France', 'Germany', 'Spain')]
        )

    >>> address_schema.validate({
            'house number': 12000,
            'street': 'tapioca boulevard',
            'country': 'Federal Kingdom of Portulombia'
        })
    ...
    ValidationError: {'house number': 'The maximum is 10000.', 'zipcode': 'Field is missing.', 'country': 'Incorrect value.'}

    >>> address_schema.validate({
            'house number': 17,
            'street': 'rambla del Raval',
            'zipcode': '08001',
            'country': 'Spain'
        })
    {'country': 'Spain',
     'house number': 17,
     'street': 'rambla del Raval',
     'zipcode': '08001'}

Validation and transformation
=============================

.. code:: python

    >>> from naval import *
    >>> from passlib.hash import bcrypt # we're going to use the passlib library to encrypt passwords

    >>> registration_form = Schema(    
            ['username', Type(str), Length(min=3, max=16)],
            ['password', Type(str)],
            ['password2'],
            [
                Assert(
                    (lambda d: d['password'] == d['password2']),
                    error_message = "Passwords don't match"
                )
            ],
            ['password', lambda s: s.encode('utf-8'), bcrypt.encrypt, Save],
            ['password2', Delete],
            ['email', Email]
        )

    >>> registration_form.validate({
            'email': 'the-king@example.com',
            'username': 'TheKing',
            'password': 'hackme',
            'password2': 'hackme'
        })
    {'email': 'the-king@example.com',
     'password': '$2a$12$JT2UlXP0REt3EX7kGIFGV.5uKPQJL4phDRpfcplW91sJAyB8RuKwm',
     'username': 'TheKing'}

    >>> registration_form.validate({
            'username': 'TheKing',
            'email': '@@@@@@@@@@',
            'password': 'hackme',
            'password2': 'saltme'
        })
    ...
    ValidationError: {'email': 'This is not a valid email address.', '*': "Passwords don't match"}

Internationalization
====================

Supply a ``lang`` keyword argument to the ``validate`` method to obtain translated error messages.

.. code:: python

    >>> editor_schema.validate(
            { 'website': 'http://#' },
            lang = 'fr'
        )
    ...
    ValidationError: {'name': 'Champ manquant.', 'website': "Ce n'est pas une url valide."}
"""

__author__ = "Benjamin Le Forestier (benjamin@leforestier.org)"
__version__ = '0.7.0'

from naval.core import *
from naval.util import Email, Domain, Url
