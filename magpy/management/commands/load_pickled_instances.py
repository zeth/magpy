"""Add a pickle file of instances to the database."""

import pickle
from magpy.management import BaseCommand, CommandError
from magpy.server.database import Database

class Command(BaseCommand):
    """Add a pickle file of instances to the database."""
    help = ('Add a pickle file of instances to the database.')

    def handle(self, *args, **kwargs):
        print args
        database = Database()
        pkl_file = open(args[0], 'rb')
        instances = pickle.load(pkl_file)
        collection = database.get_collection(args[1])
        for instance in instances:
            collection.insert(instance)
            print "Added", instance['_id']

        pkl_file.close()
