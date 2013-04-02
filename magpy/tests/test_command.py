"""Tests for Advanced REST commands."""

import unittest
from magpy.tests.javascript import JavaScriptTestCase
from magpy.server.instances import InstanceLoader
from magpy.tests.test_ravenjs import MOCK_MODELS, RavenTestCase, \
    RAVEN, open_test_collection

# pylint: disable=R0904

from magpy.server.database import Database


class RavenCommandTestCase(RavenTestCase):
    """Test advanced commands."""

    def setUp(self):  # pylint: disable=C0103
        """Open a database connection."""
        super(RavenCommandTestCase, self).setUp()

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

    def test_get_unique_id(self):
        """Test RAVEN.COMMAND.get_unique_id"""
        self.eval(
            'new_data = {"_model": "test", "name": "unique_id_test", '
            '"_id": "unique_id_test_1" }')
        self.assertIs(self.eval(
                'RAVEN.REST.create_resource("test", new_data)'), None)


if __name__ == '__main__':
    unittest.main()
