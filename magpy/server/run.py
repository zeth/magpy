"""Let's go!
Run the Magpy site backend.
Use --port to specify the port.
"""

# TODO: this eventually needs to be smarter
# We need to import magpy urls.py first
# Then import usercode (i.e. workspace) urls.py

from magpy.server import base
from magpy.server.urls import URLS
from magpy.server.urlloader import URLLoader

if __name__ == "__main__":
    loader = URLLoader()
    urls = loader.get_urls()
    base.main(urls)
