"""Tests for Magpy."""

import unittest
from javascript import JavaScriptTestCase
from magpy.management.managep import Management
from magpy.tests.test_ravenjs import open_test_collection

RAVEN = "/srv/vmr/web/static/frontend/js/raven.js"

# pylint: disable=R0904


class RavenTestCase(JavaScriptTestCase):
    """Load the Raven file into the session."""
    def setUp(self):  # pylint: disable=C0103
        super(RavenTestCase, self).setUp()
        self.load(RAVEN)
        self.eval('RAVEN._REQUEST._default_headers["X-UnitTest"] = "True";')

from test_validators import EMBEDDED_MODELS, TEST_ARTICLE
from magpy.server.database import Database


class RavenEmbedTestCase(RavenTestCase):
    """Test an embedded instance."""

    def setUp(self):  # pylint: disable=C0103
        """Open a database connection and load the models."""
        super(RavenEmbedTestCase, self).setUp()

        # Create test models
        EMBEDDED_MODELS['article']['_permissions'] = {
            'create': True,
            'read': True,
            'update': True,
            'delete': True,
            }

        manager = Management(database_name='test')
        manager.sync(tuple(EMBEDDED_MODELS.itervalues()))

        # Kill any test existing instances
        database = Database(database_name='test')
        collection = database.get_collection('article')
        collection.remove()

    def test_create_resource(self):
        """Test RAVEN._REST.get_api_url()."""
        self.eval('new_data = %s;' % TEST_ARTICLE)
        self.assertIs(self.eval(
               'RAVEN.REST.create_resource("article", new_data)'), None)
        #resource = self.collection.find_one()
        #self.assertEquals(resource['_model'], u'_test')
        #self.assertEquals(resource['name'], u'create_test')


if __name__ == '__main__':
    unittest.main()
