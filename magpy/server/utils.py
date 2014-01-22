"""Common simple utils."""
import os
from pkgutil import get_loader
import json
from bson import json_util
import base64
import uuid
import six

def dejsonify(value):
    """Converts from JSON when it is JSON, otherwise return it."""
    if six.PY2:
        if value.startswith('JSON:'):
            value = value.strip('JSON:')
            value = json.loads(value,
                               object_hook=json_util.object_hook)
    else:
        # Weird things in Python 3 happening with types
        # Seems to start as bytes
        if value.startswith(b'JSON:'):
            value = value.strip(b'JSON:')
            # But the next line seems to want a unicode str
            value = value.decode(encoding='UTF-8')
            value = json.loads(value,
                               object_hook=json_util.object_hook)
    return value


def instance_list_to_dict(list_of_instances):
    """Convert instance list to dict by id."""
    return {instance['_id']: instance for
            instance in list_of_instances}


def get_mag_path(app='magpy'):
    """Return the file path of magpy."""
    loader = get_loader(app)
    return os.path.abspath(os.path.split(loader.get_filename())[0])


def make_cookie_secret():
    """Make a cookie secret."""
    return base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)
