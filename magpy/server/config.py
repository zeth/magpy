"""Read the magpy configuration file."""

import os
import re
import json

from magpy.server.utils import get_mag_path, make_cookie_secret

# Regular expression for comments
COMMENT_RE = re.compile(
    r'(^)?[^\S\n]*/(?:\*(.*?)\*/[^\S\n]*|/[^\n]*)($)?',
    re.DOTALL | re.MULTILINE
)


class MagpyConfigParser(object):
    """Parses the magpy configuration file."""

    def __init__(self, config_file=None):
        self.port = 8000
        self.databases = None
        self.cookie_secret = None
        if not config_file:
            config_file = os.path.join(
                get_mag_path(), 'server', 'defaultconfig.json')
        print "Using config File", config_file

        self.config_file_path = config_file
        self.load_json()
        if not getattr(self, 'cookie_secret', None):
            self.cookie_secret = make_cookie_secret()
        if not getattr(self, 'databases', None):
            self.databases = {"default": {"ENGINE": "mongodb",
                                          "NAME": "vmr"}}

    def load_json(self):
        """ Parse a JSON file
            First remove comments and then use the json module package
            Comments look like :
                // ...
            or
                /*
                ...
                */
            Love to Damien Riquet
            http://www.lifl.fr/~riquetd/parse-a-json-file-with-comments.html
        """

        with open(self.config_file_path) as filepointer:
            content = ''.join(filepointer.readlines())

            ## Looking for comments
            match = COMMENT_RE.search(content)
            while match:
                # single line comment
                content = content[:match.start()] + content[match.end():]
                match = COMMENT_RE.search(content)

            ## Store all the config data
            self.__dict__.update(json.loads(content))
