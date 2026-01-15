"""
WSGI config for statdev project.
It exposes the WSGI callable as a module-level variable named ``application``.
"""
import confy
from django.core.wsgi import get_wsgi_application
from dj_static import Cling, MediaCling
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# confy.read_environment_file(BASE_DIR+"/.env")
os.environ.setdefault("BASE_DIR", BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "statdev.settings")
#application = get_wsgi_application()
application = Cling(MediaCling(get_wsgi_application()))
