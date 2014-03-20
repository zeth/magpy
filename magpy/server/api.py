"""REST service, used via JavaScript API or directly."""
from __future__ import print_function

from datetime import datetime
from copy import deepcopy
import json
import re
import os
import base64

import tornado.web
from bson import json_util
from functools import partial
from magpy.server.validators import validate_model_instance, \
    ValidationError, MissingFields
from bson.objectid import ObjectId
from magpy.server.auth import AuthenticationMixin, WhoAmIMixin, \
    permission_required
from magpy.server.database import DatabaseMixin, ValidationMixin
from magpy.server.utils import dejsonify, instance_list_to_dict
import six


class ResourceTypeHandler(tornado.web.RequestHandler,
                          DatabaseMixin,
                          AuthenticationMixin,
                          ValidationMixin,
                          WhoAmIMixin):
    """
    finds the overall collection and performs the relevant method upon it.
    """
    # pylint: disable=W0221,R0904

    writing = False
    new_instances = {}
    validated_instances = []
    _output_instances = []
    _post_history_instances = []

    @tornado.web.asynchronous
    @permission_required('delete')
    def delete(self, resource):
        """Delete multiple instances."""
        data = json.loads(self.request.body,
                          object_hook=json_util.object_hook)
        if not 'ids' in data:
            raise tornado.web.HTTPError(400, "No ids to delete")

        instances = [
            {
                '_id': objectid,
                '_model': resource,
                } for objectid in data['ids']]
        versional_comment = data.get('_versional_comment')
       
#         callback = partial(self._do_multiple_delete,
#                            ids=data['ids'],
#                           resource=resource)

        callback = partial(self._get_model,
                           ids=data['ids'],
                           resource=resource)

        self.update_history(instances,
                            'delete',
                            callback,
                            versional_comment)
        
    
    def _get_model(self, response, error, ids, resource):
        coll = self.get_collection('_model')
        success = partial(self._check_files_in_model,
                          resource=resource,
                          ids=ids)
        coll.find({'_id': resource}).to_list(callback=success)
        
    def _check_files_in_model(self, response, error, resource, ids):
        if '_file_fields' in response[0]:
            self._get_instances(response[0]['_file_fields']['fields'], resource, ids)
        else:
            self._do_multiple_delete(ids, resource)

    def _get_instances(self, file_fields, resource, ids):
        success = partial(self._delete_files,
                           file_fields=file_fields,
                           resource=resource,
                           ids=ids)
        coll = self.get_collection(resource)
        coll.find({'_id': {'$in': tuple(ids)}}).to_list(callback=success)

        
    def _delete_files(self, response, error, file_fields, resource, ids):
        for json in response:
            for field in file_fields:
                file = json[field].replace('/media/', '/srv/vmr/workspace/mediamanager/restricted/')
                if os.path.isfile(file):
                    os.unlink(file)
        self._do_multiple_delete(ids, resource)

    @tornado.web.asynchronous
    def _do_multiple_delete(self, ids=None, resource=None):
        """Delete the instances named in ids."""
        print("Superdif", ids)

        callback = partial(self._delete_success,
                           ids=ids,
                           resource=resource)
        collection = self.get_collection(resource)
        collection.remove({'_id': {'$in': tuple(ids)}},
                          callback=callback)

    def _delete_success(self, response, error, resource, ids):
        """Return the deleted ids."""
        self._return_data(
            {'resource': resource,
             'ids': ids})

    def _field_get_user(self, resource, data):
        """First get the user doing the update."""
        success = partial(self._validate_update,
                          resource=resource,
                          data=data)

        failure = partial(self._validate_update,
                          user={"_id": "unknown",
                                "name": "unknown"},
                          resource=resource,
                          data=data)
        return self.who_am_i(success, failure)

    def _validate_update(self, user, error=None, resource=None, data=None):
        """Update instances by field."""
        # What is going on with the args here? Is error ever given?

        if not resource:
            raise tornado.web.HTTPError(400, "No resource name given.")

        if not data:
            raise tornado.web.HTTPError(400, "Insufficient data in request.")

        if not user:
            user = {'_id': 'unknown', 'name': 'unknown'}

        fields = data['fields']
        versional_comment = data.get('_versional_comment')

        if '$set' in fields:
            modifiers = {'$set': fields['$set']}
            del fields['$set']
        else:
            modifiers = {'$set': {}}

        for field, value in six.iteritems(fields):
            if field.startswith('$'):
                modifiers[field] = value
            else:
                modifiers['$set'][field] = value

        success = partial(
            self._do_field_update,
            modifiers=modifiers,
            user=user,
            resource=resource,
            data=data,
            versional_comment=versional_comment)

        return self.validate_modifier(
            model_name=resource,
            modifier=modifiers,
            success=success)

    def _do_field_update(self,
                         status,
                         modification,
                         versional_comment,
                         modifiers,
                         resource,
                         data,
                         user):
        """Update the instances based on the fields."""
        if status == False:
            raise tornado.web.HTTPError(
                400,
                "Modification fields are invalid.")
        modifiers['$set']['_meta._last_modified_by'] = user['_id']
        modifiers['$set']['_meta._last_modified_time'] = datetime.now()
        modifiers['$set']['_meta._last_modified_by_display'] = user['name']
        if not '$inc' in modifiers:
            modifiers['$inc'] = {}
        modifiers['$inc']['_meta._version'] = 1

        if 'ids' in data:
            spec = {'_id': {'$in': tuple(data['ids'])}}
        elif 'criteria' in data:
            spec = data['criteria']
        else:
            # What shall we do here?
            # It would probably bad to do
            # spec = {}
            # i.e. update all instances
            raise tornado.web.HTTPError(
                400,
                "Need a criteria or ids argument.")

        callback = partial(self._get_changed_instances,
                           resource=resource,
                           spec=spec,
                           versional_comment=versional_comment)
        collection = self.get_collection(resource)
        collection.update(spec=spec,
                          document=modifiers,
                          multi=True,
                          callback=callback)

    def _get_changed_instances(self, response, error,
                               resource, spec, versional_comment):
        """Get the resources that have been updated."""
        collection = self.get_collection(resource)
        callback = partial(self._update_history_for_field,
                           versional_comment=versional_comment)
        collection.find(spec=spec).to_list(callback=callback)

    def _update_history_for_field(self, instances,
                                  error,
                                  versional_comment):
        """Add the updates to the versional history."""

        callback = partial(
            self._return_field_update,
            instances=instances)

        self.update_history(instances,
                            'update',
                            callback,
                            versional_comment)

    def _return_field_update(self, response, error, instances):
        """Return the updated instances."""
        return self._return_data({'instances': instances})

    @tornado.web.asynchronous
    @permission_required('update')
    def put(self, resource):
        """Update multiple instances
        Starting by getting the relevant model."""
        # Send fields a different way altogether

        body = self.request.body
        if six.PY3 and isinstance(body, six.binary_type):
            body = body.decode('utf8')

        data = json.loads(body,
                          object_hook=json_util.object_hook)

        if 'fields' in data:
            return self._field_get_user(resource, data)

        self._output_instances = []
        self._post_history_instances = []
        return self._request_model({'_model': resource},
                                   self._get_batch_update_user,
                                   False)

    def _get_batch_update_user(self, model, error=None):
        """We got the model, now we need the username."""
        success = partial(self._get_previous_instance_ids,
                          model=model)
        failure = partial(self._get_previous_instance_ids,
                          error=None,
                          user={"_id": "unknown",
                                 "name": "unknown"},
                          model=model)
        return self.who_am_i(success, failure)

    def _get_previous_instance_ids(self, user, error, model):
        """Now we have the user and the model,
        we need the previous user ids."""
        if not user:
            user = {"_id": "unknown",
                    "name": "unknown"}
        # 2. Now we get the data from the request.
        data = json.loads(self.request.body,
                          object_hook=json_util.object_hook)
        # 3. Now we get all the ids of the previous instances.
        if 'ids' in data:
            ids = data['ids']
        elif 'instances' in data:
            ids = [instance['_id'] for instance in data['instances']]
        else:
            raise tornado.web.HTTPError(400, "Missing required data.")

        # 3. Now we get the previous instances.
        success = partial(
            self._check_previous_exist,
            ids=ids,
            data=data,
            model=model,
            user=user)

        return self._get_previous_instances(model['_id'], ids, success)

    @tornado.web.asynchronous
    def _get_previous_instances(self, resource, ids, success):
        """Get the old instances first."""
        resources = self.get_collection(resource)
        resources.find(spec={'_id': {'$in': tuple(ids)}}).to_list(
            callback=success)

    def _check_previous_exist(self,
                              previous_instances,
                              error,
                              ids,
                              data,
                              model,
                              user):
        """Check we found all the previous instances"""
        if len(previous_instances) < len(ids):
            raise tornado.web.HTTPError(
                400, 'Asked to update %s instances'
                'but only found %s in the database' % (
                    len(ids),
                    len(previous_instances)))

        if 'instances' in data:
            if isinstance(data['instances'], list):
                # Convert to a dict
                new_instances_as_dict = {}
                for instance in data['instances']:
                    new_instances_as_dict[instance['_id']] = instance
                    data['instances'] = new_instances_as_dict

        elif 'fields' in data:
            # Make the field based approach the same as the explicit instance
            # Make the new instances
            data['instances'] = instance_list_to_dict(
                deepcopy(previous_instances))

            for instance in data['instances']:
                data['instances'][instance].update(data['fields'])
            #Now it ends up like self._update_multiple_resources
            del data['ids']
            del data['fields']

        return self._update_multiple_resources(
            model,
            model['_id'],
            data,
            user,
            ids,
            previous_instances,
            True)

    @staticmethod
    def _create_new_instance_meta(old_instance, new_instance, user,
                                  versional_comment=None):
        """Check the instances are different, and create meta field."""
        old_ins = deepcopy(old_instance)
        new_ins = deepcopy(new_instance)
        try:
            old_meta = old_ins.pop('_meta')
        except KeyError:
            old_meta = {'_version': 1,
                        '_created_time': datetime(1970, 1, 1)}
        new_ins.pop('_meta', None)
        if old_ins == new_ins:
            # The old and new instance are the same. Do nothing
            return None

        new_ins['_meta'] = {
            '_created_time': old_meta['_created_time'],
            '_last_modified_time': datetime.now(),
            '_last_modified_by': user['_id'],
            '_last_modified_by_display': user['name'],
            '_version': old_meta['_version'] + 1,
            }
        if not '_versional_comment' in new_ins:
            if versional_comment:
                new_ins['_versional_comment'] = versional_comment
            else:
                new_ins['_versional_comment'] = 'Instance updated'

        return new_ins

    def _update_multiple_resources(self,
                                   model,
                                   resource,
                                   data,
                                   user,
                                   ids,
                                   previous_instances,
                                   prefetch=False):
        """
        Update several resources:
            * check they are really updated,
            * update _meta field
            * pass on to validation.
        """
        # Check that old instances are different than new
        # and update _meta field in new ones.
        changed = []
        versional_comment = data.get('_versional_comment', None)
        instance_dict = instance_list_to_dict(
            deepcopy(previous_instances))

        for identifier in ids:
            old_instance = instance_dict[identifier]
            new_instance = data['instances'][identifier]
            new_with_meta = self._create_new_instance_meta(
                old_instance,
                new_instance,
                user,
                versional_comment)
            if new_with_meta:
                changed.append(new_with_meta)
            else:
                self._output_instances.append(old_instance)

        # Go through changed and validate it
        return self._validate_sequentially(None, changed)

    def _validate_sequentially(self,
                                         instance,
                                         changed):
        """Validate each instance in turn."""
        # If we have an instance, then it is a valid instance
        if instance:
            self.validated_instances.append(instance)

        # If we have run out of instances, then we are done.
        if not changed:
            return self._sequentially_add_to_history(None, None, None)

        # Get the next instance
        next_instance = changed.pop()

        # On success come back
        success = partial(
            self._validate_sequentially,
            changed=changed)

        self.validate_instance(next_instance, success)

    def _sequentially_add_to_history(self,
                                     version,
                                     error,
                                     instance):
        """Add each instance to history, and then move to the next.
        We can probably refactor out this recursive approach now the
        underlying driver supports lists."""
        if instance:
            self._post_history_instances.append(instance)
        if not self.validated_instances:
            return self._update_instances_sequentially(None)
        new_instance = self.validated_instances.pop()
        if '_versional_comment' in new_instance:
            versional_comment = new_instance['_versional_comment']
            del new_instance['_versional_comment']
        else:
            versional_comment = "Instance created"

        self.add_version_to_history(
            response=None, instance=new_instance,
            callback=self._sequentially_add_to_history,
            versional_comment=versional_comment)

    def _update_instances_sequentially(self, instance, error=None):
        """Go through each of the instances and update the database."""
        # If we have an instance, then it is a valid instance
        if instance:
            self._output_instances.append(instance)
        if not self._post_history_instances:
            # We are done finish up.
            return self._return_data({'instances': self._output_instances})
        next_instance = self._post_history_instances.pop()
        coll = self.get_collection(next_instance['_model'])
        coll.update({'_id': next_instance['_id']},
                    next_instance,
                    callback=self._update_instances_sequentially)

    #for files we may need to remove permission required setting not sure when that kicks in
    @tornado.web.asynchronous
    @permission_required('create')
    def post(self, resource):
        """Create a new instance.
        Start by looking if it already exists!"""
        body = self.request.body
        if six.PY3 and isinstance(body, six.binary_type):
            body = body.decode('utf8')
        
        data = json.loads(body,
                          object_hook=json_util.object_hook)


        if isinstance(data, dict):
            
            if not '_id' in data:
                # Skip straight on
                self.validate_instance(data, self._create_instance)
            else:
                callback = partial(self._process_post, data=data)
                coll = self.get_collection(resource)
                coll.find_one({'_id': data['_id']},
                              callback=callback)
        else :
            for object in data:
                if not '_id' in object:
                    # Skip straight on
                    self.validate_instance(object, self._create_instance)
                else:
                    callback = partial(self._process_post, data=object)
                    coll = self.get_collection(resource)
                    coll.find_one({'_id': object['_id']},
                                  callback=callback)
    @tornado.web.asynchronous
    @permission_required('create')              
    def _post_JSON(self, resource):
        """Create a new instance.
        Start by looking if it already exists!"""
        data = json.loads(self.request.body,
                          object_hook=json_util.object_hook)
        if isinstance(data, dict):
            if not '_id' in data:
                # Skip straight on
                self.validate_instance(data, self._create_instance)
            else:
                callback = partial(self._process_post, data=data)
                coll = self.get_collection(resource)
                coll.find_one({'_id': data['_id']},
                              callback=callback)
        else :
            for object in data:
                if not '_id' in object:
                    # Skip straight on
                    self.validate_instance(object, self._create_instance)
                else:
                    callback = partial(self._process_post, data=object)
                    coll = self.get_collection(resource)
                    coll.find_one({'_id': object['_id']},
                                  callback=callback)
        

    def _process_post(self, result, error, data):
        """Only create a new one if it does not exist."""
        if result is None:
            self.validate_instance(data, self._create_instance)
        else:
            # We have already got one!
            raise tornado.web.HTTPError(409)

    @tornado.web.asynchronous
    @permission_required('read')
    def get(self, resource):
        """Get the collection list."""
        # Count the results first
        return self._parse_arguments(resource)

    @tornado.web.asynchronous
    def _parse_arguments(self, resource):
        """Parse the critera to make friendly searches."""
        kwargs = {}
        count = None
        arguments = self.request.arguments
        if arguments:
            query = dict((key, value[0]) for \
                             key, value in six.iteritems(arguments))
            if '_limit' in query:
                try:
                    kwargs['limit'] = int(dejsonify(query['_limit']))
                except ValueError:
                    print("Warning: Invalid _limit parameter.")
                del query['_limit']

            if '_sort' in query:
                kwargs['sort'] = dejsonify(query['_sort'])
                del query['_sort']

            if '_skip' in query:
                try:
                    kwargs['skip'] = int(dejsonify(query['_skip']))
                except ValueError:
                    print("Warning: Invalid _skip parameter.")
                del query['_skip']

            if '_count' in query:
                count = dejsonify(query['_count'])
                del query['_count']

            if '_fields' in query:
                kwargs['fields'] = dejsonify(query['_fields'])
                del query['_fields']

            if query:
                # Decode any decoded values
                kwargs['spec'] = {}

                for key, value in six.iteritems(query):
                    kwargs['spec'][key] = dejsonify(value)

        if count == "true":
            return self._count_results(resource, kwargs)

        return self._get_results(count=None, error=None,
                                 resource=resource, kwargs=kwargs)

    @tornado.web.asynchronous
    def _count_results(self, resource, kwargs):
        """Count the results."""
        coll = self.get_collection(resource)
        cursor = coll.find(**kwargs)  # pylint: disable-msg=W0142
        callback = partial(self._get_results,
                           resource=resource,
                           kwargs=kwargs)
        cursor.count(callback=callback)

    @tornado.web.asynchronous
    def _get_results(self, count, error, resource, kwargs):
        """Get the collection list."""
        self.writing = False
        output_wrapper = '{'
        if count:
            output_wrapper += '"count":%s, ' % count
        output_wrapper += '"results":['
        self.write(output_wrapper)
        coll = self.get_collection(resource)
        # pylint: disable-msg=W0142
        coll.find(**kwargs).each(self._stream_processor)

    # pylint: disable-msg=W0613
    def _stream_processor(self, result, error):
        """Write the result out.
        We are fed the collection argument,
        (whether we want it or not), but currently do not use it."""
        if not result:
            self.write(']}')
            self.finish()
            return

        self.write((',' if self.writing else '') + \
                       json.dumps(result,
                                  default=json_util.default))
        self.flush()
        if not self.writing:
            self.writing = True

    def _return_data(self, data):
        """Return a single instance or anything else that can become JSON."""
        if not data:
            raise tornado.web.HTTPError(404)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(data, default=json_util.default))
        self.finish()

    def _validate_instance(self, model, instance):
        """Validate an instance against a model."""
        try:
            validate_model_instance(model, instance)
        except MissingFields as fields:
            raise tornado.web.HTTPError(400, "Missing Fields %s" % fields)
        except ValidationError:
            raise tornado.web.HTTPError(400, "Validation Error")
        self._create_instance(instance)

    def _create_instance(self, instance):
        """Create an instance."""
        

        success = partial(self._do_create_instance,
                          instance=instance)
        failure = partial(self._do_create_instance,
                          error=None,
                          user={"_id": "unknown",
                                "name": "unknown"},
                          instance=instance)
        return self.who_am_i(success, failure)

    def _do_create_instance(self, user, error, instance):
        """Create an instance."""
        instance_collection = self.get_collection(instance['_model'])
        if not user:
            user = {"_id": "unknown",
                    "name": "unknown"}
            
        if '_id' not in instance:
            instance['_id'] = str(ObjectId())
        instance['_meta'] = {'_created_time': datetime.now(),
                             '_last_modified_time': datetime.now(),
                             '_last_modified_by': user['_id'],
                             '_last_modified_by_display': user['name'],
                             '_version': 1}
        files = None
        if '_file_data' in instance:
            files = instance['_file_data']
            for label in files:
                meta, content = files[label].split(',', 1)
                ext_m = re.match("data:.*?/(.*?);base64", meta)
                if not ext_m:
                    raise ValueError("Can't parse base64 file data ({})".format(meta))
                filename = '/media/%s/%s_%s.%s' % (instance['_model'], instance['_id'], label, ext_m.group(1))
                if label in instance:
                    instance[label] = filename
            del instance['_file_data']
            
        if '_versional_comment' in instance:
            versional_comment = instance['_versional_comment']
            del instance['_versional_comment']
        else:
            versional_comment = "Instance created"

        if files is None:
            save_cb = None
        else:
            save_cb = partial(self._save_files,
                              instance=instance,
                              files=files)
        callback = partial(self.add_version_to_history,
                       instance=instance,
                       versional_comment=versional_comment,
                       callback=save_cb)

        instance_collection.insert(instance,
                                   callback=callback)
        
    def _save_files(self, response,  # pylint: disable-msg=W0613
                               error=None,
                               instance=None,
                               files=None):
        for file in files:
            meta, content = files[file].split(',', 1)
            ext_m = re.match("data:.*?/(.*?);base64", meta)
            if not ext_m:
                raise ValueError("Can't parse base64 file data ({})".format(meta))
            assert instance[file].startswith('/media/')
            filename = instance[file][7:]
            real_content = base64.b64decode(content)
            with open('/srv/vmr/workspace/mediamanager/restricted/' + filename,  'w') as f:
                f.write(real_content)
            
        return self._return_data(instance)
        

    def _return_main_data(self, response, error, data):
        """Return the data without the response."""
        # pylint: disable-msg=W0613
        return self._return_data(data)

    def add_version_to_history(self,
                               response,  # pylint: disable-msg=W0613
                               error=None,
                               instance=None,
                               callback=None,
                               versional_comment=None):
        """Add a version to the history."""

        if not callback:
            insert_callback = partial(self._return_main_data,
                                      data=instance)
        else:
            insert_callback = partial(callback,
                                      instance=instance)

        self.update_history(instance,
                            'create',
                            insert_callback,
                            versional_comment)


class CommandHandler(tornado.web.RequestHandler,
                     DatabaseMixin,
                     AuthenticationMixin,
                     ValidationMixin,
                     WhoAmIMixin):

    """Handler for advanced commands that go beyond simple REST."""

    @tornado.web.asynchronous
    def get(self, resource, objectid, command):
        """Handle commands, only one handled so far."""
        if command == "uniquify":
            return self._uniquify(resource, objectid)
        else:
            raise tornado.web.HTTPError(404)

    def _uniquify(self, resource, objectid):
        """Return a unique ID based on a string."""
        coll = self.get_collection(resource)
        callback = partial(self._handle_uniquify,
                           objectid=objectid)
        coll.find(
            spec={'_id': {'$regex': '^%s' % objectid}},
            fields=['_id']).to_list(callback=callback)

    def _handle_uniquify(self, response, error, objectid):
        """Handle the unique."""
        ids = [item['_id'] for item in response]
        new_id = self._create_unique_id(ids, objectid)
        return self.return_data(new_id)

    @staticmethod
    def _create_unique_id(list_of_ids, objectid):
        """Create a unique id."""
        relevant_suffixes = []
        for target_id in list_of_ids:
            try:
                suffix = target_id.split(objectid)[1]
            except IndexError:
                raise ValueError("Invalid %s is not a substring of %s" % (
                    target_id,
                    objectid))
            if suffix:
                if suffix[0] == '_' and suffix.count('_') == 1:
                    try:
                        suffix_int = int(suffix[1:])
                    except ValueError:
                        continue
                    else:
                        relevant_suffixes.append(suffix_int)

        relevant_suffixes.sort()
        if not relevant_suffixes:
            new_suffix = 1
        else:
            new_suffix = relevant_suffixes[-1] + 1
        return '%s_%s' % (objectid, new_suffix)

    def return_data(self, data):
        """Return the data to the browser."""
        self.write(json.dumps(data, default=json_util.default))
        self.finish()


class ResourceHandler(tornado.web.RequestHandler,
                      DatabaseMixin,
                      AuthenticationMixin,
                      ValidationMixin,
                      WhoAmIMixin):
    """
       finds a single instance and performs the relevant method upon it.
    """
    # pylint: disable=W0221,R0904

    @tornado.web.asynchronous
    @permission_required('read')
    def head(self, resource, objectid):
        """See if an instance exists."""
        coll = self.get_collection(resource)
        coll.find_one({'_id': objectid},
                      callback=self._return_status)

    def _return_status(self, resource, error=None):
        """Return if it exists or not."""
        if resource is None:
            raise tornado.web.HTTPError(404)
        else:
            self.return_instance(True)

    @tornado.web.asynchronous
    def old_get(self, resource, objectid):
        """Get a single instance."""
        print("User is", self.get_secure_cookie("user"))
        coll = self.get_collection(resource)
        coll.find_one({'_id': objectid},
                      callback=self.return_instance)

    @tornado.web.asynchronous
    @permission_required('read')
    def get(self, resource, objectid):
        """Get a single instance."""
        self._do_get(resource=resource,
                     objectid=objectid)

    def _do_get(self, resource, objectid):
        """Get a single instance."""
        #print "100", dir(self.application)
        coll = self.get_collection(resource)
        coll.find_one({'_id': objectid},
                      callback=self.return_instance)

    @tornado.web.asynchronous
    @permission_required('delete')
    def delete(self, resource, objectid):
        """Delete an instance."""
        self._record_delete(resource, objectid)

    @tornado.web.asynchronous
    def _record_delete(self, resource, objectid):
        """Record the deletion of an instance."""
        versional_comment = "Instance deleted"
        version = {
            '_id': objectid,
            '_model': resource,
            '_versional_comment': versional_comment,
            '_operation': 'delete'
            }
        
        callback = partial(self._get_model,
                           resource=resource,
                           objectid=objectid)

        self.add_version_to_history(version, callback)
        
    @tornado.web.asynchronous
    def _get_model(self, response, error, instance, resource, objectid):
        coll = self.get_collection('_model')
        success = partial(self._check_files_in_model,
                          resource=resource,
                          objectid=objectid)
        coll.find({'_id': resource}).to_list(callback=success)
        
    def _check_files_in_model(self, response, error, resource, objectid):
        if '_file_fields' in response[0]:
            self._get_instance(response[0]['_file_fields']['fields'], resource, objectid)
        else:
            self._do_delete({'_model': resource, '_id': objectid})
            
    
    def _get_instance(self, file_fields, resource, objectid):
        success = partial(self._delete_files,
                           file_fields=file_fields,
                           resource=resource,
                           objectid=objectid)
        coll = self.get_collection(resource)
        coll.find({'_id': objectid}).to_list(callback=success)

        
    def _delete_files(self, response, error, file_fields, resource, objectid):
        for json in response:
            for field in file_fields:
                file = json[field].replace('/media/', '/srv/vmr/workspace/mediamanager/restricted/')
                if os.path.isfile(file):
                    os.unlink(file)
        self._do_delete({'_model': resource, '_id': objectid})

    @tornado.web.asynchronous
    def _do_delete(self,
                   instance=None):  # pylint: disable-msg=W0613
        """Do the deletion."""
        coll = self.get_collection(instance['_model'])
        callback = self._deleted(instance=instance)
        coll.remove(instance['_id'],
                    callback=callback)

    def _deleted(self, instance, error = None):
        """Item is successfully deleted."""
        self.return_instance({'success': True,
                              '_id': instance['_id'],
                              '_model': instance['_model']})

    @tornado.web.asynchronous
    @permission_required('update')
    def put(self, resource, objectid):
        """Update a single instance."""
        new_instance = json.loads(self.request.body,
                                  object_hook=json_util.object_hook)
        if '_id' not in new_instance:
            raise tornado.web.HTTPError(400, "Missing _id key")
        if new_instance['_id'] != objectid:
            raise tornado.web.HTTPError(
                400,
                "_id in instance (%s) and URL (%s) do not match" % (
                    new_instance['_id'],
                    objectid
                    )
                )
        if new_instance['_model'] != resource:
            raise tornado.web.HTTPError(
                400,
                "model in instance (%s) and resource "
                "name (%s) do not match" % (
                    new_instance['_model'],
                    resource
                    )
                )

        self._get_previous(new_instance)

    @tornado.web.asynchronous
    def _get_previous(self, new_instance):
        """Get the old instance first."""
        coll = self.get_collection(new_instance['_model'])
        callback = partial(self._check_update,
                           new_instance=new_instance)
        coll.find_one({'_id': new_instance['_id']},
                      callback=callback)
        
    @tornado.web.asynchronous
    def _check_update(self, old_instance, error, new_instance):
        """Check who are we then check update."""
        success = partial(self._do_check_update,
                          old_instance=old_instance,
                          new_instance=new_instance)
        failure = partial(self._do_check_update,
                          user={"_id": "unknown",
                                "name": "unknown"},
                          error = None,
                          old_instance=old_instance,
                          new_instance=new_instance)

        return self.who_am_i(success, failure)

    @tornado.web.asynchronous
    def _do_check_update(self, user, error, old_instance, new_instance):
        """Check that the old instance is different than the new."""

        if not old_instance:
            raise tornado.web.HTTPError(
                400,
                "Cannot update resource because it does not exist.")
        try:
            old_meta = old_instance.pop('_meta')
        except KeyError:
            old_meta = {'_version': 1,
                        '_created_time': datetime(1970, 1, 1)}
        new_instance.pop('_meta', None)
        if old_instance == new_instance:
            # Nothing new here
            # Put your shoes back on and move along
            old_instance['_meta'] = old_meta
            return self.return_instance(old_instance)

        new_instance['_meta'] = {
            '_created_time': old_meta['_created_time'],
            '_last_modified_time': datetime.now(),
            '_last_modified_by': user['_id'],
            '_last_modified_by_display': user['name'],
            '_version': old_meta['_version'] + 1,
            }
        
        files = None
        if '_file_data' in new_instance:
            files = new_instance['_file_data']
            for_delete = []
            for label in files:
                meta, content = files[label].split(',', 1)
                ext_m = re.match("data:.*?/(.*?);base64", meta)
                if not ext_m:
                    raise ValueError("Can't parse base64 file data ({})".format(meta))
                filename = '/media/%s/%s_%s.%s' % (new_instance['_model'], new_instance['_id'], label, ext_m.group(1))
                if label in new_instance:
                    for_delete.append(old_instance[label])
                    new_instance[label] = filename
            files['_delete'] = for_delete
            del new_instance['_file_data']
        
        if not '_versional_comment' in new_instance:
            new_instance['_versional_comment'] = 'Instance updated'
        new_instance['_operation'] = 'update'
        # The update is new, so lets validate it
        success = partial(self.update_instance,
                          files=files,                        
                          )

        self.validate_instance(new_instance, success)

    @tornado.web.asynchronous
    def update_instance(self, instance, files):
        """Update an instance."""
        # pylint: disable-msg=W0613
        instance_collection = self.get_collection(instance['_model'])
        if not files:
            save_cb = None
        else:
            save_cb = partial(self._save_files,
                              instance=instance,
                              files=files)
        callback = self.add_version_to_history(instance, save_cb)
        instance_collection.update({'_id': instance['_id']},
                                   instance,
                                   callback=callback)

    def _save_files(self, response,  # pylint: disable-msg=W0613
                               error=None,
                               instance=None,
                               files=None):
        if '_delete' in files:
            for file in files['_delete']:
                filepath = file.replace('/media/', '/srv/vmr/workspace/mediamanager/restricted/')
                if os.path.isfile(filepath):
                    os.unlink(filepath)
        del files['_delete']
        for file in files:
            meta, content = files[file].split(',', 1)
            ext_m = re.match("data:.*?/(.*?);base64", meta)
            if not ext_m:
                raise ValueError("Can't parse base64 file data ({})".format(meta))
            assert instance[file].startswith('/media/')
            filename = instance[file][7:]
            real_content = base64.b64decode(content)
            with open('/srv/vmr/workspace/mediamanager/restricted/' + filename,  'w') as f:
                f.write(real_content)
            
        return self.return_instance(instance)


    @tornado.web.asynchronous
    def add_version_to_history(self, instance, callback=None):
        """Add a version to the history."""
        operation = instance['_operation']
        del instance['_operation']
        versional_comment = instance['_versional_comment']
        del instance['_versional_comment']

        if not callback:
            insert_callback = partial(self._return_main_instance,
                                      instance=instance)
        else:
            insert_callback = partial(callback,
                                      instance=instance)

        self.update_history(instance,
                            operation,
                            insert_callback,
                            versional_comment)
        
    def return_instance(self, result, error=None):
        """Return a single instance or anything else that can become JSON."""
        if not result:
            raise tornado.web.HTTPError(404)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(result, default=json_util.default))
        self.finish()
        
    def _return_main_instance(self, response, error, instance):
        """Return the data without the response."""
        # pylint: disable-msg=W0613
        return self.return_instance(instance)
