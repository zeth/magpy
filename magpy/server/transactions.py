"""Transactions support."""

import json
from functools import partial
import tornado.web

from bson import json_util
from bson.objectid import ObjectId
from pymongo import DESCENDING

from magpy.server.database import DatabaseMixin
from magpy.server.auth import AuthenticationMixin

#class TransactionMixin(object):
#    """Mix into class to get transaction support."""
#    pass


class TransactionUpdateHandler(tornado.web.RequestHandler,
                               DatabaseMixin,
                               AuthenticationMixin):
    """Given a model_name and an objectid, get all history newer than that."""
    @tornado.web.asynchronous
    def get(self, model_name, objectid):  # pylint: disable=W0221
        print "model name is", model_name
        print "object id is", objectid

        history = self.get_collection('_history')
        history.find({'document_model': model_name,
                      '_id': {'$gt': ObjectId(objectid)}}).to_list(
            callback=self._return_instance)

    def _return_instance(self, instance, error=None):
        """Return a single instance or anything else that can become JSON."""
        print "instance is", instance
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(instance, default=json_util.default))
        self.finish()


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
        models.find({'_applications': app_name},
                    fields=['_id', ]).to_list(
            callback=self.find_all_last_instances)

    def find_all_last_instances(self, models, error=None):
        """Find all the last instances of the models."""
        model_names = [model['_id'] for model in models]
        return self.find_the_next_one(
            None, None, model_names, [], model_names)

    def find_the_next_one(self, result, error, remaining, results, models):
        """Find the next instance in remaining models."""
        if result:
            results.append(result)
        if remaining:
            model_name = remaining.pop()

            callback = partial(self.find_the_next_one,
                               remaining=remaining,
                               results=results,
                               models=models)
            return self.find_the_last_use(model_name, callback)

        complete = {
            result['document_model']: str(result['_id']) for
            result in results}

        return self._return_instance({'state': complete})

    def find_the_last_use(self, model_name, callback):
        """Find the last use of the model in the history."""
        history = self.get_collection('_history')
        history.find_one({'document_model': model_name},
                         sort=[('_id', DESCENDING)],
                         fields=['document_model', '_id'],
                         callback=callback)

    def _return_instance(self, instance, error=None):
        """Return a single instance or anything else that can become JSON."""
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(instance, default=json_util.default))
        self.finish()
