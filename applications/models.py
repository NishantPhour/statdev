from __future__ import unicode_literals
from datetime import timedelta
import zlib
from django.conf import settings
from django.contrib.gis.db import models
from django.db import transaction
from django.contrib.postgres.fields import JSONField
from django.urls import reverse
from six import python_2_unicode_compatible
from model_utils import Choices
from django.contrib.auth.models import Group
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ValidationError
from django_countries.fields import CountryField
from ledger_api_client.managed_models import SystemGroup, SystemUser
# from oscar.apps.address.abstract_models import AbstractUserAddress, AbstractCountry
# from approvals.models import Approval
# from ledger.accounts.models import Organisation, Address as LedgerAddress, OrganisationAddress
# from ledger.payments.models import Invoice

upload_storage = FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)

def unicode_compatible(value):
    try: 
        return unicode(value)
    except:
        return str(value)

@python_2_unicode_compatible
class Record(models.Model):
    """This model represents a record that needs to be saved for
    future reference. It also records metadata and optional text content to be
    indexed for search.
    """
    DOC_CATEGORY_CHOICES = Choices(
        (1, 'consent', ('Landowner consent')),
        (2, 'deed', ('Deed')),
        (3, 'assessment', ('Assessment report')),
        (4, 'referee_response', ('Referee response')),
        (5, 'lodgement', ('Lodgement document')),
        (6, 'draft', ('Draft document')),
        (7, 'final', ('Final document')),
        (8, 'determination', ('Determination document')),
        (9, 'completion', ('Completed document')),
    )


    FILE_GROUP = Choices(
        (1, 'permit', ('Permit')),
        (2, 'licence', ('Licence/permit')),
        (3, 'part5', ('Part 5')),
        (4, 'emergency', ('Emergency works')),
        (5, 'part5cr', ('Part 5 - Amendment Request')),
        (6, 'part5amend', ('Part 5 - Amendment Application')),
        (7, 'test', ('Test - Application')),
        (8, 'permitamend', ('Amend Permit')),
        (9, 'licenceamend', ('Amend Licence')),
        (10, 'permitrenew', ('Renew Permit')),
        (11, 'licencerenew', ('Renew Licence')),
        (2001, 'person', ('Person')),
        (2002, 'organisation', ('Organistion')),
        (2003, 'application_comms', ('Application Communication Logs')),    
        (2004, 'account_comms', ('Account Communication Logs')),
        (2005, 'approval', ('Approval')),
        (2006, 'compliance', ('Compliance')),
        (2007, 'approval_comms', ('Approval Communication Logs'))
    )


    upload = models.FileField(max_length=512, upload_to='uploads/%Y/%m/%d', storage=upload_storage)
    name = models.CharField(max_length=256)
    category = models.IntegerField(choices=DOC_CATEGORY_CHOICES, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    text_content = models.TextField(null=True, blank=True, editable=False)  # Text for indexing
    file_group = models.IntegerField(choices=FILE_GROUP, null=True, blank=True)
    file_group_ref_id = models.IntegerField(null=True, blank=True) 
    extension = models.CharField(max_length=5, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def file_url(self):
         if self.extension is None: 
                self.extension = ''
         return settings.PRIVATE_MEDIA_URL+str(self.pk)+'-file'+self.extension

    def __str__(self):
        if self.category:
            return '{} ({})'.format(self.name, self.get_category_display())
        return self.name


@python_2_unicode_compatible
class Vessel(models.Model):
    """This model represents a vessel/craft that will be used
    in relation to the application
    """
    VESSEL_TYPE_CHOICES = Choices(
        (0, 'vessel', ('Vessel')),
        (1, 'craft', ('Craft')),
    )

    vessel_type = models.SmallIntegerField(choices=VESSEL_TYPE_CHOICES, null=True, blank=True)
    # Vessel Information
    name = models.CharField(max_length=256)
    vessel_id = models.CharField(max_length=256, null=True, blank=True, verbose_name='Vessel identification')
    registration = models.ManyToManyField(Record, blank=True, related_name='vessel_documents')
    size = models.PositiveIntegerField(null=True, blank=True, verbose_name='size (m)')
    engine = models.PositiveIntegerField(null=True, blank=True, verbose_name='engine (kW)')
    passenger_capacity = models.PositiveIntegerField(null=True, blank=True)
    # craft Information
    craft_type = models.CharField(max_length=256, null=True, blank=True, verbose_name='Craft Type')
    number_of_crafts = models.PositiveIntegerField(null=True, blank=True, verbose_name='Number of crafts')
    documents = models.ManyToManyField(Record, blank=True, related_name='craft_documents')

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class ApplicationPurpose(models.Model):
    purpose = models.CharField(max_length=256)

    def __str__(self):
        return self.purpose


class Craft(models.Model):
    name = models.CharField(max_length=256)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class BaseAddress(models.Model):
    """Generic address model, intended to provide billing and shipping
    addresses.
    Taken from django-oscar address AbstrastAddress class.
    """
    STATE_CHOICES = (
        ('ACT', 'ACT'),
        ('NSW', 'NSW'),
        ('NT', 'NT'),
        ('QLD', 'QLD'),
        ('SA', 'SA'),
        ('TAS', 'TAS'),
        ('VIC', 'VIC'),
        ('WA', 'WA')
    )

    # Addresses consist of 1+ lines, only the first of which is
    # required.
    line1 = models.CharField('Line 1', max_length=255)
    line2 = models.CharField('Line 2', max_length=255, blank=True)
    line3 = models.CharField('Line 3', max_length=255, blank=True)
    locality = models.CharField('Suburb / Town', max_length=255)
    state = models.CharField(max_length=255, default='WA', blank=True)
    country = CountryField(default='AU')
    postcode = models.CharField(max_length=10)
    # A field only used for searching addresses.
    search_text = models.TextField(editable=False)
    hash = models.CharField(max_length=255, db_index=True, editable=False)

    def __str__(self):
        return self.summary

#    def __unicode__(self):
#        return ''

    class Meta:
        abstract = True

    def clean(self):
        # Strip all whitespace
        for field in ['line1', 'line2', 'line3',
                      'locality', 'state']:
            if self.__dict__[field]:
                self.__dict__[field] = self.__dict__[field].strip()

    def save(self, *args, **kwargs):
        self._update_search_text()
        self.hash = self.generate_hash()
        super(BaseAddress, self).save(*args, **kwargs)

    def _update_search_text(self):
        search_fields = filter(
            bool, [self.line1, self.line2, self.line3, self.locality,
                   self.state, str(self.country.name), self.postcode])
        self.search_text = ' '.join(search_fields)

    @property
    def summary(self):
        """Returns a single string summary of the address, separating fields
        using commas.
        """
        return u', '.join(self.active_address_fields())

    # Helper methods
#    def active_address_fields(self):
#        """Return the non-empty components of the address.
#        """
#        fields = [self.line1, self.line2, self.line3,
#                  self.locality, self.state, self.country, self.postcode]
#        fields = [str(f).strip() for f in fields if f]
#        
#        return fields


    # Helper methods
    def active_address_fields(self):
        """Return the non-empty components of the address.
        """
        fields = [self.line1, self.line2, self.line3,
                  self.locality, self.state, self.country, self.postcode]
        #for f in fields:
        #    print unicode(f).encode('utf-8').decode('unicode-escape').strip()
        #fields = [str(f).strip() for f in fields if f]
        fields = [unicode_compatible(f).encode('utf-8').decode('unicode-escape').strip() for f in fields if f]
        
        return fields

    def join_fields(self, fields, separator=u', '):
        """Join a sequence of fields using the specified separator.
        """
        field_values = []
        for field in fields:
            value = getattr(self, field)
            field_values.append(value)
        return separator.join(filter(bool, field_values))

    def generate_hash(self):
        """
            Returns a hash of the address summary
        """
        return zlib.crc32(self.summary.strip().upper().encode('UTF8'))   
    
@python_2_unicode_compatible
class Organisation(models.Model):
    """This model represents the details of a company or other organisation.
    Management of these objects will be delegated to 0+ EmailUsers.
    """
    name = models.CharField(max_length=128, unique=True)
    abn = models.CharField(max_length=50, null=True, blank=True, verbose_name='ABN')
    # TODO: business logic related to identification file upload/changes.
    identification = models.FileField(upload_to='%Y/%m/%d', null=True, blank=True)
    postal_address = models.ForeignKey('OrganisationAddress', related_name='org_postal_address', blank=True, null=True, on_delete=models.SET_NULL)
    billing_address = models.ForeignKey('OrganisationAddress', related_name='org_billing_address', blank=True, null=True, on_delete=models.SET_NULL)
    email = models.EmailField(blank=True, null=True,)
    trading_name = models.CharField(max_length=256, null=True, blank=True)

    def upload_identification(self, request):
        with transaction.atomic():
            self.identification = request.data.dict()['identification']
            self.save()

    def __str__(self):
        return self.name
    
@python_2_unicode_compatible    
class OrganisationAddress(BaseAddress):
    organisation = models.ForeignKey(Organisation, null=True,blank=True, related_name='adresses', on_delete=models.SET_NULL)
    class Meta:
        verbose_name_plural = 'organisation addresses'
        #unique_together = ('organisation','hash') 


@python_2_unicode_compatible
class Application(models.Model):
    """This model represents an application by a customer to P&W for a single
    permit, licence/permit, part 5, etc.
    """

    APP_TYPE_CHOICES = Choices(
        (1, 'permit', ('Permit')),
        (2, 'licence', ('Licence/permit')),
        (3, 'part5', ('Part 5')),
        (4, 'emergency', ('Emergency works')),
        (5, 'part5cr', ('Part 5 - Amendment Request')),
        (6, 'part5amend', ('Section 84')),
        (7, 'test', ('Test - Application')),
        (8, 'permitamend', ('Amend Permit')),
        (9, 'licenceamend', ('Amend Licence')),
        (10, 'permitrenew', ('Renew Permit')),
        (11, 'licencerenew', ('Renew Licence'))
    )

    APP_APPLY_ON = Choices(
         (1,'yourself', ('On Behalf of yourself')),
         (2,'yourcompany', ('On Behalf of your company / government agency')),
         (3, 'somebody_else_individual', ('On Behalf of indivdual as somebody else (as an authorised agent)')),
         (4, 'somebody_else_company', ('On Behalf of a company as somebody else (as an authorised agent)')),
         (5, 'internal', ('Internal'))
    )
    APP_STATUS = Choices(
          
          (1, 'active', ('Active')),
          (2, 'cancelled', ('Cancelled')),
          (3, 'draft', ('Draft'))
    )

    APP_STATE_CHOICES = Choices(
        (0, 'unknown',('Unknown')),
        (1, 'draft', ('Draft')),
        (2, 'with_admin', ('With Admin Officer')),
        (3, 'with_referee', ('With Referrals')),
        (4, 'with_assessor', ('With Assessor')),
        (5, 'with_manager', ('With Manager')),
        (6, 'issued', ('Issued')),
        (7, 'issued_with_admin', ('Issued (with admin)')),
        (8, 'declined', ('Declined')),
        (9, 'new', ('New')),
        (10, 'approved', ('Approved')),
        (11, 'expired', ('Expired')),
        (12, 'with_director', ('With Director')),
        (13, 'with_exec', ('With Executive')),
        (14, 'completed', ('Completed')),
        (15, 'creator', ('Form Creator')),
        (16, 'current', ('Current')),
        (17, 'discard', ('Deleted')),
        (18, 'payment', ('Pending Payment')),
        (19, 'not_supported', ('Not Supported'))
    )

    APP_LOCATION_CHOICES = Choices(
        (0, 'onland', ('On Land')),
        (1, 'onwater', ('On Water')),
        (2, 'both', ('Both')),
    )

    APP_YESNO = Choices(
        (True, ('Yes')),
        (False, ('No'))
    )

    APP_VESSEL_CRAFT = Choices(
        #(1, 'vessel', ('Vessel(s)')),
        #(2, 'craft', ('Craft(s)')),
        (3, 'yes', ('yes')),
        (0, 'none', ('No'))
    )

    applicant = models.IntegerField(blank=True, null=True)
    organisation = models.ForeignKey(Organisation, blank=True, null=True, on_delete=models.PROTECT)
    app_type = models.IntegerField(choices=APP_TYPE_CHOICES, blank=True, null=True)
    apply_on_behalf_of = models.IntegerField(choices=APP_APPLY_ON, blank=True, null=True)
    assignee = models.IntegerField(blank=True, null=True)
    assigned_officer = models.IntegerField(blank=True, null=True)
    status = models.IntegerField(choices=APP_STATUS, default=APP_STATUS.active, editable=True, ) 
    state = models.IntegerField(choices=APP_STATE_CHOICES, default=APP_STATE_CHOICES.draft, editable=True)
    title = models.CharField(max_length=256)
    description = models.TextField(null=True, blank=True)
    submit_date = models.DateField()
    expire_date = models.DateField(blank=True, null=True)
    proposed_commence = models.DateField(null=True, blank=True)
    proposed_end = models.DateField(null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    cost = models.CharField(max_length=256, null=True, blank=True)
    project_no = models.CharField(max_length=256, null=True, blank=True)
    related_permits = models.TextField(null=True, blank=True)
    over_water = models.BooleanField(default=False)
    records = models.ManyToManyField(Record, blank=True, related_name='records')
    vessels = models.ManyToManyField(Vessel, blank=True)
    vessel_or_craft_details = models.IntegerField(null=True, blank=True)
    purpose = models.ForeignKey(ApplicationPurpose, null=True, blank=True, on_delete=models.CASCADE)
    max_participants = models.IntegerField(null=True, blank=True)
    proposed_location = models.SmallIntegerField(choices=APP_LOCATION_CHOICES, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    location_route_access = models.ManyToManyField(Record, blank=True, related_name='location_route_access')
    jetties = models.TextField(null=True, blank=True)
    jetty_dot_approval = models.BooleanField(default=None, null=True)
    jetty_dot_approval_expiry = models.DateField(null=True, blank=True)
    drop_off_pick_up = models.TextField(null=True, blank=True)
    food = models.BooleanField(default=None, null=True)
    beverage = models.BooleanField(default=None, null=True)
    liquor_licence = models.BooleanField(default=None, null=True)
    byo_alcohol = models.BooleanField(default=None, null=True)
    sullage_disposal = models.TextField(null=True, blank=True)
    waste_disposal = models.TextField(null=True, blank=True)
    refuel_location_method = models.TextField(null=True, blank=True)
    berth_location = models.TextField(null=True, blank=True)
    anchorage = models.TextField(null=True, blank=True)
    operating_details = models.TextField(null=True, blank=True)
    cert_survey = models.ManyToManyField(Record, blank=True, related_name='cert_survey')
    cert_public_liability_insurance = models.ManyToManyField(Record, blank=True, related_name='cert_public_liability_insurace')
    risk_mgmt_plan = models.ManyToManyField(Record, blank=True, related_name='risk_mgmt_plan')
    safety_mgmt_procedures = models.ManyToManyField(Record, blank=True, related_name='safety_mgmt_plan')
    brochures_itineries_adverts = models.ManyToManyField(Record, blank=True, related_name='brochures_itineries_adverts')
    other_relevant_documents = models.ManyToManyField(Record, blank=True, related_name='other_relevant_documents')
    land_owner_consent = models.ManyToManyField(Record, blank=True, related_name='land_owner_consent')
    deed = models.ManyToManyField(Record, blank=True, related_name='deed')
    submitted_by = models.IntegerField(blank=True, null=True)
    river_lease_require_river_lease = models.BooleanField(default=None, null=True, blank=True)
    river_lease_scan_of_application = models.ManyToManyField(Record, blank=True, related_name='river_lease_scan_of_application')
    river_lease_reserve_licence = models.BooleanField(default=None, null=True, blank=True)
    river_lease_application_number = models.CharField(max_length=30, null=True, blank=True)
    proposed_development_current_use_of_land = models.TextField(null=True, blank=True)
    proposed_development_plans = models.ManyToManyField(Record, blank=True, related_name='proposed_development_plans')
    proposed_development_description = models.TextField(null=True, blank=True)
    document_draft = models.ManyToManyField(Record, blank=True, related_name='document_draft')
    document_new_draft = models.ManyToManyField(Record, blank=True, related_name='document_newdraft')
    document_new_draft_v3 = models.ManyToManyField(Record, blank=True, related_name='document_newdraftv3')
    document_draft_signed = models.ManyToManyField(Record, blank=True, related_name='document_draft_signed')
    document_final = models.ManyToManyField(Record, blank=True, related_name='document_final')
    document_final_signed = models.ManyToManyField(Record, blank=True, related_name='document_final_signed')
    document_determination = models.ManyToManyField(Record, blank=True, related_name='document_determination')
    document_completion = models.ManyToManyField(Record, blank=True, related_name='document_completion')
    publish_documents = models.DateField(null=True, blank=True)
    publish_documents_expiry = models.DateTimeField(blank=True, null=True)
    publish_draft_report = models.DateField(null=True, blank=True)
    publish_draft_expiry = models.DateTimeField(blank=True, null=True)
    publish_final_report = models.DateField(null=True, blank=True)
    publish_final_expiry = models.DateTimeField(blank=True, null=True)
    publish_determination_report = models.DateField(null=True, blank=True)
    routeid = models.CharField(null=True, blank=True, default=1, max_length=4)
    assessment_start_date = models.DateField(null=True, blank=True)
    group = models.ForeignKey(SystemGroup, null=True, blank=True, related_name='application_group_assignment', on_delete=models.CASCADE)
    swan_river_trust_board_feedback = models.ManyToManyField(Record, blank=True, related_name='document_swan_river_board_feedback')
    document_memo = models.ManyToManyField(Record, blank=True, related_name='document_memo')
    document_memo_2 = models.ManyToManyField(Record, blank=True, related_name='document_memo_2')
    document_briefing_note = models.ManyToManyField(Record, blank=True, related_name='document_briefing_note')
    document_determination_approved = models.ManyToManyField(Record, blank=True, related_name='document_determination_approved')
    approval_id = models.IntegerField(null=True, blank=True)
    assessed_by = models.IntegerField(blank=True, null=True)
    supporting_info_demonstrate_compliance_trust_policies = models.ManyToManyField(Record, blank=True, related_name='supporting_info_demonstrate_compliance_trust_policies')
    type_of_crafts = models.ForeignKey(Craft, null=True, blank=True, related_name='craft', on_delete=models.CASCADE) 
    number_of_crafts  = models.IntegerField(null=True, blank=True)
    route_status = models.CharField(null=True, blank=True, default='Draft', max_length=256)
    submitter_comment = models.TextField(null=True, blank=True, default='', max_length=1000)
    referral_comment = models.TextField(null=True, blank=True, default='', max_length=1000)
    landowner = models.TextField(null=True, blank=True) 
    land_description = models.TextField(null=True, blank=True)
    approval_document = models.ForeignKey(Record, null=True, blank=True, related_name='application_approval_document', on_delete=models.CASCADE)
    approval_document_signed = models.ForeignKey(Record, null=True, blank=True, related_name='application_approval_document_signed', on_delete=models.CASCADE)
    old_application = models.ForeignKey('Application', null=True, blank=True, related_name='application_old_application', on_delete=models.CASCADE)
    old_approval_id = models.IntegerField(null=True, blank=True) 

    def __str__(self):
        return 'Application {}: {} - {} ({})'.format(
            self.pk, self.get_app_type_display(), self.title, self.get_state_display())

    def get_absolute_url(self):
        return reverse('application_detail', args=(self.pk,))

@python_2_unicode_compatible
class ApplicationLicenceFee(models.Model):
    app_type = models.IntegerField(choices=Application.APP_TYPE_CHOICES, blank=True, null=True)
    licence_fee = models.DecimalField(max_digits=8, decimal_places=2, default='0.00', blank=False, null=False)
    start_dt = models.DateTimeField(blank=True, null=True)
    end_dt = models.DateTimeField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)

    def clean(self, *args, **kwargs):
        if self.end_dt < self.start_dt:
              raise ValidationError('End date must be greater than Start Date') 
        if ApplicationLicenceFee.objects.filter(app_type=self.app_type,start_dt__lte=self.start_dt, end_dt__gte=self.start_dt).exclude(pk=self.pk).count() > 0:
              raise ValidationError('Start Date matches existing record.')
        if ApplicationLicenceFee.objects.filter(app_type=self.app_type,start_dt__lte=self.end_dt, end_dt__gte=self.end_dt).exclude(pk=self.pk).count() > 0:
              raise ValidationError('End Date matches existing record.')
        if ApplicationLicenceFee.objects.filter(app_type=self.app_type,start_dt__gte=self.start_dt, end_dt__lte=self.end_dt).exclude(pk=self.pk).count() > 0:
              raise ValidationError('Dates matches existing record.')

class Reason(models.Model):
    text = models.TextField()
    detailRequired = models.BooleanField(default=False)
    editable = models.BooleanField(default=True,editable=False)

    class Meta:
        ordering = ('id',)
        abstract = True

    #def save(self, *args, **kwargs):
    #    if self.mooring_group == None:
    #        raise ValidationError("Mooring Group required, please select from list.")
    #    else:
    #        super(Reason,self).save(*args,**kwargs)

    # Properties
    # ==============================
    def code(self):
        return self.__get_code()

    # Methods
    # ==============================
    def __get_code(self):
        length = len(str(self.id))
        val = '0'
        return '{}{}'.format((val*(4-length)),self.id)

class DiscountReason(Reason):
    pass
    def __str__(self):
        return '{}'.format(self.text)
    

class Booking(models.Model):
    BOOKING_TYPE_CHOICES = (
        (0, 'Reception booking'),
        (1, 'Internet booking'),
        (2, 'Black booking'),
        (3, 'Temporary reservation'),
        (4, 'Cancelled Booking'),
    )

    customer = models.IntegerField(blank=True, null=True)
    details = models.JSONField(null=True, blank=True)
    booking_type = models.SmallIntegerField(choices=BOOKING_TYPE_CHOICES, default=0)
    expiry_time = models.DateTimeField(blank=True, null=True)
    cost_total = models.DecimalField(max_digits=8, decimal_places=2, default='0.00')
    override_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    override_reason = models.ForeignKey('DiscountReason', null=True, blank=True, on_delete=models.CASCADE)
    override_reason_info = models.TextField(blank=True, null=True)
    overridden_by = models.IntegerField(blank=True, null=True)
    application = models.ForeignKey('Application', null=True, on_delete=models.CASCADE)
    send_invoice = models.BooleanField(default=False)
    cancellation_reason = models.TextField(null=True,blank=True)
    cancelation_time = models.DateTimeField(null=True,blank=True)
    confirmation_sent = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.IntegerField(blank=True, null=True)
    canceled_by = models.IntegerField(blank=True, null=True)


class BookingInvoice(models.Model):
    booking = models.ForeignKey(Booking, related_name='invoices', on_delete=models.CASCADE)
    invoice_reference = models.CharField(max_length=50, null=True, blank=True, default='')
    system_invoice = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return 'Booking {} : Invoice #{}'.format(self.id,self.invoice_reference)


@python_2_unicode_compatible
class PublicationFeedback(models.Model):
    PUB_STATES_CHOICES = Choices(
        (1, 'Western Australia', ('Western Australia')),
        (2, 'New South Wales', ('New South Wales')),
        (3, 'Victoria', ('Victoria')),
        (4, 'South Australia', ('South Australia')),
        (5, 'Northern Territory', ('Northern Territory')),
        (6, 'Queensland', ('Queensland')),
        (7, 'Australian Capital Territory', ('Australian Capital Territory')),
        (8, 'Tasmania', ('Tasmania')),
    )

    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    name = models.CharField(max_length=256)
    address = models.CharField(max_length=256)
    suburb = models.CharField(max_length=100)
    state = models.IntegerField(choices=PUB_STATES_CHOICES)
    postcode = models.CharField(max_length=4)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    comments = models.TextField(null=True, blank=True)
    records = models.ManyToManyField(Record, blank=True, related_name='feedback')
    status = models.CharField(max_length=20)

    def __str__(self):
        return 'PublicationFeedback {} ({})'.format(self.pk, self.application)

@python_2_unicode_compatible
class PublicationNewspaper(models.Model):
    """This model represents Application Published in newspapert
    """
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    newspaper = models.CharField(max_length=150)
    records = models.ManyToManyField(Record, blank=True, related_name='newspaper')

    def __str__(self):
        return 'PublicationNewspaper {} ({})'.format(self.pk, self.application)


@python_2_unicode_compatible
class PublicationWebsite(models.Model):
    """This model represents Application Published in Website
    """
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    original_document = models.ForeignKey(Record, blank=True, null=True, related_name='original_document', on_delete=models.CASCADE)
    published_document = models.ForeignKey(Record, blank=True, null=True, related_name='published_document', on_delete=models.CASCADE)

    def __str__(self):
        return 'PublicationWebsite {} ({})'.format(self.pk, self.application)


@python_2_unicode_compatible
class Location(models.Model):
    """This model represents a single spatial location associated with an
    application.
    """
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    lot = models.CharField(max_length=256, null=True, blank=True)
    reserve = models.CharField(max_length=256, null=True, blank=True)
    suburb = models.CharField(max_length=256, null=True, blank=True)
    intersection = models.CharField(max_length=256, null=True, blank=True)
    # TODO: validation related to LGA name (possible FK).
    lga = models.CharField(max_length=256, null=True, blank=True)
    poly = models.PolygonField(null=True, blank=True)
    records = models.ManyToManyField(Record, blank=True)
    # TODO: certificate of title fields (ref. screen 30)
    title_volume = models.CharField(max_length=256, null=True, blank=True)
    folio = models.CharField(max_length=30, null=True, blank=True)
    dpd_number = models.CharField(max_length=30, null=True, blank=True)
    location = models.CharField(max_length=256, null=True, blank=True)  # this seem like it different from street address based on the example form.
    street_number_name = models.CharField(max_length=256, null=True, blank=True)
    local_government_authority = models.CharField(max_length=256, null=True, blank=True)

    def __str__(self):
        return 'Location {} ({})'.format(self.pk, self.application)


@python_2_unicode_compatible
class Referral(models.Model):
    """This model represents a referral of an application to a referee
    (external or internal) for comment/conditions.
    """
    REFERRAL_STATUS_CHOICES = Choices(
        (1, 'referred', ('Referred')),
        (2, 'responded', ('Responded')),
        (3, 'recalled', ('Recalled')),
        (4, 'expired', ('Expired')),
        (5, 'with_admin',('Not Sent'))
    )

    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    referee = models.IntegerField(blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    sent_date = models.DateField(blank=True, null=True)
    period = models.PositiveIntegerField(verbose_name='period (days)')
    expire_date = models.DateField(blank=True, null=True, editable=False)
    response_date = models.DateField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    proposed_conditions = models.TextField(blank=True, null=True)
    records = models.ManyToManyField(Record, blank=True)
    status = models.IntegerField(choices=REFERRAL_STATUS_CHOICES, default=REFERRAL_STATUS_CHOICES.with_admin)

    class Meta:
        unique_together = ('application', 'referee')

    def __str__(self):
        referee = SystemUser.objects.get(ledger_id=self.referee)
        return 'Referral {} to {} ({})'.format(self.pk, referee, self.application)

    def save(self, *args, **kwargs):
        """Override save to set the expire_date field.
        """
        #self.expire_date = self.sent_date + timedelta(days=self.period)
        super(Referral, self).save(*args, **kwargs)


@python_2_unicode_compatible
class Condition(models.Model):
    """This model represents a condition of approval for an application
    (either proposed by a referee or applied by P&W).
    """
    CONDITION_STATUS_CHOICES = Choices(
        (1, 'proposed', ('Proposed')),
        (2, 'applied', ('Applied')),
        (3, 'rejected', ('Rejected')),
        (4, 'cancelled', ('Cancelled')),
    )
    CONDITION_RECUR_CHOICES = Choices(
        (1, 'weekly', ('Weekly')),
        (2, 'monthly', ('Monthly')),
        (3, 'annually', ('Annually')),
    )

    application = models.ForeignKey(Application, on_delete=models.PROTECT)
    condition_no = models.IntegerField(blank=True, null=True)
    condition = models.TextField(blank=True, null=True)
    referral = models.ForeignKey(Referral, null=True, blank=True, on_delete=models.PROTECT)
    status = models.IntegerField(choices=CONDITION_STATUS_CHOICES, default=CONDITION_STATUS_CHOICES.proposed)
    records = models.ManyToManyField(Record, blank=True)
    due_date = models.DateField(blank=True, null=True)
    # Rule: recurrence patterns (if present) begin on the due date.
    recur_pattern = models.IntegerField(choices=CONDITION_RECUR_CHOICES, null=True, blank=True)
    recur_freq = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='recurrence frequency',
        help_text='How frequently is the recurrence pattern applied (e.g. every 2 months)')
    suspend = models.BooleanField(default=False)
    advise_no = models.IntegerField(blank=True, null=True)
    advise = models.TextField(blank=True, null=True)

    def __str__(self):
        return 'Condition {}: {}'.format(self.pk, self.condition)

@python_2_unicode_compatible
class ConditionPredefined(models.Model):
    """This model represents a condition of approval for an application
    (either proposed by a referee or applied by P&W).
    """

    STATUS = Choices(
        (0, 'inactive', ('Inactive')),
        (1, 'active', ('Active')),
    )

    title = models.CharField(max_length=256, null=True, blank=True)
    condition = models.TextField(blank=True, null=True)
    status = models.IntegerField(choices=STATUS, default=1) 

    def __str__(self):
        return self.title


@python_2_unicode_compatible
class ComplianceGroup(models.Model):

    COMPLIANCE_GROUP_STATUS_CHOICES = Choices(
        (1, 'current', ('Current')),
        (2, 'due',('Due')),
        (3, 'future', ('Future')),
        (4, 'approved', ('Approved')),
        (5, 'with_assessor', ('With Assessor')),
        (6, 'with_manager', ('With Manager')),
        (7, 'with_holder', ('With Licence Holder')),
        (8, 'overdue', ('Overdue')),
        (9, 'submitted', ('Submitted'))
    )

    approval_id = models.IntegerField(blank=True, null=True)
    title = models.CharField(max_length=256, blank=True, null=True)
    app_type = models.IntegerField(choices=Application.APP_TYPE_CHOICES, blank=True, null=True)
#    cid = models.ManyToManyField(Compliance, blank=True)
    applicant = models.IntegerField(blank=True, null=True)
    organisation = models.ForeignKey(Organisation, blank=True, null=True, on_delete=models.PROTECT)
    status = models.IntegerField(choices=COMPLIANCE_GROUP_STATUS_CHOICES, default=COMPLIANCE_GROUP_STATUS_CHOICES.future)
    due_date = models.DateField(blank=True, null=True)
    assignee = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return 'Condition Group {}: {}'.format(self.pk, self.title)


@python_2_unicode_compatible
class Compliance(models.Model):
    """This model represents a request for confirmation of fulfilment of the
    requirements for a single condition, based upon supplied evidence.
    """
    COMPLIANCE_STATUS_CHOICES = Choices(
        (1, 'current', ('Current')),
        (2, 'due',('Due')),
        (3, 'future', ('Future')),
        (4, 'approved', ('Approved')),
        (5, 'with_assessor', ('With Assessor')),
        (6, 'with_manager', ('With Manager')),
        (7, 'with_holder', ('With Licence Holder')),
        (8, 'overdue', ('Overdue')),
        (9, 'submitted', ('Submitted'))
    )

    approval_id = models.IntegerField(blank=True, null=True)
    title = models.CharField(max_length=256, blank=True, null=True) 
    app_type = models.IntegerField(choices=Application.APP_TYPE_CHOICES, blank=True, null=True)
    condition = models.ForeignKey(Condition, on_delete=models.PROTECT)
    applicant = models.IntegerField(blank=True, null=True)
    assignee = models.IntegerField(blank=True, null=True)
    organisation = models.ForeignKey(Organisation, blank=True, null=True, on_delete=models.PROTECT) 
    assessed_by = models.IntegerField(blank=True, null=True)
    assessed_date = models.DateField(blank=True, null=True)
    status = models.IntegerField(choices=COMPLIANCE_STATUS_CHOICES, default=COMPLIANCE_STATUS_CHOICES.future)
    submitted_by = models.IntegerField(blank=True, null=True)
    submit_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(blank=True, null=True)
    compliance = models.TextField(blank=True, null=True, help_text='Information to fulfil requirement of condition.')
    external_comments = models.TextField(blank=True, null=True)
    external_documents = models.ManyToManyField(Record, blank=True, related_name='compliance_external_documents')
    comments = models.TextField(blank=True, null=True)
    approve_date = models.DateField(blank=True, null=True)
    records = models.ManyToManyField(Record, blank=True)
    compliance_group = models.ForeignKey(ComplianceGroup, blank=True, null=True, on_delete=models.PROTECT)
    group = models.ForeignKey(Group, null=True, blank=True, related_name='compliance_group_assignment', on_delete=models.CASCADE)

    def __str__(self):
        return 'Compliance {} ({})'.format(self.pk, self.condition)

class Communication(models.Model):
    """This model represents the communication model
    """
    COMM_TYPE = Choices(
        (0, 'none', ('None')),
        (1, 'phone', ('Phone')),
        (2, 'email', ('Email')),
        (3, 'mail', ('Mail')),
        (4, 'system', ('System'))
    )

    application = models.ForeignKey(Application, on_delete=models.PROTECT)
    comms_to = models.CharField(max_length=256, null=True, blank=True)
    comms_from = models.CharField(max_length=256, null=True, blank=True)
    subject = models.CharField(max_length=256, null=True, blank=True)
    comms_type = models.IntegerField(choices=COMM_TYPE, default=COMM_TYPE.none )
    details = models.TextField(blank=True, null=True)
    records = models.ManyToManyField(Record, blank=True, related_name='communication_docs')
    state = models.IntegerField(blank=True, null=True)  # move to foreign key once APP_STATE_CHOICES becomes a model
    created = models.DateTimeField(auto_now_add=True)


class CommunicationAccount(models.Model):
    """This model represents the communication model
    """
    COMM_TYPE = Choices(
        (0, 'none', ('None')),
        (1, 'phone', ('Phone')),
        (2, 'email', ('Email')),
        (3, 'mail', ('Mail')),
    )

    user = models.IntegerField(null=True)
    comms_to = models.CharField(max_length=256, null=True, blank=True)
    comms_from = models.CharField(max_length=256, null=True, blank=True)
    subject = models.CharField(max_length=256, null=True, blank=True)
    comms_type = models.IntegerField(choices=COMM_TYPE, default=COMM_TYPE.none)
    details = models.TextField(blank=True, null=True)
    records = models.ManyToManyField(Record, blank=True, related_name='account_communication_docs')
    state = models.IntegerField(blank=True, null=True)  # move to foreign key once APP_STATE_CHOICES becomes a model
    created = models.DateTimeField(auto_now_add=True)

class CommunicationOrganisation(models.Model):
    """This model represents the communication model
    """
    COMM_TYPE = Choices(
        (0, 'none', ('None')),
        (1, 'phone', ('Phone')),
        (2, 'email', ('Email')),
        (3, 'mail', ('Mail')),
    )

    org = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    comms_to = models.CharField(max_length=256, null=True, blank=True)
    comms_from = models.CharField(max_length=256, null=True, blank=True)
    subject = models.CharField(max_length=256, null=True, blank=True)
    comms_type = models.IntegerField(choices=COMM_TYPE, default=COMM_TYPE.none)
    details = models.TextField(blank=True, null=True)
    records = models.ManyToManyField(Record, blank=True, related_name='org_communication_docs')
    state = models.IntegerField(blank=True, null=True)  # move to foreign key once APP_STATE_CHOICES becomes a model
    created = models.DateTimeField(auto_now_add=True)

class CommunicationCompliance(models.Model):
    """This model represents the communication model
    """
    COMM_TYPE = Choices(
        (0, 'none', ('None')),
        (1, 'phone', ('Phone')),
        (2, 'email', ('Email')),
        (3, 'mail', ('Mail')),
    )

    compliance = models.ForeignKey(Compliance, on_delete=models.PROTECT)
    comms_to = models.CharField(max_length=256, null=True, blank=True)
    comms_from = models.CharField(max_length=256, null=True, blank=True)
    subject = models.CharField(max_length=256, null=True, blank=True)
    comms_type = models.IntegerField(choices=COMM_TYPE, default=COMM_TYPE.none)
    details = models.TextField(blank=True, null=True)
    records = models.ManyToManyField(Record, blank=True, related_name='compliance_communication_docs')
    state = models.IntegerField(blank=True, null=True)  # move to foreign key once APP_STATE_CHOICES becomes a model
    created = models.DateTimeField(auto_now_add=True)


@python_2_unicode_compatible
class Delegate(models.Model):
    """This model represents the delegation of authority for an EmailUser to
    submit applications on behalf of an Organisation, within the Statutory
    Development application.
    """
    email_user = models.IntegerField(blank=False, null=True)
    organisation = models.ForeignKey(Organisation, blank=False, on_delete=models.PROTECT)
    
    def __str__(self):
        email = SystemUser.objects.get(ledger_id = self.email_user)
        return '{}: {}'. format(email, self.organisation.name)

    class Meta:
        unique_together = ('email_user', 'organisation')

@python_2_unicode_compatible
class OrganisationContact(models.Model):
    """This model represents the contact people within the organisation for this application.
    """
    email = models.EmailField(unique=False, blank=False)
    first_name = models.CharField(max_length=128, blank=True, verbose_name='Given name(s)')
    last_name = models.CharField(max_length=128, blank=True)
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    mobile_number = models.CharField(max_length=50, null=True, blank=True)
    fax_number = models.CharField(max_length=50, null=True, blank=True)
    organisation = models.ForeignKey(Organisation, blank=False, null=True, on_delete=models.PROTECT)

    def __str__(self):
        return '{}: {}'. format(self.first_name, self.last_name, self.email)


@python_2_unicode_compatible
class OrganisationPending(models.Model):
    """This model represents the contact people within the organisation for this application.
    """

    STATUS_CHOICES = Choices(
        (1, 'pending', ('Pending')),
        (2, 'approve',('Approved')),
        (3, 'decline', ('Declined'))
    )

    name = models.CharField(max_length=128,  null=True, blank=True)
    abn = models.CharField(max_length=50, null=True, blank=True, verbose_name='ABN')
    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_CHOICES.pending)
    identification = models.ForeignKey(Record, null=True, blank=True, on_delete=models.SET_NULL)
    #identification = models.ManyToManyField(Record, blank=True, related_name='Identification Documents')
    postal_address = models.ForeignKey(OrganisationAddress, related_name='org_pending_postal_address', blank=True, null=True, on_delete=models.SET_NULL)
    billing_address = models.ForeignKey(OrganisationAddress, related_name='org_pending_billing_address', blank=True, null=True, on_delete=models.SET_NULL)
    email_user = models.IntegerField(blank=False, null=True)
    assignee = models.IntegerField(blank=True, null=True)
    company_exists = models.BooleanField(default=False)
    submit_date = models.DateField(auto_now_add=True, null=True, blank=True)
    pin1 = models.CharField(max_length=50, null=True, blank=True)
    pin2 = models.CharField(max_length=50, null=True, blank=True)


    def __str__(self):
        return '{}: {}'. format(self.name,self.abn, self.status)


@python_2_unicode_compatible
class OrganisationExtras(models.Model):
    organisation = models.ForeignKey(Organisation, blank=False, null=True, on_delete=models.PROTECT, related_name='organisation_extras_org_id')
    pin1 = models.CharField(max_length=50, null=True, blank=True)
    pin2 = models.CharField(max_length=50, null=True, blank=True)
    identification = models.ForeignKey(Record, null=True, blank=True, on_delete=models.SET_NULL, related_name='organisation_extras_org_identification')

    def __str__(self):
        return '{}: {}'. format(self.pk,self.organisation.name,)


@python_2_unicode_compatible
class ApplicationInvoice(models.Model):
    """This model represents a reference to an invoice for payment raised against
    an application.
    """
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    invoice_reference = models.CharField(max_length=64)

    def __str__(self):
        return 'Application {} invoice {}'.format(self.application, self.invoice_reference)

@python_2_unicode_compatible
class StakeholderComms(models.Model):
    """This model represents a reference to the stakeholder communication for 
    an application.
    """
    STAKEHOLDER_ROLE_TYPE = Choices(
        (0, 'none', ('None')),
        (1, 'applicant', ('Applicant')),
        (2, 'submitter', ('Submitter')),
        (3, 'referral', ('Referral')),
        (4, 'feedback', ('Feedback'))
    )

    STAKEHOLDER_COMM_TYPE = Choices(
        (0, 'none', ('None')),
        (1, 'email', ('Email')),
        (2, 'posted', ('Posted')),
    )

    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    email = models.EmailField(unique=False, blank=False)
    name = models.CharField(max_length=255)
    sent_date = models.DateTimeField(auto_now_add=True)
    role = models.IntegerField(choices=STAKEHOLDER_ROLE_TYPE, default=STAKEHOLDER_ROLE_TYPE.none) 
    comm_type = models.IntegerField(choices=STAKEHOLDER_COMM_TYPE, default=STAKEHOLDER_COMM_TYPE.none)

    def __str__(self):
        return 'Stakeholder {} Sent {}'.format(self.name, self.sent_date)

