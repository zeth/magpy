"""Load an instance on the server side."""
# TODO: this doesn't really use the multiple database support correctly
# TODO: get rid of this module altoghether, merge into database.Database

from __future__ import print_function

from magpy.server.database import Database
from magpy.server.validators import validate_model_instance, ValidationError
import sys


class InstanceLoader(object):
    """Load instance into the database."""

    def __init__(self,
                 handle_none=False,
                 validation=True,
                 database=None,
                 embedded=False):
        """Startup the loader."""
        self.handle_none = handle_none
        self.validation = validation
        database_type = None
        if embedded:
            database_type = 'ainodb'
        else:
            database_type = None

        self.database = Database(
            database_name=database,
            database_type=database_type)

    def add_instance(self, instance):
        """Add instance to the db."""
        model_name = instance['_model']

        if self.validation:
            model_collection = self.database.get_collection('_model')
            model = model_collection.find_one({'_id': model_name})
            try:
                validate_model_instance(model,
                                        instance,
                                        handle_none=self.handle_none)
            except ValidationError:
                print("Died on instance:")
                print(instance)
                raise

        # We got this far, yay!
        instance_collection = self.database.get_collection(model_name)
        instance_collection.save(instance)
        sys.stdout.write(model_name[0])

    def add_instances(self, instances):
        """All several instances to the db."""
        for instance in instances:
            self.add_instance(instance)
