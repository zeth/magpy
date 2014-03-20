"""Tests for Magpy."""

import six

import os
import unittest
from magpy.tests.javascript import JavaScriptTestCase
from magpy.server.instances import InstanceLoader
from magpy.tests.test_magjs import open_test_collection
from magpy.server.utils import get_mag_path

# pylint: disable=R0904


class MagTestCase(JavaScriptTestCase):
    """Load the Mag file into the session."""
    def setUp(self):  # pylint: disable=C0103
        super(MagTestCase, self).setUp()
        magjs = os.path.join(get_mag_path(), 'static/js/mag.js')
        self.load(magjs)
        self.eval('MAG._REQUEST._default_headers["X-UnitTest"] = "True";')

from magpy.tests.test_validators import EMBEDDED_MODELS, TEST_ARTICLE
from magpy.server.database import Database


class MagEmbedTestCase(MagTestCase):
    """Test an embedded instance."""

    def setUp(self):  # pylint: disable=C0103
        """Open a database connection and load the models."""
        super(MagEmbedTestCase, self).setUp()

        # Create test models
        EMBEDDED_MODELS['article']['_permissions'] = {
            'create': True,
            'read': True,
            'update': True,
            'delete': True,
            }

        instance_loader = InstanceLoader(
            database='test',
            validation=False)
        instance_loader.add_instances(tuple(six.itervalues(EMBEDDED_MODELS)))

        # Kill any test existing instances
        database = Database(database_name='test')
        collection = database.get_collection('article')
        collection.remove()

    def test_create_resource(self):
        """Test MAG._REST.get_api_url()."""
        data = 'new_data = %s;' % TEST_ARTICLE
        if six.PY3:
            data = bytes(data, 'utf8')
        self.eval(data)
        self.assertIs(self.eval(
               'MAG.REST.create_resource("article", new_data)'), None)
        #resource = self.collection.find_one()
        #self.assertEqual(resource['_model'], u'_test')
        #self.assertEqual(resource['name'], u'create_test')


if __name__ == '__main__':
    unittest.main()
