"""URL handlers for the core server
Other URL handler files can be added by the applications."""

from magpy.server.api import ResourceHandler, ResourceTypeHandler, \
    CommandHandler
from magpy.server.auth import AuthLoginHandler, AuthLogoutHandler, \
    AuthWhoAmIHandler, AuthPermissionHandler, AuthPermissionsHandler,\
    AuthWhoAreTheyHandler

from magpy.server.transactions import TransactionSyncHandler, \
    TransactionUpdateHandler

URLS = [
    (r"/api/_sync/state/(\w+)/?", TransactionSyncHandler),
    (r"/api/_sync/update/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)/?", TransactionUpdateHandler),
    (r"/api/(\w+)/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)/?", CommandHandler),
    (r"/api/(\w+)/([a-zA-Z0-9_-]+)/?", ResourceHandler),
    (r"/api/(\w+)/?", ResourceTypeHandler),
    (r"/auth/login/", AuthLoginHandler),
    (r"/auth/logout/", AuthLogoutHandler),
    (r"/auth/whoami/", AuthWhoAmIHandler),
    (r"/auth/whoarethey/", AuthWhoAreTheyHandler),
    (r"/auth/checkpermission/(\w+)/([a-zA-Z0-9_-]+)/?", AuthPermissionHandler),
    (r"/auth/checkpermission/?", AuthPermissionsHandler),
    ]
