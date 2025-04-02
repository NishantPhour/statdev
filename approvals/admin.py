from django.contrib.admin import register, ModelAdmin
from django.contrib import admin
from .models import Approval

from django.contrib.gis import admin

from ledger_api_client.ledger_models import EmailUserRO as EmailUser

admin.site.index_template = "admin-index.html"
admin.site.site_header = "Commercial Operator Admin"
admin.autodiscover()

@register(Approval)
class ApprovalsAdmin(ModelAdmin):
    date_hierarchy = 'start_date'
#    filter_horizontal = ('records',)
    list_display = ('id', 'title','app_type', 'applicant','application', 'start_date', 'expiry_date', 'status', 'issue_date',)
    list_filter = ('app_type','status')
    search_fields = ('applicant__email', 'organisation__name', 'title')


# Register your models here.
