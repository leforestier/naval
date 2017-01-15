from __future__ import unicode_literals
from past.builtins import basestring
import functools, gettext, re, sys, os
from postpone import evalr, LazyString as _

__all__ = [
    'Apply', 'Assert', 'Default', 'Delete', 'Discard', 'Do', 'Each', 'Each0', 'Each1', 'In',
    'Length', 'MoveTo', 'Optional', 'Range', 'Regex', 'Save', 'SaveAs', 'Schema', 'Type',
    'ValidationError'
]

class Settings(object):
    def __init__(self, default_lang, locale_dir = None):        
        self.default_lang = default_lang
        self._locale_dir = locale_dir

    @property
    def locale_dir(self):
        if self._locale_dir:
            return self._locale_dir
        for path in sys.path:
            candidate = os.path.join(path, 'naval', 'locale')
            if os.path.isdir(candidate):
                self._locale_dir = candidate
                return candidate
        raise IOError("Couldn't find locale directory.")
        
    @locale_dir.setter
    def locale_dir(self, directory):
        self._locale_dir = directory
        
settings = Settings('en')

class ValidationError(Exception):
    def __init__(self, error_details):
        self.error_details = error_details

class Filter(object):
    """
    Base class for all transformation and/or validation operations.
    The subclasses of Filter override the `run` method.
    """
    def run(self, value):
        """
        This method should raise a ValidationError if its argument is invalid.
        Otherwise, (if it's valid), it should return the argument, or a computed value in the 
        case of a transformation filter.
        """
        raise NotImplementedError

    def validate(self, value, lang = None):
        """
        Encapsulates the `run` method.
        Translates the error messages if necessary.
        Subclasses shouldn't need to override this method.
        """
        try:
            return self.run(value)
        except ValidationError as exc:
            lang = lang or settings.default_lang
            if lang == 'en':
                translate_message = lambda x:x
            else:
                locale_dir = settings.locale_dir
                try:
                    translation = gettext.translation(
                        "naval", locale_dir, [lang]
                    )
                except (IOError, OSError) as exc2: # OSError from python 3.3, IOError before that 
                    translate_message = lambda x:x
                else:
                    try:
                        translate_message = translation.ugettext # python 2
                    except AttributeError:
                        translate_message = translation.gettext # python 3
            raise ValidationError(evalr(exc.error_details, translate_message))

class _Optional(object):
    def __repr__(self):
        return "Optional"

Optional = _Optional()

del _Optional

class DefaultBase(object):
    def __init__(self, val):
        self._val = val

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self._val))

class DefaultVal(DefaultBase):
    def getvalue(self, dct):
        return self._val

class DefaultFunc(DefaultBase):
    def getvalue(self, dct):
        return self._val(dct)

def Default(val):
    """
    `Default` should be placed after a field name in a chain.
    The `Default` constructor takes an object or a callable as an argument.

    Example:
        ['currency', Default('USD')]

    Example (using a callable):
        ['username', Default(lambda d: ''.join(random.choice(string.ascii_lowercase) for _ in range(6)))]
        
        This would generate a random username if no username was supplied.

    If you pass a callable, this should be a unary function. It will be passed the whole dictionary.
    This way, it is possible to set a default value for a field using other fields of a document. For example:

        schema = Schema(
            ['email', Email],
            ['username', Default(lambda d: d['email'])]
        )
        This would set the username to be the email address if no username was supplied.        
    """
    if callable(val):
        return DefaultFunc(val)
    else:
        return DefaultVal(val)

class Discard(tuple):
    """
    `Discard` should be placed after a field name in a chain. 
    `Discard` is used to indicate that if a key in the input dictionary contains a particular value, this
    key should be regarded as absent from the dictionary.

    >>> schema = Schema(
            ['name', Type(str)],
            ['address', Discard(''), Type(str)]
        )

    >>> schema.validate({'name': 'Marcel Bichon', 'address': ''})
    ...
    ValidationError: {'address': 'Field is missing.'}

    It can prove useful to combine `Discard` with `Optional`:

    >>> schema = Schema(
            ['name', Type(str)],
            ['address', Discard(''), Optional, Type(str)]
        )

    >>> schema.validate({'name': 'Marcel Bichon', 'address': ''})
    {'name': 'Marcel Bichon'}

    Or with `Default`:

    >>> household_schema = Schema(
            ['married', Type(bool)],
            ['number of children', Discard(''), Default('0'), int, Save]
        )

    >>> household_schema.validate({'married': False, 'number of children': ''})
    {'married': False, 'number of children': 0}

    You can decide to discard multiple values. For example:

    ['task_id', Discard('', None)]

    would discard both `''` and `None`.
    """
    def __new__(cls, *args):
        return super(Discard, cls).__new__(cls, args)

class Chain(object):

    def _parse_start(self, instructions):
        if isinstance(instructions[0], Filter):
            self._parse_filters(instructions)
        elif callable(instructions[0]):
            self._parse_filters((Apply(instructions[0]),) + instructions[1:])
        else:
            self.field = [instructions[0]]
            self._parse_field_options(instructions[1:])

    def _parse_field_options(self, instructions):
        i = 0
        if i < len(instructions) and isinstance(instructions[i], Discard):
            self.discard = instructions[i]
            i += 1
        if i < len(instructions) and instructions[i] is Optional:
            self.optional = True
            i += 1
        if i < len(instructions) and isinstance(instructions[i], DefaultBase):
            self.default = instructions[i]
            i += 1
        self._parse_filters(instructions[i:])

    def _parse_filters(self, instructions):
        for i, instr in enumerate(instructions):
            if isinstance(instr, StorageInstruction):
                return self._parse_storage(instructions[i:])
            self.filters.append(to_filter(instr))

    def _parse_storage(self, instructions):
        storage_instruction = instructions[0]
        if not self.field:
            if storage_instruction is Delete:
                raise ValueError(
                    "Can't use Delete without a field name at the start of the chain."
                )
            if isinstance(storage_instruction, MoveTo):
                raise ValueError(
                    "Can't use MoveTo without a field name at the start of the chain."
                )
        self.storage_instruction = storage_instruction
        if len(instructions) > 1:
            raise ValueError(
                "Can't add additional instructions after %s." % storage_instruction.classname()
            )
    
    def __init__(self, *instructions):
        self.field = []
        self.discard = ()
        self.optional = False
        self.default = None        
        self.filters = []
        self.storage_instruction = None
        if instructions:
            self._parse_start(instructions)

class Schema(Filter):
    """
    Defines a sequence of validation and/or transformation rules, to validate and/or transform
    python dictionaries.

    Example:
        address_form = Schema(
            ['house number', Type(int), range(1, 10000)],
            ['street', Type(str), Length(min=5, max=255)],
            ['zipcode', Type(str), Regex('\d{4,5}')],
            ['country', Type(str), ('France', 'Belgium', 'Switzerland')]
        )

    To validate a dictionary, use the `validate` method:
        
        address = {
            'house number': 91,
            'street': 'rue de rivoli',
            'zipcode': '75011',
            'country': 'France'
        }
        try:    
            address_form.validate(address)
        except ValidationError as exc:
            print(exc.error_details)

    Quite often, not only do you want to validate the data, you also want to transform it.

    When using the `validate` method, the original dictionary is never modified.
    It is, however, possible to obtain a transformed version of the input dictionary as a 
     return value of the `validate` method.
    For that, use the modification instructions when you define your schema.
    The modification instructions are Default, Delete, Discard, MoveTo, Save and SaveAs.

    If you don't use any of these instructions, the `validate` method will return a shallow copy of the 
    original with no modification.

    For example:

        >>> Schema(['age', round]).validate({'age': 25.4})
        
        {'age': 25.4}

    The modification doesn't show up in the return value.
    However, using Save:

        >>> Schema(['age', round, Save]).validate({'age': 25.4})

        {'age': 25}

    Using SaveAs:

        >>> Schema(['age', round, SaveAs('age_round')]).validate({'age': 25.4})

        {'age': 25.4, 'age_round': 25}
   
    A Schema is a Filter. Therefore you can reuse Schemas inside Schemas.

    Example:
    
        author_schema = Schema(
            ['name', Type(str)],
            ['biography', Type(str)],
            ['website', Optional, Url]
        )
        
        book_schema = Schema(
            ['title', Type(str)],
            ['isbn13', Type(str), Length(13,13), Regex('\d+')],
            ['author', author_schema]
        )

    The Schema constructor takes an optional `unexpected_keys` argument.
    It defines what should be done with keys that don't appear in your schema.

    With `unexpected_keys=Schema.FAIL`, the schema will refuse to validate a dictionary if it 
     contains unknown keys. This is the default.
    With `unexpected_keys=Schema.KEEP`, the schema will validate a dictionary even if it 
     contains unknown keys. These unknown items will appear in the output dictionary (the dictionary 
     returned by the `validate` method).
    With `unexpected_keys=Schema.DELETE`, the schema will agree to validate a dictionary that
     contains unknown keys, but these items won't appear in the output dictionary.
    """

    FAIL = 1
    KEEP = 2
    DELETE = 3

    def __init__(self, *lists, **kwargs):
        unexpected_keys, = _get_kwargs(kwargs, (('unexpected_keys', Schema.FAIL),))
        self.chains = [Chain(*lst) for lst in lists]
        self.unexpected_keys_policy = unexpected_keys
        self.expected_fields = set(functools.reduce(
            list.__add__,
            (chain.field for chain in self.chains),
            []
        ))

    def run(self, dict_):
        Type(dict, subclasses = True).run(dict_)
        dct = dict_.copy()
        errors = {}
        policy = self.unexpected_keys_policy
        if policy is not Schema.KEEP:
            for key in dict_:
                if key not in self.expected_fields:
                    if policy is Schema.FAIL:
                        errors[key] = _("Unexpected key {key}.").format(key = repr(key))
                    del dct[key]

        for chain in self.chains:

            if chain.field:
                field = chain.field[0]
                if field in dct:
                    if dct[field] in chain.discard:
                        del dct[field]
                try:
                    value = dct[field]
                except KeyError:
                    if chain.optional:
                        continue
                    if chain.default:
                        if errors and isinstance(chain.default, DefaultFunc):
                            continue # avoid working with potentially invalid data
                        dct[field] = value = chain.default.getvalue(dct)
                    else:
                        errors[field] = _("Field is missing.")
                        continue
            else:
                # we work on the whole document
                if errors:
                    continue # avoid working with potentially invalid data
                value = dct
            
            # applying filters
            error = False
            for f in chain.filters:
                try:
                    value = f.run(value)
                except ValidationError as exc:
                    if chain.field:
                        errors[chain.field[0]] = exc.error_details
                    else:
                        errors['*'] = exc.error_details               
                    error = True
                    break
            if error:
                if isinstance(chain.storage_instruction, (SaveAs, MoveTo)):
                    errors[chain.storage_instruction.name] = _("Couldn't compute field.")
                continue

            if chain.storage_instruction:
                if not chain.field and chain.storage_instruction is Save:
                    dct = value
                else:
                    chain.storage_instruction.execute(dct, chain.field[0] if chain.field else None, value)

        if errors:
            raise ValidationError(errors)
        return dct


    def validate(self, dict_, lang = None):
        # we only override it to add the docstring
        """
        Validates a dictionary against the defined schema.
        
        On success, returns a shallow copy of the original dictionary.
        If the schema uses modification instructions (Default, Delete, Discard, MoveTo, Save or SaveAs),
         the return value will be a modified version of the original dictionary.

        On failure (if the input doesn't validate against the schema rules), a ValidationError is raised.
        The error details are to be found in the error_details attribute of the ValidationError object.

        Use the optional `lang` argument to translate the error messages in the desired language.

        Example:

        >>> address_schema = Schema(
                ['house number', Type(str, int), int, Range(1, 10000), Save],
                ['street', Type(str), Length(max=200)],
                ['zipcode', Type(str), Regex('\d{4,5}')],
                ['city', Type(str), Length(max=100), str.title, Save],
            )

        >>> try:
                dict_out = address_schema.validate(
                    {'house number': '3', 'street': 'van Rossum avenue', 'zipcode': '1011', 'city': 'amsterdam'},
                    lang = 'fr'
                )
            except ValidationError as exc:
                print(exc.error_details)

        >>> dict_out
        {'city': 'Amsterdam', 'house number': 3, 'street': 'van Rossum avenue', 'zipcode': '1011'}

        """
        return super(Schema, self).validate(dict_, lang)
                  
class StorageInstruction(object):
    def execute(self, dct, field, value):
        raise NotImplementedError

    @classmethod
    def classname(cls):
        return cls.__name__

class _SaveClass(StorageInstruction):
    """
    Use Save at the end of a chain in order to save the current value under the current key.
    Keep in mind that it doesn't modify the input dictionary. The modification is seen only
     in the output dictionary (the return value of the `validate` method).

    Example:
        
        >>> original = {'age': 25.4}

        >>> Schema(['age', round, Save]).validate()
        {'age': 25}

        >>> original
        {'age': 25.4}        

    """

    def execute(self, dct, field, value):
        dct[field] = value

Save = _SaveClass()

del _SaveClass

class SaveAs(StorageInstruction):
    """
    Use SaveAs at the end of chain to save the current value under another key.
    Keep in mind that it doesn't modify the input dictionary. The modification is seen only
     in the output dictionary (the return value of the `validate` method).

    Example:

    >>> Schema(['age', round, SaveAs('age_round')]).validate({'age': 25.4})
    {'age': 25.4, 'age_round': 25}
        
    """

    def __init__(self, name):
        self.name = name

    def execute(self, dct, field, value):
        dct[self.name] = value

class MoveTo(StorageInstruction):

    """
    Use MoveTo at the end of a chain to move an item under another key, and delete the current key.
    Keep in mind that it doesn't modify the input dictionary. The modification is seen only
     in the output dictionary (the return value of the `validate` method).

    Example:

    >>> Schema(['age', round, MoveTo('age_round')]).validate({'age': 25.4})
    {'age_round': 25}
        
    """

    def __init__(self, name):
        self.name = name

    def execute(self, dct, field, value):
        dct[self.name] = value
        try:
            del dct[field]
        except KeyError:
            pass

class _DeleteClass(StorageInstruction):

    """
    Use Delete at the end of a chain to delete the current key.
    Keep in mind that it doesn't modify the input dictionary. The modification is seen only
     in the output dictionary (the return value of the `validate` method).

    Example:

        >>> from passlib.hash import bcrypt

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
                ['password2', Delete]
            )

        >>> registration_form.validate(
                {'username': 'TheKing', 'password': 'hackme', 'password2': 'hackme'}
            )

        This returns the dictionary:
        
            {
                'username': 'TheKing',
                'password': '$2a$12$ppHoYoDQkligaQ2jTyHysuPKmLwxBzSGulD1FkllLXx7OgEtdq8d.'
            }

    """
    
    def execute(self, dct, field, value):
        try:
            del dct[field]
        except KeyError:
            pass

Delete = _DeleteClass()

del _DeleteClass

class Apply(Filter):

    def __init__(self, unary_function, catch = (Exception,),
     error_message = None ):
        self.unary_function = unary_function
        self.catch = catch
        self.error_message = error_message

    def run(self, value):
        try:
            return self.unary_function(value)
        except self.catch as exc:
            if self.error_message:
                raise ValidationError(self.error_message)
            else:
                raise ValidationError(str(exc))

class Assert(Filter):

    def __init__(self, unary_test, error_message = _("Incorrect value.")):
        self.unary_test = unary_test
        self.error_message = error_message

    def run(self, value):
        if self.unary_test(value):
            return value
        else:
            raise ValidationError(self.error_message)

class In(Filter):

    def __init__(self, collection, error_message = _("Incorrect value.")):
        self.collection = collection
        self.error_message = error_message

    def run(self, value):
        if value not in self.collection:
            raise ValidationError(self.error_message)
        return value

class Do(Filter):

    """
    Creates a new filter from existing filters. The filters will be applied one after another.
    For example, the Url filter is defined this way:

        Url = Do(
            Type(str),
            Length(max=2083),
            Regex("# a huge regex here"),
            error_message = _("This is not a valid url.")
        )

    As you can see, it is possible to specify an error message.
    This error message will override any error message that could be triggered by 
     the filters in the sequence.
    """ 

    def __init__(self, *filters, **kwargs):
        error_message, = _get_kwargs(kwargs, (('error_message', None),))
        self._filters = [to_filter(f) for f in filters]
        self.error_message = error_message

    def run(self, value):
        for f in self._filters:
            try:
                value = f.run(value)
            except ValidationError:
                if self.error_message:
                    raise ValidationError(self.error_message)
                else:
                    raise
        return value

class Each(Filter):

    """
    Use `Each` if you want to apply a filter to every element of a collection.

    Example (validating that a field is a list of integers):

        >>> schema = Schema(
            ['integers', Type(list), Each(Type(int))]
        )

        >>> schema.validate({'integers': [1, 2, 3, 5]})
        {'integers': [1, 2, 3, 5]}

        >>> schema.validate({'integers': [8, "broccoli", 21]})
        ...
        ValidationError: {'integers': 'Item #2: Wrong type. Expected int. Got str instead.'}

    It can prove useful to use `Each` in combination with `Do` in order to apply many filters
     to each elements of a list. For example:

    >>> schema = Schema(
        ['keywords', Type(list), Each( Do( Type(str), Length(min=2, max=30), str.lower) ), Save]
    )

    >>> schema.validate({'keywords': ['PANCAKES', 'FOOD', 'Recipe']})
    {'keywords': ['pancakes', 'food', 'recipe']}
    """

    ITEM_START = 1

    def __init__(self, filtr):
        self._filter = filtr

    def run(self, value):
        result = []
        for i, val in enumerate(value):
            try:
                result.append(self._filter.run(val))
            except ValidationError as exc:
                raise ValidationError(
                    _("Item #%s: ") % (i + self.__class__.ITEM_START) + exc.error_details
                )
        if isinstance(value, (tuple, set)):
            result = type(value)(result)
        return result

class Each0(Each):
    """
    Same as Each but the items are numbered from 0 when generating the error messages.
    """
    ITEM_START = 0

Each1 = Each

class Type(Filter):
    """
    Check a value's type.

    Example:
    
        schema = Schema(
            ['width', Type(int, float)],
            ['height', Type(int, float)],
        )

    By default, the type must match exactly.
    Use `subclasses = True` to allow for subclasses (equivalent of `isinstance`).

    Example:

        schema = Schema(
            ['text', Type(basestring, subclasses = True)]
        )

        # This would allow all subclasses of basestring.
    """
    def __init__(self, type_, *types, **kwargs):
        subclasses, = _get_kwargs(kwargs, (('subclasses', False),))
        self.types = (type_,) + tuple(types)
        self._subclasses = subclasses
    
    def run(self, value):
        type_ = type(value)
        if (
            (self._subclasses and not (any (issubclass(type_, t) for t in self.types)))
            or
            (not self._subclasses and type_ not in self.types)
        ):
            types_str = ', '.join(t.__name__ for t in self.types)
            if len(self.types) == 1:
                raise ValidationError(
                    _("Wrong type. Expected {type}. Got {wrong_type} instead.").format(
                        type = types_str,
                        wrong_type = type_.__name__
                    )
                )
            else:
                raise ValidationError(
                    _("Wrong type. Expected one of {types}. Got {wrong_type} instead.").format(
                        types = types_str,
                        wrong_type = type_.__name__
                    )
                )
        return value

class Length(Filter):

    """
    Check for length.
    
    Example:
        
        schema = Schema(
            ['username', Type(str), Length(min=5, max=30)]
        )        

    You can customize error messages using the following keyword arguments:

    `empty_error`: message used when the length is 0 and it shouldn't be
    `too_short_error`: message used when the value is too short
    `too_long_error`: message used when the value is too long
    `exact_length_error`: message used when the value doesn't have the good
      length, and there's only one length possible (min == max)

    Example:

        schema = Schema(
            ['blog_post', Type(str)],
            ['categories',
                Type(list),
                Each(Type(str)),
                Length(
                    min=1,
                    max=5,
                    empty_error = "Please select at least one category.",
                    too_long_error = "Maximum {max_length} categories."
                )
            ]          
        ) 
    """

    empty_error = _("This value shouldn't be empty.")
    too_short_error = _("The value is too short. Min length is {min_length}.")
    too_long_error = _("The value is too long. Max length is {max_length}.")
    exact_length_error = _("The length should be {length}.")

    def __init__(
        self, min=0, max=None, empty_error = None, too_short_error = None,
        too_long_error = None, exact_length_error = None
    ):  
        self.min = min
        self.max = max
        self.empty_error = empty_error or self.__class__.empty_error
        self.too_short_error = too_short_error or self.__class__.too_short_error
        self.too_long_error = too_long_error or self.__class__.too_long_error
        self.exact_length_error = exact_length_error or self.__class__.exact_length_error

    def run(self, value):
        l = len(value)
        if l < self.min:
            if l == 0:
                raise ValidationError(self.empty_error)
            elif self.min == self.max:
                raise ValidationError(self.exact_length_error.format(length = self.min))
            else:
                raise ValidationError(
                    self.too_short_error.format(min_length = self.min)
                )
        if self.max is not None and l > self.max:
            if self.min == self.max:
                raise ValidationError(self.exact_length_error.format(length = self.min))
            raise ValidationError(self.too_long_error.format(max_length = self.max))
        return value        

class Range(Filter):
    """
    Set minimum and or maximum values allowed.

    Example:
        laptop_config_schema = Schema(
            ['ram(Go)', int, Range(8, 16)],
            ['#cpu cores', int, Range(min=4)],
            ['screen size(inches)', float, Range(14.1, 15.4)],
            ['weight(kg)', float, Range(max=3.5)]
        )
    """

    min_message = _("The minimum is {min}.")
    max_message = _("The maximum is {max}.")

    def __init__(self, min=None, max=None, min_message = None, max_message = None):
        self.min = min
        self.max = max
        self.min_message = min_message or self.__class__.min_message
        self.max_message = max_message or self.__class__.max_message

    def run(self, value):
        if self.min is not None:
            if value < self.min:
                raise ValidationError(self.min_message.format(min = self.min))
        if self.max is not None:
            if value > self.max:
                raise ValidationError(self.max_message.format(max = self.max))
        return value

class Regex(Filter):
    """
    Regex filter

    Example:
    
        >>> schema = Schema(['username', Regex('[A-Za-z][-_A-Za-z0-9]+')])
        
        >>> schema.validate({'username': "The King"})
        ...
        ValidationError: {'username': 'Incorrect value'}

        >>> schema.validate({'username': "The-King"})
        {'username': 'The-King'}        
    """

    def __init__(self, regex, flags = 0, error_message = _("Incorrect value.")):
        if isinstance(regex, basestring):
            if not regex.startswith('^'):
                regex = '^' + regex
            if not regex.endswith('$'):
                regex = regex + '$'
            self.regex = re.compile(regex, flags)
        else:
            self.regex = regex        
        self.error_message = error_message

    def run(self, value):
        if not self.regex.match(value):
            raise ValidationError(self.error_message)
        return value

def to_filter(f):
    if isinstance(f, Filter):
        return f
    elif f is int:
        return ToInt # to get the i18ned error messages
    elif f is float:
        return ToFloat # same as above
    elif callable(f):
        return Apply(f)
    elif hasattr(f, '__contains__'):
        return In(f) 
    else:
        raise ValueError("%s is not a valid filter" % repr(f)) 

ToInt = Apply(int, error_message = _("This should be an integer.")) # useful to get i18ned error messages
ToFloat = Apply(float, error_message = _("This should be a number."))


# function to extract named keyword arguments from **kwargs (required for Python 2
# compatibility, see https://github.com/leforestier/naval/issues/1 )
def _get_kwargs(kwargs, defaults):
    result = []
    for (key, default) in defaults:
        result.append(kwargs.pop(key, default))
    if kwargs:
        raise ValueError(
            "Unsupported keyword argument {kwarg}.".format(
                kwarg = next(k for k in kwargs.keys())
            )
        )
    return result
