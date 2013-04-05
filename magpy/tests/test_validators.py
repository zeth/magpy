# -*- coding: utf-8 -*-
"""Tests for validators.py."""

import six

import re
import datetime
from decimal import Decimal
from unittest import TestCase, main

from magpy.server.validators import validate_integer, ValidationError, \
    validate_email, validate_slug, validate_ipv4_address, \
    validate_ipv46_address, validate_comma_separated_integer_list, \
    MaxValueValidator, MinValueValidator, validate_ipv6_address, \
    URLValidator, MaxLengthValidator, MinLengthValidator, \
    BaseValidator, RegexValidator, MissingFields, InvalidFields, \
    OrphanedInstance, ModelValidator, validate_dict, \
    validate_model_instance, parse_instance, validate_list, \
    validate_embedded_list, validate_xml, smart_unicode, smart_str, \
    WrappedUnicodeDecodeError, is_valid_ipv6_address, clean_ipv6_address, \
    validate_char, validate_date, validate_datetime, \
    validate_float, validate_nullboolean, validate_postiveinteger, \
    validate_smallinteger, validate_biginteger, \
    validate_positivesmallinteger, validate_text, validate_time, \
    validate_bool, validate_decimal, validate_modification, ValidationError
    # validate_long


# pylint: disable=R0904,R0903,W0232

NOW = datetime.datetime.now()

# 1. Start with the low level tests.


class TestSimpleValidators(TestCase):
    """Test the validators directly."""
    def test_single_message(self):
        """Test the error message."""
        validity = ValidationError('Not Valid')
        if six.PY3:
            self.assertEqual(str(validity), "['Not Valid']")
            self.assertEqual(repr(validity), "ValidationError(['Not Valid'])")
        else:
            self.assertEqual(str(validity), "[u'Not Valid']")
            self.assertEqual(repr(validity), "ValidationError([u'Not Valid'])")

    def test_message_list(self):
        """Test a list of messages."""
        validity = ValidationError(['First Problem', 'Second Problem'])
        if six.PY3:
            self.assertEqual(str(validity),
                             "['First Problem', 'Second Problem']")
            self.assertEqual(
                repr(validity),
                "ValidationError(['First Problem', 'Second Problem'])")

        else:
            self.assertEqual(str(validity),
                             "[u'First Problem', u'Second Problem']")
            self.assertEqual(
                repr(validity),
                "ValidationError([u'First Problem', u'Second Problem'])")

    def test_message_dict(self):
        """Test the message dict."""
        validity = ValidationError({'first': 'First Problem'})
        self.assertEqual(str(validity), "{'first': 'First Problem'}")
        self.assertEqual(repr(validity), \
                             "ValidationError({'first': 'First Problem'})")

    def test_smart_unicode(self):
        """Test the smart unicode function (originally from Django."""
        class Test:
            """Test Unicode string."""
            def __str__(self):
                return 'ŠĐĆŽćžšđ'

        class TestU:
            """Another test string."""
            def __str__(self):
                return 'Foo'

            # pylint: disable=R0201
            def __unicode__(self):
                return u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111'

        self.assertEqual(
            smart_unicode(Test()),
            u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111')
        self.assertEqual(
            smart_unicode(TestU()),
            u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111')
        self.assertEqual(
            smart_unicode(1), u'1')
        self.assertEqual(
            smart_unicode('foo'), u'foo')

        self.assertRaises(
            WrappedUnicodeDecodeError,
            smart_unicode,
            b'\xff\xfeS0\n\x00'
            )
        self.assertEqual(
            smart_unicode(Exception('Ryökäle')), 'Ry\xf6k\xe4le')

        self.assertRaises(
            WrappedUnicodeDecodeError,
            smart_unicode,
            Exception('\xff\xfeS0\n\x00')
            )

    def test_smart_str(self):
        """Test the smart_str function."""
        if six.PY3:
            first_result = b'\xc5\xa0\xc4\x90\xc4\x86\xc5\xbd\xc4\x87\xc5\xbe\xc5\xa1\xc4\x91'
            second_result = b'Ry\xc3\xb6k\xc3\xa4le'
            third_result = b'\xd0\x91'
        else:
            first_result = '\xc5\xa0\xc4\x90\xc4\x86\xc5\xbd\xc4\x87\xc5\xbe\xc5\xa1\xc4\x91'
            second_result = 'Ry\xc3\xb6k\xc3\xa4le'
            third_result = '\xd0\x91'

        self.assertEqual(
            smart_str('ŠĐĆŽćžšđ'),
            first_result)
        self.assertEqual(
            smart_str(u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111'),
            first_result)

        self.assertEqual(
            smart_str(Exception(u'Ryökäle')), second_result)

        self.assertEqual(smart_str(u"\u0411"), third_result)
        self.assertEqual(smart_str(1), '1')
        self.assertEqual(smart_str(1, strings_only=True), 1)

    def test_validate_integer(self):
        self.assertEqual(validate_integer('42'), None)
        self.assertEqual(validate_integer('-42'), None)
        self.assertEqual(validate_integer(-42), None)
        self.assertEqual(validate_integer(-42.5), None)
        self.assertRaises(ValidationError, validate_integer, None)
        self.assertRaises(ValidationError, validate_integer, 'a')

    def test_validate_email(self):
        self.assertEqual(validate_email('email@here.com'), None)
        self.assertEqual(validate_email('weirder-email@here.and.there.com'),
                         None)
        self.assertEqual(validate_email('email@[127.0.0.1]'), None)
        self.assertRaises(ValidationError, validate_email, None)
        self.assertRaises(ValidationError, validate_email, '')
        self.assertRaises(ValidationError, validate_email, 'abc')
        self.assertRaises(ValidationError, validate_email, 'a @x.cz')
        self.assertRaises(ValidationError, validate_email,
                          'something@@somewhere.com')
        self.assertRaises(ValidationError, validate_email, 'email@127.0.0.1')
        # Quoted-string format (CR not allowed)
        self.assertEqual(validate_email('"\\\011"@here.com'), None)
        self.assertRaises(ValidationError, validate_email, '"\\\012"@here.com')

    def test_validate_slug(self):
        self.assertEqual(validate_slug('slug-ok'), None)
        self.assertEqual(validate_slug('longer-slug-still-ok'), None)
        self.assertEqual(validate_slug('--------'), None)
        self.assertEqual(validate_slug('nohyphensoranything'), None)
        self.assertRaises(ValidationError, validate_slug, '')
        self.assertRaises(ValidationError, validate_slug, ' text ')
        self.assertRaises(ValidationError, validate_slug, ' ')
        self.assertRaises(ValidationError, validate_slug, 'some@mail.com')
        self.assertRaises(ValidationError, validate_slug, '你好')
        self.assertRaises(ValidationError, validate_slug, '\n')

    def test_validate_ipv4_address(self):
        self.assertEqual(validate_ipv4_address('1.1.1.1'), None)
        self.assertEqual(validate_ipv4_address('255.0.0.0'), None)
        self.assertEqual(validate_ipv4_address('0.0.0.0'), None)
        self.assertRaises(ValidationError, validate_ipv4_address, '256.1.1.1')
        self.assertRaises(ValidationError, validate_ipv4_address, '25.1.1.')
        self.assertRaises(ValidationError, validate_ipv4_address, '25,1,1,1')
        self.assertRaises(ValidationError, validate_ipv4_address, '25.1 .1.1')

    def test_validate_ipv6_address(self):
        # validate_ipv6_address uses django.utils.ipv6, which
        # is tested in much greater detail in it's own testcase
        self.assertEqual(validate_ipv6_address('fe80::1'), None)
        self.assertEqual(validate_ipv6_address('::1'), None)
        self.assertEqual(validate_ipv6_address('1:2:3:4:5:6:7:8'), None)
        self.assertRaises(ValidationError, validate_ipv6_address, '1:2')
        self.assertRaises(ValidationError, validate_ipv6_address, '::zzz')
        self.assertRaises(ValidationError, validate_ipv6_address, '12345::')

    def test_validate_ipv46_address(self):
        self.assertEqual(validate_ipv46_address('1.1.1.1'), None)
        self.assertEqual(validate_ipv46_address('255.0.0.0'), None)
        self.assertEqual(validate_ipv46_address('0.0.0.0'), None)
        self.assertEqual(validate_ipv46_address('fe80::1'), None)
        self.assertEqual(validate_ipv46_address('::1'), None)
        self.assertEqual(validate_ipv46_address('1:2:3:4:5:6:7:8'), None)
        self.assertRaises(ValidationError, validate_ipv46_address, '256.1.1.1')
        self.assertRaises(ValidationError, validate_ipv46_address, '25.1.1.')
        self.assertRaises(ValidationError, validate_ipv46_address, '25,1,1,1')
        self.assertRaises(ValidationError, validate_ipv46_address, '25.1 .1.1')
        self.assertRaises(ValidationError, validate_ipv46_address, '1:2')
        self.assertRaises(ValidationError, validate_ipv46_address, '::zzz')
        self.assertRaises(ValidationError, validate_ipv46_address, '12345::')

    def test_validate_csinteger_list(self):
        self.assertEqual(validate_comma_separated_integer_list('1'), None)
        self.assertEqual(validate_comma_separated_integer_list('1,2,3'), None)
        self.assertEqual(validate_comma_separated_integer_list('1,2,3,'), None)
        self.assertRaises(ValidationError,
                          validate_comma_separated_integer_list, '')
        self.assertRaises(ValidationError,
                          validate_comma_separated_integer_list, 'a,b,c')
        self.assertRaises(ValidationError,
                          validate_comma_separated_integer_list, '1, 2, 3')

    def test_validate_dict(self):
        self.assertEqual(validate_dict({'mykey': 'myvalue'}), None)
        self.assertRaises(ValidationError, validate_dict, [])

    def test_validate_list(self):
        self.assertEqual(validate_list(['item1', 'item2', 'item3']), None)
        self.assertRaises(ValidationError, validate_list, {})

    def test_validate_xml(self):
        self.assertEqual(validate_xml('<p>Hello World</p>'), None)
        self.assertRaises(ValidationError, validate_xml, '<p></td>')

    #def test_validate_long(self):
    #    self.assertEqual(validate_long(100), None)
    #    self.assertRaises(ValidationError, validate_long, "I am a string")

    def test_validate_char(self):
        self.assertEqual(validate_char("Hello World"), None)
        self.assertRaises(ValidationError, validate_char, 1.5)

    def test_validate_date(self):
        self.assertEqual(validate_date(datetime.date.today()), None)
        self.assertRaises(ValidationError, validate_date, 1.5)

    def test_validate_datetime(self):
        self.assertEqual(validate_datetime(datetime.datetime.now()), None)
        self.assertRaises(ValidationError, validate_datetime, "Today")

    def test_validate_float(self):
        self.assertEqual(validate_float(1.5), None)
        self.assertRaises(ValidationError, validate_float, "1.5")

    def test_validate_nullboolean(self):
        self.assertEqual(validate_nullboolean(True), None)
        self.assertEqual(validate_nullboolean(False), None)
        self.assertEqual(validate_nullboolean(None), None)
        self.assertRaises(ValidationError, validate_nullboolean, 1.5)
        self.assertRaises(ValidationError,
                          validate_nullboolean, "I am a string")

    def test_validate_postiveinteger(self):
        self.assertEqual(validate_postiveinteger(5), None)
        self.assertRaises(ValidationError, validate_postiveinteger, -6)
        self.assertRaises(ValidationError,
                          validate_postiveinteger, "I am a string")

    def test_validate_smallinteger(self):
        self.assertEqual(validate_smallinteger(5), None)
        self.assertEqual(validate_smallinteger(-5), None)
        self.assertRaises(ValidationError, validate_smallinteger, -50000)
        self.assertRaises(ValidationError, validate_smallinteger, 50000)
        self.assertRaises(ValidationError,
                          validate_smallinteger, "I am a string")

    def test_validate_biginteger(self):
        self.assertEqual(validate_biginteger(5), None)
        self.assertEqual(validate_biginteger(-5), None)
        self.assertRaises(ValidationError,
                          validate_biginteger,  10000000000000000000)
        self.assertRaises(ValidationError,
                          validate_biginteger, -10000000000000000000)
        self.assertRaises(
            ValidationError, validate_biginteger, "I am a string")

    def test_validate_possmallinteger(self):
        self.assertEqual(validate_positivesmallinteger(5), None)
        self.assertRaises(ValidationError,
                          validate_positivesmallinteger, "I am a string")
        self.assertRaises(
            ValidationError, validate_positivesmallinteger, 50000)
        self.assertRaises(ValidationError, validate_positivesmallinteger, -5)

    def test_validate_text(self):
        self.assertEqual(validate_text("Hello World"), None)
        self.assertRaises(ValidationError, validate_text, 1.5)

    def test_validate_time(self):
        self.assertEqual(validate_time(datetime.time(12, 10, 30)), None)
        self.assertRaises(ValidationError, validate_time, "12:10:30")

    def test_validate_bool(self):
        self.assertEqual(validate_bool(True), None)
        self.assertEqual(validate_bool(False), None)
        self.assertRaises(ValidationError, validate_bool, None)
        self.assertRaises(ValidationError, validate_bool, "OK")
        self.assertRaises(ValidationError, validate_bool, 1)

    def test_validate_decimal(self):
        self.assertEqual(validate_decimal(Decimal(1)), None)
        self.assertEqual(validate_decimal(Decimal(10.99)), None)
        self.assertRaises(ValidationError, validate_decimal, 1.5)
        self.assertRaises(ValidationError, validate_decimal, "I am a string")

    def test_max_value_validator(self):
        self.assertEqual(MaxValueValidator(10)(10), None)
        self.assertEqual(MaxValueValidator(10)(-10), None)
        self.assertEqual(MaxValueValidator(10)(0), None)
        self.assertEqual(MaxValueValidator(NOW)(NOW), None)
        self.assertEqual(
            MaxValueValidator(NOW)(NOW - datetime.timedelta(days=1)), None)

        self.assertRaises(ValidationError, MaxValueValidator(0), 1)
        self.assertRaises(ValidationError,
                          MaxValueValidator(NOW),
                          NOW + datetime.timedelta(days=1))

    def test_min_value_validator(self):
        self.assertEqual(MinValueValidator(-10)(-10), None)
        self.assertEqual(MinValueValidator(-10)(10), None)
        self.assertEqual(MinValueValidator(-10)(0), None)
        self.assertEqual(MinValueValidator(NOW)(NOW), None)
        self.assertEqual(
            MinValueValidator(NOW)(NOW + datetime.timedelta(days=1)), None)
        self.assertRaises(ValidationError, MinValueValidator(0), -1)
        self.assertRaises(ValidationError, MinValueValidator(NOW),
                          NOW - datetime.timedelta(days=1))

    def test_max_length_validator(self):
        self.assertEqual(MaxLengthValidator(10)(''), None)
        self.assertEqual(MaxLengthValidator(10)(10 * 'x'), None)
        self.assertRaises(ValidationError, MaxLengthValidator(10), 15 * 'x')

    def test_min_length_validator(self):
        self.assertEqual(MinLengthValidator(10)(15 * 'x'), None)
        self.assertEqual(MinLengthValidator(10)(10 * 'x'), None)
        self.assertRaises(ValidationError, MinLengthValidator(10), '')

    def test_url_validator(self):
        self.assertEqual(URLValidator()('http://www.djangoproject.com/'), None)
        self.assertEqual(URLValidator()('http://localhost/'), None)
        self.assertEqual(URLValidator()('http://example.com/'), None)
        self.assertEqual(URLValidator()('http://www.example.com/'), None)
        self.assertEqual(URLValidator()('http://www.example.com:8000/test'),
                         None)
        self.assertEqual(URLValidator()(
                'http://valid-with-hyphens.com/'), None)
        self.assertEqual(URLValidator()(
                'http://subdomain.example.com/'), None)
        self.assertEqual(URLValidator()('http://200.8.9.10/'), None)
        self.assertEqual(URLValidator()('http://200.8.9.10:8000/test'), None)
        self.assertEqual(URLValidator()('http://valid-----hyphens.com/'), None)
        self.assertEqual(URLValidator()('http://example.com?something=value'),
                         None)
        self.assertEqual(URLValidator()(\
                'http://example.com/index.php?something=value&another=value2'),
                         None)
        self.assertRaises(ValidationError, URLValidator(), 'foo')
        self.assertRaises(ValidationError, URLValidator(), 'http://')
        self.assertRaises(ValidationError, URLValidator(), 'http://example')
        self.assertRaises(ValidationError, URLValidator(), 'http://example.')
        self.assertRaises(ValidationError, URLValidator(), 'http://.com')
        self.assertRaises(ValidationError, URLValidator(),
                          'http://invalid-.com')
        self.assertRaises(ValidationError, URLValidator(),
                          'http://-invalid.com')
        self.assertRaises(ValidationError, URLValidator(),
                          'http://inv-.alid-.com')
        self.assertRaises(ValidationError, URLValidator(),
                          'http://inv-.-alid.com')

    def test_base_validator(self):
        self.assertEqual(BaseValidator(True)(True), None)
        self.assertRaises(ValidationError, BaseValidator(True), False)

    def test_regex_validator(self):
        self.assertEqual(RegexValidator()(''), None)
        self.assertEqual(RegexValidator()('x1x2'), None)
        self.assertRaises(ValidationError, RegexValidator('[0-9]+'), 'xxxxxx')
        self.assertEqual(RegexValidator('[0-9]+')('1234'), None)
        self.assertEqual(RegexValidator(re.compile('[0-9]+'))('1234'), None)
        self.assertEqual(RegexValidator('.*')(''), None)
        self.assertEqual(RegexValidator(re.compile('.*'))(''), None)
        self.assertEqual(RegexValidator('.*')('xxxxx'), None)
        self.assertRaises(ValidationError, RegexValidator('x'), 'y')
        self.assertRaises(
            ValidationError, RegexValidator(re.compile('x')), 'y')


class TestURLValidatorExists(TestCase):
    """Test URLValidator when verify_exists is True.
    Must have internet for this to work.
    """

    def test_site_exists(self):
        """Test that the site w3.org exists."""
        validator = URLValidator(verify_exists=True)
        self.assertEquals(validator('http://w3.org'), None)

    def test_broken_link(self):
        """Test that a URL does not exist."""
        validator = URLValidator(verify_exists=True)
        self.assertRaises(ValidationError, validator,
            'http://www.example.invalid')

    def test_invalid_link(self):
        """Test a URL which is not even valid."""
        validator = URLValidator(verify_exists=True)
        self.assertRaises(ValidationError, validator,
            'http://')


class TestUtilsIPv6(TestCase):
    """Test IPv6 Utils."""

    def test_correct_plain_address(self):
        """Test simple IPv6 address validation."""
        self.assertTrue(is_valid_ipv6_address('fe80::223:6cff:fe8a:2e8a'))
        self.assertTrue(is_valid_ipv6_address('2a02::223:6cff:fe8a:2e8a'))
        self.assertTrue(is_valid_ipv6_address('1::2:3:4:5:6:7'))
        self.assertTrue(is_valid_ipv6_address('::'))
        self.assertTrue(is_valid_ipv6_address('::a'))
        self.assertTrue(is_valid_ipv6_address('2::'))

    def test_correct_with_v4mapping(self):
        """Test mapped IPv6 address validation."""
        self.assertTrue(is_valid_ipv6_address('::ffff:254.42.16.14'))
        self.assertTrue(is_valid_ipv6_address('::ffff:0a0a:0a0a'))

    def test_incorrect_plain_address(self):
        """Test that incorrect addresses fail to validate."""
        self.assertFalse(is_valid_ipv6_address('foo'))
        self.assertFalse(is_valid_ipv6_address('127.0.0.1'))
        self.assertFalse(is_valid_ipv6_address('12345::'))
        self.assertFalse(is_valid_ipv6_address('1::2:3::4'))
        self.assertFalse(is_valid_ipv6_address('1::zzz'))
        self.assertFalse(is_valid_ipv6_address('1::2:3:4:5:6:7:8'))
        self.assertFalse(is_valid_ipv6_address('1:2'))
        self.assertFalse(is_valid_ipv6_address('1:::2'))

    def test_incorrect_with_v4mapping(self):
        """Test that incorrect mapped addresses fail to validate."""
        self.assertFalse(is_valid_ipv6_address('::ffff:999.42.16.14'))
        self.assertFalse(is_valid_ipv6_address('::ffff:zzzz:0a0a'))
        # The ::1.2.3.4 format used to be valid but was deprecated
        # in rfc4291 section 2.5.5.1
        self.assertTrue(is_valid_ipv6_address('::254.42.16.14'))
        self.assertTrue(is_valid_ipv6_address('::0a0a:0a0a'))
        self.assertFalse(is_valid_ipv6_address('::999.42.16.14'))
        self.assertFalse(is_valid_ipv6_address('::zzzz:0a0a'))

    def test_cleanes_plain_address(self):
        """Test that addresses clean correctly."""
        self.assertEqual(clean_ipv6_address('DEAD::0:BEEF'), u'dead::beef')
        self.assertEqual(
            clean_ipv6_address('2001:000:a:0000:0:fe:fe:beef'),
            u'2001:0:a::fe:fe:beef')
        self.assertEqual(
            clean_ipv6_address('2001::a:0000:0:fe:fe:beef'),
            u'2001:0:a::fe:fe:beef')

    def test_cleanes_with_v4_mapping(self):
        """Test that mapped addresses clean correctly."""
        self.assertEqual(
            clean_ipv6_address('::ffff:0a0a:0a0a'),
            u'::ffff:10.10.10.10')
        self.assertEqual(
            clean_ipv6_address('::ffff:1234:1234'),
            u'::ffff:18.52.18.52')
        self.assertEqual(
            clean_ipv6_address('::ffff:18.52.18.52'),
            u'::ffff:18.52.18.52')

    def test_unpacks_ipv4(self):
        """Test that addresses unpack and clean correctly."""
        self.assertEqual(
            clean_ipv6_address('::ffff:0a0a:0a0a', unpack_ipv4=True),
            u'10.10.10.10')
        self.assertEqual(
            clean_ipv6_address('::ffff:1234:1234', unpack_ipv4=True),
            u'18.52.18.52')
        self.assertEqual(
            clean_ipv6_address('::ffff:18.52.18.52', unpack_ipv4=True),
            u'18.52.18.52')


# 2. Now lets test some model validation

IMAGE = {
    '_id': 'image',
    'src': {
        'field': 'URL',
        'required': False,
        'default': '/',
        'limits': {},
        },
    'width': {'field': 'Integer',
              'limits': {'max_value': 1400},
              },
    'height': {'field': 'Integer',
               'limits': {'max_value': 1400},
               },
    'alt': {'field': 'Char',
            'limits': {'max_length': 255},
            },
    }

MODEL_TEST_DATA = {
    # _model: (Tests: data, expected)
    'IMAGE': (
        # Lets test a correct image
        ({'_model': 'image',
          'src': 'http://zeth.ltd.uk/static/consultancy/images/zethltd.png',
          'width': 269,
          'height': 176,
          'alt': 'Zeth Ltd Header Logo'}, None),
        # Now lets test one with missing fields
        ({'_model': 'image',
          'src': 'http://zeth.ltd.uk/static/consultancy/images/zethltd.png',
          'alt': 'Zeth Ltd Header Logo'}, MissingFields),
        # Now lets test one with a junk field
        ({'_model': 'image',
          'src': 'http://zeth.ltd.uk/static/consultancy/images/zethltd.png',
          'width': 269,
          'height': 176,
          'alt': 'Zeth Ltd Header Logo',
          'animal': 'sheep'
          }, InvalidFields),
        # Lets test one missing the _model name
        ({'src': 'http://zeth.ltd.uk/static/consultancy/images/zethltd.png',
          'width': 269,
          'height': 176,
          'alt': 'Zeth Ltd Header Logo'}, OrphanedInstance),
        ),
    }


class TestModelValidator(TestCase):
    """Test the model validation."""
    def test_correct_model(self):
        """Lets test a correct image."""
        modelvalidator = ModelValidator(IMAGE)
        errors = modelvalidator.validate_instance(
            {'_model': 'image',
             'src': 'http://zeth.ltd.uk/static/consultancy/images/zethltd.png',
             'width': 269,
             'height': 176,
             'alt': 'Zeth Ltd Header Logo'})
        self.assertEqual(errors, None)

    def test_model_missing_fields(self):
        """Lets test one with missing fields."""
        modelvalidator = ModelValidator(IMAGE)
        self.assertRaises(
            MissingFields,
            modelvalidator.validate_instance,
            {'_model': 'image',
             'src': 'http://zeth.ltd.uk/static/consultancy/images/zethltd.png',
             'alt': 'Zeth Ltd Header Logo'})

    def test_model_junk_field(self):
        """lets test one with a junk field."""
        modelvalidator = ModelValidator(IMAGE)
        self.assertRaises(
            InvalidFields,
            modelvalidator.validate_instance,
            {'_model': 'image',
             'src': 'http://zeth.ltd.uk/static/consultancy/images/zethltd.png',
             'width': 269,
             'height': 176,
             'alt': 'Zeth Ltd Header Logo',
             'animal': 'sheep'
             })

    def test_instance_missing_model(self):
        """Lets test one missing the _model name."""
        modelvalidator = ModelValidator(IMAGE)
        self.assertRaises(
            OrphanedInstance,
            modelvalidator.validate_instance,
            {'src': 'http://zeth.ltd.uk/static/consultancy/images/zethltd.png',
             'width': 269,
             'height': 176,
             'alt': 'Zeth Ltd Header Logo'})

EMBEDDED_MODELS = {
    'article': {
    '_id': 'article',
    '_model': '_model',
    'body': {'field': 'Text'},
    'author': {
            'field': 'Embedded',
            'valid_models': ['author']},
    'comments': {
            'field': 'EmbeddedList',
            'required': False,
            'valid_models': ['comment']}
    },
    'author': {
        '_id': 'author',
        '_model': '_model',
        'name': {'field': 'Char'},
    },
    'comment': {
        '_id': 'comment',
        '_model': '_model',
        'text': {'field': 'Text'},
        'author': {'field': 'Embedded'}
    }
}


TEST_ARTICLE = {
    '_id': 'testarticle',
    '_model': 'article',
    'body': 'This is the body of the article.',
    'author': {
        '_id': 'ZG',
        '_model': 'author',
        'name': 'Zeth',
        },
    'comments': [
        {'_id': 'comment1',
         '_model': 'comment',
         'text': 'What a wonderful article.',
         'author': {
                '_id': 'Al',
                '_model': 'author',
                'name': 'Alice',
                },
         },
        {'_id': 'comment2',
         '_model': 'comment',
         'text': 'What a bad article.',
         'author': {
                '_id': 'Bo',
                '_model': 'author',
                'name': 'Bob',
                },
         },
        ]
    }


class ParseInstanceTestCase(TestCase):
    """Test the parse_instance function."""

    def test_parse_simple_instance(self):
        """Simple instance has no embedded models."""

        # Setup the instance:
        instance = TEST_ARTICLE['author'].copy()

        # We don't want the top level model:
        del instance['_model']

        # Store the results in results:
        results = set()

        # Parse the instance
        parse_instance(instance, results)

        # Result should be an empty set
        self.assertFalse(results)

    def test_parse_complex_instance(self):
        """Complex instance has embedded models."""

        # Setup the instance:
        instance = TEST_ARTICLE.copy()

        # We don't want the top level model:
        del instance['_model']

        # Store the results in results:
        results = set()

        # Parse the instance
        parse_instance(instance, results)

        # Test Result
        self.assertEquals(results, set(['comment', 'author']))


class EmbedTestCase(TestCase):
    """Test the embedded validation."""

    def test_embed_author_example(self):
        """Test that the embedded author is valid on its own."""
        self.assertEqual(
            validate_model_instance(
                EMBEDDED_MODELS['author'],
                TEST_ARTICLE['author'],
                embedded_models=EMBEDDED_MODELS),
            None)

    def test_embed_comment_example(self):
        """Test that the embedded comment is valid on its own."""
        self.assertEqual(
            validate_model_instance(
                EMBEDDED_MODELS['comment'],
                TEST_ARTICLE['comments'][0],
                embedded_models=EMBEDDED_MODELS),
            None)

    def test_embed_article_example(self):
        """Test that the whole article is valid."""
        self.assertEqual(
            validate_model_instance(
                EMBEDDED_MODELS['article'],
                TEST_ARTICLE,
                embedded_models=EMBEDDED_MODELS),
            None)

    def test_invalid_embedded_list(self):
        """Test that some junk is not an embedded list."""

        self.assertRaises(
            ValidationError,
            validate_embedded_list,
            {'key': 'value'},  # dict is not a list
            {}
            )

MOCK_MODIFICATION_MODEL = {
    '_id': 'test',
    '_model': '_model',
    'modeldescription': 'A collection to store test data in.',
    'name': {
        'field': 'Char'
        },
    'age': {
        'field': 'Integer',
        'required': False
        },
    'friends': {
        'field': 'List',
        'required': False
        },
    '_permissions': {
        'create': True,
        'read': True,
        'update': True,
        'delete': True,
        }
    }


class TestModificationValidation(TestCase):
    """Test validate_modification."""

    def test_set_modification(self):
        """Test the set modifier validation."""
        errors = validate_modification(
            MOCK_MODIFICATION_MODEL,
            {'$set': {'name': 'Bob'}})
        self.assertEqual(errors, None)

    def test_error_set_modification(self):
        """Test the set modifier validation.
        field name needs to be a Char, so lets
        set to an Integer in order to raise an
        exception."""
        self.assertRaises(ValidationError,
                          validate_modification,
                          MOCK_MODIFICATION_MODEL,
                          {'$set': {'name': 1}})

    def test_unset_modification(self):
        """Test the unset modifier validation."""
        errors = validate_modification(
            MOCK_MODIFICATION_MODEL,
            {'$unset': {'age': 1}})
        self.assertEqual(errors, None)

    def test_error_unset_modification(self):
        """Unsetting a field requires it is required=False,
        so lets try to unset something which is required=True
        in order to raise a ValidationError."""
        self.assertRaises(ValidationError,
                          validate_modification,
                          MOCK_MODIFICATION_MODEL,
                          {'$unset': {'name': 1}})

    def test_inc_modification(self):
        """Test the inc modifier validation."""
        errors = validate_modification(
            MOCK_MODIFICATION_MODEL,
            {'$inc': {'age': 1}})
        self.assertEqual(errors, None)

    def test_error_inc_modification(self):
        """Test the inc modifier validation."""
        self.assertRaises(ValidationError,
                          validate_modification,
                          MOCK_MODIFICATION_MODEL,
                          {'$inc': {'age': "one"}})

    def test_error_inc_modification_two(self):
        """Test the inc modifier validation."""
        self.assertRaises(ValidationError,
                          validate_modification,
                          MOCK_MODIFICATION_MODEL,
                          {'$inc': {'name': 1}})

    def test_push_modification(self):
        """Test the push modifier validation."""
        errors = validate_modification(
            MOCK_MODIFICATION_MODEL,
            {'$push': {'friends': "Jim"}})
        self.assertEqual(errors, None)

    def test_error_push_modification(self):
        """Test the push modifier validation."""
        self.assertRaises(ValidationError,
                          validate_modification,
                          MOCK_MODIFICATION_MODEL,
                          {'$push': {'age': "Jim"}})

    def test_bitwise_modification(self):
        """Test the bitwise modifier validation."""
        errors = validate_modification(
            MOCK_MODIFICATION_MODEL,
            {'$bit': {'age': {'and': 2}}})
        self.assertEqual(errors, None)

    def test_error_bitwise_modification(self):
        """Test the bitwise modifier validation."""
        self.assertRaises(ValidationError,
                          validate_modification,
                          MOCK_MODIFICATION_MODEL,
                          {'$bit': {'name': {'and': 2}}})

    def test_error_rename_modification(self):
        """Test the rename modifier validation.
        This is not supported so should raise exception."""
        self.assertRaises(ValidationError,
                          validate_modification,
                          MOCK_MODIFICATION_MODEL,
                          {'$rename': {'age': 'years_old'}})


if __name__ == '__main__':
    main()
