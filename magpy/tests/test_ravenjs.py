"""Tests for Magpy."""
from __future__ import print_function

import six

import os
import time
import unittest
import json

from pymongo import Connection

from magpy.server.instances import InstanceLoader
from magpy.server.database import Database
from magpy.server.utils import get_mag_path
from magpy.tests.javascript import JavaScriptTestCase

# pylint: disable=R0904


class RavenTestCase(JavaScriptTestCase):
    """Load the Raven file into the session."""
    _delay = 0.5

    def setUp(self):  # pylint: disable=C0103
        super(RavenTestCase, self).setUp()
        magjs = os.path.join(get_mag_path(), 'static/js/mag.js')
        self.load(magjs)
        self.eval('RAVEN._REQUEST._default_headers["X-UnitTest"] = "True";')

    def sleep(self,
              delay=None):
        """Pause to avoid database race conditions."""
        if not delay:
            delay = self._delay

        print("%s sec delay to give the database time . . ." % delay, end=' ')
        time.sleep(delay)
        print(". . now we continue")


class RavenTopLevelTestCase(RavenTestCase):
    """Test the top level of the module."""
    def test_version(self):
        """Check what version we are testing."""
        self.assertEqual(self.eval('RAVEN.get_version();'), '0.2')


class RavenFuncToolsTestCase(RavenTestCase):
    """Test the FUNCTOOLS submodule."""
    def test_attempt(self):
        """Test RAVEN.FUNCTOOLS.attempt.
        We make the first function throw a Javascript exception.
        The second is successful, so its return value should be returned."""
        self.assertEqual(
            self.eval('RAVEN.FUNCTOOLS.attempt(function() {throw new E'
                              'rror("This first function is wrong")}, function'
                              '() {return "success"});'),
            'success')

    def test_get_function_from_string(self):
        """Test RAVEN.FUNCTOOLS.get_function_from_string.
        This should get the get_api_url function and then run it."""
        self.assertEqual(
            self.eval("RAVEN.FUNCTOOLS.get_function_from_string("
                              "'RAVEN._REST.get_api_url')();"),
            'http://localhost/api/')


class RavenTypesTestCase(RavenTestCase):
    """Test the TYPES submodule."""
    def test_array_literal_is_array(self):
        """[] should be detected as an array."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_array([]);"),
                              True)

    def test_new_array_is_array(self):
        """new Array () should be detected as an array."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_array(new Array ());"),
            True)

    def test_object_is_not_array(self):
        """{} should not be detected as an array."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_array({});"),
            False)

    def test_string_is_not_array(self):
        """A string should not be detected as an array."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_array('hello');"),
            False)

    def test_boolean_is_not_array(self):
        """true should not be detected as an array."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_array(true);"),
            False)

    def test_literal_object_is_object(self):
        """{} should be detected as an object."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_object({});"),
            True)

    def test_new_object_is_object(self):
        """new Object() should be detected as an object."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_object(new Object());"),
            True)

    def test_array_is_not_an_object(self):
        """[] should not be detected as an object."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_object([]);"),
            False)

    def test_string_is_not_an_object(self):
        """A string should not be detected as an object."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_object('Hello');"),
            False)

    def test_object_is_empty(self):
        """An empty object should be empty."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_empty_object({});"),
            True)

    def test_object_is_not_empty(self):
        """Not empty objects should not be empty."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_empty_object({key: 'value'});"),
            False)

    def test_integer_is_number(self):
        """An integer should be detected as a number."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_number(1);"),
            True)

    def test_decimal_is_number(self):
        """A decimal number should be detected as a number."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_number(3.14159265);"),
            True)

    def test_string_is_not_number(self):
        """A string should not be detected as a number."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_number('hello');"),
            False)

    def test_true_is_boolean(self):
        """true should be detected as a boolean."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_boolean(true);"),
            True)

    def test_false_is_boolean(self):
        """false should be detected as a boolean."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_boolean(false);"),
            True)

    def test_string_is_not_boolean(self):
        """A string should not be detected as a boolean."""
        self.assertIs(
            self.eval("RAVEN.TYPES.is_boolean('monkey');"),
            False)


class RavenUrlTestCase(RavenTestCase):
    """Test the URL submodule."""

    def test_contains_question_mark(self):
        """A question mark in the string should be detected."""
        self.assertIs(self.eval(
                'RAVEN.URL.contains_question_mark("http://localhost?key=val");'
                ),
                      True)

    def test_no_question_mark(self):
        """A question mark in the string should not be detected."""
        self.assertIs(
            self.eval(
                'RAVEN.URL.contains_question_mark("http://localhost");'),
            False)

    def test_parse_query_string(self):
        """Test the parse_query_string function."""
        arguments = self.eval(
            'RAVEN.URL.parse_query_string("?man=Adam;woman=Eve;");')
        self.assertEquals(arguments['man'], "Adam")
        self.assertEquals(arguments['woman'], "Eve")

    def test_build_query_string(self):
        """Test the build_query_string function."""
        query_string = self.eval(
            'RAVEN.URL.build_query_string({A: "one", B: "two", C: "three"})'
            )
        self.assertEquals(query_string, 'A=one;B=two;C=three')

    def test_build_complex_query_string(self):
        """Test the build_query_string function."""
        query_string = self.eval(
            'RAVEN.URL.build_query_string({number: 1, '
            'object: {"key": "value"}, boolean: true, '
            '"array": ["A", "B", "C"]})'
            )
        self.assertEquals(
            query_string,
            'number=JSON:1;object=JSON:%7B%22key%22%3A%22value%22%7D;'
            'boolean=JSON:true;array=JSON:%5B%22A%22%2C%22B%22%2C%22C%22%5D'
            )

    def test_parse_complex_query_string(self):
        """Test the parse_query_string function."""
        arguments = self.eval(
            'RAVEN.URL.parse_query_string("'
            'number=JSON:1;object=JSON:%7B%22key%22%3A%22value%22%7D;'
            'boolean=JSON:true;array=JSON:%5B%22A%22%2C%22B%22%2C%22C%22%5D'
            '");'
            )
        self.assertEquals(arguments["number"], 1)
        self.assertEquals(arguments['boolean'], True)
        self.assertEquals(dict(arguments['object']), {'key': 'value'})
        self.assertEquals(list(arguments['array']), ['A', 'B', 'C'])

    def test_add_argument_to_url(self):
        """Test the add_argument_to_url function."""
        url = self.eval(
            'RAVEN.URL.add_argument_to_url("http://localhost/", "A", "one")'
            )
        self.assertEquals(url, 'http://localhost/?A=one')

    def test_add_arg_with_existing_args(self):
        """Test the add_argument_to_url function."""
        url = self.eval(
            'RAVEN.URL.add_argument_to_url("http://localhost/?A=one",'
            ' "B", "two")'
            )
        self.assertEquals(url, 'http://localhost/?A=one;B=two')

    def test_get_current_query(self):
        """Test get_current_query, which is empty.
        Gets the current query (as an object) then turns
        it back into a string. Which is empty anyway."""
        query = self.eval(
            'RAVEN.URL.build_query_string(RAVEN.URL.get_current_query())'
            )
        self.assertEquals(query, '')

    def test_get_non_empty_query(self):
        """Test get_current_query, which we will set to non empty.
        Gets the current query (as an object) then
        turns it back into a string."""
        self.eval('window.location.search="?A=one;B=two;C=three"')

        query = self.eval(
            'RAVEN.URL.build_query_string(RAVEN.URL.get_current_query())'
            )
        self.assertEquals(query, 'A=one;B=two;C=three')
        self.eval('window.location.search=""')


class RavenUnderscoreRestTestCase(RavenTestCase):
    """Test the REST submodule's implementation functions."""

    def test_get_api_url(self):
        """Test RAVEN._REST.get_api_url()."""
        self.assertEqual(self.eval('RAVEN._REST.get_api_url();'),
                         'http://localhost/api/')

    def test_get_api_query_url(self):
        """Test RAVEN._REST.get_api_query_url()."""
        self.assertEqual(self.eval('RAVEN._REST.get_api_query_url();'),
                         'http://localhost/api/query/?')

    def test_get_api_resource_url(self):
        """Test RAVEN._REST.get_api_simple_resource_instance_url."""
        self.assertEqual(self.eval(
                'RAVEN._REST.get_api_simple_resource_instance_url('
                '"author", "Suess");'),
                         'http://localhost/api/author/Suess/')

    def test_cache_api_data(self):
        """Test the caching of API data."""
        # put the data in
        self.eval(
            'RAVEN._REST.cache_api_data({_model: "author", "_id": "Suess", '
            'title: "Dr"});')
        # get the data out again
        data_string = self.eval(
            'localStorage["api:http://localhost/api/author/Suess/"]')
        # Decode it back to JSON
        data = json.loads(data_string)
        # Check the type member
        self.assertEqual(data['type'],
                         "json")
        # Check the _model
        self.assertEqual(data['data']['_model'],
                         "author")
        # Check the _id
        self.assertEqual(data['data']['_id'],
                         "Suess")
        # Check the title
        self.assertEqual(data['data']['title'],
                         "Dr")

    def test_cache_api_list(self):
        """Test cache_api_list."""
        # put the data in
        self.eval(
            'RAVEN._REST.cache_api_list({results:['
            '{_model:"author", name: "Douglas Adams", "_id": "AdamsD"}, '
            '{_model:"author", name: "William Gibson", "_id": "GibsonW"}, '
            '{_model:"author", name: "Ray Bradbury", "_id": "BradburyR"}, '
            '{_model:"author", name: "Arthur C. Clarke", "_id": "ClarkeA"}, '
            '{_model:"author", name: "Isaac Asimov", "_id": "AsimovI"}, '
            '{_model:"author", name: "Jules Verne", "_id": "VerneJ"}, '
            '{_model:"author", name: "H.G. Wells", "_id": "WellsH"}'
            ']}, "author", {category:"science_fiction"})')
        # Get the data out again
        data_string = self.eval(
            'localStorage["api:http://localhost/api/author/?category='
            'science_fiction"]')
        # Decode it back to JSON
        data = json.loads(data_string)
        # Check the type member
        self.assertEqual(data['type'],
                         "json")
        # Check the _model of the first entry
        self.assertEqual(data['data']['results'][0]['_model'],
                         "author")
        # Turn the data into a id, name dict.
        authors = {author['_id']: author['name'] for \
                       author in data['data']['results']}
        # Check the authors
        self.assertEqual(authors['ClarkeA'],
                         'Arthur C. Clarke')
        self.assertEqual(authors['AdamsD'],
                         'Douglas Adams')
        self.assertEqual(authors['AsimovI'],
                         'Isaac Asimov')
        self.assertEqual(authors['VerneJ'],
                         'Jules Verne')
        self.assertEqual(authors['BradburyR'],
                         'Ray Bradbury')
        self.assertEqual(authors['WellsH'],
                         'H.G. Wells')
        self.assertEqual(authors['GibsonW'],
                         'William Gibson')

    def test_delete_api_data(self):
        """Test delete_api_data."""
        # put the data in
        self.eval(
            'RAVEN._REST.cache_api_data({_model: "author", "_id": "Suess", '
            'title: "Dr"});')
        # check the data is in
        data_string = self.eval(
            'localStorage["api:http://localhost/api/author/Suess/"]')
        self.assertIs(data_string.startswith('{"type":"json"'), True)
        # delete the data
        self.eval(
            'RAVEN._REST.delete_api_data({_model: "author", "_id": "Suess", '
            'title: "Dr"});')
        #delete_api_data
        data_string = self.eval(
            'typeof localStorage["api:http://localhost/api/author/'
            'Suess/"] === "undefined"')
        data_string_text = self.eval(
            'localStorage["api:http://localhost/api/author/Suess/"]')

        self.assertIs(data_string, True)


def open_test_collection(collection='test',
                         database_name='test'):
    """Open the MongoDB Database."""
    connection = Connection()
    database = connection[database_name]
    return database[collection]

MOCK_MODELS = (
    {
        '_id': 'test',
        '_model': '_model',
        'modeldescription': 'A collection to store test data in.',
        'name': {
            'field': 'Char'
            },
        'optional_field': {
            'field': 'Char',
            'required': False
            },
        '_permissions': {
            'create': True,
            'read': True,
            'update': True,
            'delete': True,
            }
        },
)


class RavenRequestTestCase(RavenTestCase):
    """Test the REQUEST module functions."""
    pass


class RavenRestTestCase(RavenTestCase):
    """Test the REST module functions."""

    def setUp(self):  # pylint: disable=C0103
        """Open a database connection."""
        super(RavenRestTestCase, self).setUp()

        # Create a new test model
        instance_loader = InstanceLoader(
            database='test',
            validation=False)
        instance_loader.add_instances(MOCK_MODELS)

        # Kill any test existing instances
        self.collection = open_test_collection()
        self.collection.remove()

    def tearDown(self):  # pylint: disable=C0103
        """Close the database."""
        self.collection.remove()

    def test_create_resource(self):
        """Test create_resource."""
        self.eval('new_data = {"_model": "test", "name": "create_test" }')
        self.assertIs(self.eval(
                'RAVEN.REST.create_resource("test", new_data)'), None)
        resource = self.collection.find_one()
        self.assertEquals(resource['_model'], u'test')
        self.assertEquals(resource['name'], u'create_test')

    def test_delete_resources(self):
        """Test delete resources."""
        # make a couple of resources
        self.eval(
            'new_data_1 = {"_model": "test", "name": "delete_test_1", '
            '"_id": "delete_test_1" }')
        self.assertIs(self.eval(
                'RAVEN.REST.create_resource("test", new_data_1)'), None)
        self.eval(
            'new_data_2 = {"_model": "test", "name": "delete_test_2", '
            '"_id": "delete_test_2" }')
        self.assertIs(self.eval(
                'RAVEN.REST.create_resource("test", new_data_2)'), None)
        # now delete them
        # Now we delete it
        self.assertIs(self.eval(
                'RAVEN.REST.delete_resources("test", '
                '["delete_test_1", "delete_test_2"]'
                ', {comment: "super delete test"}'
                ')'
                ), None)
        self.sleep()
        # Now we see if it has been deleted
        self.assertEquals(self.collection.find_one(), None)

    def test_delete_resource(self):
        """Test delete_resource"""
        self.eval(
            'new_data = {"_model": "test", "name": "delete_test", '
            '"_id": "delete_test" }')
        self.assertIs(self.eval(
                'RAVEN.REST.create_resource("test", new_data)'), None)
        resource = self.collection.find_one()
        self.assertEquals(resource['_model'], u'test')
        self.assertEquals(resource['name'], u'delete_test')
        # Now we delete it
        self.assertIs(self.eval(
                'RAVEN.REST.delete_resource("test", "delete_test")'), None)
        self.sleep()
        # Now we see if it has been deleted
        self.assertEquals(self.collection.find_one(), None)

    def test_check_resource_existence(self):
        """Test check_resource_existence."""
        self.eval(
            'new_data = {"_model": "test", '
            '"name": "check_resource_existence_test", '
            '"_id": "existence_test" }')
        self.assertIs(self.eval(
                'RAVEN.REST.create_resource("test", new_data)'), None)
        self.assertIs(self.eval(
                'RAVEN.REST.check_resource_existence("test", '
                '"existence_test", {success: function (item) {'
                'window.test_answer = item;}})'), None)
        self.assertIs(self.eval('window.test_answer;'), True)

    def test_update_resource(self):
        """Test update_resource."""
        self.assertIs(
            self.eval(
                'RAVEN.REST.create_resource('
                '"test",'
                '{_model: "test",'
                '_id: "update_test",'
                'name: "original_version"}'
                ')'
                ), None)

        # Lets prove the first version went in.
        resource = self.collection.find_one()
        self.assertEquals(resource['_model'], u'test')
        self.assertEquals(resource['name'], u'original_version')
        self.sleep(1)

        # Now lets update the instance
        self.assertIs(
            self.eval(
                'RAVEN.REST.update_resource('
                '"test",'
                '{_model: "test",'
                '_id: "update_test",'
                'name: "second_version"}'
                ')'
                ), None)

        self.sleep(1)
        # Lets prove the second version went in.
        resource = self.collection.find_one()
        self.assertEquals(resource['name'], u'second_version')

    def test_update_resources(self):
        """Test update_resources."""
        self.assertIs(
            self.eval(
                'RAVEN.REST.create_resource('
                '"test",'
                '{_model: "test",'
                '_id: "name",'
                'name: "Prince Adam"}'
                ')'
                ), None)
        self.assertIs(
            self.eval(
                'RAVEN.REST.create_resource('
                '"test",'
                '{_model: "test",'
                '_id: "house",'
                'name: "The Royal Palace"}'
                ')'
                ), None)
        self.assertIs(
            self.eval(
                'RAVEN.REST.create_resource('
                '"test",'
                '{_model: "test",'
                '_id: "companion",'
                'name: "Cringer"}'
                ')'
                ), None)

        self.assertIs(
            self.eval(
                'RAVEN.REST.update_resources("test",'
                '['
                '{_model: "test",'
                '_id: "name",'
                'name: "He-Man"},'
                '{_model: "test",'
                '_id: "house",'
                'name: "Castle_Grayskull"},'
                '{_model: "test",'
                '_id: "companion",'
                'name: "Battle Cat"}'
                '])'
                ), None)

    def test_update_fields(self):
        """Test update_fields."""
        self.assertIs(
            self.eval(
                'RAVEN.REST.create_resource('
                '"test",'
                '{_model: "test",'
                '_id: "france",'
                'name: "French Account",'
                'optional_field: "red"}'
                ')'
                ), None)
        self.assertIs(
            self.eval(
                'RAVEN.REST.create_resource('
                '"test",'
                '{_model: "test",'
                '_id: "germany",'
                'name: "German Account",'
                'optional_field: "black"}'
                ')'
                ), None)
        self.assertIs(
            self.eval(
                'RAVEN.REST.create_resource('
                '"test",'
                '{_model: "test",'
                '_id: "italy",'
                'name: "Italian Account",'
                'optional_field: "red"}'
                ')'
                ), None)

        self.assertIs(
            self.eval(
                'RAVEN.REST.update_fields('
                '"test",'
                '["france", "germany"],'
                '{optional_field: "black"})'
                ), None)
        resource = self.collection.find_one({'_id': 'france'})
        self.assertEqual(resource['optional_field'], 'black')

    def test_update_field_selection(self):
        """Test update_fields."""
        self.assertIs(
            self.eval(
                'RAVEN.REST.create_resource('
                '"test",'
                '{_model: "test",'
                '_id: "france",'
                'name: "primary account",'
                'optional_field: "red"}'
                ')'
                ), None)
        self.assertIs(
            self.eval(
                'RAVEN.REST.update_field_selection('
                '"test",'
                '{name: "primary account"},'
                '{optional_field: "black"})'
                ), None)
        resource = self.collection.find_one({'_id': 'france'})
        self.assertEqual(resource['optional_field'], 'black')

    def test_update_fields_with_unset(self):
        """Test update_fields."""
        self.assertIs(
            self.eval(
                'RAVEN.REST.create_resource('
                '"test",'
                '{_model: "test",'
                '_id: "france",'
                'name: "French Account",'
                'optional_field: "red"}'
                ')'
                ), None)
        self.assertIs(
            self.eval(
                'RAVEN.REST.create_resource('
                '"test",'
                '{_model: "test",'
                '_id: "germany",'
                'name: "German Account",'
                'optional_field: "black"}'
                ')'
                ), None)
        self.assertIs(
            self.eval(
                'RAVEN.REST.create_resource('
                '"test",'
                '{_model: "test",'
                '_id: "italy",'
                'name: "Italian Account",'
                'optional_field: "red"}'
                ')'
                ), None)

        self.assertIs(
            self.eval(
                'RAVEN.REST.update_fields('
                '"test",'
                '["france", "germany"],'
                '{"$unset": {"optional_field": 1}}'
                ', {comment: "Remove optional field."}'
                ')'
                ), None)
        resource = self.collection.find_one({'_id': 'france'})
        self.assertEqual(
            resource.get('optional_field'),
            None)

EMBEDDED_MODELS = {
    'article': {
        '_id': 'article',
        '_model': '_model',
        '_permissions': {
            'create': True,
            'read': True,
            'update': True,
            'delete': True,
            },
        'body': {'field': 'Text'},
        'author': {
            'field': 'Embedded',
            'valid_models': ['author']},
        'comment': {
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
    'comment': [
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

class TestEmbedModificationValidation(RavenTestCase):
    """Test validate_modification on a complex example with
    embedded resources."""
    def setUp(self):  # pylint: disable=C0103
        """Open a database connection."""
        super(TestEmbedModificationValidation, self).setUp()

        # Create a new test model
        # Create a new test model
        instance_loader = InstanceLoader(
            database='test',
            validation=False)
        instance_loader.add_instances(six.itervalues(EMBEDDED_MODELS))
        # Kill any test existing instances
        database = Database(database_name='test')
        self.collection = database.get_collection('article')
        self.collection.remove()
        # Add the test article
        self.collection.insert(TEST_ARTICLE)


    def test_embed_modification(self):
        """Test the embedded modification."""
        self.assertIs(
            self.eval(
                'RAVEN.REST.update_fields('
                '"article",'
                '["testarticle",],'
                '{"$set": {"author.name": "Mr Man"}}'
                ', {comment: "Update embedded list field."}'
                ')'
                ), None)

        resource = self.collection.find_one({'_id': 'testarticle'})
        author = resource['author']['name']

        self.assertEqual(
            author,
            "Mr Man")


    def test_embed_list_modification(self):
        """Test the embedded modification."""
        self.assertIs(
            self.eval(
                'RAVEN.REST.update_fields('
                '"article",'
                '["testarticle",],'
                '{"$set": {"comment.0.author.name": "Mr Happy"}}'
                ', {comment: "Update embedded list field."}'
                ')'
                ), None)

        resource = self.collection.find_one({'_id': 'testarticle'})
        author = resource['comment'][0]['author']['name']

        self.assertEqual(
            author,
            "Mr Happy")

EMBEDDED_MODELS_B = {
    'article': {
        '_id': 'article',
        '_model': '_model',
        '_permissions': {
            'create': True,
            'read': True,
            'update': True,
            'delete': True,
            },
        'body': {'field': 'Text'},
        'writer': {
            'field': 'Embedded',
            'resource': 'author'},
        'comments': {
            'field': 'EmbeddedList',
            'required': False,
            'resource': 'comment'}
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


TEST_ARTICLE_B = {
    '_id': 'testarticle',
    '_model': 'article',
    'body': 'This is the body of the article.',
    'writer': {
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

class TestEmbedModificationValidationB(RavenTestCase):
    """Test validate_modification on a complex example with
    embedded resources."""
    def setUp(self):  # pylint: disable=C0103
        """Open a database connection."""
        super(TestEmbedModificationValidationB, self).setUp()

        # Create a new test model
        instance_loader = InstanceLoader(
            database='test',
            validation=False)
        instance_loader.add_instances(six.itervalues(EMBEDDED_MODELS_B))
        # Kill any test existing instances
        database = Database(database_name='test')
        self.collection = database.get_collection('article')
        self.collection.remove()
        # Add the test article
        self.collection.insert(TEST_ARTICLE_B)


    def test_embed_modification(self):
        """Test the embedded modification."""
        self.assertIs(
            self.eval(
                'RAVEN.REST.update_fields('
                '"article",'
                '["testarticle",],'
                '{"$set": {"writer.name": "Mr Man"}}'
                ', {comment: "Update embedded list field."}'
                ')'
                ), None)

        resource = self.collection.find_one({'_id': 'testarticle'})
        author = resource['writer']['name']

        self.assertEqual(
            author,
            "Mr Man")


    def test_embed_list_modification(self):
        """Test the embedded modification."""
        self.assertIs(
            self.eval(
                'RAVEN.REST.update_fields('
                '"article",'
                '["testarticle",],'
                '{"$set": {"comments.0.author.name": "Mr Happy"}}'
                ', {comment: "Update embedded list field."}'
                ')'
                ), None)

        resource = self.collection.find_one({'_id': 'testarticle'})
        author = resource['comments'][0]['author']['name']

        self.assertEqual(
            author,
            "Mr Happy")


if __name__ == '__main__':
    unittest.main()
