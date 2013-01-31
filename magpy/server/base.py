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
import motor


class App(tornado.web.Application):
    """Simple Web Application."""
    def __init__(self, ioloop, handlers, cookie_secret):
        settings = dict(
            debug=True,
            io_loop=ioloop,
            cookie_secret=cookie_secret)
        self.connection = motor.MotorClient(tz_aware=True).open_sync()

        # pylint: disable=W0142
        tornado.web.Application.__init__(self, handlers, **settings)


def main(handlers, cookie_secret=None, port=8000):
    """Site startup boilerplate."""
    if not cookie_secret:
        cookie_secret = open('cookie.txt').read()
    tornado.options.parse_command_line()
    ioloop = tornado.ioloop.IOLoop.instance()
    http_server = tornado.httpserver.HTTPServer(App(ioloop,
                                                    handlers,
                                                    cookie_secret))
    http_server.listen(port)
    tornado.autoreload.start()
    ioloop.start()

if __name__ == '__main__':
    print "To run the server type:\n" \
        "mag.py run"
