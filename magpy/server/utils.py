"""Common simple utils."""
import os
from pkgutil import get_loader
import json
from bson import json_util


def dejsonify(value):
    """Converts from JSON when it is JSON, otherwise return it."""
    if value.startswith('JSON:'):
        value = value.strip('JSON:')
        value = json.loads(value,
                           object_hook=json_util.object_hook)
    return value


def instance_list_to_dict(list_of_instances):
    """Convert instance list to dict by id."""
    return {instance['_id']: instance for \
                instance in list_of_instances}

def get_mag_path():
    """Return the file path of magpy."""
    loader = get_loader('magpy')
    return os.path.abspath(os.path.split(loader.get_filename())[0])
