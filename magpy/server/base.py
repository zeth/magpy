"""Base Tornado server startup.
All the boilerplate we don't care so much about.
"""

# pylint: disable=W0404

from __future__ import print_function

import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.autoreload
import motor

from magpy.server.config import MagpyConfigParser

class App(tornado.web.Application):
    """Simple Web Application."""
    def __init__(self, ioloop, handlers, cookie_secret, databases, google_secrets, login_redirect):
        settings = dict(
            debug=True,
            io_loop=ioloop,
            cookie_secret=cookie_secret,
            google_oauth=google_secrets,
            login_redirect=login_redirect)
        print(settings)
        self.connection = motor.MotorClient(tz_aware=True).open_sync()
        self.databases = databases
        # pylint: disable=W0142
        tornado.web.Application.__init__(self, handlers, **settings)


def main(handlers, port=None, config=None):
    """Site startup boilerplate."""
    magpyconf = MagpyConfigParser(config)
    if not port:
        port = getattr(magpyconf, 'port', 8000)

    tornado.options.parse_command_line()
    ioloop = tornado.ioloop.IOLoop.instance()
    http_server = tornado.httpserver.HTTPServer(App(ioloop,
                                                    handlers,
                                                    magpyconf.cookie_secret,
                                                    magpyconf.databases,
                                                    magpyconf.google_oauth,
                                                    magpyconf.login_redirect))
    http_server.listen(port)
    tornado.autoreload.start()
    ioloop.start()

if __name__ == '__main__':
    print ("To run the server type:\n"
           "mag.py run")
