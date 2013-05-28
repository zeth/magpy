"""Transactions support."""

import tornado.web
import json
from bson import json_util
from magpy.server.database import DatabaseMixin
from magpy.server.auth import AuthenticationMixin

#class TransactionMixin(object):
#    """Mix into class to get transaction support."""
#    pass


class TransactionSyncHandler(tornado.web.RequestHandler,
                             DatabaseMixin,
                             AuthenticationMixin):
    """Given app_name, gives a list of relevant models and the
    current collection version numbers. """
    @tornado.web.asynchronous
    def get(self, app_name):  # pylint: disable=W0221
        return self.find_relevant_models(app_name)

    def find_relevant_models(self, app_name):
        """Find the relevant models for the app."""
        models = self.get_collection('_model')
        models.find({'_applications': app_name}).to_list(
            callback=self._return_instance)

    def _return_instance(self, instance, error=None):
        """Return a single instance or anything else that can become JSON."""
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(instance, default=json_util.default))
        self.finish()
