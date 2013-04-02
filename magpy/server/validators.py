"""Validation code, much of it originally forked from Django."""
from __future__ import print_function

# Import half of the friggin stdlib
import platform
import re
import urllib
import urllib2
import urlparse
import operator
import types
import datetime
from decimal import Decimal
import xml.parsers.expat
from numbers import Number
from functools import reduce
import six


def validate_model_instance(model,
                            instance,
                            handle_none=False,
                            embedded_models=None,
                            callback=None):
    """Validate a single instance.
    Required Arguments:

    * model - the model definition (dictionary or dictionary-like object)
    * instance - the instance (dictionary or dictionary-like object)

    Optional Arguments:

    * handle_none - set to True to allow None to always be valid data,
    default is False. This can be useful in dealing data that came
    (at least at one time) from SQL data.
    * embedded_models - a dictionary of model definitions, where the key is
    the model name, value is the model definition. This dictionary is used
    to validate embedded instances.
    * callback - an optional callback to run after validation.
    """
    model_validator = ModelValidator(model,
                                     handle_none=handle_none,
                                     embedded_models=embedded_models)
    if callback:
        try:
            model_validator.validate_instance(instance)
        except ValidationError:
            callback(False, instance)
        else:
            callback(True, instance)
    else:
        model_validator.validate_instance(instance)


def parse_instance(instance, result_set):
    """Add the models that an instance uses to result_set."""
    for key, value in six.iteritems(instance):
        if key == '_model':
            result_set.add(value)
        if isinstance(value, dict):
            if '_model' in value:
                result_set.add(value['_model'])
                parse_instance(value, result_set)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    parse_instance(item, result_set)


def validate_modification(model,
                          modification,
                          handle_none=False,
                          embedded_models=None,
                          callback=None):
    """We validate a modification.
    This assumes the existing version has already been through validation.

    TODO: support embedded instances.
    """

    model_validator = ModelValidator(model,
                                     handle_none=handle_none,
                                     embedded_models=embedded_models)

    try:
        model_validator.validate_modification(model, modification)
    except ValidationError:
        if callback:
            return callback(False, modification)
        else:
            raise
    else:
        if callback:
            return callback(True, modification)


class ModelValidator(object):
    """Validates instances according to a model."""
    def __init__(self,
                 model,
                 handle_none=False,
                 dispatcher=None,
                 embedded_models=None):
        if dispatcher:
            self.dispatch = dispatcher
        else:
            self.dispatch = dict(DISPATCHER)
        self.model = model
        self.model_keys = set(model.keys())
        self.handle_none = handle_none

        self.embedded_models = embedded_models
        try:
            self.model_keys.remove('modeldescription')
        except KeyError:
            pass
        try:
            self.model_keys.remove(u'_id')
        except KeyError:
            pass
        try:
            self.model_keys.remove('_permissions')
        except KeyError:
            pass
        try:
            self.model_keys.remove('_view')
        except KeyError:
            pass
        try:
            self.model_keys.remove('_model')
        except KeyError:
            pass

    def do_dispatch(self, field_type, field_data):
        """Do the dispatch."""
        if field_type == 'Embedded' or field_type == 'EmbeddedList':
            return self.dispatch[field_type](field_data,
                                             self.embedded_models)
        self.dispatch[field_type](field_data)

    def validate_field(self, field_type, field_data):
        """Validate if the field_data is valid for the field_type."""
        try:
            self.do_dispatch(field_type, field_data)
        except ValidationError:
            if field_data is None and self.handle_none:
                pass
            else:
                raise

    def validate_instance(self, instance):
        """Validate that the instance meets the requirements of the model."""
        instance_keys = set(instance.keys())
        try:
            instance_keys.remove('_model')
        except KeyError:
            raise OrphanedInstance('The instance does not have a model key.')
        try:
            instance_keys.remove('_id')
        except KeyError:
            pass
        try:
            instance_keys.remove('_meta')
        except KeyError:
            pass
        try:
            instance_keys.remove('_view')
        except KeyError:
            pass
        try:
            instance_keys.remove('_versional_comment')
        except KeyError:
            pass
        try:
            instance_keys.remove('_operation')
        except KeyError:
            pass
        try:
            instance_keys.remove('_permissions')
        except KeyError:
            pass

        # Sanity checks
        self.check_for_unknown_fields(instance_keys)
        self.check_for_missing_fields(instance_keys)

        # Check for valid fields
        try:
            validity = [self.validate_field(self.model[field]['field'],
                                            instance[field]) for \
                            field in instance_keys]
        except TypeError:
            print("Died on %s " % instance['_id'])
            print("Perhaps invalid model?")
            raise

        # If they are all valid, then do nothing
        return None

    def check_for_unknown_fields(self, instance_keys):
        """Check for nonsense extra fields."""
        extra_fields = instance_keys - self.model_keys

        if extra_fields:
            if len(extra_fields) == 1:
                raise InvalidFields(extra_fields.pop())
            else:
                raise InvalidFields(tuple(extra_fields))

    def check_for_missing_fields(self, instance_keys):
        """Some fields are allowed to be missing, others are just AWOL."""
        missing_fields = self.model_keys - instance_keys
        if missing_fields:
            # Some fields are allowed to be missing, others are just AWOL.
            awol = set()
            for field in missing_fields:
                try:
                    if self.model[field]['required'] == True:
                        awol.add(field)
                except KeyError:
                    awol.add(field)
            if awol:
                if len(awol) == 1:
                    raise MissingFields(awol.pop())
                else:
                    raise MissingFields(tuple(awol))

    def validate_modification(self, model, modification):
        for modification_name, modification_value in six.iteritems(modification):
            validator = MODIFICATION_DISPATCHER[modification_name]
            for tfield, value in six.iteritems(modification_value):
                field, field_type = self.get_field(tfield, model)
                validator(self, model, field, field_type, value)

    def get_field(self, field, model):
        """If no dots, it is a top level field,
        otherwise look through the models for the field."""
        if not '.' in field:
            return field, model[field]['field']
        parts = field.split('.')
        field_name = parts.pop(-1)
        if field_name == '$':
            field_name = parts.pop(-1)
        model_name = parts.pop(-1)
        if model_name == '$':
            model_name = parts.pop(-1)

        if model_name in self.embedded_models:
            if field_name in self.embedded_models[model_name]:
                field = self.embedded_models[model_name][field_name]
        elif model_name in model:
            real_model_name = model[model_name].get('resource', model_name)
            field = self.embedded_models[real_model_name][field_name]

        field_type = field['field']
        return field, field_type

def get_all_modification_modelnames(model, modification):
    """Get all model names from a modification."""
    models = set()
    tree = []
    for modification_type, field in six.iteritems(modification):
        tree.append(field)
        for fieldname, fieldvalue in six.iteritems(field):
            tree.append(fieldname)
            if '.' in fieldname:
                parts = fieldname.split('.')
                parts = [part for part in parts if part != '$']
                for part in parts[:-1]:
                    tree.append(part)
                    models.add(part)

    real_models = set()
    unknown_keys = set()
    for model_name in models:
        # Maybe it is a top level field
        if model_name in model:
            real_models.add(model[model_name].get('resource', model_name))
            continue
        # It is not a top level field
        if isinstance(model_name, int):
            # It is a positional operator, skip it
            continue
        # Not sure what it is yet.
        unknown_keys.add(model_name)

    # Get rid of anything we know about.
    # Maybe later we do something else
    unknown_keys = unknown_keys - real_models

    return list(real_models), list(unknown_keys)

class InvalidInstance(Exception):
    """An instance has not met the requirements of the model.

    If you do not care why an instance is invalid, you can
    use this superclass and it will catch all subclasses."""
    pass


class InvalidFields(InvalidInstance):
    """An instance has a field(s) which is not defined in the model."""
    pass


class MissingFields(InvalidInstance):
    """An instance is missing a field(s) which is required by the model."""
    pass


class OrphanedInstance(InvalidInstance):
    """An instance is not associated with a class."""
    pass


URL_VALIDATOR_USER_AGENT = 'Django (http://www.djangoproject.com/)'
NON_FIELD_ERRORS = '__all__'


class ValidationError(Exception):
    """An error while validating data."""
    def __init__(self, message, code=None, params=None):
        """
        ValidationError can be passed any object that can be printed (usually
        a string), a list of objects or a dictionary.
        """
        super(ValidationError, self).__init__(message)

        if isinstance(message, dict):
            self.message_dict = message
            # Reduce each list of messages into a single list.
            message = reduce(operator.add, message.values())

        if isinstance(message, list):
            self.messages = [force_unicode(msg) for msg in message]
        else:
            self.code = code
            self.params = params
            message = force_unicode(message)
            self.messages = [message]

    def __str__(self):
        # This is needed because, without a __str__(), printing an exception
        # instance would result in this:
        # AttributeError: ValidationError instance has no attribute 'args'
        # See http://www.python.org/doc/current/tut/node10.html#handling
        if hasattr(self, 'message_dict'):
            return repr(self.message_dict)
        return repr(self.messages)

    def __repr__(self):
        if hasattr(self, 'message_dict'):
            return 'ValidationError(%s)' % repr(self.message_dict)
        return 'ValidationError(%s)' % repr(self.messages)

    def update_error_dict(self, error_dict):
        """Update the error dict with messages."""
        if hasattr(self, 'message_dict'):
            if error_dict:
                for k, value in self.message_dict.items():
                    error_dict.setdefault(k, []).extend(value)
            else:
                error_dict = self.message_dict
        else:
            error_dict[NON_FIELD_ERRORS] = self.messages
        return error_dict

# These values, if given to validate(), will trigger the self.required check.
EMPTY_VALUES = (None, '', [], (), {})


class RegexValidator(object):
    """
    A validator is a callable that takes a value and raises a
    ValidationError if it doesn't meet some criteria.
    Validators can be useful for re-using validation logic
    between different types of fields.

    Parameters:

    regex -- If not None, overrides regex.
    Can be a regular expression string or a pre-compiled regular expression.
    message -- If not None, overrides message.
    code -- If not None, overrides code.

    regex

    The regular expression pattern to search for the provided value,
    or a pre-compiled regular expression.
    Raises a ValidationError with message and code if no match is found.
    By default, matches any string (including an empty string).

    message

    The error message used by ValidationError if validation fails.
    Defaults to "Enter a valid value".

    code

    The error code used by ValidationError if validation fails.
    Defaults to "invalid".

    """
    regex = ''
    message = u'Enter a valid value.'
    code = 'invalid'

    def __init__(self, regex=None, message=None, code=None):
        if regex is not None:
            self.regex = regex
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code

        # Compile the regex if it was not passed pre-compiled.
        if isinstance(self.regex, basestring):
            self.regex = re.compile(self.regex)

    def __call__(self, value):
        """
        Validates that the input matches the regular expression.
        """
        if not self.regex.search(smart_unicode(value)):
            raise ValidationError(self.message, code=self.code)


class URLValidator(RegexValidator):
    """
    A RegexValidator that ensures a value looks like a URL
    and optionally verifies that the URL actually exists
    (i.e., doesn't return a 404 status code).

    Raises an error code of 'invalid' if it doesn't look like a URL,
    and a code of 'invalid_link' if it doesn't exist.

    Parameters:

    verify_exists -- Sets verify_exists. Defaults to False.
    validator_user_agent -- Sets validator_user_agent.
    Defaults to URL_VALIDATOR_USER_AGENT or,
    if that setting is set to a null value,
    "Django (http://www.djangoproject.com/)".

    validator_user_agent

    If verify_exists is True, Django uses this value as
    the "User-agent" for the request.

    verify_exists

    If set to True, this validator checks that the URL actually exists
    and resolves, by issuing a request to it.

    This is really handy, but should only be used for trusted users,
    e,g. staff-only mode.
    If you allow public-facing code to use this, there is potential for
    a denial of service attack.

    This option is to be used between consenting adults only!

    This problem is particularly pronounced in Python 2.5 and below
    since the underlying socket libraries in Python do not have a timeout.
    This can manifest as a security problem in three different ways:

    1. An attacker can supply a slow-to-respond URL.
    Each request will tie up a server process for a period of time;
    if the attacker is able to make enough requests,
    they can tie up all available server processes.

    2. An attacker can supply a URL under his or her control,
    and which will simply hold an open connection indefinitely.
    Due to the lack of timeout, the Django process attempting to
    verify the URL will similarly spin indefinitely.
    Repeating this can easily tie up all available server processes.

    3. An attacker can supply a URL under his or her control which
    not only keeps the connection open, but also sends an unending
    stream of random garbage data.
    This data will cause the memory usage of the Django process
    (which will hold the response in memory) to grow without bound,
    thus consuming not only server processes but also server memory.

    Note, Python 2.5 is not actually supported by Magpy because of the
    Python 3 compatibility.

    For Python versions 2.6 and above, which support setting a timeout,
    a timeout of ten seconds will be set;

    Therefore only use in trusted contexts and where the utility
    is sufficient to warrant the potential risks it creates.

    """
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)'
        r'+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def __init__(self, verify_exists=False,
                 validator_user_agent=URL_VALIDATOR_USER_AGENT):
        super(URLValidator, self).__init__()
        self.verify_exists = verify_exists
        self.user_agent = validator_user_agent

    def __call__(self, value):
        try:
            super(URLValidator, self).__call__(value)
        except ValidationError, excptn:
            # Trivial case failed. Try for possible IDN domain
            if value:
                value = smart_unicode(value)
                scheme, \
                    netloc, \
                    path, \
                    query, \
                    fragment = urlparse.urlsplit(value)
                try:
                    netloc = netloc.encode('idna')  # IDN -> ACE
                except UnicodeError:  # invalid domain part
                    raise excptn
                url = urlparse.urlunsplit((scheme,
                                           netloc,
                                           path,
                                           query,
                                           fragment))
                super(URLValidator, self).__call__(url)
            else:
                raise
        else:
            url = value

        if self.verify_exists:
            import warnings
            warnings.warn(
                "The URLField verify_exists argument has intractable security "
                "and performance issues. Accordingly, it has been deprecated.",
                DeprecationWarning
                )

            headers = {
                "Accept": "text/xml,application/xml,application/xhtml+xml,"
                "text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5",
                "Accept-Language": "en-us,en;q=0.5",
                "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.7",
                "Connection": "close",
                "User-Agent": self.user_agent,
            }
            url = url.encode('utf-8')
            # Quote characters from the unreserved set, refs #16812
            url = urllib.quote(url, "!*'();:@&=+$,/?#[]")
            broken_error = ValidationError(
                u'This URL appears to be a broken link.',
                code='invalid_link')
            try:
                req = urllib2.Request(url, None, headers)
                req.get_method = lambda: 'HEAD'
                #Create an opener that does not support local file access
                opener = urllib2.OpenerDirector()

                #Don't follow redirects, but don't treat them as errors either
                error_nop = lambda *args, **kwargs: True
                http_error_processor = urllib2.HTTPErrorProcessor()
                http_error_processor.http_error_301 = error_nop
                http_error_processor.http_error_302 = error_nop
                http_error_processor.http_error_307 = error_nop

                handlers = [urllib2.UnknownHandler(),
                            urllib2.HTTPHandler(),
                            urllib2.HTTPDefaultErrorHandler(),
                            urllib2.FTPHandler(),
                            http_error_processor]
                try:
                    import ssl
                except ImportError:
                    # Python isn't compiled with SSL support
                    pass
                else:
                    handlers.append(urllib2.HTTPSHandler())
                list(map(opener.add_handler, handlers))
                if platform.python_version_tuple() >= (2, 6):
                    opener.open(req, timeout=10)
                else:
                    opener.open(req)
            except ValueError:
                raise ValidationError(u'Enter a valid URL.', code='invalid')
            except:  # urllib2.URLError, httplib.InvalidURL, etc.
                raise broken_error


class EmailValidator(RegexValidator):
    """
    A RegexValidator instance that ensures a value looks like an email address.
    """

    def __call__(self, value):
        try:
            super(EmailValidator, self).__call__(value)
        except ValidationError as excptn:
            # Trivial case failed. Try for possible IDN domain-part
            if value and u'@' in value:
                parts = value.split(u'@')
                try:
                    parts[-1] = parts[-1].encode('idna')
                except UnicodeError:
                    raise excptn
                super(EmailValidator, self).__call__(u'@'.join(parts))
            else:
                raise

EMAIL_RE = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+"
    r"(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    # quoted-string, see also http://tools.ietf.org/html/rfc2822#section-3.2.5
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|'
    r'\\[\001-\011\013\014\016-\177])*"'
    r')@((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$)'  # domain
    r'|\[(25[0-5]|2[0-4]\d|[0-1]?\d?\d)'
    r'(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\]$',
    re.IGNORECASE)  # literal form, ipv4 address (SMTP 4.1.3)
validate_email = EmailValidator(EMAIL_RE,
                                u'Enter a valid e-mail address.',
                                'invalid')

slug_re = re.compile(r'^[-\w]+$')
validate_slug = RegexValidator(
    slug_re,
    u"Enter a valid 'slug' consisting of letters, numbers, "
    u"underscores or hyphens.",
    'invalid')

ipv4_re = re.compile(r'^(25[0-5]|2[0-4]\d|[0-1]?\d?\d)'
                     r'(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}$')
validate_ipv4_address = RegexValidator(ipv4_re,
                                       'Enter a valid IPv4 address.',
                                       'invalid')


def validate_ipv6_address(value):
    """
    Check the validity of an IPv6 address.
    """
    if not is_valid_ipv6_address(value):
        raise ValidationError('Enter a valid IPv6 address.',
                              code='invalid')


def validate_ipv46_address(value):
    """
    Uses both validate_ipv4_address and validate_ipv6_address
    to ensure a value is either a valid IPv4 or IPv6 address.
    """
    try:
        validate_ipv4_address(value)
    except ValidationError:
        try:
            validate_ipv6_address(value)
        except ValidationError:
            raise ValidationError(u'Enter a valid IPv4 or IPv6 address.',
                                  code='invalid')

ip_address_validator_map = {
    'both': ([validate_ipv46_address],
             'Enter a valid IPv4 or IPv6 address.'),
    'ipv4': ([validate_ipv4_address],
             'Enter a valid IPv4 address.'),
    'ipv6': ([validate_ipv6_address],
             'Enter a valid IPv6 address.'),
}


def ip_address_validators(protocol, unpack_ipv4):
    """
    Depending on the given parameters returns the appropriate validators for
    the GenericIPAddressField.

    This code is here, because it is exactly the same for the
    model and the form field.
    """
    if protocol != 'both' and unpack_ipv4:
        raise ValueError(
            "You can only use `unpack_ipv4` if `protocol` is set to 'both'")
    try:
        return ip_address_validator_map[protocol.lower()]
    except KeyError:
        raise ValueError("The protocol '%s' is unknown. Supported: %s"
                         % (protocol, ip_address_validator_map.keys()))

# A RegexValidator instance that ensures a value is a comma-separated
# list of integers.
comma_separated_int_list_re = re.compile('^[\d,]+$')
validate_comma_separated_integer_list = RegexValidator(
    comma_separated_int_list_re,
    u'Enter only digits separated by commas.',
    'invalid')


class BaseValidator(object):
    """Base class of the validation classes defined below."""
    compare = lambda self, a, b: a is not b
    clean = lambda self, x: x
    message = u'Ensure this value is %(limit_value)s ' \
        u'(it is %(show_value)s).'
    code = 'limit_value'

    def __init__(self, limit_value):
        self.limit_value = limit_value

    def __call__(self, value):
        cleaned = self.clean(value)
        params = {'limit_value': self.limit_value, 'show_value': cleaned}
        if self.compare(cleaned, self.limit_value):
            raise ValidationError(
                self.message % params,
                code=self.code,
                params=params,
                )


class MaxValueValidator(BaseValidator):
    """
    Raises a ValidationError with a code of 'max_value' if value is
    greater than max_value."""

    compare = lambda self, a, b: a > b
    message = u'Ensure this value is less than or equal to %(limit_value)s.'
    code = 'max_value'


class MinValueValidator(BaseValidator):
    """
    Raises a ValidationError with a code of 'min_value' if
    value is less than min_value.
    """

    compare = lambda self, a, b: a < b
    message = u'Ensure this value is greater than or ' \
        u'equal to %(limit_value)s.'
    code = 'min_value'


class MinLengthValidator(BaseValidator):
    """
    Raises a ValidationError with a code of 'min_length'
    if the length of value is less than min_length.
    """
    compare = lambda self, a, b: a < b
    clean = lambda self, x: len(x)
    message = u'Ensure this value has at least ' \
        u'%(limit_value)d characters (it has %(show_value)d).'
    code = 'min_length'


class MaxLengthValidator(BaseValidator):
    """
    Raises a ValidationError with a code of 'max_length' if the
    length of value is greater than max_length.
    """
    compare = lambda self, a, b: a > b
    clean = lambda self, x: len(x)
    message = u'Ensure this value has at most %(limit_value)d ' \
        u'characters (it has %(show_value)d).'
    code = 'max_length'


def smart_unicode(stringy_thingy,
                  encoding='utf-8',
                  strings_only=False,
                  errors='strict'):
    """
    Returns a unicode object representing 'stringy_thingy'.
    Treats bytestrings using the 'encoding' codec.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    return force_unicode(stringy_thingy, encoding, strings_only, errors)


def smart_str(stringy_thingy,
              encoding='utf-8',
              strings_only=False,
              errors='strict'):
    """
    Returns a bytestring version of 'stringy_thingy',
    encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.

    smart_str is essentially the opposite of smart_unicode().
    It forces the first argument to a bytestring.
    The strings_only parameter has the same behavior as for
    smart_unicode() and force_unicode(). This is slightly different
    semantics from Python's builtin str() function,
    but the difference can be useful.
    """
    if strings_only and isinstance(stringy_thingy, (type(None), int)):
        return stringy_thingy
    if not isinstance(stringy_thingy, basestring):
        try:
            return str(stringy_thingy)
        except UnicodeEncodeError:
            if isinstance(stringy_thingy, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in stringy_thingy])
            return unicode(stringy_thingy).encode(encoding, errors)
    elif isinstance(stringy_thingy, unicode):
        return stringy_thingy.encode(encoding, errors)
    elif stringy_thingy and encoding != 'utf-8':
        return stringy_thingy.decode('utf-8', errors).encode(encoding, errors)
    else:
        return stringy_thingy


def is_protected_type(obj):
    """Determine if the object instance is of a protected type.

    Objects of protected types are preserved as-is when passed to
    force_unicode(strings_only=True).
    """
    return isinstance(obj, (
        type(None),
        int, long,
        datetime.datetime, datetime.date, datetime.time,
        float, Decimal)
    )


class WrappedUnicodeDecodeError(UnicodeDecodeError):
    """UnicodeDecodeError wrapped with the obj."""
    def __init__(self, obj, *args):
        self.obj = obj
        UnicodeDecodeError.__init__(self, *args)

    def __str__(self):
        original = UnicodeDecodeError.__str__(self)
        return '%s. You passed in %r (%s)' % (original, self.obj,
                type(self.obj))


def force_unicode(stringy_thingy,
                  encoding='utf-8',
                  strings_only=False,
                  errors='strict'):
    """
    Similar to smart_unicode, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first, saves 30-40% in performance when s
    # is an instance of unicode. This function gets called often in that
    # setting.
    if isinstance(stringy_thingy, unicode):
        return stringy_thingy
    if strings_only and is_protected_type(stringy_thingy):
        return stringy_thingy
    try:
        if not isinstance(stringy_thingy, basestring,):
            if hasattr(stringy_thingy, '__unicode__'):
                stringy_thingy = unicode(stringy_thingy)
            else:
                try:
                    stringy_thingy = unicode(str(stringy_thingy),
                                             encoding,
                                             errors)
                except UnicodeEncodeError:
                    if not isinstance(stringy_thingy, Exception):
                        raise
                    # If we get to here, the caller has passed in an Exception
                    # subclass populated with non-ASCII data without special
                    # handling to display as a string. We need to handle this
                    # without raising a further exception. We do an
                    # approximation to what the Exception's standard str()
                    # output should be.
                    stringy_thingy = u' '.join([force_unicode(arg,
                                                              encoding,
                                                              strings_only,
                                                              errors) for \
                                                    arg in stringy_thingy])
        elif not isinstance(stringy_thingy, unicode):
            # Note: We use .decode() here, instead of unicode(s, encoding,
            # errors), so that if s is a SafeString, it ends up being a
            # SafeUnicode at the end.
            stringy_thingy = stringy_thingy.decode(encoding, errors)
    except UnicodeDecodeError as excptn:
        if not isinstance(stringy_thingy, Exception):
            raise WrappedUnicodeDecodeError(stringy_thingy, *excptn.args)
        else:
            # If we get to here, the caller has passed in an Exception
            # subclass populated with non-ASCII bytestring data without a
            # working unicode method. Try to handle this without raising a
            # further exception by individually forcing the exception args
            # to unicode.
            stringy_thingy = u' '.join([force_unicode(arg,
                                                      encoding,
                                                      strings_only,
                                                      errors) for \
                                            arg in stringy_thingy])
    return stringy_thingy

# IP Address support
# This code was mostly based on ipaddr-py
# Copyright 2007 Google Inc. http://code.google.com/p/ipaddr-py/
# Licensed under the Apache License, Version 2.0 (the "License").


def clean_ipv6_address(ip_str, unpack_ipv4=False,
        error_message="This is not a valid IPv6 address"):
    """
    Cleans a IPv6 address string.

    Validity is checked by calling is_valid_ipv6_address() - if an
    invalid address is passed, ValidationError is raised.

    Replaces the longest continious zero-sequence with "::" and
    removes leading zeroes and makes sure all hextets are lowercase.

    Args:
        ip_str: A valid IPv6 address.
        unpack_ipv4: if an IPv4-mapped address is found,
        return the plain IPv4 address (default=False).
        error_message: A error message for in the ValidationError.

    Returns:
        A compressed IPv6 address, or the same value

    """
    best_doublecolon_start = -1
    best_doublecolon_len = 0
    doublecolon_start = -1
    doublecolon_len = 0

    if not is_valid_ipv6_address(ip_str):
        raise ValidationError(error_message)

    # This algorithm can only handle fully exploded
    # IP strings
    ip_str = _explode_shorthand_ip_string(ip_str)

    ip_str = _sanitize_ipv4_mapping(ip_str)

    # If needed, unpack the IPv4 and return straight away
    # - no need in running the rest of the algorithm
    if unpack_ipv4:
        ipv4_unpacked = _unpack_ipv4(ip_str)

        if ipv4_unpacked:
            return ipv4_unpacked

    hextets = ip_str.split(":")

    for index in range(len(hextets)):
        # Remove leading zeroes
        hextets[index] = hextets[index].lstrip('0')
        if not hextets[index]:
            hextets[index] = '0'

        # Determine best hextet to compress
        if hextets[index] == '0':
            doublecolon_len += 1
            if doublecolon_start == -1:
                # Start of a sequence of zeros.
                doublecolon_start = index
            if doublecolon_len > best_doublecolon_len:
                # This is the longest sequence of zeros so far.
                best_doublecolon_len = doublecolon_len
                best_doublecolon_start = doublecolon_start
        else:
            doublecolon_len = 0
            doublecolon_start = -1

    # Compress the most suitable hextet
    if best_doublecolon_len > 1:
        best_doublecolon_end = (best_doublecolon_start +
                                best_doublecolon_len)
        # For zeros at the end of the address.
        if best_doublecolon_end == len(hextets):
            hextets += ['']
        hextets[best_doublecolon_start:best_doublecolon_end] = ['']
        # For zeros at the beginning of the address.
        if best_doublecolon_start == 0:
            hextets = [''] + hextets

    result = ":".join(hextets)

    return result.lower()


def _sanitize_ipv4_mapping(ip_str):
    """
    Sanitize IPv4 mapping in a expanded IPv6 address.

    This converts ::ffff:0a0a:0a0a to ::ffff:10.10.10.10.
    If there is nothing to sanitize, returns an unchanged
    string.

    Args:
        ip_str: A string, the expanded IPv6 address.

    Returns:
        The sanitized output string, if applicable.
    """
    if not ip_str.lower().startswith('0000:0000:0000:0000:0000:ffff:'):
        # not an ipv4 mapping
        return ip_str

    hextets = ip_str.split(':')

    if '.' in hextets[-1]:
        # already sanitized
        return ip_str

    ipv4_address = "%d.%d.%d.%d" % (
        int(hextets[6][0:2], 16),
        int(hextets[6][2:4], 16),
        int(hextets[7][0:2], 16),
        int(hextets[7][2:4], 16),
    )

    result = ':'.join(hextets[0:6])
    result += ':' + ipv4_address

    return result


def _unpack_ipv4(ip_str):
    """
    Unpack an IPv4 address that was mapped in a compressed IPv6 address.

    This converts 0000:0000:0000:0000:0000:ffff:10.10.10.10 to 10.10.10.10.
    If there is nothing to sanitize, returns None.

    Args:
        ip_str: A string, the expanded IPv6 address.

    Returns:
        The unpacked IPv4 address, or None if there was nothing to unpack.
    """
    if not ip_str.lower().startswith('0000:0000:0000:0000:0000:ffff:'):
        return None

    hextets = ip_str.split(':')
    return hextets[-1]


def is_valid_ipv6_address(ip_str):
    """
    Ensure we have a valid IPv6 address.

    Args:
        ip_str: A string, the IPv6 address.

    Returns:
        A boolean, True if this is a valid IPv6 address.

    """

    # We need to have at least one ':'.
    if ':' not in ip_str:
        return False

    # We can only have one '::' shortener.
    if ip_str.count('::') > 1:
        return False

    # '::' should be encompassed by start, digits or end.
    if ':::' in ip_str:
        return False

    # A single colon can neither start nor end an address.
    if ((ip_str.startswith(':') and not ip_str.startswith('::')) or
            (ip_str.endswith(':') and not ip_str.endswith('::'))):
        return False

    # We can never have more than 7 ':' (1::2:3:4:5:6:7:8 is invalid)
    if ip_str.count(':') > 7:
        return False

    # If we have no concatenation, we need to have 8 fields with 7 ':'.
    if '::' not in ip_str and ip_str.count(':') != 7:
        # We might have an IPv4 mapped address.
        if ip_str.count('.') != 3:
            return False

    ip_str = _explode_shorthand_ip_string(ip_str)

    # Now that we have that all squared away, let's check that each of the
    # hextets are between 0x0 and 0xFFFF.
    for hextet in ip_str.split(':'):
        if hextet.count('.') == 3:
            # If we have an IPv4 mapped address, the IPv4 portion has to
            # be at the end of the IPv6 portion.
            if not ip_str.split(':')[-1] == hextet:
                return False
            try:
                validate_ipv4_address(hextet)
            except ValidationError:
                return False
        else:
            try:
                # a value error here means that we got a bad hextet,
                # something like 0xzzzz
                if int(hextet, 16) < 0x0 or int(hextet, 16) > 0xFFFF:
                    return False
            except ValueError:
                return False
    return True


def _explode_shorthand_ip_string(ip_str):
    """
    Expand a shortened IPv6 address.

    Args:
        ip_str: A string, the IPv6 address.

    Returns:
        A string, the expanded IPv6 address.

    """
    if not _is_shorthand_ip(ip_str):
        # We've already got a longhand ip_str.
        return ip_str

    new_ip = []
    hextet = ip_str.split('::')

    # If there is a ::, we need to expand it with zeroes
    # to get to 8 hextets - unless there is a dot in the last hextet,
    # meaning we're doing v4-mapping
    if '.' in ip_str.split(':')[-1]:
        fill_to = 7
    else:
        fill_to = 8

    if len(hextet) > 1:
        sep = len(hextet[0].split(':')) + len(hextet[1].split(':'))
        new_ip = hextet[0].split(':')

        for _ in range(fill_to - sep):
            new_ip.append('0000')
        new_ip += hextet[1].split(':')

    else:
        new_ip = ip_str.split(':')

    # Now need to make sure every hextet is 4 lower case characters.
    # If a hextet is < 4 characters, we've got missing leading 0's.
    ret_ip = []
    for hextet in new_ip:
        ret_ip.append(('0' * (4 - len(hextet)) + hextet).lower())
    return ':'.join(ret_ip)


def _is_shorthand_ip(ip_str):
    """Determine if the address is shortened.

    Args:
        ip_str: A string, the IPv6 address

    Returns:
        A boolean, True if the address is shortened.

    """
    if ip_str.count('::') == 1:
        return True
    if list(filter(lambda x: len(x) < 4, ip_str.split(':'))):
        return True
    return False


def validate_bool(data):
    """If the data is True or False."""
    if not isinstance(data, bool):
        raise ValidationError("Not a bool.")


def validate_long(data):
    """If the data is (or can become) a long
    i.e. a 64 bit integer."""
    try:
        long(data)
    except (ValueError, TypeError):
        raise ValidationError('Not a long')


def validate_char(data):
    """
    A string field, for small-to medium-sized strings.
    TODO: this will have to become a method to implement limit.
    """
    if not isinstance(data, basestring):
        raise ValidationError("%s is not a char." % data)


def validate_date(data):
    """Validate a date."""
    if not isinstance(data, datetime.date):
        raise ValidationError("Not a date.")


def validate_datetime(data):
    """Validate a datetime."""
    if not isinstance(data, datetime.datetime):
        raise ValidationError("Not a datetime.")


def validate_decimal(data):
    """Validate a decimal."""
    if not isinstance(data, Decimal):
        raise ValidationError("Not a decimal.")


def validate_filepath(data):
    """A the moment,
    this just checks that it is a string."""
    if not isinstance(data, basestring):
        raise ValidationError("Not a filepath.")


def validate_float(data):
    """Function to be written here."""
    if not isinstance(data, float):
        raise ValidationError("Not a float.")


def validate_integer(value):
    """Ensure a value is an integer."""
    try:
        int(value)
    except (ValueError, TypeError):
        raise ValidationError('Not an Integer.')


def validate_nullboolean(data):
    """If the data is True or False or None."""
    if not isinstance(data, bool):
        if not isinstance(data, type(None)):
            raise ValidationError("Not a nullboolean.")


def validate_postiveinteger(data):
    """Ensure a value is a postive integer."""
    try:
        valid_int = int(data)
    except (ValueError, TypeError):
        raise ValidationError('Not a positive integer.')
    else:
        if valid_int < 0:
            raise ValidationError('Postive integer cannot be negative.')


def validate_smallinteger(data):
    """Integer between -32768 to +32767."""
    try:
        if not -32768 <= int(data) <= 32767:
            raise ValidationError('Not a small integer.')
    except (ValueError, TypeError):
        raise ValidationError('Not a small integer.')


def validate_biginteger(data):
    """Big (8 byte) integer."""
    try:
        if not -9223372036854775808 <= int(data) <= 9223372036854775807:
            raise ValidationError('Not a big integer.')
    except (ValueError, TypeError):
        raise ValidationError('Not a big integer.')


def validate_positivesmallinteger(data):
    """Function to be written here."""
    try:
        if not 0 <= int(data) <= 32767:
            raise ValidationError('Not a positive small integer.')
    except (ValueError, TypeError):
        raise ValidationError('Not a positive small integer.')


def validate_text(data):
    """Text of unlimited size."""
    if not isinstance(data, basestring):
        raise ValidationError("Not a char.")


def validate_time(data):
    """Validate a time."""
    if not isinstance(data, datetime.time):
        raise ValidationError("Not a time.")


def validate_url(data):
    """Validates a valid URL."""
    urlval = URLValidator()
    urlval(data)


def validate_verified_url(data):
    """Validates a valid and existing URL.
    Read the warnings above."""
    urlval = URLValidator(verify_exists=True)
    urlval(data)


def validate_xml(data):
    """See if data is well formed XML.
    This is pretty leniant.
    It also does not check for validity against a DTD or schema.
    """
    parser = xml.parsers.expat.ParserCreate()
    try:
        parser.Parse(data)
    except xml.parsers.expat.ExpatError:
        raise ValidationError("Not well formed.")


def validate_dict(data):
    """Very simple check that data is a well format dict."""
    try:
        data.keys()
    except AttributeError:
        raise ValidationError('Not an dict.')


def validate_list(data):
    """Check list is a list.
    """
    try:
        data.insert
    except AttributeError:
        raise ValidationError('Not a list.')


def validate_file(data):
    """Function to be written here."""
    raise NotImplementedError(data)


def validate_image(data):
    """Function to be written here."""
    raise NotImplementedError(data)


def validate_embedded(data,
                      embedded_models,
                      handle_none=False):
    """Check that embedded data validates."""
    try:
        model = embedded_models[data['_model']]
    except KeyError:
        raise ValidationError('Missing _model key on embedded data.')
    validate_model_instance(model,
                            data,
                            handle_none=handle_none,
                            embedded_models=embedded_models)


def validate_embedded_list(data,
                           embedded_models,
                           handle_none=False):
    """Check that all the embedded data in the list validates."""
    try:
        data.insert
    except AttributeError:
        raise ValidationError('Not an embedded list.')
    for embedded_model in data:
        try:
            model = embedded_models[embedded_model['_model']]
        except KeyError:
            raise ValidationError('Missing _model key on embedded data.')

        validate_model_instance(model,
                                embedded_model,
                                handle_none=handle_none,
                                embedded_models=embedded_models)


def validate_set_modifier(model_validator, model, field, field_type, value):
    """Sets field to value. All datatypes are supported with $set."""
    model_validator.validate_field(field_type, value)


def validate_unset_modifier(model_validator, model, field, field_type, value):
    """Deletes a given field."""
    if not 'required' in model[field]:
        raise ValidationError(
            'Field %s cannot be unset because it is required.' % field,
            code='invalid')
    if model[field]['required'] != False:
        raise ValidationError(
            'Field %s cannot be unset because it is required.' % field,
            code='invalid')


def validate_inc_modifier(model_validator, model, field, field_type, value):
    """increments field by the number value if field is present
    in the object, otherwise sets field to the number value.
    This can also be used to decrement by using a negative value."""
    # We need to check that the target can be incremented, and that
    #the value is sensible
    if not isinstance(value, Number):
        raise ValidationError(
            'Cannot increment by value '
            '%s because it is not a number.' % value,
            code='invalid')
    if field_type not in (
        'BigInteger', 'Decimal', 'Float', 'Integer', 'LongInteger',
        'PositiveInteger', 'PositiveSmallInteger', 'SmallInteger'):
        raise ValidationError(
            'Cannot increment field %s'
            'because it is not a numeric type.' % field,
            code='invalid')

    if field_type in (
        'PositiveInteger', 'PositiveSmallInteger'):
        model_validator.validate_field(
            field_type, abs(value))
    else:
        model_validator.validate_field(
            field_type, abs(value))


def validate_array_modifier(model_validator, model, field, field_type, value):
    """Several modifiers for dealing with lists."""
    if field_type not in ('EmbeddedList', 'List'):
        raise ValidationError(
            'Field %s is not a list type.' % field,
            code='invalid')


def validate_rename_modifier(model_validator, model, field, field_type, value):
    """Renames the field with name 'old_field_name' to 'new_field_name'"""
    raise ValidationError(
                'Rename is currently not supported.',
                code='invalid')


def validate_bitwise_modifier(model_validator, model, field, field_type, value):
    """Does a bitwise update of field. Can only be used with integers."""
    if field_type not in (
        'BigInteger', 'Integer', 'LongInteger',
        'PositiveInteger', 'PositiveSmallInteger', 'SmallInteger'):
        raise ValidationError(
            'Field %s is not an integer type.' % field,
            code='invalid')

MODIFICATION_DISPATCHER = {
    '$set': validate_set_modifier,
    '$unset': validate_unset_modifier,
    '$inc': validate_inc_modifier,
    '$push': validate_array_modifier,
    '$pushAll': validate_array_modifier,
    '$addToSet': validate_array_modifier,
    '$each': validate_array_modifier,
    '$pop': validate_array_modifier,
    '$pull': validate_array_modifier,
    '$pullAll': validate_array_modifier,
    '$rename': validate_rename_modifier,
    '$bit': validate_bitwise_modifier
    }

DISPATCHER = (
    ('Boolean', validate_bool),
    ('BigInteger', validate_biginteger),
    ('Char', validate_char),
    ('CommaSeparatedInteger', validate_comma_separated_integer_list),
    ('Date', validate_date),
    ('DateTime', validate_datetime),
    ('Decimal', validate_decimal),
    ('Dict', validate_dict),
    ('Email', validate_email),
    ('Embedded', validate_embedded),
    ('EmbeddedList', validate_embedded_list),
    ('File', validate_file),
    ('FilePath', validate_filepath),
    ('Float', validate_float),
    ('Image', validate_image),
    ('Integer', validate_integer),
    ('IPAddress', validate_ipv46_address),
    ('IP4Address', validate_ipv4_address),
    ('IP6Address', validate_ipv6_address),
    ('List', validate_list),
    ('LongInteger', validate_long),
    ('NullBoolean', validate_nullboolean),
    ('PositiveInteger', validate_postiveinteger),
    ('PositiveSmallInteger', validate_positivesmallinteger),
    ('Slug', validate_slug),
    ('SmallInteger', validate_smallinteger),
    ('Text', validate_text),
    ('Time', validate_time),
    ('URL', validate_url),
    ('VerifiedURL', validate_verified_url),
    ('XML', validate_xml),
    )
