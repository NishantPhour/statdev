from django.contrib.admin import register, ModelAdmin
from .models import Action
from django.contrib.gis import admin

# from ledger_api_client.ledger_models import EmailUserRO as EmailUser

admin.site.index_template = "admin-index.html"
admin.site.site_header = "Commercial Operator Admin"
admin.autodiscover()


@register(Action)
class ActionAdmin(ModelAdmin):
    list_display = ('content_object', 'category', 'action')
    list_filter = ('category',)
    search_fields = ('action',)
