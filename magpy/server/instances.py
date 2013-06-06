"""Load an instance on the server side."""
# TODO: this doesn't really use the multiple database support correctly
# TODO: get rid of this module altoghether, merge into database.Database

from __future__ import print_function

from magpy.server.database import Database


class InstanceLoader(object):
    """Load instance into the database."""

    def __init__(self,
                 handle_none=False,
                 validation=True,
                 database=None,
                 embedded=False):
        """Startup the loader."""
        self.handle_none = handle_none
        self.skip_validation = not validation
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
        self.database.add_instance(
            instance,
            skip_validation=self.skip_validation,
            handle_none=self.handle_none)

    def add_instances(self, instances):
        """All several instances to the db."""
        for instance in instances:
            self.add_instance(instance)
