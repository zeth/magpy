"""EJDB driver for Magpy.
Currently does not do much except support certain command line scripts.
"""
import os
import pyejdb


class Database(object):
    """Simple database connection for use in serverside scripts etc."""
    def __init__(self,
                 database_name=None,
                 config_file=None):
        self.config_file = config_file
        if not database_name:
            database_name = os.path.expanduser('~/magpy.tct')
        self._database_name = database_name
        self.database = pyejdb.EJDB(database_name,
                                    pyejdb.DEFAULT_OPEN_MODE |
                                    pyejdb.JBOTRUNC)

    def get_collection(self, collection):
        """Get a collection by name."""
        return Collection(collection, self)

    def drop_collections(self, collections):
        """Drop a named tuple or list of collections."""
        for collection in collections:
            self.database.dropCollection(collection)


class Collection(object):
    """A mongodb style collection object."""
    def __init__(self, name, database):
        self.database = database
        self.name = name

    def find(self):
        """Find instances from a collection."""
        return self.database.database.find(self.name)

    def find_one(self):
        """Find a single instance from a collection."""
        raise NotImplementedError

    def save(self, instance):
        """Save an instance."""
        instance['id'] = instance.pop('_id')
        self.database.database.save(self.name, instance)
