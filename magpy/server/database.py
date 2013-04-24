B"""Database access."""

from __future__ import print_function

from copy import deepcopy
from functools import partial

import tornado.web
from bson.objectid import ObjectId
from pymongo import Connection
from pymongo.errors import ConnectionFailure

from magpy.server.utils import instance_list_to_dict
from magpy.server.validators import validate_model_instance, \
    ValidationError, MissingFields, parse_instance, validate_modification, \
    get_all_modification_modelnames

from magpy.server.config import MagpyConfigParser

try:
    from settings import DEFAULT_DATABASE
except:
    DEFAULT_DATABASE = None

try:
    from settings import TEST_DATABASE
except:
    TEST_DATABASE = 'test'


class Database(object):
    """Simple database connection for use in serverside scripts etc."""
    def __init__(self,
                 database_name=None,
                 config_file=None):
        try:
            self.connection = Connection(tz_aware=True)
        except ConnectionFailure:
            print("Could not connect to MongoDB database.")
            print("Are you sure it is installed and is running?")
            print("The exception is shown below.")
            print("")

            raise

        self.config = MagpyConfigParser(config_file)

        if not database_name:
            if DEFAULT_DATABASE:
                database_name = DEFAULT_DATABASE
            else:
                database_name = self.config.databases['default']['NAME']

        self._database_name = database_name
        self.database = self.connection[database_name]

    def drop_database(self):
        """Drop the whole database."""
        self.connection.drop_database(self.database)
        self.database = self.connection[self._database_name]

    def get_collection(self, collection):
        """Get a collection by name."""
        return self.database[collection]

    def drop_collection(self, collection):
        """Drop a collection by name."""
        self.database.drop_collection(collection)

    def drop_collections(self, collections):
        """Drop a named tuple or list of collections."""
        for collection in collections:
            self.drop_collection(collection)

    def get_setting_category(self, category):
        """Get a setting category from the database."""
        settings = self.get_collection('_settings')
        return settings.find_one({'_id': category})

    def get_setting(self, category, setting):
        """Get a setting from the database."""
        category = self.get_setting_category(category)
        if not category:
            return None
        try:
            return category[setting]
        except KeyError:
            return None

    def add_setting(self, category, setting, value):
        """Add a setting to the database."""
        category_instance = self.get_setting_category(category)
        if category_instance:
            category_instance[setting] = value
        else:
            category_instance = {'_id': category,
                                 setting: value}
        settings = self.get_collection('_settings')
        settings.save(category_instance)

    def remove_setting(self, category, setting):
        """Remove a setting from the database."""
        category_instance = self.get_setting_category(category)
        if not category_instance:
            return
        if not setting in category_instance:
            return
        del category_instance[setting]
        settings = self.get_collection('_settings')

        if len(category_instance.keys()) == 1:
            settings.remove(category_instance['_id'])
        else:
            settings.update(category_instance)

    def add_list_setting(self, category, setting, value):
        """Add a value to a list setting."""
        category_instance = self.get_setting_category(category)
        if category_instance:
            if not setting in category_instance:
                category_instance['setting'] = []
        else:
            category_instance = {'_id': category,
                                 setting: []}
        if value not in category_instance[setting]:
            category_instance[setting].append(value)
            settings = self.get_collection('_settings')
            settings.save(category_instance)
        else:
            print("Already set, skipping.")

    def remove_list_setting(self, category, setting, value):
        """Add a value to a list setting."""
        category_instance = self.get_setting_category(category)

        # To remove the value from the setting, the setting must exist
        if not category_instance:
            return
        if not setting in category_instance:
            return

        # Now lets try to remove the named setting
        try:
            category_instance[setting].remove(value)
        except ValueError:
            # It was not in the list.
            return

        settings = self.get_collection('_settings')
        settings.save(category_instance)
        return

    def get_app_list(self):
        """Get the list of installed applications from the database."""
        return self.get_setting('applications', 'installed_apps')

    def add_app(self, app_name):
        """Add an app name to the list of installed applications."""
        self.add_list_setting('applications', 'installed_apps', app_name)

    def remove_app(self, app_name):
        """Remove an app name from the list of installed applications."""
        self.remove_list_setting('applications', 'installed_apps',
                                 app_name)


class DatabaseMixin(object):
    """Mix into class to get database support."""

    @property
    def database_name(self):
        """Get the correct database name."""
        try:
            return self._database_name
        except:
            pass

        if 'X-UnitTest' in self.request.headers:
            if self.request.headers['X-UnitTest'] == 'True':
                self._database_name = TEST_DATABASE
                return TEST_DATABASE
        default_database = self.application.databases['default']['NAME']
        self._database_name = default_database
        return default_database

    @property
    def database(self):
        """Get the database object."""
        try:
            return self._database
        except:
            database = self.application.connection[self.database_name]
            self._database = database
            return database

    def get_collection(self, collection):
        """Get a collection.
        """
        return self.database[collection]

    def get_model(self, model_name, callback):
        """Get a model."""
        models = self.get_collection('_model')
        models.find_one({'_id': model_name},
                        callback=callback)

    def get_models(self, model_names, callback):
        """Get a set of models by name."""
        models = self.get_collection('_model')
        models.find(spec={'_id': {'$in': tuple(model_names)}}).to_list(
            callback=callback)

    def update_history(self,
                       instance,
                       operation,
                       success,
                       versional_comment=None):
        """Add version or versions to history."""

        if isinstance(instance, dict):
            # We have a single instance
            version = create_version(instance, operation, versional_comment)
        else:
            # We have multiple versions (or junk)
            version = create_versions(instance, operation, versional_comment)
        history_collection = self.get_collection('_history')
        history_collection.insert(version,
                                  callback=success)


class ValidationMixin(object):
    """Provides validation support to MongoDB stored models."""
    embedded_models = {}

    def validate_instance(self, instance, success):
        """Validate an instance."""
        callback = partial(
            self._do_validate,
            instance=instance,
            success=success)
        self._request_model(instance, callback)

    def _old_request_model(self, instance, success):
        """Get the model from the database."""
        coll = self.get_collection('_model')
        callback = partial(self._do_validate,
                           instance=instance,
                           success=success)
        try:
            instance['_model']
        except KeyError:
            raise tornado.web.HTTPError(400, 'Missing model key')
        coll.find_one({'_id': instance['_model']},
                      callback=callback)

#    def validate_modifier(self, model_name, error,
#                          modifier, success):
    def validate_modifier(self, model_name,
                          error=None,
                          modifier=None,
                          success=None):
        """Validate a modification."""
        # start by getting the model

        callback = partial(self._get_embedded_modifier_models,
                           model_name=model_name,
                           modifier=modifier,
                           success=success)

        self.get_model(model_name,
                       callback=callback)

    def _get_embedded_modifier_models(self, model,
                                      error=None,
                                      model_name=None,
                                      modifier=None,
                                      success=None):
        """Validate a modification."""
        embedded_model_names, \
            unknown_names = \
            get_all_modification_modelnames(model,
                                            modifier)
        model_names = deepcopy(embedded_model_names)
        model_names.append(model_name)
        model_names.extend(unknown_names)

        callback = partial(
            self._validate_modifier,
            model_name=model_name,
            modifier=modifier,
            embedded_model_names=embedded_model_names,
            unknown_names=unknown_names,
            success=success)
        self.get_models(model_names,
                        callback=callback)

    def _validate_modifier(self,
                           models,
                           error,
                           model_name, modifier,
                           embedded_model_names,
                           unknown_names, success):
        """Validate modifier."""
        embedded_models = instance_list_to_dict(models)
        model = embedded_models.pop(model_name)

        validate_modification(model,
                              modifier,
                              handle_none=False,
                              embedded_models=embedded_models,
                              callback=success)

    def _request_model(self, instance, success, get_embedded=True):
        """Get the model from the database."""
        coll = self.get_collection('_model')
        if get_embedded:
            callback = partial(self._get_embedded_model_names,
                               instance=instance,
                               success=success)
        else:
            callback = success

        try:
            instance['_model']
        except KeyError:
            raise tornado.web.HTTPError(400, 'Missing model key')
        coll.find_one({'_id': instance['_model']},
                      callback=callback)

    def _get_embedded_model_names(self, model, error, instance, success):
        """Get the names of the embedded instance models."""
        # Make a copy without the top level model
        # This is important in the case of a model that can embed
        # itself
        new_instance = instance.copy()
        del new_instance['_model']

        # Get all the model names used
        embedded_model_names = set()
        parse_instance(new_instance, embedded_model_names)

        # Skip any that we have in memory already
        if self.embedded_models:
            embedded_model_names = embedded_model_names - set(
                self.embedded_models.keys())

        # If we have them all, move along.
        if not embedded_model_names:
            return success(
                model=model,
                embedded_models=None)

        return self._get_embedded_models(model,
                                         instance,
                                         success,
                                         embedded_model_names)

    def _get_embedded_models(self,
                             model,
                             instance,
                             success,
                             model_names):
        """Get the models from the model_names."""

        callback = partial(self._handle_embedded_models,
                           model=model,
                           instance=instance,
                           success=success)
        self.get_models(model_names=model_names,
                        callback=callback)

    def _handle_embedded_models(self,
                                list_of_embedded_models,
                                error,
                                model,
                                instance,
                                success):
        """When looping through the model results has finished,
        validate the instance."""
        embedded_models = instance_list_to_dict(list_of_embedded_models)

        return success(
            model=model,
            embedded_models=embedded_models)

    def _do_validate(self, model, instance, success,
                     embedded_models=None):
        """Validate an instance."""
        try:
            validate_model_instance(model,
                                    instance,
                                    embedded_models=embedded_models)
        except MissingFields as fields:
            raise tornado.web.HTTPError(400, "Missing Fields %s" % fields)
        except ValidationError:
            raise tornado.web.HTTPError(400, "Validation Error")
        success(instance)


def create_version(instance,
                   operation,
                   versional_comment=None):
    """Create a version dictionary for an instance.
    operation - one of 'create', 'update' or 'delete'.
    """
    if not versional_comment:
        versional_comment = "Instance %sd" % operation

    return {
        '_id': str(ObjectId()),
        'document_id': instance['_id'],
        'document_model': instance['_model'],
        'document': instance,
        'comment': versional_comment,
        'operation': operation}


def create_versions(instances, operation, versional_comment):
    """Create a version dictionaries for a list of instances."""
    return [create_version(instance, operation, versional_comment)
            for instance in instances]
