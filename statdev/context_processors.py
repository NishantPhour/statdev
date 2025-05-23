from django.conf import settings
from django.contrib.auth.models import Group
from ledger_api_client import utils as ledger_api_utils
import hashlib 

def has_group(user):
    staff_groups = ['Statdev Approver','Statdev Assessor','Statdev Director','Statdev Emergency','Statdev Executive','Statdev Processor']
    # user_groups = user.groups.all()
    # for sg in user_groups:
    #     group = SystemGroup.objects.get(name=sg)
    #     if group in user.groups.all():
    #         return True
    return True

def has_staff(user):
    if user.is_staff is True:
        return True
    else:
        return False

def has_admin_assessor(user):
    staff_groups = ['Statdev Processor','Statdev Assessor']
    # user_groups = user.groups.all()
    # for sg in staff_groups:
    #     group = SystemGroup.objects.get(name=sg)
    #     if group in user.groups.all():
    #         return True
    return True

def has_admin(user):
    staff_groups = ['Statdev Processor']
    # user_groups = user.groups.all()
    # for sg in staff_groups:
    #     group = SystemGroup.objects.get(name=sg)
    #     if group in user.groups.all():
    #         return True
    return True

def template_context(request):
    """Pass extra context variables to every template.
    """
    context = {
        'project_version': settings.APPLICATION_VERSION_NO,
        'project_last_commit_date': settings.GIT_COMMIT_DATE,
        'staff': has_staff(request.user),
        'admin_staff': has_admin(request.user),
        'admin_assessor_staff':  has_admin_assessor(request.user),
        'TEMPLATE_GROUP': "rivers",
        'GIT_COMMIT_DATE' : settings.GIT_COMMIT_DATE,
        'GIT_COMMIT_HASH' : settings.GIT_COMMIT_HASH,
        'EXTERNAL_URL' : settings.EXTERNAL_URL

        #['Approver','Assessor','Director','Emergency','Executive','Processor']
    }
    return context

def payment_processor(request):

    web_url = request.META.get('HTTP_HOST', None)
    lt = ledger_api_utils.get_ledger_totals()

    checkouthash = None
    if 'payment_pk' in request.session:
        checkouthash =  hashlib.sha256(str(request.session["payment_pk"]).encode('utf-8')).hexdigest()

    return {
        'public_url': web_url,
        # 'template_group': 'ria',
        'LEDGER_API_URL': f'{settings.LEDGER_API_URL}',
        'LEDGER_UI_URL': f'{settings.LEDGER_UI_URL}',
        # 'LEDGER_SYSTEM_ID': f'{settings.LEDGER_SYSTEM_ID}',
        'ledger_totals': lt,
        'checkouthash' : checkouthash,
    }



