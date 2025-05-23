"""
Django settings for statdev project.
Generated by 'django-admin startproject' using Django 1.10.5.
"""
import os
import confy
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
confy.read_environment_file(BASE_DIR+"/.env")
os.environ.setdefault("BASE_DIR", BASE_DIR)

from confy import env, database
import os
from ledger_api_client.settings_base import *

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROOT_URLCONF = 'statdev.urls'
SITE_ID = 1
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

BOOKING_TIMEOUT = 1200
LEDGER_TEMPLATE = 'bootstrap5'
JCAPTCHA_EXPIRY_MINUTES=15
JCAPTCHA_CLEANUP_MINUTES=100

# Define the following in the environment:
DEBUG = env('DEBUG', False)
SECRET_KEY = env('SECRET_KEY')
ENABLE_DJANGO_LOGIN = env('ENABLE_DJANGO_LOGIN', False)
CSRF_TRUSTED_ORIGINS_STRING = decouple.config("CSRF_TRUSTED_ORIGINS", default='[]')
CSRF_TRUSTED_ORIGINS = json.loads(str(CSRF_TRUSTED_ORIGINS_STRING))
#if not DEBUG:
#    ALLOWED_HOSTS = [env('ALLOWED_DOMAIN'), ]
#else:
#    ALLOWED_HOSTS = ['*']
#GIT_COMMIT_DATE = os.popen('git log -1 --format=%cd').read()
# Application definition
#AUTH_USER_MODEL = 'accounts.EmailUser'
INSTALLED_APPS += [
###    'reversion',
    'webtemplate_dbca',
    'crispy_forms',
    'bootstrap3',
    'django_q',
    'public',
    'rest_framework',
    'rest_framework_gis',
    'django_crispy_jcaptcha',
    'ledger_api_client',
    'django.contrib.flatpages',
    'crispy_bootstrap5',
    'haystack',
    'treebeard',
    'django_tables2',
    'applications',
    'actions',
    'approvals',
##    'ajax_upload'
]
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'statdev.perms.OfficerPermission',
    )
}
SITE_ID=1

if not DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES']=('rest_framework.renderers.JSONRenderer',)
else:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES']=('rest_framework.renderers.JSONRenderer','rest_framework_csv.renderers.CSVRenderer')
MIDDLEWARE_CLASSES += [
#    'django.middleware.security.SecurityMiddleware',
#    'django.contrib.sessions.middleware.SessionMiddleware',
#    'django.middleware.common.CommonMiddleware',
#    'django.middleware.csrf.CsrfViewMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'django.contrib.messages.middleware.MessageMiddleware',
#    'django.middleware.clickjacking.XFrameOptionsMiddleware',
#    'reversion.middleware.RevisionMiddleware',
#    'dpaw_utils.middleware.SSOLoginMiddleware',
     'social_django.middleware.SocialAuthExceptionMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'applications.middleware.FirstTimeNagScreenMiddleware'
    
]
MIDDLEWARE = MIDDLEWARE_CLASSES

#TEMPLATES += [
#    {
#        'BACKEND': 'django.template.backends.django.DjangoTemplates',
#        'DIRS': [
#            os.path.join(BASE_DIR, 'statdev', 'templates'),
#            os.path.join(BASE_DIR, 'applications', 'email')
#        ],
#        'APP_DIRS': True,
#        'OPTIONS': {
#            'context_processors': [
#                'django.template.context_processors.debug',
#                'django.template.context_processors.request',
#                'django.contrib.auth.context_processors.auth',
#                'django.contrib.messages.context_processors.messages',
#                'statdev.context_processors.template_context',
#            ],
#        },
#    },
#]
#

TEMPLATES[0]['DIRS'].append(os.path.join(BASE_DIR, 'statdev', 'templates'))
TEMPLATES[0]['DIRS'].append(os.path.join(BASE_DIR, 'applications', 'email'))
TEMPLATES[0]['DIRS'].append(os.path.join(BASE_DIR, 'applications', 'templates'))
TEMPLATES[0]['DIRS'].append(os.path.join(BASE_DIR, 'applications', 'templates', 'applications'))

TEMPLATES[0]['OPTIONS']['context_processors'].append('statdev.context_processors.template_context')
TEMPLATES[0]['OPTIONS']['context_processors'].append('statdev.context_processors.payment_processor')
#TODO: check this change to env
PAYMENT_INTERFACE_SYSTEM_PROJECT_CODE='0637'
PAYMENT_INTERFACE_SYSTEM_ID='41'
WSGI_APPLICATION = 'statdev.wsgi.application'
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

#LOGIN_URL = 'login'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'social_core.backends.email.EmailAuth',
)

LOGIN_REDIRECT_URL = 'home'
STATIC_CONTEXT_VARS = {}
APPLICATION_VERSION_NO = '0.3'
ALLOWED_UPLOAD_TYPES = [
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-word.document.12',
    'application/rtf',
    'application/pdf',
    'image/tiff',
    'image/jpeg',
    'image/gif',
    'image/png',
    'text/csv',
    'text/plain'
]
DATA_UPLOAD_MAX_NUMBER_FIELDS = 50240
MAX_UPLOAD_SIZE = "5242880"

#USER_FIELDS = ['email']
##SOCIAL_AUTH_STRATEGY = 'social_django.strategy.DjangoStrategy'
##SOCIAL_AUTH_STORAGE = 'social_django.models.DjangoStorage'
##SOCIAL_AUTH_EMAIL_FORM_URL = '/ledger/'
##SOCIAL_AUTH_EMAIL_VALIDATION_FUNCTION = 'ledger.accounts.mail.send_validation'
##SOCIAL_AUTH_EMAIL_VALIDATION_URL = '/ledger/validation-sent/'
##SOCIAL_AUTH_PASSWORDLESS = True
##SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
##SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True
##SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['first_name', 'last_name', 'email']
##SOCIAL_AUTH_PIPELINE = (
##    'social_core.pipeline.social_auth.social_details',
##    'ledger.accounts.pipeline.lower_email_address',
##    'ledger.accounts.pipeline.logout_previous_session',
##    'social_core.pipeline.social_auth.social_uid',
##    'social_core.pipeline.social_auth.auth_allowed',
##    'social_core.pipeline.social_auth.social_user',
##    'social_core.pipeline.user.get_username',
##    # 'social.pipeline.mail.mail_validation',
##    'ledger.accounts.pipeline.mail_validation',
##    'ledger.accounts.pipeline.user_by_email',
##    'social_core.pipeline.user.create_user',
##    'social_core.pipeline.social_auth.associate_user',
##    'social_core.pipeline.social_auth.load_extra_data',
##    #'social_core.pipeline.user.user_details'
##)

# Email settings
DEFAULT_FROM_EMAIL = 'DoNotReply@dpaw.wa.gov.au'

# Email settings Ledger
ADMINS = ('asi@dpaw.wa.gov.au',)
EMAIL_HOST = env('EMAIL_HOST', 'email.host')
EMAIL_PORT = env('EMAIL_PORT', 25)
EMAIL_FROM = env('EMAIL_FROM', ADMINS[0])
DEFAULT_FROM_EMAIL =env('EMAIL_FROM','DoNotReply@dpaw.wa.gov.au') 

# Database configuration
# DATABASES += {'default': database.config()}

# Password validation
#AUTH_PASSWORD_VALIDATORS = [
#    {
#        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#    },
#    {
#        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#    },
#    {
#        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#    },
#    {
#        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#    },
#]


# Internationalization
LANGUAGE_CODE = 'en-AU'
TIME_ZONE = 'Australia/Perth'
USE_I18N = True
USE_L10N = True
USE_TZ = True
# Sensible AU date input formats
DATE_INPUT_FORMATS = (
    '%d/%m/%Y',
    '%d/%m/%y',
    '%d-%m-%Y',
    '%d-%m-%y',
    '%d %b %Y',
    '%d %b, %Y',
    '%d %B %Y',
    '%d %B, %Y',
)


# Static files (CSS, JavaScript, Images)
# Ensure that the media directory exists:
if not os.path.exists(os.path.join(BASE_DIR, 'media')):
    os.mkdir(os.path.join(BASE_DIR, 'media'))

PRIVATE_MEDIA_ROOT = os.path.join(BASE_DIR, 'private-media')
PRIVATE_MEDIA_URL = '/private-media/view/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

#STATICFILES_DIR = (
#    os.path.join(BASE_DIR, "applications/static"),
#)

STATICFILES_DIR = (
    "static",
)

 
# Logging settings
# Ensure that the logs directory exists:
if not os.path.exists(os.path.join(BASE_DIR, 'logs')):
    os.mkdir(os.path.join(BASE_DIR, 'logs'))
#LOGGING.extend = {
#    'version': 1,
#    'disable_existing_loggers': False,
#    'formatters': {
#        'simple': {
#            'format': '%(levelname)s %(asctime)s %(message)s'
#        },
#    },
#    'handlers': {
#        'statdev_log': {
#            'class': 'logging.handlers.RotatingFileHandler',
#            'filename': os.path.join(BASE_DIR, 'logs', 'statdev.log'),
#            'formatter': 'simple',
#            'maxBytes': 1024 * 1024 * 5,
#            'backupCount': 5,
#        }
#    },
#    'loggers': {
#        'django.request': {
#            'handlers': ['statdev_log'],
#            'level': 'INFO'
#        },
#        'statdev': {
#            'handlers': ['statdev_log'],
#            'level': 'INFO'
#        },
#    }
#}

# django-crispy-forms
# CRISPY_TEMPLATE_PACK = 'bootstrap3'

# Cache settings.
#CACHES = {
#    'default': {
#        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
#        'LOCATION': 'django_cache_table',
#    }
#}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(BASE_DIR, 'statdev', 'cache'),
    }
}


# django-q configuration
#Q_CLUSTER = {
#    'name': 'statutory_dev_cluster',
#    'workers': 4,
#    'recycle': 100,
#    'timeout': 90,
#    'retry': 120,
#    'queue_limit': 50,
#    'bulk': 10,
#    'orm': 'default',
#}

LEDGER_UI_ACCOUNTS_MANAGEMENT = [
    {"email": {"options": {"view": True, "edit": False}}},
    {"first_name": {"options": {"view": True, "edit": True}}},
    {"last_name": {"options": {"view": True, "edit": True}}},
    {"title": {"options": {"view": True, "edit": True}}},
    {"dob": {"options": {"view": True, "edit": True}}},
    {"phone_number": {"options": {"view": True, "edit": True}}},
    {"mobile_number": {"options": {"view": True, "edit": True}}},
    {"fax_number": {"options": {"view": True, "edit": True}}},
    {"identification": {"options": {"view": True, "edit": True}}},
]

DEPT_DOMAINS = env('DEPT_DOMAINS', ['dpaw.wa.gov.au', 'dbca.wa.gov.au'])
SOCIAL_AUTH_RAISE_EXCEPTIONS = True
SOCIAL_AUTH_URL_NAMESPACE = 'social'
RAISE_EXCEPTIONS = True
SYSTEM_NAME = env('SYSTEM_NAME', 'Statdev System')
SYSTEM_NAME_SHORT = env('SYSTEM_NAME_SHORT', 'statdev')
DEFAULT_AUTO_FIELD='django.db.models.AutoField'

# Use git commit hash for purging cache in browser for deployment changes
GIT_COMMIT_HASH = ''
GIT_COMMIT_DATE = ''
if  os.path.isdir(BASE_DIR+'/.git/') is True:
    GIT_COMMIT_DATE = os.popen('cd '+BASE_DIR+' ; git log -1 --format=%cd').read()
    GIT_COMMIT_HASH = os.popen('cd  '+BASE_DIR+' ; git log -1 --format=%H').read()
if len(GIT_COMMIT_HASH) == 0: 
    GIT_COMMIT_HASH = os.popen('cat /app/git_hash').read()
    if len(GIT_COMMIT_HASH) == 0:
       print ("ERROR: No git hash provided")


PS_PAYMENT_SYSTEM_ID = env('PS_PAYMENT_SYSTEM_ID', 'S637')
if not VALID_SYSTEMS:
    VALID_SYSTEMS = [PS_PAYMENT_SYSTEM_ID]
BPAY_ALLOWED = env('BPAY_ALLOWED',False)
EXTERNAL_URL = env('EXTERNAL_URL','')
