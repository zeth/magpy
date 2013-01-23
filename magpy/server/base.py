"""Base Tornado server startup.
All the boilerplate we don't care so much about.
"""

# pylint: disable=W0404

import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.autoreload
from tornado.options import define, options
import motor

define("port", default=8000, help="run on the given port", type=int)


# TODO: Move cookie secret out of here to userspace.

COOKIE = open('cookie.txt').read()

class App(tornado.web.Application):
    """Simple Web Application."""
    def __init__(self, ioloop, handlers):
        settings = dict(
            debug=True,
            io_loop=ioloop,
            cookie_secret=COOKIE)
        self.connection = motor.MotorClient().open_sync()

        # pylint: disable=W0142
        tornado.web.Application.__init__(self, handlers, **settings)


def main(handlers):
    """Site startup boilerplate."""
    tornado.options.parse_command_line()
    ioloop = tornado.ioloop.IOLoop.instance()
    http_server = tornado.httpserver.HTTPServer(App(ioloop,
                                                    handlers))
    http_server.listen(options.port)
    tornado.autoreload.start()
    ioloop.start()
