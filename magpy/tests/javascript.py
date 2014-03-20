"""Simple JavaScript testing from Python.
Including friendly console and session classes.
Requires PyV8 to be installed.

The idea is that you can test your Python and JavaScript
code in an integrated way by using the regular Python unittest
module to test your JavaScript code.

You do this by inheriting from JavaScriptTestCase
instead of unittest.TestCase directly.

If you override setUp, and you probably will, you need to make sure
the superclass's setUp is called, as in the following example:

from javascript import JavaScriptTestCase
class ExampleTestCase(JavaScriptTestCase):
    def setUp(self):
        super(ExampleTestCase, self).setUp()
        ...

Like all good software, this library is written like an onion,
keeping peeling off the layers until you find the right level of
abstraction for your need.
"""
from __future__ import print_function

import os
import sys
import traceback
import cmd
import unittest
import six
import PyV8

from magpy.server.utils import get_mag_path




class JavaScriptTestCase(unittest.TestCase):  # pylint: disable=R0904
    """Base Test case for JavaScript Code.
    Subclass this to test your JavaScript."""

    def setUp(self):  # pylint: disable=C0103
        self.session = JavascriptSession()

    def load(self, filename):
        """Load a JavaScript file into the global context."""
        self.session.load_file(filename)

    def eval(self, js_code):
        """Evaluate JavaScript code from a string."""
        return self.session.eval(js_code)


class JavascriptSession(object):
    """Create a Javascript session for running code."""
    def __init__(self, pure=False, context=None):
        """Setup the context"""
        if not pure and not context:
            console = Console()
            context = {
                'XMLHttpRequest': XMLHttpRequest,
                'console': console
                }
        if context:
            self.context = PyV8.JSContext(context)
        else:
            self.context = PyV8.JSContext()
        self.context.enter()

        if not pure:
            self.eval(COMPAT)

    def load_file(self, path):
        """Load a Javascript file into the context."""
        js_code = open(path, 'rb').read()
        try:
            self.context.eval(js_code)
        except UnicodeDecodeError:
            self.context.eval(js_code.decode('utf8'))

    def eval(self, js_code):
        """Evaluate some JavaScript code."""
        try:
            return self.context.eval(js_code)
        except:
            return traceback.format_exc()  # pylint: disable=W0702


class JavascriptShell(cmd.Cmd):  # pylint: disable=R0904
    """Simple shell for entering Javascript"""

    def __init__(self, *args, **kwargs):
        """
        By default, the browser emulation objects (window, localStorage etc)
        are included in JavaScript's global context.
        Set keyword argument `pure` to `True` in order to prevent inclusion.

        Use the use keyword argument `context`, to provide your own
        global context. When using the `context` argument, the browser
        emulation objects need to be explicitly added if you want them.

        Specials are JavaScript files that can be loaded by keyword.
        Use the keyword argument `specials` to override the dict of specials.
        """

        if 'pure' in kwargs:
            pure = kwargs['pure']
            del kwargs['pure']
        else:
            pure = False

        if 'context' in kwargs:
            self.session = JavascriptSession(kwargs['context'], pure)
            del kwargs['context']
        else:
            self.session = JavascriptSession(pure=pure)

        if 'specials' in kwargs:
            self.specials = kwargs['specials']
            del kwargs['specials']
        else:
            magpy_path = get_mag_path()
            self.specials = {
                "mag": os.path.join(magpy_path, 'static/js/mag.js'),
                "domcore": os.path.join(magpy_path, 'tests/js/domcore.js')}

        cmd.Cmd.__init__(self, *args, **kwargs)
        self.count = 1
        self.prompt_template = "In [%s]: "
        self.prompt = self.prompt_template % self.count

    @staticmethod
    def do_EOF(line):  # pylint: disable=C0103,W0613
        """
        Handle the end-of-file marker at the end of the input,
        i.e. exit cleanly by returning True.
        """
        return True

    def do_load(self, line):
        """Load a file from the full path."""
        try:
            self.session.load_file(line)
        except IOError:
            print(sys.exc_info()[1])
        except:
            print(traceback.format_exc())

    def do_special(self, line):
        """Load a file from existing file list."""
        try:
            special = self.specials[line]

        except KeyError:
            print("Does Not Exist")
            print("Today's specials are:")
            print(', '.join(self.specials.keys()))

        else:
            self.do_load(special)

    def postloop(self):
        print()

    def do_prompt(self, line):
        "Change the interactive prompt"
        self.prompt = line + ': '

    def postcmd(self, stop, line):
        self.count += 1
        self.prompt = self.prompt_template % self.count
        return cmd.Cmd.postcmd(self, stop, line)

    def default(self, line):
        try:
            print(self.session.context.eval(line))
        except:
            print(traceback.format_exc())  # pylint: disable=W0702

### Fake web browser objects ###

try:
    # Python 2
    from urllib2 import Request, urlopen
except:
    from urllib.request import Request, urlopen

class RequestWithMethod(Request):
    """Subclass Request to allow PUT, DELETE and HEAD
    as well as POST and GET."""
    def __init__(self, *args, **kwargs):
        self._method = kwargs.pop('method', None)
        Request.__init__(self, *args, **kwargs)

    def get_method(self):
        if self._method:
            return self._method
        return Request.get_method(self)


class XMLHttpRequest(object):
    """Simple XMLHttpRequest implementation.
    Does what I need to make my unit tests work at least.
    See https://developer.mozilla.org/en/DOM/XMLHttpRequest for more info.
    """
    # pylint: disable=C0103,R0902

    def __init__(self):
        # Properties we need to be compliant with the JavaScipt standard
        self.onreadystatechange = lambda: None
        self.readyState = 0
        self.status = 0
        self.responseText = ""  # Should become readonly

        self.withCredentials = False

        self.response = ""
        self.responseType = ""
        self.responseXML = None
        self.statusText = ""  # Should become readonly
        self.timeout = 0
        self.UNSENT = 0
        self.OPENED = 1
        self.HEADERS_RECEIVED = 2
        self.LOADING = 3
        self.DONE = 4
        self.multipart = False

        #self.channel = None
        #self.mozBackgroundRequest = False

        # Properties we need to make the Python implementation work
        self._url = None
        self._method = "GET"
        self._async = True
        self._user = None
        self._password = None
        self._request_headers = {}
        self._response_headers = {}

    # pylint: disable=R0913
    def open(self, method, url,
             async=True, user="", password=""):
        """Initializes a request."""
        self._url = url
        self._method = method
        self._async = async
        self._user = user
        self._password = password
        self.readyState = 1
        if self.onreadystatechange:
            self.onreadystatechange()

    def setRequestHeader(self, header, value):
        """Sets the value of an HTTP request header.
        You must call open() before using this method.
        header - The name of the header whose value is to be set.
        value - The value to set as the body of the header.
        """
        self._request_headers[header] = value

    def send(self, data=None):
        """Sends the request. If the request is asynchronous
        (which is the default), this method returns as soon
        as the request is sent. If the request is synchronous,
        this method doesn't return until the response has arrived.

        Note: Any event listeners you wish to set must be set before
        calling send().
        """
        if data and six.PY3:
            print ("here", type(data))
            data = bytes(data, 'utf8')    
        request = RequestWithMethod(self._url, data,
                                    headers=self._request_headers,
                                    method=self._method)
        response = urlopen(request)
        self.status = response.getcode()
        self.statusText = response.msg
        self.responseText = response.read()
        self.response = response.read()

        if six.PY2:
            self._response_headers = response.headers.dict
        else:
            self._response_headers = response.headers.__dict__
        self.responseXML = None
        self.readyState = 4
        if self.onreadystatechange:
            self.onreadystatechange()

    # Not used directly from here
    def abort(self):
        """Aborts the request if it has already been sent."""
        pass

    def getAllResponseHeaders(self):
        """Returns all the response headers as a string, or null
        if no response has been received. Note: For multipart requests,
        this returns the headers from the current part of the request,
        not from the original channel."""
        pass

    def getResponseHeader(self, header):
        """Returns the string containing the text of the specified header,
        or null if either the response has not yet been received or the
        header doesn't exist in the response."""
        try:
            return self._response_headers[header]
        except KeyError:
            return None

    def overrideMimeType(self, mimetype):
        """Overrides the MIME type returned by the server.
        This may be used, for example, to force a stream to be treated
        and parsed as text/xml, even if the server does not report it
        as such. This method must be called before send()."""
        pass
        #raise NotImplementedError


from PyV8 import JSObject, JSArray


def convert(obj):
    """Convert a JavaScript object into something printable."""
    if isinstance(obj, JSArray):
        return [convert(v) for v in obj]
    if isinstance(obj, JSObject):
        return dict(
            [[str(k),
              convert(obj.__getattr__(str(k)))] for k in obj.__members__])
    return obj


class Console(object):
    """Console commands.
    Ala http://getfirebug.com/wiki/index.php/Console_API
    So far only console.log and console.dir are implemented.
    """
    def __init__(self):
        pass

    @staticmethod
    def log(lobject):
        """Write a message or an object to the console."""
        obj = convert(lobject)
        if lobject != obj:
            print(lobject, obj)
        else:
            print(lobject)

    @staticmethod
    def dir(lobject):
        """List the properties of the object.
        Warning: consulting adults only!
        This includes all the private methods of the
        internal Python class.
        No attempt is made to hide them or make them look
        JavaScriptic, though this might be something worth
        considering later.
        For now, this is mostly useful for helping to understand
        the abstraction, for example, when writing unit tests.
        """
        print(dir(lobject))

COMPAT = """
//** Make the serverside environment suitable for testing client side code. */
var window, location, localStorage;

/** Define global object for serverside use */
if (typeof window === 'undefined') {
    window = this;
}

if (typeof location === 'undefined') {
    location = {
        hash: "",
        host: "localhost",
        hostname: "localhost",
        href: "http://localhost/",
        pathname: "/",
        port: "",
        protocol: "http:",
        search: ""
    };
}

if (typeof localStorage === 'undefined') {
    localStorage = {
        setItem: function() {},
        removeItem: function() {},
        key: function() {},
        getItem: function() {},
        removeItem: function(key) {return delete this[key]},
        length: 0
};
}
"""

if __name__ == "__main__":
    JavascriptShell().cmdloop()
