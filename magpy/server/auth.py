"""Authentication for Magpy backend."""

import tornado.auth
import tornado.web  # pylint: disable=W0404
import tornado.gen
import json
from bson import json_util
from bson.objectid import ObjectId
from functools import partial
from magpy.server.database import DatabaseMixin
from magpy.server.utils import dejsonify
import six
import base64

# pylint: disable=R0904,W0613,R0913


def permission_required(operation):
    """Decorator that makes the decorated function
    require permission to do the operation.
    operation - create, read, update or delete.
    """

    def decorator(func):
        """Wraps the method with autentication."""
        def wrapper(self, resource, *args, **kwargs):
            """If successful, apply the arguments and use it."""
            success = partial(func,
                              self,
                              resource,
                              *args,
                              **kwargs)
            presource = resource
            poperation = operation
            if resource == '_model' and operation == 'read':
                if args:
                    model = args[0]
                    if model:
                        presource = model

            if resource == "_history":
                arguments = self.request.arguments
                if 'document_model' in arguments:
                    presource = arguments['document_model'][0]
                    poperation = "delete"
                else:
                    # We got _history but without 'document_model'
                    raise tornado.web.HTTPError(
                        400,
                        "Missing argument - "
                        "history requires 'document_model'.")

            return self.check_permission(success=success,
                                         resource=presource,
                                         permission=poperation)
        return wrapper
    return decorator


class AuthenticationMixin(object):
    """
    Provides authentication checks for the api.
    """

    def check_permissions(self,
                          success,
                          failure=None,
                          permissions=None):  # pylint: disable=W0221
        """Check that the user is allowed to use the resources
        defined in permissions.
        permissions - a dictionary with each entry having a
                        resource type as the key, and a list of permissions
                        as the values, e.g.
                        {'author': ['read', 'create', 'update', 'delete']}
        success - the callback to run on success.
        failure - the callback to run on failure.
        """
        if not permissions:
            permissions = {arg: dejsonify(self.request.arguments[arg][0])
                           for arg in self.request.arguments}
        if not failure:
            failure = self.permission_denied

        # 1. get user
        # 2. get relevant groups
        # 2. get models
        # 3. combine them together
        # 4. Test it against the input

        if not self.get_secure_cookie("user"):
            # We are not logged in, go to the next stage
            return self._get_models_for_check_perms(
                groups=None,
                error=None,
                user=None,
                permissions=permissions,
                success=success,
                failure=failure)

        callback = partial(self._get_relevant_groups,
                           permissions=permissions,
                           success=success,
                           failure=failure)
        coll = self.get_collection('_user')
        coll.find_one({'_id': self.get_secure_cookie("user")},
                      callback=callback,
                      fields=['_permissions'])

    def _get_relevant_groups(self,
                             user,
                             error,
                             permissions,
                             success,
                             failure):
        """Get relevant groups.
        Result is a list of results, e.g.:
        [{u'_id': u'citations_editors',
        u'_permissions': {u'author':
        {u'update': {u'author': True}}}}]
        """
        callback = partial(self._get_models_for_check_perms,
                           user=user,
                           permissions=permissions,
                           success=success,
                           failure=failure)

        groups = self.get_collection('_group')

        model_names = permissions.keys()
        or_query = [
            {
                '_permissions.%s' % model_name: {
                    "$exists": True}} for model_name in model_names]

        groups.find(
            {'members': user['_id'],
             '$or': or_query},
            ['_permissions']).to_list(callback=callback)

    def _get_models_for_check_perms(self,
                                    groups,
                                    error,
                                    user,
                                    permissions,
                                    success,
                                    failure):
        """Get the required models to satisfy permissions."""
        callback = partial(self._do_check_permissions,
                           permissions=permissions,
                           user=user,
                           groups=groups,
                           success=success,
                           failure=failure)

        models = self.get_collection('_model')
        models.find(
            spec={
                '_id': {
                    '$in': tuple(permissions.keys())}},
            fields=['_permissions']).to_list(callback=callback)

    @staticmethod
    def _overlay_permissions(models,
                             user,
                             groups):
        """Combine the user, group and model permissions.
        1. We start with default permissions of read-only,
        2. We overlay any permissions set in the model,
        3. We overlay any permissions in a group,
        4. We overlay any permissions in the user.
        """
        permissions = {}

        for model in models:
            model_permissions = {
                'read': True,
                'create': False,
                'update': False,
                'delete': False}

            if '_permissions' in model:
                model_permissions.update(model['_permissions'])

            if groups:
                for group in groups:
                    if model['_id'] in group['_permissions']:
                        model_permissions.update(
                            group['_permissions'][model['_id']])

            if user:
                if '_permissions' in user:
                    if model['_id'] in user['_permissions']:
                        model_permissions.update(
                            user['_permissions'][model['_id']])

            permissions[model['_id']] = model_permissions

        return permissions

    def _do_check_permissions(self,
                              models,
                              error,
                              user,
                              groups,
                              permissions,
                              success,
                              failure):
        """Process the stored permissions."""
        stored_permissions = self._overlay_permissions(models, user, groups)
        missing_permissions = {}

        for resource, perm_list in six.iteritems(permissions):
            for perm in perm_list:
                if not stored_permissions[resource][perm]:
                    if resource in missing_permissions:
                        missing_permissions[resource].append(perm)
                    else:
                        missing_permissions[resource] = [perm]
        if missing_permissions:
            return failure([False, missing_permissions])
        return success([True, missing_permissions])

    def check_permission(self,
                         resource,
                         permission,
                         success,
                         failure=None):  # pylint: disable=W0221
        """Check that the user is allowed to use the resource.
        resource - the model name of the resource.
        permission - create, read, update or delete.
        success - the callback to run on success.
        failure - the callback to run on failure.
        """
        if not failure:
            failure = self.permission_denied

        if not self.get_secure_cookie("user"):
            # We are not logged in, go to the next stage
            return self._request_modelp(resource, permission, success, failure)

        callback = partial(self._check_user,
                           resource=resource,
                           permission=permission,
                           success=success,
                           failure=failure)
        coll = self.get_collection('_user')
        coll.find_one({'_id': self.get_secure_cookie("user")},
                      callback=callback)

    def _check_user(self, user, error, resource, permission, success, failure):
        """Check if the user has the required permission."""
        if not user:
            return self._request_modelp(resource, permission, success, failure)
        if '_permissions' not in user:
            return self._request_modelp(resource, permission, success, failure)
        if resource not in user['_permissions']:
            return self._request_modelp(resource, permission, success, failure)
        if permission in user['_permissions'][resource]:
            permission_value = \
                user['_permissions'][resource].get(permission)
            if permission_value:
                return success()
            else:
                return failure()
        return self._request_modelp(resource, permission, success, failure)

    def _request_modelp(self, resource, permission, success, failure):
        """Get the model from the database."""

        coll = self.get_collection('_model')

        callback = partial(self._check_model,
                           permission=permission,
                           on_success=success,
                           on_failure=failure)
        coll.find_one({'_id': resource},
                      callback=callback)

    #def _check_model(self, model, permission, success, failure):
    def _check_model(self, model, error, permission,
                     on_success, on_failure, *args, **kwargs):
        """See that permissions there are in the model."""
        if not model:
            return on_failure()
        if '_permissions' not in model:
            return self._standard(permission, on_success, on_failure)
        if permission in model['_permissions']:
            if model['_permissions'][permission]:
                return on_success()
            else:
                return on_failure()

        return self._standard(permission, on_success, on_failure)

    @staticmethod
    def _standard(permission, success, failure):
        """Give the standard answer."""
        if permission == 'read':
            return success()
        else:
            return failure()

    @staticmethod
    def permission_denied(details=None):
        """The user should not access this resource.
        A useful default failure callback."""
        # TODO: do something with details
        raise tornado.web.HTTPError(401)



class AuthPermissionsHandler(tornado.web.RequestHandler,
                             DatabaseMixin,
                             AuthenticationMixin):
    """Check permissions.
    """
    @tornado.web.asynchronous
    def get(self):  # pylint: disable=W0221
        success = self._return_instance
        failure = self._return_instance
        self.check_permissions(success,
                               failure)

    def _return_instance(self, instance, error=None):
        """Return a single instance or anything else that can become JSON."""
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        json_response = json.dumps(instance, default=json_util.default)
        if six.PY3:
            json_response = bytes(json_response, 'utf8')
        
        self.write(json_response)
        self.finish()


class AuthPermissionHandler(tornado.web.RequestHandler,
                            DatabaseMixin,
                            AuthenticationMixin):
    """Check permissions.
    """
    @tornado.web.asynchronous
    def get(self, resource, permission):  # pylint: disable=W0221
        success = partial(self._return_instance,
                          instance=True)
        failure = partial(self._return_instance,
                          instance=False)
        self.check_permission(resource,
                              permission,
                              success,
                              failure)

    def _return_instance(self, instance, error=None):
        """Return a single instance or anything else that can become JSON."""
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(instance, default=json_util.default))
        self.finish()


class WhoAmIMixin(object):
    """Answer who am I queries - get user information."""
    # pylint: disable=R0903
    @tornado.web.asynchronous
    def who_am_i(self, success, failure=None):
        """If logged in, find user from cookie."""
        if not self.get_secure_cookie("user"):
            if failure:
                return failure()
            else:
                raise tornado.web.HTTPError(404)
        coll = self.get_collection('_user')
        coll.find_one({'_id': self.get_secure_cookie("user")},
                      callback=success)


class AuthWhoAmIHandler(tornado.web.RequestHandler,
                        DatabaseMixin,
                        WhoAmIMixin):
    """Answer who am I queries - get user information."""
    @tornado.web.asynchronous
    def get(self):
        return self.who_am_i(self._return_user)

    def _return_user(self, instance, error):
        """Return a single instance or anything else that can become JSON."""
        if not instance:
            raise tornado.web.HTTPError(404)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(instance, default=json_util.default))
        self.finish()

class AuthWhoAreTheyHandler(tornado.web.RequestHandler,
                        DatabaseMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument('ids', None):
            ids = json.loads(self.get_argument('ids')[5:])
            #self.resolve_ids_to_names(ids)
            coll = self.get_collection('_user')
            callback = partial(self._build_dictionary)
            coll.find(spec={'_id': {'$in': ids}}).to_list(callback=callback)
        else:
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            empty_response = json.dumps({}, default=json_util.default)
            if six.PY3:
                empty_response = bytes(json_response, 'utf8')
            self.write(empty_response)
            self.finish()
            return
        
    def resolve_ids_to_names(self, ids):
        coll = self.get_collection('_user')
        callback = partial(self._build_dictionary)
        coll.find(spec={'_id': {'$in': ids}}).to_list(callback=callback)
        
        
    def _build_dictionary(self, result, error):
        resolved = {}
        for entry in result:
            if 'name' in entry.keys():
                resolved[entry['_id']] = entry['name']
            elif 'last_name' in entry.keys():
                resolved[entry['_id']] = entry['last_name']
            elif 'first_name' in entry.keys():
                resolved[entry['_id']] = entry['first_name']
            else:
                resolved[entry['_id']] = entry['_id']
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(resolved, default=json_util.default))
        self.finish()
        return

class AuthLogoutHandler(tornado.web.RequestHandler):
    """Handle logouts."""
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.get_argument("next", "/"))


class AuthLoginHandler(tornado.web.RequestHandler,
                       tornado.auth.GoogleOAuth2Mixin,
                       DatabaseMixin):
    """Handle logins."""
    # pylint: disable=E1101
#    @tornado.web.asynchronous
#     def get(self):
#         if self.get_argument("openid.mode", None):
#             self.get_authenticated_user(self.async_callback(self._on_auth))
#             return
#         self.authenticate_redirect()

    @tornado.gen.coroutine
    @tornado.web.asynchronous
    def get(self):
        
        if self.get_argument('code', False):
            next_page = self.get_argument('state', '/')
            access_token = yield self.get_authenticated_user(
                redirect_uri = base64.b64decode(self.settings['login_redirect']),
                code = self.get_argument('code'))
            http = self.get_auth_http_client()
            callback = partial(self._on_auth, next_page=next_page)
            http.fetch("https://www.googleapis.com/oauth2/v2/userinfo", 
                       callback,
                       headers = {'Authorization': 'Bearer %s' % access_token['access_token']})        
        else:
            #in tornado 3.2 this does not return a Future so we can't use yield 
            #docs say it should do so if we can get up to a later version of tornado it might be better
            next_page = base64.b64encode(self.get_argument("next", "/"))
            self.authorize_redirect(
                redirect_uri = base64.b64decode(self.settings['login_redirect']),
                client_id = self.settings['google_oauth']['key'],
                scope = ['email', 'profile'],
                response_type = 'code',
                extra_params = {'approval_prompt': 'auto', 'state': next_page})

    def _on_auth(self, resp, next_page):
        """Find the relevant user."""
        user = json.loads(resp.body)
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")
        coll = self.get_collection('_user')
        callback = partial(self._process_user, user=user, next_page=next_page)
        coll.find_one({'email': user["email"]},
                      callback=callback)

    def _process_user(self, result, error, user, next_page):
        print(user)
        """Process the mongo user and the request user"""
        if result is None:
            # User does not exist yet, create account.
            coll = self.get_collection('_user')
            callback = partial(self._set_cookie, next_page=next_page)
            coll.insert({'email': user["email"],
                         'name': user["name"],
                         'locale': user['locale'],
                         'first_name': user['given_name'],
                         'last_name': user['family_name'],
                         '_id': str(ObjectId())
                         },
                        callback=callback)
        else:
            # User exists
            self._set_cookie(result["_id"], None, next_page)

    def _set_cookie(self, user_id, error, next_page):
        """Set the cookie to the user_id."""
        self.set_secure_cookie("user", str(user_id))
        self.redirect(base64.b64decode(next_page))
