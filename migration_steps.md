## Step 1: Use Segregated Branch of Statdev.
```

Statdev Segregated branch: https://github.com/dbca-wa/statdev/tree/seg_statdev

```


## Step 2: Create new database.
```

CREATE DATABASE statdev_dev;
CREATE USER statdev_dev WITH PASSWORD '<password>';
GRANT ALL PRIVILEGES ON DATABASE "statdev_dev" to statdev_dev;
\c statdev_dev
create extension postgis;
GRANT ALL ON ALL TABLES IN SCHEMA public TO statdev_dev;
GRANT ALL ON SCHEMA public TO statdev_dev;

```

## Step 3: Create ENV file (create ledger api key from ledger admin database (System ID: 0637))
```

ALLOWED_DOMAINS=['localhost:9216']
ALLOWED_HOSTS=['localhost:9216']
CSRF_TRUSTED_ORIGINS=["localhost:9216"]
DATABASE_URL=postgis://statdev_dev:statdev_dev@172.17.0.1:25432/statdev_dev?sslmode=require
LEDGER_DATABASE_URL=postgis://ledger_dev:ledger_dev@172.17.0.1:25432/ledger_dev?sslmode=require
LEDGER_API_KEY=<LEDGER_API_KEY>
LEDGER_API_URL=http://10.17.0.10:7001
LEDGER_UI_URL=http://10.17.0.10:7001
DEBUG=True
DEFAULT_URL_INTERNAL=<INTERNAL_URL>
EMAIL_DELIVERY=on
EMAIL_FROM=no-reply@dbca.wa.gov.au
EMAIL_HOST=smtp.lan.fyi
EMAIL_INSTANCE=UAT
EMAIL_PORT=25
EXTERNAL_URL=<EXTERNAL_URL>
NON_PROD_EMAIL=email
NOTIFICATION_EMAIL=email
OVERRIDE_EMAIL=email
PRODUCTION_EMAIL=False
SECRET_KEY=<Secret>

```

## Step 4: install packages
```
pip install -r requirements.txt
```


## Step 5: apply patches
```
vi venv/lib/python3.8/site-packages/django/contrib/admin/migrations/0001_initial.py (see changes in patch_for_admin_0001_initial.patch)
```


## Step 6: Run Migrations
```
./manage.py migrate auth
./manage.py migrate ledger_api_client
./manage.py migrate admin
./manage.py migrate 
```

## Step 7: Generate system groups
```
python manage.py generate_groups.py
```


## Step 8: Add user to groups


Go to http://<site-domain>/admin and use the DBCA login details

Go to http://<site-domain>/admin/ledger_api_client/systemgroup/

Add the email user account in the required group (Note: For now, user can only be added using user_id)

## Step 9: Ledger payment setup


Go to http://<ledger-url>/admin/payments/oracleinterfacesystem

Add Statdev in the Oracle Interface System

Add these variable in the ENV

```
PAYMENT_INTERFACE_SYSTEM_PROJECT_CODE=<SYSTEM CODE>
PAYMENT_INTERFACE_SYSTEM_ID=<SYSTEM ID>
```
