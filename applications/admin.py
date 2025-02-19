from django.contrib.admin import register, ModelAdmin
from django.contrib.gis import admin

from .models import (
    Record, Vessel, ApplicationPurpose, Application, Location, Referral,
    Condition, Compliance, Delegate, ApplicationInvoice, Communication, Craft, 
    OrganisationContact, OrganisationPending, OrganisationExtras,PublicationFeedback, 
    PublicationWebsite,ComplianceGroup, StakeholderComms, ConditionPredefined, ApplicationLicenceFee, 
    Booking, DiscountReason, BookingInvoice)


admin.site.index_template = "admin-index.html"
admin.site.site_header = "Commercial Operator Admin"
admin.autodiscover()



@register(Record)
class RecordAdmin(ModelAdmin):
    list_display = ('name', 'category', 'file_group','file_group_ref_id', 'upload')
    list_filter = ('category',)
    search_fields = ('name',)

class BookingInvoiceInline(admin.TabularInline):
    model = BookingInvoice
    extra = 0

@register(Booking)
class BookingAdmin(ModelAdmin):
    # list_display = ('customer', 'application', 'cost_total','created')
    # list_filter = ('customer',)
    # raw_id_fields = ('customer','application','overridden_by','canceled_by','created_by',)
    # search_fields = ('customer','application')
    # inlines = [BookingInvoiceInline,]
    x='x'

@register(DiscountReason)
class DiscountReasonAdmin(ModelAdmin):
    list_display = ('text', 'detailRequired', 'editable',)

@register(Vessel)
class VesselAdmin(ModelAdmin):
    filter_horizontal = ('registration',)
    list_display = ('name', 'vessel_type', 'vessel_id')
    list_filter = ('vessel_type',)
    search_fields = ('name', 'vessel_id')
    readonly_fields = ('registration','documents',)


@register(ApplicationPurpose)
class ApplicationPurposeAdmin(ModelAdmin):
    search_fields = ('purpose',)

@register(ApplicationLicenceFee)
class ApplicationLicenceFeeAdmin(ModelAdmin):
    list_display = ('app_type','licence_fee','start_dt','end_dt','created',)
    list_filter = ('app_type',)
    order_by = ('-start_dt',)
    
@register(Application)
class ApplicationAdmin(ModelAdmin):
    # date_hierarchy = 'submit_date'
    # filter_horizontal = ('records',)
    # raw_id_fields = ('applicant','assignee','assigned_officer','approval_document','approval_document_signed','submitted_by','assessed_by','organisation','group','old_application',)
    # readonly_fields = ('records','location_route_access','cert_survey','cert_public_liability_insurance','risk_mgmt_plan','safety_mgmt_procedures','brochures_itineries_adverts','other_relevant_documents','vessels','land_owner_consent','deed','river_lease_scan_of_application','proposed_development_plans','document_draft','document_new_draft','document_new_draft_v3','document_draft_signed','swan_river_trust_board_feedback','document_memo','document_memo_2','document_briefing_note','document_determination_approved','supporting_info_demonstrate_compliance_trust_policies','document_final','document_final_signed','document_determination','document_completion',)
    # list_display = ('id', 'app_type', 'organisation', 'state', 'title', 'submit_date', 'expire_date')
    # list_filter = ('app_type', 'state')
    # search_fields = ('applicant__email', 'organisation__name', 'assignee__email', 'title')
    x='x'


@register(Location)
class LocationAdmin(ModelAdmin):
    filter_horizontal = ('records',)
    search_fields = ('application__title', 'lot', 'reserve', 'suburb', 'intersection', 'lga')


@register(Referral)
class ReferralAdmin(ModelAdmin):
    date_hierarchy = 'sent_date'
    filter_horizontal = ('records',)
    list_display = ('id', 'application', 'referee', 'sent_date', 'period', 'status', 'expire_date', 'response_date')
    list_filter = ('status',)
    search_fields = ('application__title', 'referee__email', 'details', 'feedback')
    raw_id_fields = ('application',)
    readonly_fields = ('referee',)



@register(Condition)
class ConditionAdmin(ModelAdmin):
    filter_horizontal = ('records',)
    list_display = ('id', 'referral', 'status', 'due_date', 'recur_pattern')
    raw_id_fields = ('application','referral',)
    readonly_fields = ('records',)
    list_filter = ('status', 'recur_pattern')
    search_fields = ('application__title', 'condition')


@register(Compliance)
class ComplianceAdmin(ModelAdmin):
    # date_hierarchy = 'submit_date'
    # filter_horizontal = ('records',)
    # raw_id_fields = ('condition','assessed_by','applicant','assignee','assessed_by','submitted_by')
    # readonly_fields = ('external_documents',)
    # list_display = ('__str__', 'applicant', 'approval_id','assignee', 'status', 'submit_date', 'approve_date','due_date','compliance_group')
    # search_fields = ('applicant__email', 'assignee__email', 'compliance', 'comments')
    x='x'

@register(ComplianceGroup)
class ComplianceGroupAdmin(ModelAdmin):
    list_display = ('__str__', 'applicant', 'approval_id','assignee', 'status', 'due_date')
    search_fields = ('applicant__email', 'assignee__email', 'compliance', 'comments')

@register(Delegate)
class DelegateAdmin(ModelAdmin):
    pass

@register(ApplicationInvoice)
class ApplicationInvoiceAdmin(ModelAdmin):
    pass

# @register(Communication)
# class CommunicationAdmin(ModelAdmin):
#     list_display = ('application', 'comms_to', 'comms_from','subject','comms_type','details','created')
#     search_fields = ('comms_to','comms_from','subject','details')
#     raw_id_fields = ('application',)
#     readonly_fields = ('records',)


@register(Craft)
class CraftAdmin(ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@register(OrganisationContact)
class CommunicationAdmin(ModelAdmin):
    list_display = ('email','first_name','last_name','phone_number','mobile_number','fax_number')
    search_fields = ('email','first_name','last_name','phone_number','mobile_number','fax_number')

@register(OrganisationPending)
class OrganisationPending(ModelAdmin):
    list_display = ('name','abn','identification','postal_address','billing_address')
    search_fields = ('name','abn','identification','postal_address','billing_address')

@register(OrganisationExtras)
class OrganisationExtras(ModelAdmin):
    list_display = ('organisation','pin1','pin2')
    search_fields = ('organisation','pin1','pin2')

@register(PublicationFeedback)
class PublicationFeedback(ModelAdmin):
    list_display = ('name','status','address','suburb')
    search_fields = ('name','status','address','suburb')

@register(PublicationWebsite)
class PublicationWebsite(ModelAdmin):
    list_display = ('application','original_document','published_document')
    search_fields = ('application','original_document','published_document')

@register(StakeholderComms)
class StakeholderComms(ModelAdmin):
    list_display = ('application','email','name','sent_date','role')
    search_fields = ('application','email','name','sent_date','role')
    raw_id_fields = ('application',)


@register(ConditionPredefined)
class ConditionPredefined(ModelAdmin):
    list_display = ('title','condition','status')
    search_fields = ('title','condition','status')


