.. image:: https://travis-ci.org/leforestier/naval.svg
    :target: https://travis-ci.org/leforestier/naval

-----------------------------
Naval is a validation library
-----------------------------

Using *Naval*, you can define schemas to validate or transform python dictionaries or other objects.
*Naval* provides you with error messages in multiple languages. You can use it to validate JSON documents.

*Naval* offers a very flexible and readable way to transform python dictionaries, which makes it a valuable 
tool when implementing RESTful apis.

You could also use *Naval* to validate HTML forms.

`table of contents`_

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

Composing schemas
=================

Schemas can be reused to build bigger schemas.

.. code:: python

    >>> from naval import *

    >>> editor_schema = Schema(
            ['name', Type(str)],
            ['website', Optional, Url]
        )
        
    >>> book_schema = Schema(
            ['title', Type(str)],
            ['author', Type(str), Length(max=200)],
            ['isbn13', Type(str), Length(13,13), Regex('\d+')],
            ['editor', editor_schema]
        )

    >>> book_schema.validate({
            'title': 'Lose weight by eating pancakes',
            'author': 'John Greedyquack',
            'isbn13': '1234567890123',
            'editor': {
                'name': 'Flawed Books',
                'website': 'http://#'
            }
        })
    ...
    ValidationError: {'editor': {'website': 'This is not a valid url.'}}


Internationalization
====================

Supply a ``lang`` keyword argument to the ``validate`` method to obtain translated error messages.

.. code:: python

    >>> editor_schema.validate({ 'website': 'http://#' }, lang = 'fr')
    ...
    ValidationError: {'name': 'Champ manquant.', 'website': "Ce n'est pas une url valide."}


-------
Filters
-------

Filters are used to validate or transform python objects. Filters are instances of the many subclasses of ``naval.Filter``.
A filter's ``validate`` method takes a value to examine, and either returns it (or a modified version of it), or it raises a
``ValidationError`` exception. You can catch this exception like this:

.. code:: python 

        try:
            potentially_modified_version = my_filter.validate(obj)
        except ValidationError as exc:
            print(exc.error_details)

The ``ValidationError`` instance has a ``error_details`` attribute, that contains, well, details about the error.
For elementary filters, ``exc.error_details`` is just a string describing the error. 
For the ``Schema`` filter (used to validate python dictionaries), ``exc.error_details`` is a dictionary 
(each key of this dictionary contains details about the errors generated by a particular item).

It's always possible to supply custom error messages when constructing a filter.


Elementary filters
==================

Range
-----

.. code:: python

    >>> Range(5, 10).validate(7)
    7

    >>> Range(5, 10).validate(-16)
    ...
    ValidationError: The minimum is 5.

Length
------

.. code:: python

    >>> Length(max=3).validate(['one', 'two', 'three'])
    ['one', 'two', 'three']

    >>> Length(max=3).validate(['one', 'two', 'three', 'four'])
    ValidationError: The value is too long. Max length is 3.

    # customizing the error message
    >>> Length(max=3, too_long_error="Please, no more than {max_length} items").validate(
            ['one', 'two', 'three', 'four']
        )
    ...
    ValidationError: Please, no more than 3 items

Type
----

.. code:: python

    >>> Type(int, float).validate(3.14)
    3.14

By default, the type must match exactly.
Use ``subclasses = True`` to allow for subclasses.

.. code:: python

    >>> from collections import OrderedDict

    >>> Type(dict).validate(OrderedDict([('a', 1), ('b', 2)]))
    ...
    ValidationError: Wrong type. Expected dict. Got OrderedDict instead.
    
    >>> Type(dict, subclasses = True).validate(OrderedDict([('a', 1), ('b', 2)]))
    OrderedDict([('a', 1), ('b', 2)])

Regex
-----

    The pattern must match exactly, from the beginning to the end of the string.

.. code:: python

    >>> Regex('[A-Za-z][-_A-Za-z0-9]+').validate('TheKing!!!')
    ...
    ValidationError: Incorrect value.

    >>> Regex('[A-Za-z][-_A-Za-z0-9]+').validate('TheKing')
    'TheKing'

Email
-----

Email validator.

Internally, this filter uses the email validation function from the *validators* library: https://github.com/kvesteri/validators

.. code:: python

    >>> Email.validate('email@example.com')
    'email@example.com'

.. code:: python

    >>> Email.validate('user@92.80.0.1')
    ...
    ValidationError: This is not a valid email address.

Url
---

Url validator.
The regex used to validate urls was borrowed from the Spoon php library: http://spoon-library.be

.. code:: python

    >>> Url.validate('http://www.example.com/v1/?sort=asc')
    'http://www.example.com/v1/?sort=asc'

.. code:: python

    >>> Url.validate('http://0.0.0.0')
    ...
    ValidationError: This is not a valid url.
    
Domain
------

Domain name validator.

Internally, this filter uses the domain name validation function from the *validators* library: https://github.com/kvesteri/validators

.. code:: python

    >>> Domain.validate('example.com')
    'example.com'

.. code:: python

    >>> Domain.validate('example.com/')
    ...
    ValidationError: This is not a valid domain name.

Assert
------

Assert builds a filter from a boolean function.

.. code:: python

    >>> only_digits = Assert(str.isdigit, error_message = "Only digits are allowed")

    >>> only_digits.validate('12345')
    '12345'

    >>> only_digits.validate('12-345')
    ...
    ValidationError: Only digits are allowed
    


Apply
-----

``Apply`` applies a function to its argument and returns the result.
By default, it will reraise any exception as a ValidationError, but you can specify what kind of exception
(if any) is expected. 

.. code:: python
    
    >>> hex_to_int = Apply(lambda h: int(h, 16))
    
    >>> hex_to_int.validate('aa')
    170

    >>> hex_to_int.validate('zz')
    ...
    ValidationError: invalid literal for int() with base 16: 'zz'

You rarely have to use ``Apply`` inside a ``Schema``, because any callable is converted implicitly to an ``Apply`` filter.

.. code:: python

    forum_post = Schema(
        ['title', Length(max=100), str.lower, str.capitalize, Save],
        ['post', Length(max=4000)]
    )

However, it can sometimes be useful to explicitly use ``Apply`` to customize the error message, or to specify exactly what kind of exception
is expected.

.. code:: python

    >>> import numpy as np
    >>> matrix_inverter = Schema(
            ['matrix',
                np.array,
                Apply(
                    np.linalg.inv,
                    catch = (np.linalg.LinAlgError,),
                    error_message = "Please supply an invertible square matrix"
                ),
                (lambda mat: mat.tolist()),
                MoveTo('inverse')
            ]
        )

This example uses three ``Apply`` filters. ``np.array`` and ``(lambda mat: mat.tolist())`` are implicitly converted 
to ``Apply`` filters by the ``Schema`` constructor.

.. code:: python

    >>> matrix_inverter.validate({'matrix': [[1,1],[1,0]]})
    {'inverse': [[0.0, 1.0], [1.0, -1.0]]}

    >>> matrix_inverter.validate({'matrix': [[1,1],[1,1]]})
    ...
    ValidationError: {'matrix': 'Please supply an invertible square matrix', 'inverse': "Couldn't compute field."}

In
--

.. code:: python

    >>> In(['red', 'blue', 'yellow']).validate('blue')
    'blue'

    >>> In(['red', 'blue', 'yellow']).validate("broccoli")
    ...    
    ValidationError: Incorrect value.

    >>> In(
            ['red', 'blue', 'yellow'],
            error_message = "Please choose one of the available colors."
        ).validate("broccoli")
    ...
    ValidationError: Please choose one of the available colors.
    

You rarely have to use ``In`` explicitly in a ``Schema``. Any object that implements the ``__contains__`` special method (like for example, python lists, tuples, set, and many more) will be automatically converted to an ``In`` filter by the ``Schema`` constructor.

.. code:: python
    
    shipping_schema = Schema(
        ['address', address_schema],
        ['shipping method', ('priority mail', 'parcel post', 'bottle to the sea')] 
    )
    
As you can see, unless you want to customize the error message, you don't have to build a ``In`` filter explicitly, when 
you define a ``Schema``.


Filter builders
===============

You can build filters from other filters.
The most sophisticated example is probably ``Schema`` which is used to create a filter for python dictionaries.

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

But first let's talk about some simpler filter builders.

Do
--

``Do`` creates a new filter from existing filters. The filters will be applied one after another.
For example, the ``Url`` validator is actually defined this way:

.. code:: python

    Url = Do(
        Type(str),
        Length(max=2083),
        Regex("a huge regex here"),
        error_message = _("This is not a valid url.")
    )

As you can see, it is possible to specify an error message.
This error message will override any error message that could be triggered by 
the filters in the sequence. 

Each
----

Use ``Each`` if you want to apply a filter to every element of a collection.

For example, to validate that a field is a list of integers:

.. code:: python

    >>> schema = Schema(
            ['integers', Type(list), Each(Type(int))]
        )

    >>> schema.validate({'integers': [1, 2, 3, 5]})
    {'integers': [1, 2, 3, 5]}

    >>> schema.validate({'integers': [8, "broccoli", 21]})
    ...
    ValidationError: {'integers': 'Item #2: Wrong type. Expected int. Got str instead.'}

You can use ``Each0`` if you want the items to be numbered from 0 when generating the error messages:

.. code:: python

    >>> Each0(Type(int)).validate([8, "broccoli", 21])
    ...
    ValidationError: Item #1: Wrong type. Expected int. Got str instead.

It can prove useful to use ``Each`` in combination with ``Do`` in order to apply many filters
to each elements of a list. For example:

.. code:: python

    >>> schema = Schema(
        ['keywords', Type(list), Each( Do( Type(str), Length(min=2, max=30), str.lower) ), Save]
    )

    >>> schema.validate({'keywords': ['PANCAKES', 'FOOD', 'Recipe']})
    {'keywords': ['pancakes', 'food', 'recipe']}

Schema
------

``Schema`` is the class used to define validation and transformation rules for python dictionaries.
Each rule is expressed as a list. Like this:

.. code:: python

    address_schema = Schema(
        ['house number', Type(int), Range(1, 10000)],
        ['street', Type(str), Length(min=5, max=255)],
        ['zipcode', Type(str), Regex('\d{4,5}')],
        ['country', ('France', 'Germany', 'Spain')],
    )

or this:

.. code:: python

    registration_form = Schema(    
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

Each rule either apply to a particular field of the dictionary, or it applies to the dictionary
as a whole. If a rule starts with a filter, or a callable, then the rule applies to the whole dictionary.
Otherwise (for example if the rule starts with a string like ``"username"``), then the rule applies to this
particular item of the dictionary.

In the preceding example, the rule

.. code:: python

        [
            Assert(
                (lambda d: d['password'] == d['password2']),
                error_message = "Passwords don't match"
            )
        ]

is a global rule. The ``Assert`` filter is called on the whole dictionary.


Here's another example:

.. code:: python

    schema = Schema(
        ['first name', Type(str), Length(min=1, max=50)],
        ['last name', Type(str), Length(min=1, max=50)],
        [lambda d: d['first name'] + ' ' + d['last name'], SaveAs('full name')]
    )

The last rule starts with a callable so it applies to the whole dictionary.
I guess it's time to introduce the ``SaveAs`` instruction.

Each rule can optionally end with a storage instruction: ``SaveAs``, ``MoveTo``, ``Save`` or ``Delete``.

SaveAs
~~~~~~

Use SaveAs at the end of chain to save the current value under another key.
Keep in mind that it doesn't modify the input dictionary. The modification is seen only
in the output dictionary (the return value of the ``validate`` method).

Example:

.. code:: python

    >>> original = {'age': 25.4}

    >>> Schema(['age', round, SaveAs('age_round')]).validate(original)
    {'age': 25.4, 'age_round': 25}

    >>> original
    {'age': 25.4}


MoveTo
~~~~~~

Use MoveTo at the end of a chain to move an item under another key, and delete the current key.
Keep in mind that it doesn't modify the input dictionary. The modification is seen only
in the output dictionary (the return value of the ``validate`` method).

Example:

.. code:: python

    >>> original = {'age': 25.4}

    >>> Schema(['age', round, MoveTo('age_round')]).validate(original)
    {'age_round': 25}

    >>> >>> original
    {'age': 25.4}


Save
~~~~

Use Save at the end of a chain in order to save the current value under the current key.
Keep in mind that it doesn't modify the input dictionary. The modification is seen only
in the output dictionary (the return value of the ``validate`` method).

Example:

.. code:: python
        
    >>> original = {'age': 25.4}

    >>> Schema(['age', round, Save]).validate()
    {'age': 25}

    >>> original
    {'age': 25.4}

Delete
~~~~~~

Use Delete at the end of a chain to delete the current key.
Keep in mind that it doesn't modify the input dictionary. The modification is seen only
in the output dictionary (the return value of the ``validate`` method).

I have to introduce 3 other useful instructions now: ``Optional``, ``Default`` and ``Discard``.

Optional
~~~~~~~~

Optional should be placed after a field name in a chain.

.. code:: python

   >>> icecream_order = Schema(
           ['flavour', ('vanilla', 'chocolate', 'pistachio')],
           ['topping', Optional, ('whipped cream', 'chocolate sprinkles', 'peanuts')],
           ['quantity', int, Range(1, 12)]
       )

The schema will just skip to the next rule if it doesn't find the key in the dictionary.

.. code:: python

    >>> icecream_order.validate({'flavour': 'vanilla', 'quantity': 4})
    {'flavour': 'vanilla', 'quantity': 4}

Default
~~~~~~~

``Default`` should be placed after a field name in a chain.
The ``Default`` constructor takes an object or a callable as an argument.

Example:

.. code:: python

     ['currency', Default('USD')]

Example (using a callable):

.. code:: python

        ['username', Default(lambda d: ''.join(random.choice(string.ascii_lowercase) for _ in range(6)))]
        
This would generate a random username if no username was supplied.

If you pass a callable, this should be a unary function. It will be passed the whole dictionary.
This way, it is possible to set a default value for a field using other items of the dictionary. For example:

.. code:: python

    >>> schema = Schema(
            ['email', Email],
            ['username', Default(lambda d: d['email'])]
        )
        
This would set the username to be the email address if no username was supplied.

.. code:: python

    >>> schema.validate({'email': 'the-king@example.com'})
    {'email': 'the-king@example.com', 'username': 'the-king@example.com'}
    

Discard
~~~~~~~ 

``Discard`` should be placed after a field name in a chain. 
``Discard`` is used to indicate that if a key in the input dictionary contains a particular value, this
key should be regarded as absent from the dictionary.

.. code:: python

    >>> schema = Schema(
            ['name', Type(str)],
            ['address', Discard(''), Type(str)]
        )

    >>> schema.validate({'name': 'Marcel Bichon', 'address': ''})
    ...
    ValidationError: {'address': 'Field is missing.'}

It can prove useful to combine ``Discard`` with ``Optional``:

.. code:: python

    >>> schema = Schema(
            ['name', Type(str)],
            ['address', Discard(''), Optional, Type(str)]
        )

    >>> schema.validate({'name': 'Marcel Bichon', 'address': ''})
    {'name': 'Marcel Bichon'}

Or with ``Default``:

.. code:: python

    >>> household_schema = Schema(
            ['married', Type(bool)],
            ['number of children', Discard(''), Default('0'), int, Save]
        )

    >>> household_schema.validate({'married': False, 'number of children': ''})
    {'married': False, 'number of children': 0}

You can decide to discard multiple values. For example:

.. code:: python

    ['task_id', Discard('', None)]

This would discard both ``''`` and ``None``.

Unexpected Keys
~~~~~~~~~~~~~~~

The Schema constructor takes an optional ``unexpected_keys`` argument.
It defines what should be done with keys that don't appear in your schema.

With ``unexpected_keys=Schema.FAIL``, the schema will refuse to validate a dictionary if it 
contains unknown keys. This is the default.

With ``unexpected_keys=Schema.KEEP``, the schema will validate a dictionary even if it 
contains unknown keys. These unknown items will appear in the output dictionary (the dictionary 
returned by the ``validate`` method).

With ``unexpected_keys=Schema.DELETE``, the schema will agree to validate a dictionary that
contains unknown keys, but these items won't appear in the output dictionary.

---------------------------------
Translation of the error messages
---------------------------------

Built-in messages
=================

The ``validate`` method of the ``Filter`` class (and its subclasses, like for example, ``Schema``),
takes an optional ``lang`` keyword argument.
Use this ``lang`` keyword argument to obtain the potential error messages in the desired language.

.. code:: python

    >>> editor_schema = Schema(
            ['name', Type(str)],
            ['website', Optional, Url]
        )

    >>> editor_schema.validate(
            { 'website': 'http://#' },
            lang = 'fr'
        )
    ...
    ValidationError: {'name': 'Champ manquant.', 'website': "Ce n'est pas une url valide."}

If the built-in error messages are not available in the language you're looking for, submit an issue,
or (if you feel like contributing to the project by translating the messages yourself) a pull request at https://github.com/leforestier/naval .

Custom messages
===============

*Naval* translation feature relies on the *postpone* library and the *gettext* module.
Here's how you could define customized translatable error messages.

.. code:: python

    from postpone import LazyString as _

    pencil_schema = Schema(
        ['thickness',
            Type(int),
            Range(1, 100, max_message = _("Maximum thickness is {max}."))
        ],
        ['color',
            Type(str),
            Regex(
                '[0-9a-fA-F]{6}',
                error_message = _("This is not a valid color.")
            )
        ]
    )

You just added two new messages that aren't translatable yet.

*Naval*'s ``locale`` directory contain the translations for the standard *Naval* messages.
You should copy this directory. For example, if you've installed the naval library inside
/usr/local/lib/python3.5/site-packages:
    
    $ cp -r /usr/local/lib/python3.5/site-packages/naval/locale /home/myuser/myapp/naval-locale

Then add your translations to the relevant .po files and, in your application code, insert the line:

.. code:: python

    import naval
    naval.settings.locale_directory = '/home/myuser/myapp/naval-locale'

After that, *Naval* will search for translations in the directory ``'/home/myuser/myapp/naval-locale'``
instead of *Naval*'s default locale directory.

.. _`table of contents`:

-----------------
Table of contents
-----------------
.. contents::




