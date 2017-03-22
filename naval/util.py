from validators import email, domain, ValidationFailure
from naval.core import *
from postpone import LazyString as _

__all__ = ['Email', 'Domain', 'Url']

Email = Assert(
    lambda v: not isinstance(email(v, whitelist = ()), ValidationFailure),
    error_message = _("This is not a valid email address.")
)

Email.__doc__ = """
    Email validator.
    This validator uses the email validator from the "validators" library: https://github.com/kvesteri/validators
"""

Domain = Assert(
    lambda v: not isinstance(domain(v), ValidationFailure),
    error_message = _("This is not a valid domain name.")
)

Domain.__doc__ = """
    Domain name validator.
    This validator uses the domain name validator from the "validators" library: https://github.com/kvesteri/validators
"""

Url = Do(
    Type(str),
    Length(max=2083),
    # regex stolen from the php Spoon Library: https://github.com/spoon/library/blob/master/spoon/filter/filter.php
    Regex(
        r'(?:(?:https?|ftp)://)(?:\S+(?::\S*)?@)?(?:(?!10(?:\.\d{1,3}){3})(?!127(?:\.\d{1,3}){3})(?!169\.254(?:\.\d{1,3}){2})(?!192\.168(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\xa1-\xff0-9]+-?)*[a-z\xa1-\xff0-9]+)(?:\.(?:[a-z\xa1}-\xff0-9]+-?)*[a-z\xa1-\xff0-9]+)*(?:\.(?:[a-z\xa1-\xff]{2,})))(?::\d{2,5})?(?:/[^\s]*)?'
    ),
    error_message = _("This is not a valid url.")
)
Url.__doc__ = """
    Url validator.
    The regex used is stolen from the php Spoon Library: https://github.com/spoon/library/blob/master/spoon/filter/filter.php    
"""

