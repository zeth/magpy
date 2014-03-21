"""Test auth."""
from __future__ import print_function

import unittest
import time

from magpy.server.instances import InstanceLoader
from magpy.tests.test_magjs import open_test_collection, MagTestCase

import six

if six.PY3:
    NOTFOUND = 'urllib.error.HTTPError: HTTP Error 404: Not Found'
else:
    NOTFOUND = 'HTTPError: HTTP Error 404: Not Found'

if six.PY3:
    UNAUTHORISED = 'urllib.error.HTTPError: HTTP Error 401: Unauthorized'
else:
    UNAUTHORISED = 'HTTPError: HTTP Error 401: Unauthorized'

MOCK_AUTH_MODELS = (
    {
        '_id': 'auth_test',
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
            'create': False,
            'read': False,
            'update': False,
            'delete': False,
            }
        },
)

class MagUnauthorisedAuthTestCase(MagTestCase):
    """Check that the auth module blocks requests as Unauthorized."""
    _delay = 0.5
    def setUp(self):  # pylint: disable=C0103
        """Open a database connection."""
        super(MagUnauthorisedAuthTestCase, self).setUp()
        # Create a new test model
        instance_loader = InstanceLoader(
            database='test',
            validation=False)
        instance_loader.add_instances(MOCK_AUTH_MODELS)

        # Kill any test existing instances
        self.collection = open_test_collection('auth_test')
        self.collection.remove()

    def tearDown(self):  # pylint: disable=C0103
        """Close the database."""
        self.collection.remove()

    def sleep(self,
              delay=None):
        """Pause to avoid database race conditions."""
        if not delay:
            delay = self._delay

        print("%s sec delay to give the database time . . ." % delay, end=' ')
        time.sleep(delay)
        print(". . now we continue")

    def test_unauthorised_create(self):
        """Test that we cannot create_resource."""
        self.eval('new_data = {"_model": "auth_test", "name": "create_test" }')
        response = self.eval(
                'MAG.REST.create_resource("auth_test", new_data)')
        self.assertEqual(response.splitlines()[-1],
                         UNAUTHORISED)

    def test_unauthorised_update(self):
        """Test update_resource."""

        response = self.eval(
            'MAG.REST.update_resource('
            '"auth_test",'
            '{_model: "auth_test",'
            '_id: "update_test",'
            'name: "second_version"}'
            ')')
        self.assertEqual(response.splitlines()[-1],
                          UNAUTHORISED)

    def test_unauthorised_delete(self):
        """Test that the unauthorised user cannot delete a resource."""
        self.collection.save(
            {'_model': 'auth_test',
            '_id': 'delete_test',
            'name': 'first_version'})
        response = self.eval(
                'MAG.REST.delete_resource("test", "delete_test")')
        self.assertEqual(response,
                          None)
        self.assertEqual(
            self.collection.find_one(),
            {u'_model': u'auth_test',
             u'_id': u'delete_test',
             u'name': u'first_version'})

    def test_unauthorised_read(self):
        """Test that the unauthorised user cannot read a resource."""
        self.collection.save(
            {'_model': 'auth_test',
            '_id': 'read_test',
            'name': 'first_version'})
        self.assertEqual(
            self.collection.find_one(),
            {u'_model': u'auth_test',
             u'_id': u'read_test',
             u'name': u'first_version'})

        response = self.eval(
                'MAG.REST.apply_to_resource("test", "read_test")')
        self.assertEqual(response.splitlines()[-1],
                          NOTFOUND)


if __name__ == '__main__':
    unittest.main()
