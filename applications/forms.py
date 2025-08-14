from __future__ import unicode_literals
from django.urls import reverse
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML, Fieldset, MultiField, Div
from crispy_forms.bootstrap import FormActions, InlineRadios
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.forms import Form, ModelForm, ChoiceField, FileField, CharField, Textarea, ClearableFileInput, HiddenInput, Field, RadioSelect, ModelChoiceField, Select, FileInput
from applications.widgets import ClearableMultipleFileInput, RadioSelectWithCaptions, AjaxFileUploader
from multiupload.fields import MultiFileField
from .crispy_common import crispy_heading, crispy_para_with_label, crispy_box, crispy_empty_box, crispy_para, crispy_para_red, check_fields_exist, crispy_button_link, crispy_button, crispy_para_no_label, crispy_h1, crispy_h2, crispy_h3,crispy_h4,crispy_h5,crispy_h6, crispy_alert
from ledger_api_client.ledger_models import EmailUserRO as EmailUser, Address, Document
from ledger_api_client.managed_models import SystemUser, SystemUserAddress, SystemGroup
from .models import (
    Application, Referral, Condition, Compliance, Vessel, Record, PublicationNewspaper,
    PublicationWebsite, PublicationFeedback, Delegate, Communication, Organisation, OrganisationAddress, OrganisationContact, OrganisationPending, CommunicationAccount, CommunicationOrganisation,OrganisationExtras, CommunicationCompliance, ConditionPredefined)
#from ajax_upload.widgets import AjaxClearableFileInput
from django_countries.fields import CountryField
from django_countries.data import COUNTRIES
from model_utils import Choices

from django import forms

User = get_user_model()



class BaseFormHelper(FormHelper):
    form_class = 'form-horizontal'
    label_class = 'col-xs-12 col-sm-4 col-md-3 col-lg-2'
    field_class = 'col-xs-12 col-sm-8 col-md-6 col-lg-4'

class FullBaseFormHelper(FormHelper):
    form_class = 'form-horizontal'
    label_class = 'col-xs-12 col-sm-4 col-md-3 col-lg-2'
    field_class = 'col-xs-12 col-sm-8 col-md-9 col-lg-10'

class ButtonBaseFormHelper(FormHelper):
    form_class = 'form-horizontal'
    label_class = 'col-xs-0 col-sm-0 col-md-0 col-lg-0'
    field_class = 'col-xs-12 col-sm-12 col-md-12 col-lg-12'


class PopupFormHelper(FormHelper):
    form_class = 'form-horizontal popup-form'
    label_class = 'col-xs-12 col-sm-4 col-md-3 col-lg-3'
    field_class = 'col-xs-12 col-sm-8 col-md-6 col-lg-6'

class ApplicationCreateForm(ModelForm):

    class Meta:
        model = Application
        fields = ['app_type']

    def __init__(self, *args, **kwargs):
        # User must be passed in as a kwarg.
        user = kwargs.pop('user')
        super(ApplicationCreateForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()

        app_type = None
        if 'app_type' in self.initial:
            app_type = self.initial['app_type']
            if app_type == 4:
                self.fields['app_type'].widget.attrs['disabled'] = True

        self.helper.form_id = 'id_form_create_application'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('create', 'Create', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))

        # Limit the organisation queryset unless the user is a superuser.
        #if not user.is_superuser:
            #user_orgs = [d.pk for d in Delegate.objects.filter(email_user=user)]
            #self.fields['organisation'].queryset = Organisation.objects.filter(pk__in=user_orgs)
        #self.fields['organisation'].help_text = '''The company or organisation
            #on whose behalf you are applying (leave blank if not applicable).'''

        # Add labels for fields
        self.fields['app_type'].label = "Application Type"

class ApplicationApplyForm(ModelForm):
    apply_on_behalf_of = ChoiceField(choices=Application.APP_APPLY_ON ,widget=RadioSelect(attrs={'class':'radio-inline'}))

    class Meta:
        model = Application
        fields = ['apply_on_behalf_of']

    def __init__(self, *args, **kwargs):
        # User must be passed in as a kwarg.
        user = kwargs.pop('user')
        super(ApplicationApplyForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()
        # delete internal option
        # print("Original choices:", self.fields['apply_on_behalf_of'].choices)
        # del self.fields['apply_on_behalf_of'].choices[4]

        # # Delete on behalf of indivdual or company (Future development)
        # # These two lines delete option id 3 and 4 from models.Application.APP_APPLY_ON 
        # # The lines below are duplicated for purpose :)
        # del self.fields['apply_on_behalf_of'].choices[2]
        # del self.fields['apply_on_behalf_of'].choices[2]
        # print("After deleting:", self.fields['apply_on_behalf_of'].choices)
        
        
        # delete internal option
        # Delete on behalf of indivdual or company (Future development)
        self.fields['apply_on_behalf_of'].choices = [
            choice for choice in self.fields['apply_on_behalf_of'].choices
            if choice[0] not in [3,4,5]
        ]

        crispy_boxes = crispy_empty_box()
        self.helper.form_show_labels = False
        crispy_boxes.append(crispy_box('on_behalf_collapse','form_on_behalf','Apply on behalf of',crispy_h3("Do you want to apply"),'apply_on_behalf_of' ))
        self.helper.layout = Layout(crispy_boxes,)

        self.helper.form_id = 'id_form_apply_application'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('Continue', 'Continue', css_class='btn-lg'))


class PaymentDetailForm(ModelForm):

    class Meta:
        model = Application
        fields = ['id',]

    def __init__(self, *args, **kwargs):
        # User must be passed in as a kwarg.
        super(PaymentDetailForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()
        # delete internal option
        crispy_boxes = crispy_empty_box()
        #self.helper.form_show_labels = False

        #crispy_boxes.append(crispy_h3("Do you want to apply"),)
        self.helper.layout = Layout(crispy_boxes,)

        self.helper.form_id = 'id_form_payment_details'
        self.helper.attrs = {'novalidate': ''}
        self.helper.layout = Layout(HTML("{% include 'applications/application_payment_details_form_price_override.html' %}"),)
        self.helper.add_input(Submit('Proceed to Payment', 'Proceed to Payment', css_class='btn-lg'))

class CreateAccountForm(ModelForm):

    class Meta:
        model = SystemUser 
        fields = ['email']

    def __init__(self, *args, **kwargs):
        # User must be passed in as a kwarg.
        super(CreateAccountForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()
        # delete internal option
        crispy_boxes = crispy_empty_box()
        #self.helper.form_show_labels = False

        self.fields['email'].label = "Email Address:"
        crispy_boxes.append(crispy_box('new_account_collapse','form_new_account','Please enter email address','email' ))
        self.helper.layout = Layout(crispy_boxes,)

        self.helper.form_id = 'id_form_new_account'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('Continue', 'Continue', css_class='btn-lg'))

class OrganisationAddressForm(ModelForm):
    postal_line1 = CharField(required=False,max_length=255)
    postal_line2 = CharField(required=False, max_length=255)
    postal_line3 = CharField(required=False, max_length=255)
    postal_locality = CharField(required=False, max_length=255, label='Town/Suburb')
    postal_postcode = CharField(required=False, max_length=10)
    postal_state = ChoiceField(required=False, choices=Address.STATE_CHOICES)
    postal_country = ChoiceField(choices=sorted(COUNTRIES.items()), required=False)

    billing_line1 = CharField(required=False,max_length=255)
    billing_line2 = CharField(required=False, max_length=255)
    billing_line3 = CharField(required=False, max_length=255)
    billing_locality = CharField(required=False, max_length=255, label='Town/Suburb')
    billing_postcode = CharField(required=False, max_length=10)
    billing_state = ChoiceField(required=False, choices=Address.STATE_CHOICES)
    billing_country = ChoiceField(choices=sorted(COUNTRIES.items()), required=False)

    class Meta:
        model = OrganisationAddress
        fields = ['postal_line1']

    def __init__(self, *args, **kwargs):
        super(OrganisationAddress, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()

        crispy_boxes = crispy_empty_box()

        crispy_boxes.append(crispy_box('postal_information_collapse','form_postal_informtion','Enter Postal Information','postal_line1','postal_line2','postal_line3','postal_locality','postal_postcode','postal_state','postal_country'))
        crispy_boxes.append(crispy_box('billing_information_collapse','form_billing_information','Enter Billing Information','billing_line1','billing_line2','billing_line3','billing_locality','billing_postcode','billing_state','billing_country'))


        self.helper.layout = Layout(crispy_boxes,)
        self.helper.form_id = 'id_form_apply_application'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('Continue', 'Continue', css_class='btn-lg'))


class CreateLinkCompanyForm(ModelForm):
    company_name = CharField(required=False,max_length=255)
    abn = CharField(required=False,max_length=255)
    pin1 = CharField(max_length=50, required=False)
    pin2 = CharField(max_length=50, required=False)
    identification = FileField(required=False, max_length=128, widget=ClearableFileInput)

    postal_line1 = CharField(required=False,max_length=255)
    postal_line2 = CharField(required=False, max_length=255)
    postal_line3 = CharField(required=False, max_length=255)
    postal_locality = CharField(required=False, max_length=255, label='Town/Suburb')
    postal_postcode = CharField(required=False, max_length=10)
    postal_state = ChoiceField(required=False, choices=Address.STATE_CHOICES)
    postal_country = ChoiceField(choices=sorted(COUNTRIES.items()), required=False)

    billing_line1 = CharField(required=False,max_length=255)
    billing_line2 = CharField(required=False, max_length=255)
    billing_line3 = CharField(required=False, max_length=255)
    billing_locality = CharField(required=False, max_length=255, label='Town/Suburb')
    billing_postcode = CharField(required=False, max_length=10)
    billing_state = ChoiceField(required=False, choices=Address.STATE_CHOICES)
    billing_country = ChoiceField(choices=sorted(COUNTRIES.items()), required=False)
    company_exists = CharField(required=False,widget=HiddenInput()) 
    company_id = CharField(required=False,max_length=255,widget=HiddenInput())

    class Meta:
        model = SystemUser
        fields = ['first_name']

    def __init__(self, *args, **kwargs):
        super(CreateLinkCompanyForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()
        step = self.initial['step']
        #step = self.initial['step']
        #self.fields['country'].required = False
        del self.fields['first_name']
        crispy_boxes = crispy_empty_box()

        if step == '1':
            crispy_boxes.append(crispy_box('company_create_link_collapse','form_company_create_link','Enter Company Information','company_name','abn' ))
            self.fields['company_name'].required = True
            self.fields['abn'].required = True
        elif step == '2':
            #print self.request['POST'].get
            #print Organisation.objects.get(abn=)
            #print self.initial['company_exists']
            if self.initial['company_exists'] == 'yes':
                crispy_boxes.append(crispy_box('pins_collapse','form_pins','Please Enter Pins',crispy_h3("Please enter company pins?"),'pin1','pin2','company_exists','company_id' ,crispy_para_no_label('The following people can provide pins for this organisation:'), crispy_para_no_label(str(self.initial['company_delegates']))))
                self.fields['pin1'].required = True
                self.fields['pin2'].required = True
            else:
                self.fields['identification'].required = True
                crispy_boxes.append(crispy_box('ident_collapse','form_ident','Certificate of Incorporation',crispy_h3("Please provide certificate of incorporation?"),'identification' ))
                self.fields['identification'].label = "Incorporation Certificate"
        elif step == '3':
            crispy_boxes.append(crispy_box('postal_information_collapse','form_postal_informtion','Enter Postal Information','postal_line1','postal_line2','postal_line3','postal_locality','postal_postcode','postal_state','postal_country'))
            crispy_boxes.append(crispy_box('billing_information_collapse','form_billing_information','Enter Billing Information','billing_line1','billing_line2','billing_line3','billing_locality','billing_postcode','billing_state','billing_country'))
        elif step == '4':
            if self.initial['company_exists'] == 'yes':
                  crispy_boxes.append(crispy_box('company_complete_collapse','form_complete_company','Complete',crispy_para_no_label('To complete your company access request, please click complete.')))
            else:
                  crispy_boxes.append(crispy_box('company_complete_collapse','form_complete_company','Complete',crispy_para_no_label('To complete your company access request, please click complete.  This will place your request in a queue pending approval.')))

        self.helper.layout = Layout(crispy_boxes,)
        self.helper.form_id = 'id_form_apply_application'
        self.helper.attrs = {'novalidate': ''}
#        self.helper.add_input(Submit('Continue', 'Continue', css_class='btn-lg'))
        if step == '4':
            self.helper.add_input(Submit('Prev Step', 'Prev Step', css_class='btn-lg'))
            self.helper.add_input(Submit('Complete', 'Complete', css_class='btn-lg'))
        else:
            if int(step) > 1:
                self.helper.add_input(Submit('Prev Step', 'Prev Step', css_class='btn-lg'))
            self.helper.add_input(Submit('Next Step', 'Next Step', css_class='btn-lg'))
#TODO remove this
# class FirstLoginInfoForm(ModelForm):
#     BOOL_CHOICES = ((True, 'Yes'), (False, 'No'))
#     identification2 = FileField(required=False, max_length=128, widget=ClearableFileInput)
#     line1 = CharField(required=False,max_length=255)
#     line2 = CharField(required=False, max_length=255)
#     line3 = CharField(required=False, max_length=255)
#     locality = CharField(required=False, max_length=255, label='Town/Suburb')
#     postcode = CharField(required=False, max_length=10)
#     state = ChoiceField(required=False, choices=Address.STATE_CHOICES)
#     country = ChoiceField(choices=sorted(COUNTRIES.items()), required=False)
#     manage_permits = ChoiceField(label='Do you manage licences, permits or Part 5 on behalf of a company?', required=False,choices=BOOL_CHOICES, widget=RadioSelect(attrs={'class':'radio-inline'}))

#     class Meta:
#         model = EmailUser 
#         fields = ['first_name','last_name','dob','phone_number','mobile_number','email']

#     def __init__(self, *args, **kwargs):
#         # User must be passed in as a kwarg.
#         # user = kwargs.pop('user')
#         super(FirstLoginInfoForm, self).__init__(*args, **kwargs)
#         self.helper = BaseFormHelper()
#         step = '1'
#         if 'step' in self.initial:
#             step = self.initial['step']
#         self.fields['country'].required = False
#         # delete internal option
#         crispy_boxes = crispy_empty_box()
#         #  self.helper.form_show_labels = False

#         if step == '1':
#             crispy_boxes.append(crispy_box('person_details_collapse','person_details','Personal Details','first_name','last_name','dob'))
#             self.fields['first_name'].required = True
#             self.fields['last_name'].required = True
#             self.fields['dob'].required = True

#             del self.fields['identification2']
#             del self.fields['phone_number']
#             del self.fields['mobile_number']
#             del self.fields['email']

#         elif step == '2':
#             #self.initial['identification2'].initial_text = "JASON "
#             #self.initial['identification2'].attr.url = '/jason/test'
#             #print (self.fields['identification2'].widget.is_initial((self.fields['identification2'])))
#             #print (self.fields['identification2'].value = setUrl('JASON TEST URL', " DEFAULT VALUE"))
        

#             #self.initial['identification2'].value = {'url' : '/jason/test'}

#             identification_img = None
#             if  'identification2' in self.initial:
#                  id_name = self.initial['identification2']
#                  att_ext = str(id_name)[-4:].lower()
#                  if att_ext in ['.png','.jpg']:
#                      identification_img = HTML("<label for='id_identification' class='control-label col-xs-12 col-sm-4 col-md-3 col-lg-2 requiredField'>Identification Image<span class='asteriskField'>*</span> </label><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4'><img style='max-width: 400px;' src='/private-ledger/view/"+str(self.initial['identification2'])+"' ></div>")


#             crispy_boxes.append(crispy_box('identification_collapse','identification_details','Identification','identification2',identification_img))
#             self.fields['identification2'].required = True
#             del self.fields['first_name']
#             del self.fields['last_name']
#             del self.fields['dob']
#             del self.fields['phone_number']
#             del self.fields['mobile_number']
#             del self.fields['email']
#         elif step == '3':
#             crispy_boxes.append(crispy_box('address_collapse','address_details','Address','line1','line2','line3','locality','postcode','state','country'))
#             self.fields['line1'].required = True
#             self.fields['line2'].required = False
#             self.fields['line3'].required = False 
#             self.fields['locality'].required = True
#             self.fields['postcode'].required = True
#             self.fields['state'].required = True
#             self.fields['country'].required = True

#             del self.fields['first_name']
#             del self.fields['last_name']
#             del self.fields['dob']
#             del self.fields['identification2']
#             del self.fields['phone_number']
#             del self.fields['mobile_number']
#             del self.fields['email']
#         elif step == '4':
#             crispy_boxes.append(crispy_box('contact_details_collapse','contact_details','Contact Details','phone_number','mobile_number','email'))
#             self.fields['phone_number'].required = False 
#             self.fields['mobile_number'].required = False 
#             self.fields['email'].required = False
#             self.fields['email'].disabled = True

#             del self.fields['first_name']
#             del self.fields['last_name']
#             del self.fields['dob']
#             del self.fields['identification2']
#         elif step == '5':
#             crispy_boxes.append(crispy_box('company_details_collapse','company_details','Company Details','manage_permits'))
#             del self.fields['first_name']
#             del self.fields['last_name']
#             del self.fields['dob']
#             del self.fields['identification2']
#             del self.fields['phone_number']
#             del self.fields['mobile_number']
#             del self.fields['email']
#         else:
#             del self.fields['first_name'] 
#             del self.fields['last_name']
#             del self.fields['dob']
#             del self.fields['identification2']
#             del self.fields['phone_number']
#             del self.fields['mobile_number']
#             del self.fields['email']

#         self.helper.layout = Layout(crispy_boxes,)

#         self.helper.form_id = 'id_form_apply_application'
#         self.helper.attrs = {'novalidate': ''}
#         if step == '5':
#             self.helper.add_input(Submit('Prev Step', 'Prev Step', css_class='btn-lg'))
#             self.helper.add_input(Submit('Complete', 'Complete', css_class='btn-lg'))
#         else:
#             if int(step) > 1:
#                 self.helper.add_input(Submit('Prev Step', 'Prev Step', css_class='btn-lg'))
#             self.helper.add_input(Submit('Next Step', 'Next Step', css_class='btn-lg'))

 

class ApplicationApplyUpdateForm(ModelForm):

    apply_on_behalf_of = ChoiceField(choices=Application.APP_APPLY_ON ,widget=RadioSelect(attrs={'class':'radio-inline'}))
    app_type = ChoiceField(choices=Application.APP_TYPE_CHOICES,
            widget=RadioSelectWithCaptions(
                attrs={'class':'radio-inline'}, 
                caption={'caption-2':'Apply for a licence and permit to undertake an activity within the Swan Canning Riverpark etc.', 
                         'caption-1':'Apply for permit to carry out works or, activities within the Riverpark', 
                         'caption-3':'Apply for development approval in accordance with Part 5 of the <i>Swan and Canning Rivers Management Act 2006</i>', 
                         'caption-4': 'Issue an emergency works'
                         } 
                 
                ))
    #organisation = ModelChoiceField(queryset=None, empty_label=None, widget=RadioSelect(attrs={'class':'radio-inline'}))

    # Indivdual & Company
    applicant_company_given_names = CharField(max_length=256, required=False)
    applicant_company_surname = CharField(max_length=256, required=False)
    applicant_company_dob = CharField(max_length=256, required=False)
    applicant_company_email = CharField(max_length=256, required=False)

    # Company only
    applicant_company = CharField(max_length=256, required=False)
    applicant_abn = CharField(max_length=256, required=False)

    class Meta:
        model = Application
        fields = ['apply_on_behalf_of','app_type','organisation']

    def __init__(self, *args, **kwargs):
        # User must be passed in as a kwarg.
        #user = kwargs.pop('user')
        super(ApplicationApplyUpdateForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()
        self.helper.field_class = 'col-xs-12 col-sm-8 col-md-6 col-lg-6'
        APP_TYPE_CHOICES = [] 
        # print Application.APP_APPLY_ON

        action = self.initial['action']
        self.fields['organisation'].choices = self.initial['organisations_list']
        if action == 'new':
            crispy_boxes = crispy_empty_box()
            self.helper.form_show_labels = False
            crispy_boxes.append(crispy_box('on_behalf_collapse','form_on_behalf','Apply on behalf of',crispy_h3("Do you want to apply"),'apply_on_behalf_of' ))
         #   self.helper.layout = Layout(crispy_boxes,)
        elif action == 'apptype':
            del self.fields['applicant_company_given_names']
            del self.fields['applicant_company_surname']
            del self.fields['applicant_company_dob']
            del self.fields['applicant_company_email']
            del self.fields['applicant_company']
            del self.fields['applicant_abn']
            del self.fields['apply_on_behalf_of']
            del self.fields['organisation']

            self.fields['app_type'].label = ''

            for i in Application.APP_TYPE_CHOICES:
                if i[0] in [5,6,7,8,9,10,11]:
                    skip = 'yes'
                else:
                    if i[0] == 4:
                        if self.initial['is_staff'] is True:
                            APP_TYPE_CHOICES.append(i)

                    else:
                        APP_TYPE_CHOICES.append(i)
            self.fields['app_type'].choices = APP_TYPE_CHOICES

            crispy_boxes = crispy_empty_box()
            crispy_boxes.append(crispy_box('apply_for_collapse','form_apply_for','Apply for',crispy_h3("Do you want to apply for"),'app_type',crispy_para_no_label("Unsure which application you require Click Here")))
        else:
            apply_on_behalf_of = self.initial['apply_on_behalf_of']
            del self.fields['app_type']
            del self.fields['apply_on_behalf_of']

            del self.fields['applicant_company_given_names']
            del self.fields['applicant_company_surname']
            del self.fields['applicant_company_dob']
            del self.fields['applicant_company_email']
            del self.fields['applicant_company']
            del self.fields['applicant_abn']

            if apply_on_behalf_of == 3:
                del self.fields['organisation']
                crispy_boxes = crispy_empty_box()
                crispy_boxes.append(crispy_box('on_behalf_indivdual_collapse','form_on_behalf_indivdual','Apply on behalf of indivdual',crispy_h3("Please Complete:"),'applicant_company_given_names','applicant_company_surname','applicant_company_dob','applicant_company_email'))
                self.helper.layout = Layout(crispy_boxes,)
            elif apply_on_behalf_of == 2:
                self.helper.form_show_labels = False
                crispy_boxes = crispy_empty_box()
                crispy_boxes.append(crispy_box('choose_organisation_collapse','form_choose_organisation','Choose Company / Organisation',crispy_h3("Please choose a company / government agency."),'organisation'))
            elif apply_on_behalf_of == 4:
                del self.fields['organisation']
                crispy_boxes = crispy_empty_box()
                crispy_boxes.append(crispy_box('on_behalf_indivdual_collapse','form_on_behalf_indivdual','Apply on behalf of company',crispy_h3("Please Complete"),'applicant_company','applicant_abn','applicant_company_given_names','applicant_company_surname','applicant_company_dob','applicant_company_email'))

        self.helper.layout = Layout(crispy_boxes,)
        self.helper.form_id = 'id_form_apply_application'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('Continue', 'Continue', css_class='btn-lg'))

class CommunicationCreateForm(ModelForm):
#    records = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}),  label='Documents')
    records = Field(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}),  label='Documents', help_text='')
    #attach_to_email = Field(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}),  label='Attach to Email', help_text='')

    class Meta:
        model = Communication 
        fields = ['comms_to','comms_from','subject','comms_type','details','records','details']

    def __init__(self, *args, **kwargs):
        # User must be passed in as a kwarg.
        user = kwargs.pop('user')
        #application = kwargs.pop('application')
        super(CommunicationCreateForm, self).__init__(*args, **kwargs)

        # Werid just deleting the option doesn't from the array doesn't update the array..
        del self.fields['comms_type'].choices[4]
        # because just a delete doesn't update  the array.  Have to do this line as well to update the choices list.
        self.fields['comms_type'].choices = self.fields['comms_type'].choices

        self.fields['comms_to'].required = True
        self.fields['comms_from'].required = True
        self.fields['subject'].required = True
        self.fields['comms_type'].required = True

        self.helper = BaseFormHelper()
        self.helper.form_id = 'id_form_create_communication'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('save', 'Create', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))
        # Add labels for fields
        #self.fields['app_type'].label = "Application Type"

class CommunicationOrganisationCreateForm(ModelForm):
    records = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}),  label='Documents')

    class Meta:
        model = CommunicationOrganisation
        fields = ['comms_to','comms_from','subject','comms_type','details','records','details']

    def __init__(self, *args, **kwargs):
        # User must be passed in as a kwarg.
        user = kwargs.pop('user')
        #application = kwargs.pop('application')
        super(CommunicationOrganisationCreateForm, self).__init__(*args, **kwargs)

        self.fields['comms_to'].required = True
        self.fields['comms_from'].required = True
        self.fields['subject'].required = True
        self.fields['comms_type'].required = True

        self.helper = BaseFormHelper()
        self.helper.form_id = 'id_form_create_communication'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('save', 'Create', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))
        # Add labels for fields
        #self.fields['app_type'].label = "Application Type"

class CommunicationAccountCreateForm(ModelForm):
    #records = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}),  label='Documents')
    records = Field(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}),  label='Documents', help_text='')

    class Meta:
        model = CommunicationAccount 
        fields = ['comms_to','comms_from','subject','comms_type','details','records','details']

    def __init__(self, *args, **kwargs):
        # User must be passed in as a kwarg.
        user = kwargs.pop('user')
        #application = kwargs.pop('application')
        super(CommunicationAccountCreateForm, self).__init__(*args, **kwargs)

        self.fields['comms_to'].required = True
        self.fields['comms_from'].required = True
        self.fields['subject'].required = True
        self.fields['comms_type'].required = True

        self.helper = BaseFormHelper()
        self.helper.form_id = 'id_form_create_communication'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('save', 'Create', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))
        # Add labels for fields
        #self.fields['app_type'].label = "Application Type"

class CommunicationComplianceCreateForm(ModelForm):
    records = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}),  label='Documents')

    class Meta:
        model = CommunicationCompliance
        fields = ['comms_to','comms_from','subject','comms_type','details','records','details']

    def __init__(self, *args, **kwargs):
        # User must be passed in as a kwarg.
        user = kwargs.pop('user')
        #application = kwargs.pop('application')
        super(CommunicationComplianceCreateForm, self).__init__(*args, **kwargs)

        self.fields['comms_to'].required = True
        self.fields['comms_from'].required = True
        self.fields['subject'].required = True
        self.fields['comms_type'].required = True

        self.helper = BaseFormHelper()
        self.helper.form_id = 'id_form_create_communication'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('save', 'Create', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))
        # Add labels for fields
        #self.fields['app_type'].label = "Application Type"

class OrganisationAccessRequestForm(ModelForm):
    details = CharField(required=False, widget=Textarea, help_text='Details for communication log.')

    class Meta:
        model = OrganisationPending
        fields = ['status','details']

    def __init__(self, *args, **kwargs):
        super(OrganisationAccessRequestForm, self).__init__(*args, **kwargs)

        self.fields['status'].widget.attrs['disabled'] = True
        self.fields['status'].required = False
        self.helper = BaseFormHelper()
        self.helper.form_id = 'id_form_create_communication'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('save', 'Confirm', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))

class ApplicationWebPublishForm(ModelForm):

    class Meta:
        model = Application
        fields = ['publish_documents', 'publish_draft_report', 'publish_final_report', 'publish_determination_report','publish_documents_expiry','publish_draft_expiry','publish_final_expiry']

    def __init__(self, *args, **kwargs):
        super(ApplicationWebPublishForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()
        self.helper.form_id = 'id_form_web_publish_application'
        self.helper.attrs = {'novalidate': ''}

        self.fields['publish_documents_expiry'].label = "Expiry (Unpublish Date)"
        self.fields['publish_draft_expiry'].label = "Expiry (Unpublish Date)"
        self.fields['publish_final_expiry'].label = "Expiry (Unpublish Date)"

        self.fields['publish_documents_expiry'].css_class = 'dateinput'
        self.fields['publish_draft_expiry'].css_class = 'dateinput'
        self.fields['publish_final_expiry'].css_class = 'dateinput'

        # Delete publish fields not required for update.
        if kwargs['initial']['publish_type'] in 'received':
            del self.fields['publish_draft_report']
            del self.fields['publish_final_report']
            del self.fields['publish_determination_report']
            
            del self.fields['publish_draft_expiry']
            del self.fields['publish_final_expiry']

            self.fields['publish_documents_expiry'].required = True
            self.fields['publish_documents'].label = "Published Date"
            #self.fields['publish_documents'].widget.attrs['hidden'] = True
            self.fields['publish_documents'].widget = HiddenInput()
        elif kwargs['initial']['publish_type'] in 'draft':
            del self.fields['publish_final_report']
            del self.fields['publish_documents']
            del self.fields['publish_determination_report']

            del self.fields['publish_documents_expiry']
            del self.fields['publish_final_expiry']

            self.fields['publish_draft_expiry'].required = True
            self.fields['publish_draft_report'].label = "Published Date"
            self.fields['publish_draft_report'].widget = HiddenInput()
        elif kwargs['initial']['publish_type'] in 'final':
            del self.fields['publish_draft_report']
            del self.fields['publish_documents']
            del self.fields['publish_determination_report']

            del self.fields['publish_documents_expiry']
            del self.fields['publish_draft_expiry']

            self.fields['publish_final_expiry'].required = True
            self.fields['publish_final_report'].label = "Published Date"
            self.fields['publish_final_report'].widget = HiddenInput()
        elif kwargs['initial']['publish_type'] in 'determination':
            del self.fields['publish_draft_report']
            del self.fields['publish_documents']
            del self.fields['publish_final_report']

            del self.fields['publish_documents_expiry']
            del self.fields['publish_draft_expiry']
            del self.fields['publish_final_expiry']

            self.fields['publish_determination_report'].label = "Published Date"
            self.fields['publish_determination_report'].widget.attrs['disabled'] = True
        else:
            del self.fields['publish_draft_report']
            del self.fields['publish_final_report']
            del self.fields['publish_documents']
            del self.fields['publish_determination_report']
            del self.fields['publish_documents_expiry']
            del self.fields['publish_draft_expiry']
            del self.fields['publish_final_expiry']
            raise 
        self.helper.add_input(Submit('save', 'Publish to Website', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))


class ApplicationFormMixin(object):
    """Form mixin containing validation rules common to all application types.
    """
    def clean(self):
        cleaned_data = super(ApplicationFormMixin, self).clean()
        # Rule: proposed commence date cannot be later then proposed end date.
        #if cleaned_data.get('proposed_commence') and cleaned_data.get('proposed_end'):
            #difference = cleaned_data['proposed_end'] - cleaned_data['proposed_commence'] 
            #years = (difference.days + difference.seconds/86400)/365.2425
            #if cleaned_data['proposed_commence'] > cleaned_data['proposed_end']:
            #    msg = 'Commence date cannot be later than the end date'
            #    self._errors['proposed_commence'] = self.error_class([msg])
            #    self._errors['proposed_end'] = self.error_class([msg])
            #if years > 2: 
            #    msg = 'Proposed end date must be two years or less from proposed commencement date.'
            #    self._errors['proposed_commence'] = self.error_class([msg])
            #    self._errors['proposed_end'] = self.error_class([msg])

            
        return cleaned_data


class ApplicationLicencePermitForm(ApplicationFormMixin, ModelForm):
#    cert_survey = FileField(
#        label='Certificate of survey', required=False, max_length=128)
#    cert_public_liability_insurance = FileField(
#        label='Public liability insurance certificate', required=False, max_length=128)
#    risk_mgmt_plan = FileField(
#        label='Risk managment plan (if available)', required=False, max_length=128)
#    safety_mgmt_procedures = FileField(
#        label='Safety management procedures (if available)', required=False, max_length=128)
#    deed = FileField(required=False, max_length=128, widget=ClearableFileInput)

    cert_survey = FileField(label='Certificate of survey', required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
    cert_public_liability_insurance = FileField(label='Public liability insurance certificate', required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
    risk_mgmt_plan = FileField(label='Risk managment plan (if available)', required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'})) 
    safety_mgmt_procedures = FileField(label='Safety management procedures (if available)', required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
  
#    deed = FileField(required=False, max_length=128, widget=AjaxFileUploader())
    deed = Field(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}) , label='Deed')
    brochures_itineries_adverts = Field(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}) , label='Brochures, itineraries or advertisements (if available)' )
#    brochures_itineries_adverts = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}) , label='Brochures, itineraries or advertisements (if available)' )
    #MultiFileField(
    #    required=False, label='Brochures, itineraries or advertisements',
    #    help_text='Choose multiple files to upload (if required). NOTE: this will replace any existing uploads.')
    #    land_owner_consent = MultiFileField(
            #        required=False, label='Landowner consent statement(s)',
        #        help_text='Choose multiple files to upload (if required). NOTE: this will replace any existing uploads.')
#    land_owner_consent = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}),  label='Landowner consent statement(s)', help_text='Choose multiple files to upload (if required). NOTE: this will replace any existing uploads.' )
    land_owner_consent = Field(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}),  label='Landowner consent statement(s)', help_text='Choose multiple files to upload (if required). NOTE: this will replace any existing uploads.')

#    location_route_access = FileField(required=False, max_length=128, widget=ClearableFileInput)
    location_route_access = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))

#    document_final = FileField(required=False, max_length=128, widget=ClearableFileInput)
    document_final = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))

    other_relevant_documents = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Other relevant supporting documentation (if available)' )
#    other_relevant_documents = FileField(required=False, max_length=128, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}), label='Other relevant supporting documentation (if available)' )
 
    vessel_or_craft_details = ChoiceField(choices=Application.APP_VESSEL_CRAFT ,widget=RadioSelect(attrs={'class':'radio-inline'}))

    jetty_dot_approval = ChoiceField(choices=Application.APP_YESNO ,widget=RadioSelect())
    food = ChoiceField(choices=Application.APP_YESNO ,widget=RadioSelect())
    beverage = ChoiceField(choices=Application.APP_YESNO ,widget=RadioSelect())
    liquor_licence = ChoiceField(choices=Application.APP_YESNO ,widget=RadioSelect(), label='Do you have an appropriate liquor licence?')
    byo_alcohol = ChoiceField(choices=Application.APP_YESNO ,widget=RadioSelect())


    class Meta:
        model = Application
        fields = [
            'applicant','title', 'description', 'proposed_commence', 'proposed_end',
            'purpose', 'max_participants', 'proposed_location', 'address',
            'jetties', 'jetty_dot_approval','jetty_dot_approval_expiry','type_of_crafts','number_of_crafts',
            'drop_off_pick_up', 'food', 'beverage', 'liquor_licence','byo_alcohol', 'sullage_disposal', 'waste_disposal',
            'refuel_location_method', 'berth_location', 'anchorage', 'operating_details','assessment_start_date','expire_date','vessel_or_craft_details'
        ]

    def __init__(self, *args, **kwargs):
        super(ApplicationLicencePermitForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()
        self.helper.form_id = 'id_form_update_licence_permit'
        self.helper.attrs = {'novalidate': ''}

        may_update =  self.initial["workflow"]['may_update']
        show_form_buttons = self.initial["workflow"]['show_form_buttons']

        if 'brochures_itineries_adverts_json' in self.data:
            self.initial['brochures_itineries_adverts'] = self.data.get('brochures_itineries_adverts_json')
        #self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
        #self.helper.add_input(Submit('cancel', 'Cancel'))

        # Add labels for fields
        self.fields['description'].label = "Summary"
#       self.fields['project_no'].label = "Riverbank Project Number"
        self.fields['purpose'].label = "Purpose of Approval"
        self.fields['purpose'].widget.attrs.update({'class': 'form-control'})
        self.fields['proposed_commence'].label = "Proposed Commencement Date"
        self.fields['proposed_commence'].widget.attrs['autocomplete'] = 'off'

        self.fields['proposed_end'].label = "Proposed End Date"
        self.fields['proposed_end'].widget.attrs['autocomplete'] = 'off'

        self.fields['expire_date'].widget.attrs['autocomplete'] = 'off'
        self.fields['max_participants'].label = "Maximum Number of Participants"
        self.fields['address'].label = "Address of any landbased component of the commercial activity"
        self.fields['proposed_location'].label = "Proposed Location"
        self.fields['proposed_location'].widget.attrs.update({'class': 'form-control'})
        self.fields['location_route_access'].label = "Location / Route and Access Points (mark clearly on map)"
        # self.fields['proposed_location'].label = "Location / Route and Access Points"
        self.fields['jetties'].label = "List all jetties to be used"
        self.fields['jetty_dot_approval'].label = "Do you have approval to use Department of Transport service jetties?"
        self.fields['drop_off_pick_up'].label = "List all drop off and pick up points"
        self.fields['food'].label = "Food to be served?"
        self.fields['beverage'].label = "Beverage to be served?"
        self.fields['byo_alcohol'].label = "Do you allow BYO alcohol?"
        self.fields['sullage_disposal'].label = "Details of sullage disposal method"
        self.fields['waste_disposal'].label = "Details of waste disposal method"
        self.fields['refuel_location_method'].label = "Location and method of refueling"
        self.fields['anchorage'].label = "List all anchorage areas"
        self.fields['operating_details'].label = "Hours and days of operation including length of tours / lessons"
        self.fields['vessel_or_craft_details'].label = "Are there any vessels or crafts to be noted in this application?"
        self.fields['assessment_start_date'].label = "Start Date"
        self.fields['assessment_start_date'].widget.attrs['autocomplete'] = 'off'

        vesselandcraftdetails = crispy_para("Any vessel or craft to be used by a commercial operator in the river reserve must be noted in this application with the relevent Department of Transport certificate of survery or hire and driver registration.")
        deeddesc = crispy_para("Print <a href=''>the deed</a>, sign it and attach it to this application")
        landownerconsentdesc = crispy_para("Print <A href=''>this document</A> and have it signed by each landowner (or body responsible for management)")
        landownerconsentdesc2 = crispy_para("Then attach all signed documents to this application.")
        landownerconsentdesc3 = crispy_para("Landowner signature is required")

        self.fields['title'].required = False
        self.fields['jetty_dot_approval'].required = False
        self.fields['vessel_or_craft_details'].required = False
        self.fields['food'].required = False
        self.fields['beverage'].required = False
        self.fields['byo_alcohol'].required = False
        self.fields['liquor_licence'].required = False

        for fielditem in self.initial["fieldstatus"]:
            if fielditem in self.fields:
                del self.fields[fielditem]

        for fielditem in self.initial["fieldrequired"]:
            if fielditem in self.fields:
                self.fields[fielditem].required = True

        crispy_boxes = crispy_empty_box()
#        organisation = self.initial['organisation']

#        if check_fields_exist(self.fields,['applicant']) is True:
#            self.fields['applicant'].disabled = True
#    #        print self.initial["workflow"]["hidden"]['vessels']
#            if self.initial["may_change_application_applicant"] == "True":
#                changeapplicantbutton = crispy_button_link('Change Applicant',reverse('applicant_change', args=(self.initial['application_id'],)))
#            else: 
#                changeapplicantbutton = HTML('')
#
#
#            if organisation is not None:
#               applicant_info = HTML('{% include "applications/organisation_update_snippet.html" %}')
#            else:
#               applicant_info = HTML('{% include "applications/applicant_update_snippet.html" %}')
#
#
#            crispy_boxes.append(crispy_box('applicant_collapse','form_applicant','Applicant', applicant_info,changeapplicantbutton))
#            del self.fields['applicant']

        organisation = self.initial['organisation']

        if self.initial['state'] == 1:
             if 'submitter_comment' in self.initial:
                 if len(self.initial['submitter_comment']) > 1:
                      crispy_boxes.append(crispy_alert(self.initial['submitter_comment']))


        #if 'submitter_comment' in self.initial:
        #     if len(self.initial['submitter_comment']) > 1:
        #         crispy_boxes.append(crispy_alert(self.initial['submitter_comment']))

        if self.initial["may_change_application_applicant"] == "True":
            changeapplicantbutton = crispy_button_link('Update Applicant',reverse('applicant_change', args=(self.initial['application_id'],)))
        else:
            changeapplicantbutton = HTML('')

        if organisation is not None:
            applicant_info = HTML('{% include "applications/organisation_update_snippet.html" %}')
        else:
            applicant_info = HTML('{% include "applications/applicant_update_snippet.html" %}')

        if organisation is not None:
            applicant_info = HTML('{% include "applications/organisation_update_snippet.html" %}')
        else:
            applicant_info = HTML('{% include "applications/applicant_update_snippet.html" %}')


#       if 'applicant' in self.fields:
        crispy_boxes.append(crispy_box('applicant_collapse','form_applicant','Applicant', applicant_info,changeapplicantbutton))
        if 'applicant' in self.fields:
           del self.fields['applicant']

        if check_fields_exist(self.fields,['title']) is True and may_update == "True":
            #self.fields['title'].widget.attrs['placeholder'] = "Enter Title, ( Director of Corporate Services )"
            crispy_boxes.append(crispy_box('title_collapse', 'form_title' , 'Title','title'))
        else:
            try:
               del self.fields['title']
            except:
               donothing =''

            applicant_title = HTML('{% include "applications/application_title.html" %}')
            if self.initial["workflow"]["hidden"]["title"] == 'False':
                crispy_boxes.append(applicant_title)

        if check_fields_exist(self.fields,['description']) is True and may_update == "True":
             crispy_boxes.append(crispy_box('summary_collapse', 'form_summary' , 'Proposed Commercial Acts or Activities','description'))
        else:
            try:
               del self.fields['description']
            except:
               donothing =''

            crispy_boxes.append(HTML('{% include "applications/application_proposed_commercial_acts_activities.html" %}'))

        if check_fields_exist(self.fields,['vessel_or_craft_details']) is True and may_update == "True":
             crispy_boxes.append(crispy_box('vessel_or_crafts_view_collapse', 'form_vessel_or_crafts_view' , 'Vessel or Craft Details',vesselandcraftdetails,InlineRadios('vessel_or_craft_details'), HTML('{% include "applications/application_vessels.html" %}'),))
             #crispy_box('crafts_collapse', 'form_crafts' , 'Craft Details','type_of_crafts','number_of_crafts')))
        else:
            try:
               del self.fields['vessel_or_craft_details']
            except:
               donothing = ''

            crispy_boxes.append(HTML('{% include "applications/application_vessel_and_craft_details.html" %}'))

        if self.initial["workflow"]["hidden"]["conditions"] == 'False':
            crispy_boxes.append(HTML('{% include "applications/application_conditions.html" %}'))

        if self.initial["workflow"]["hidden"]["referrals"] == 'False':
             crispy_boxes.append(HTML('{% include "applications/application_referrals.html" %}'))

#        else:
#             crispy_boxes.append()
 
        #if self.initial["workflow"]["hidden"]['vessels'] == "False":
        #    if self.initial['vessel_or_craft_details'] == 1:
        #        crispy_boxes.append(crispy_box('vessel_or_crafts_collapse', 'form_vessel_or_crafts' , 'Vessel Details',HTML('{% include "applications/application_vessels.html" %}')))
                

    #    if 'crafts' in self.initial["workflow"]["hidden"]:    
   #         if self.initial["workflow"]["hidden"]['crafts'] == "False":
   #             if self.initial['vessel_or_craft_details'] == 2:
  #                  crispy_boxes.append(crispy_box('crafts_collapse', 'form_crafts' , 'Craft Details','type_of_crafts','number_of_crafts'))
 #               else: 
#                    del self.fields['type_of_crafts']
 #                   del self.fields['number_of_crafts']
                    
        if check_fields_exist(self.fields,['purpose']) is True and may_update == "True":
             crispy_boxes.append(crispy_box('proposal_details_collapse', 'form_proposal_details' , 'Proposal Details ','purpose','proposed_commence','proposed_end','max_participants','proposed_location','address','location_route_access','jetties',InlineRadios('jetty_dot_approval'),'jetty_dot_approval_expiry','drop_off_pick_up',InlineRadios('food'),InlineRadios('beverage'),InlineRadios('liquor_licence'),InlineRadios('byo_alcohol'),'sullage_disposal','waste_disposal','refuel_location_method','berth_location','anchorage','operating_details'))
        else:
            try:
               del self.fields['purpose']
               del self.fields['proposed_commence']
               del self.fields['proposed_end']
               del self.fields['max_participants']
               del self.fields['proposed_location']
               del self.fields['address']
               del self.fields['location_route_access']
               del self.fields['jetties']
               del self.fields['jetty_dot_approval']
               del self.fields['jetty_dot_approval_expiry']
               del self.fields['drop_off_pick_up']
               del self.fields['food']
               del self.fields['beverage']
               del self.fields['liquor_licence']
               del self.fields['byo_alcohol']
               del self.fields['sullage_disposal']
               del self.fields['waste_disposal']
               del self.fields['refuel_location_method']
               del self.fields['berth_location']
               del self.fields['anchorage']
               del self.fields['operating_details']
            except:
               donothing =''

            crispy_boxes.append(HTML('{% include "applications/application_proposal_details.html" %}'))



        if check_fields_exist(self.fields,['cert_survey','cert_public_liability_insurance','risk_mgmt_plan','safety_mgmt_procedures','brochures_itineries_adverts','other_relevant_documents']) is True and may_update == "True":
             crispy_boxes.append(crispy_box('other_documents_collapse', 'form_other_documents' , 'Other Documents','cert_survey','cert_public_liability_insurance','risk_mgmt_plan','safety_mgmt_procedures','brochures_itineries_adverts','other_relevant_documents'))
        else:
            try:
               del self.fields['cert_survey']
               del self.fields['cert_public_liability_insurance']
               del self.fields['risk_mgmt_plan']
               del self.fields['safety_mgmt_procedures']
               del self.fields['brochures_itineries_adverts']
               del self.fields['other_relevant_documents']
            except:
               donothing =''

            application_other_docs = HTML('{% include "applications/application_other_docs.html" %}')
            crispy_boxes.append(application_other_docs)



        # Landowner Consent
        if check_fields_exist(self.fields,['land_owner_consent']) is True and may_update == "True":
            crispy_boxes.append(crispy_box('land_owner_consent_collapse', 'form_land_owner_consent' , 'Landowner Consent',landownerconsentdesc,landownerconsentdesc2,'land_owner_consent',landownerconsentdesc3))
            pass
        else:
            try:
               del self.fields['land_owner_consent']
            except:
               pass 

            application_land_owner = HTML('{% include "applications/application_land_owner_consent.html" %}')
            crispy_boxes.append(application_land_owner)

        # Deed
        if check_fields_exist(self.fields,['deed']) is True and may_update == "True":
            crispy_boxes.append(crispy_box('deed_collapse', 'form_deed' , 'Deed',deeddesc,'deed'))
        else:
            try:
               del self.fields['deed']
            except:
               donothing =''
            if self.initial["workflow"]["hidden"]["deed"] == 'False':
                  application_deed = HTML('{% include "applications/application_deed.html" %}')
                  crispy_boxes.append(application_deed)
    
#        if self.initial["workflow"]["hidden"]["conditions"] == 'False':
#            crispy_boxes.append(HTML('{% include "applications/application_conditions.html" %}'))



        if check_fields_exist(self.fields,['document_final']) is True and may_update == "True":
            crispy_boxes.append(crispy_box('document_final_collapse', 'form_document_final' , 'Assessment','document_final','assessment_start_date','expire_date'))
        else:
            try:
               del self.fields['document_final']
               del self.fields['assessment_start_date']
               del self.fields['expire_date']
            except:
               donothing =''

            if self.initial["workflow"]["hidden"]["assessments"] == 'False':
                  crispy_boxes.append(HTML('{% include "applications/application_assessment.html" %}'))


        #dynamic_selections = HTML('{% include "applications/application_form_js_dynamics.html" %}')
        dynamic_selections = HTML('{% include "applications/application_form_js_licence_dynamics.html" %}')
        self.helper.layout = Layout(crispy_boxes,dynamic_selections)

        if show_form_buttons == 'True' and may_update == "True":
                 if 'condactions' in self.initial['workflow']:
                     if  self.initial['workflow']['condactions'] is not None:
                         for ca in self.initial['workflow']['condactions']: 
                              if 'steplabel' in self.initial['workflow']['condactions'][ca]: 
                                   self.helper = crispy_button(self.helper,ca,self.initial['workflow']['condactions'][ca]['steplabel'])
                     else:
                          self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
                          self.helper.add_input(Submit('cancel', 'Cancel'))
                             


    def clean(self):
        cleaned_data = super(ApplicationLicencePermitForm, self).clean()
        # Clean the uploaded file fields (acceptable file types).
        for field in [
                'cert_survey', 'cert_public_liability_insurance', 'risk_mgmt_plan',
                'safety_mgmt_procedures', 'deed']:
            up = cleaned_data.get(field)
            if up and hasattr(up, 'content_type') and up.content_type not in settings.ALLOWED_UPLOAD_TYPES:
                self._errors[field] = self.error_class(['{}: this file type is not permitted'.format(up.name)])
        # Clean multi-upload fields:
        for field in ['brochures_itineries_adverts', 'land_owner_consent']:
            up = cleaned_data.get(field)
            errors = []
            if up:
                for f in up:
                    if hasattr(f, 'content_type') and f.content_type not in settings.ALLOWED_UPLOAD_TYPES:
                        errors.append('{}: this file type is not permitted'.format(f.name))
                if errors:
                    self._errors[field] = self.error_class(errors)


        if 'proposed_location' in self.cleaned_data:
             proposed_location = self.cleaned_data.get('proposed_location')
             if proposed_location == 0 or proposed_location == 2:
                  if '2-prevstep' in self.data:
                      pass
                  else:
                      if len(self.data.get('land_owner_consent_json')) == 0 or self.data.get('land_owner_consent_json') == '[]':
                         raise forms.ValidationError('Landowner consent must be provided')



        return cleaned_data


class ApplicationPermitForm(ApplicationFormMixin, ModelForm):

#    document_final = FileField(required=False, max_length=128, widget=ClearableFileInput)
#    records = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}),  label='Attach more detailed descripton, maps or plans')
#    land_owner_consent = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}),  label='Land Owner Consent')
#    deed = FileField(required=False, max_length=128, widget=ClearableFileInput) 

    document_final = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
    records = Field(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}),  label='Attach more detailed descripton, maps or plans')
    land_owner_consent = Field(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}),  label='Land Owner Consent')
    deed = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
    over_water = ChoiceField(choices=Application.APP_YESNO, widget=RadioSelect(attrs={'class':'radio-inline'}))

    lot = CharField(required=False)
    reserve_number = CharField(required=False)
    town_suburb = CharField(required=False)
    nearest_road_intersection = CharField(required=False)
    local_government_authority = CharField(required=False)
    street_number_and_name = CharField(required=False, label='Street Address')

#    proposed_development_plans = FileField(required=False, max_length=128, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}))
#    supporting_info_demonstrate_compliance_trust_policies = FileField(required=False, max_length=128, widget=ClearableFileInput) 

    proposed_development_plans = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
    supporting_info_demonstrate_compliance_trust_policies = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))

    class Meta:
        model = Application
        fields = [
            'applicant','title', 'description', 'proposed_commence', 'proposed_end',
            'cost', 'project_no', 'related_permits', 'over_water', 'assessment_start_date','expire_date']

    def __init__(self, *args, **kwargs):
        super(ApplicationPermitForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()
        self.helper.form_id = 'id_form_update_permit'
        self.helper.attrs = {'novalidate': ''}
        #self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
#        self.helper.add_input(Submit('cancel', 'Cancel'))

        may_update =  self.initial["workflow"]['may_update']
        show_form_buttons = self.initial["workflow"]['show_form_buttons'] 
       
        # Add labels and help text for fields
        self.fields['proposed_commence'].label = "Proposed commencement date"
        self.fields['proposed_commence'].help_text = "(Please that consider routine assessment takes approximately 4 - 6 weeks, and set your commencement date accordingly)"
        self.fields['proposed_commence'].widget.attrs['autocomplete'] = 'off'

        self.fields['proposed_end'].label = "Proposed end date"
        self.fields['proposed_end'].widget.attrs['autocomplete'] = 'off'

        self.fields['expire_date'].widget.attrs['autocomplete'] = 'off'

        self.fields['cost'].label = "Approximate cost"
        self.fields['cost'].widget.attrs['autocomplete'] = 'off'

        self.fields['project_no'].label = "Riverbank project number (if applicable)"
        self.fields['project_no'].widget.attrs['autocomplete'] = 'off'

        self.fields['related_permits'].label = "Details of related permits"
        self.fields['description'].label = "Description of works, acts or activities"
        self.fields['description'].widget.attrs['autocomplete'] = 'off'

        self.fields['assessment_start_date'].label = "Start Date"
        self.fields['assessment_start_date'].widget.attrs['autocomplete'] = 'off'

        self.fields['over_water'].label = "Are any proposed works, acts or activities in or over waters?"

#       self.fields['records'].label = "Attach more detailed descripton, maps or plans"
        self.fields['title'].required = False      
        for fielditem in self.initial["fieldstatus"]:
            if fielditem in self.fields:
                del self.fields[fielditem]

        for fielditem in self.initial["fieldrequired"]:
            if fielditem in self.fields:
                self.fields[fielditem].required = True

        deeddesc = crispy_para("Print <a href=''>the deed</a>, sign it and attach it to this application")
        landownerconsentdesc = crispy_para("Print <A href=''>this document</A> and have it signed by each landowner (or body responsible for management)")
        landownerconsentdesc2 = crispy_para("Then attach all signed documents to this application.")
        landownerconsentdesc3 = crispy_para_red("Landowner signature is required")
 
        crispy_boxes = crispy_empty_box()
        #self.fields['applicant'].disabled = True
        organisation = self.initial['organisation']

        if self.initial['state'] == 1:
             if 'submitter_comment' in self.initial:
                 if len(self.initial['submitter_comment']) > 1:
                      crispy_boxes.append(crispy_alert(self.initial['submitter_comment']))

        #if 'submitter_comment' in self.initial and may_update == "True":
        #     if len(self.initial['submitter_comment']) > 1:
        #         crispy_boxes.append(crispy_alert(self.initial['submitter_comment']))

        if self.initial["may_change_application_applicant"] == "True":
            changeapplicantbutton = crispy_button_link('Change Applicant',reverse('applicant_change', args=(self.initial['application_id'],)))
        else:
            changeapplicantbutton = HTML('')

        if organisation is not None:
            applicant_info = HTML('{% include "applications/organisation_update_snippet.html" %}')
        else:
            applicant_info = HTML('{% include "applications/applicant_update_snippet.html" %}')


        if organisation is not None:
            applicant_info = HTML('{% include "applications/organisation_update_snippet.html" %}')
        else:
            applicant_info = HTML('{% include "applications/applicant_update_snippet.html" %}')        


#       if 'applicant' in self.fields:
        crispy_boxes.append(crispy_box('applicant_collapse','form_applicant','Applicant', applicant_info,changeapplicantbutton))
        if 'applicant' in self.fields:
           del self.fields['applicant']


#        if self.initial["may_change_application_applicant"] == "True":
#            changeapplicantbutton = crispy_button_link('Add / Change Applicant',reverse('applicant_change', args=(self.initial['application_id'],)))
#        else:
#            changeapplicantbutton = HTML('')
#        crispy_boxes.append(crispy_box('applicant_collapse','form_applicant','Applicant','applicant', changeapplicantbutton))


        if check_fields_exist(self.fields,['title']) is True and may_update == "True":
            #self.fields['title'].widget.attrs['placeholder'] = "Enter Title, ( Director of Corporate Services )"
            crispy_boxes.append(crispy_box('title_collapse', 'form_title' , 'Title','title'))
        else:
            applicant_title = HTML('{% include "applications/application_title.html" %}')
            if self.initial["workflow"]["hidden"]["title"] == 'False':
                try: 
                    del self.fields['title']
                except:
                    donothing =''
                crispy_boxes.append(applicant_title)

        # Location 
        if check_fields_exist(self.fields,['lot','reserve_number','town_suburb','nearest_road_intersection','local_government_authority','over_water']) is True and may_update == "True":
            crispy_boxes.append(crispy_box('location_collapse', 'form_location' , 'Location','street_number_and_name','lot','reserve_number','town_suburb','nearest_road_intersection','local_government_authority','over_water') )
        else:
            try:
               del self.fields['over_water']
            except:
               donothing =''

            application_location = HTML('{% include "applications/application_location.html" %}')
            crispy_boxes.append(application_location)

        if check_fields_exist(self.fields,['proposed_commence','proposed_end','cost','project_no','related_permits']) is True and may_update == "True":
            crispy_boxes.append(crispy_box('other_information_collapse', 'form_other_information' , 'Other Information','proposed_commence','proposed_end','cost','project_no','related_permits'))
        else:
            try:
                del self.fields['proposed_commence']
                del self.fields['proposed_end']
                del self.fields['cost']
                del self.fields['project_no']
                del self.fields['related_permits']
            except:
                donothing =''

            #application_other_docs = HTML('{% include "applications/application_other_docs.html" %}')
            #crispy_boxes.append(application_other_docs)
            application_other_info =  HTML('{% include "applications/application_other_information.html" %}')
            crispy_boxes.append(application_other_info)

        if check_fields_exist(self.fields,['description','proposed_development_plans']) is True and may_update == "True":
            crispy_boxes.append(crispy_box('description_collapse', 'form_description' , 'Description','description','proposed_development_plans','supporting_info_demonstrate_compliance_trust_policies'))
        else:
            try: 
                del self.fields['description']
                del self.fields['proposed_development_plans']
                del self.fields['supporting_info_demonstrate_compliance_trust_policies']
            except:
                donothing =''

            application_descriptions = HTML('{% include "applications/application_description.html" %}')
            crispy_boxes.append(application_descriptions)

        # Landowner Consent
        if check_fields_exist(self.fields,['land_owner_consent']) is True and may_update == "True":
            crispy_boxes.append(crispy_box('land_owner_consent_collapse', 'form_land_owner_consent' , 'Landowner Consent',landownerconsentdesc,landownerconsentdesc2,'land_owner_consent',landownerconsentdesc3))
        else:
            application_land_owner = HTML('{% include "applications/application_land_owner_consent.html" %}')
            crispy_boxes.append(application_land_owner) 

        if self.initial["workflow"]["hidden"]["referrals"] == 'False':
             crispy_boxes.append(HTML('{% include "applications/application_referrals.html" %}'))

        # Deed
        #if check_fields_exist(self.fields,['deed']) is True and may_update == "True":
        #    crispy_boxes.append(crispy_box('deed_collapse', 'form_deed' , 'Deed',deeddesc,'deed'))
        #else:
        #   
        #    application_deed = HTML('{% include "applications/application_deed.html" %}')
        #    crispy_boxes.append(application_deed)

        # Assessment
        if check_fields_exist(self.fields,['assessment_start_date','expire_date']) is True and may_update == "True":
            crispy_boxes.append(HTML('{% include "applications/application_conditions.html" %}'))
            crispy_boxes.append(crispy_box('assessment_collapse', 'form_assessement', 'Assessment','assessment_start_date','expire_date','document_final'))

        else:
            try:
                del self.fields['assessment_start_date']
                del self.fields['expire_date']
            except:
                donothing =''

            if self.initial["workflow"]["hidden"]["assessments"] == 'False':
                crispy_boxes.append(HTML('{% include "applications/application_conditions.html" %}'))
                crispy_boxes.append(HTML('{% include "applications/application_assessment.html" %}'))

        dynamic_selections = HTML('{% include "applications/application_form_js_permit_dynamics.html" %}')
        self.helper.layout = Layout(crispy_boxes,dynamic_selections)
        #if 'hide_form_buttons' in self.initial["workflow"]["hidden"]:
        if show_form_buttons == 'True':
             if 'condactions' in self.initial['workflow']:
                 if  self.initial['workflow']['condactions'] is not None:
                     for ca in self.initial['workflow']['condactions']:
                         if 'steplabel' in self.initial['workflow']['condactions'][ca]:
                             self.helper = crispy_button(self.helper,ca,self.initial['workflow']['condactions'][ca]['steplabel'])
                 else:
                     self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
                     self.helper.add_input(Submit('cancel', 'Cancel'))


        #self.fields['other_supporting_docs'].label = "Attach supporting information to demonstrate compliance with relevant Trust policies"

class ApplicationChange(ApplicationFormMixin, ModelForm):
     proposed_development_plans = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}),  label='Supporting Documents')

     class Meta:
        model = Application
        fields = ['title','app_type','proposed_development_plans','proposed_development_description']

     def __init__(self, *args, **kwargs):
        super(ApplicationChange, self).__init__(*args, **kwargs)

        self.helper = BaseFormHelper()
        self.fields['proposed_development_description'].label = "Details of proposed ammendment"
        self.fields['app_type'].widget.attrs.update({'class': 'form-control'})
        self.fields['app_type'].disabled = True
        self.fields['title'].disabled = True
        self.helper.form_id = 'id_form_change_ammend'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('createform', 'Create Form', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))

class ApplicationPart5Form(ApplicationFormMixin, ModelForm):

    certificate_of_title_volume = CharField(required=False)
    folio = CharField(required=False)
    diagram_plan_deposit_number = CharField(required=False, label='Diagram / Plan / Deposit number')
    lot = CharField(required=False, label='Subject lot Lot Number')
    location = CharField(required=False)
    reserve_number = CharField(required=False)
    street_number_and_name = CharField(required=False)
    town_suburb = CharField(required=False, label='Town / Suburb')
    nearest_road_intersection = CharField(required=False)

#    land_owner_consent = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}),  label='Land Owner Consent')
    land_owner_consent = Field(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}),  label='Land Owner Consent')
#    proposed_development_plans = FileField(required=False, max_length=128, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}))
    proposed_development_plans = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
    
    document_new_draft = FileField(required=False, max_length=128 , widget=ClearableFileInput)
    #document_draft = FileField(required=False, max_length=128 , widget=ClearableFileInput)
    document_draft = FileField(required=False, max_length=128 , widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
     
#    document_draft_signed = FileField(required=False, max_length=128 , widget=ClearableFileInput)
    document_draft_signed = FileField(required=False, max_length=128 , widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
    #document_final = FileField(required=False, max_length=128, widget=ClearableFileInput)
    document_final = FileField(required=False, max_length=128 , widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label="Document Final (Unsigned)")
#    document_final_signed = FileField(required=False, max_length=128 , widget=ClearableFileInput)
    document_final_signed = FileField(required=False, max_length=128 , widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
    document_determination = FileField(required=False, max_length=128, widget=ClearableFileInput)
    document_completion = FileField(required=False, max_length=128, widget=ClearableFileInput)
    #river_lease_scan_of_application = FileField(required=False, max_length=128, widget=ClearableFileInput)
    river_lease_scan_of_application = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))

#    deed = FileField(required=False, max_length=128, widget=ClearableFileInput)

    deed = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
#   swan_river_trust_board_feedback = FileField(required=False, max_length=128, widget=ClearableFileInput)

    swan_river_trust_board_feedback = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
#    document_new_draft_v3 = FileField(required=False, max_length=128, widget=ClearableFileInput, label='Draft Version 3')
#    document_memo = FileField(required=False, max_length=128, widget=ClearableFileInput, label='Memo')

    document_new_draft_v3 = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Draft Version 3')
    document_memo = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Memo')
    document_memo_2 = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Memo 2')

#    document_determination = FileField(required=False, max_length=128, widget=ClearableFileInput, label='Determination Report')
#    document_briefing_note = FileField(required=False, max_length=128, widget=ClearableFileInput, label='Briefing Note')

    document_determination = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Determination Report')
    document_briefing_note = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Briefing Note')

#    document_determination_approved = FileField(required=False, max_length=128, widget=ClearableFileInput, label='Determination Signed Approved')
    document_determination_approved = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Determination Signed Approved')

    river_lease_require_river_lease = ChoiceField(choices=Application.APP_YESNO ,widget=RadioSelect(attrs={'class':'radio-inline'}), label='Does the development require a River reserve lease?')
    river_lease_reserve_licence = ChoiceField(choices=Application.APP_YESNO ,widget=RadioSelect(attrs={'class':'radio-inline'}), label='Does the proposed development involve an activity in the River reserve that will require a River reserve licence?')
    river_lease_application_number = CharField(required=False, label='Application number')
    approval_document = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={}), label='Signed Approval (minster)')
    approval_document_signed = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={}), label='Approval Document Signed')

    class Meta:
        model = Application
        fields = ['applicant','title', 'description','cost', 'river_lease_require_river_lease','river_lease_reserve_licence','river_lease_application_number','proposed_development_description','proposed_development_current_use_of_land','assessment_start_date','landowner','land_description','approval_document','approval_document_signed']

    def __init__(self, *args, **kwargs):
        super(ApplicationPart5Form, self).__init__(*args, **kwargs)

        may_update =  self.initial["workflow"]['may_update']
        show_form_buttons = self.initial["workflow"]['show_form_buttons']
        self.fields['title'].required = False
        self.fields['river_lease_require_river_lease'].required = False
        self.fields['river_lease_reserve_licence'].required = False
        self.fields['assessment_start_date'].widget.attrs['autocomplete'] = 'off'
 
        for fielditem in self.initial["fieldstatus"]:
            if fielditem in self.fields:
                del self.fields[fielditem]

        for fielditem in self.initial["fieldrequired"]:
            if fielditem in self.fields:
                self.fields[fielditem].required = True

        self.helper = BaseFormHelper()

        # Field helper Description text.
        fieldtext = crispy_para('Text Description') 
        attachpdf = crispy_para('Please attach application (PDF)')
        riverleasedesc = crispy_para("If you intend to apply for a lease in relation to this proposed develeopment, you will need to complete a seperate Form - Application for a River reserve lease - and lodge it concurrently with this application. Note "+'"'+" River reserve leases will not be granted for developments requiring approval under section 70 of the Act - to which the proposed lease relates - unless that approval has been granted. "+'"'+"")
        landownerconsentdesc = crispy_para("Print <A href=''>this document</A> and have it signed by each landowner (or body responsible for management)")
        landownerconsentdesc2 = crispy_para("Then attach all signed documents to this application.")
        deeddesc = crispy_para("Print <a href=''>the deed</a>, sign it and attach it to this application")


        # Field Groups & Collaspable Box Styling.

        # Create Empty Object to append to.
        crispy_boxes = crispy_empty_box()
#        changeapplicantbutton = crispy_button_link('Add / Change Applicant',reverse('applicant_change', args=(self.initial['application_id'],)))
#        crispy_boxes.append(crispy_box('applicant_collapse','form_applicant','Applicant','applicant', changeapplicantbutton))
#        if self.initial["may_change_application_applicant"] == "True":
#            changeapplicantbutton = crispy_button_link('Add / Change Applicant',reverse('applicant_change', args=(self.initial['application_id'],)))
#        else:
#            changeapplicantbutton = HTML('')
#        crispy_boxes.append(crispy_box('applicant_collapse','form_applicant','Applicant','applicant', changeapplicantbutton))
        organisation = self.initial['organisation']
        if self.initial['state'] == 1:
            if 'submitter_comment' in self.initial: 
               crispy_boxes.append(crispy_alert(self.initial['submitter_comment']))
        if self.initial["may_change_application_applicant"] == "True":
            changeapplicantbutton = crispy_button_link('Change Applicant',reverse('applicant_change', args=(self.initial['application_id'],)))
        else:
            changeapplicantbutton = HTML('')

        if organisation is not None:
            applicant_info = HTML('{% include "applications/organisation_update_snippet.html" %}')
        else:
            applicant_info = HTML('{% include "applications/applicant_update_snippet.html" %}')

        if self.initial["workflow"]["hidden"]["applicant"] == 'False':
            crispy_boxes.append(crispy_box('applicant_collapse','form_applicant','Applicant', applicant_info, changeapplicantbutton))
        del self.fields['applicant']


        if self.initial["workflow"]["hidden"]["title"] == 'False':
            # Title Box
            if check_fields_exist(self.fields,['title']) is True and may_update == "True":
                 #self.fields['title'].widget.attrs['placeholder'] = "Enter Title, ( Director of Corporate Services )"
                 crispy_boxes.append(crispy_box('title_collapse', 'form_title' , 'Title','title'))
            else:
                 try:
                    del self.fields['title']
                 except:
                    donothing =''
                 crispy_boxes.append(HTML('{% include "applications/application_title.html" %}'))



        if self.initial["workflow"]["hidden"]["certificate_of_title"] == 'False':
             # Certificate of Title Information
             if check_fields_exist(self.fields,['certificate_of_title_volume','folio','diagram_plan_deposit_number','location','reserve_number','street_number_and_name','town_suburb','lot','nearest_road_intersection']) is True and may_update == "True":
                  crispy_boxes.append(crispy_box('certificate_collapse', 'form_certificate' , 'Certificate of Title Information','certificate_of_title_volume','folio','diagram_plan_deposit_number','lot','location','reserve_number','street_number_and_name','town_suburb','nearest_road_intersection'))
                  donothing =''
             else:
                 try:
                     del self.fields['certificate_of_title_volume']
                     del self.fields['folio']
                     del self.fields['diagram_plan_deposit_number']
                     del self.fields['lot']
                     del self.fields['location']
                     del self.fields['reserve_number']
                     del self.fields['street_number_and_name']
                     del self.fields['town_suburb']
                     del self.fields['nearest_road_intersection']

                 except:
                     donothing =''
                 crispy_boxes.append(HTML('{% include "applications/application_certificate_of_title_information.html" %}'))


        if self.initial["workflow"]["hidden"]["river_lease_section_29"] == 'False':
            # River Reserve Lease (Swan and Cannning Management Act 2006 - section 29
            if check_fields_exist(self.fields,['river_lease_require_river_lease','river_lease_scan_of_application']) is True and may_update == "True":
                 crispy_boxes.append(crispy_box('riverleasesection29_collapse', 'form_riverleasesection29' , 'River Reserve Lease (Swan and Cannning Management Act 2006 - section 29',riverleasedesc,InlineRadios('river_lease_require_river_lease'),attachpdf,'river_lease_scan_of_application'))
            else:
                 try:
                    del self.fields['river_lease_require_river_lease']
                    del self.fields['river_lease_scan_of_application']
                 except:
                    donothing =''

                 crispy_boxes.append(HTML('{% include "applications/application_river_lease_29.html" %}'))

        if self.initial["workflow"]["hidden"]["river_lease_section_32"] == 'False':
            if check_fields_exist(self.fields,['river_lease_reserve_licence','river_lease_application_number']) is True and may_update == "True":
            # River Reserve Lease (Swan and Cannning Management Act 2006 - section 32
                 crispy_boxes.append(crispy_box('riverleasesection32_collapse', 'form_riverleasesection32' , 'River Reserve Lease (Swan and Cannning Management Act 2006 - section 32',InlineRadios('river_lease_reserve_licence'),'river_lease_application_number'))
            else:
                 try:
                    del self.fields['river_lease_reserve_licence']
                    del self.fields['river_lease_application_number']
                 except:
                    donothing =''


                 crispy_boxes.append(HTML('{% include "applications/application_river_lease_32.html" %}'))

        # Details of Proposed Development
        if check_fields_exist(self.fields,['cost','proposed_development_current_use_of_land','proposed_development_description','proposed_development_plans']) is True and may_update == "True":
            crispy_boxes.append(crispy_box('proposed_development_collapse', 'form_proposed_development' , 'Details of Proposed Development','cost','proposed_development_current_use_of_land','proposed_development_description','proposed_development_plans'))
        else:
             try:
                del self.fields['cost']
                del self.fields['proposed_development_current_use_of_land']
                del self.fields['proposed_development_description']
                del self.fields['proposed_development_plans']
             except:
                donothing =''

             crispy_boxes.append(HTML('{% include "applications/application_details_of_proposed_development.html" %}'))

        if self.initial["workflow"]["hidden"]["land_owner_consent"] == 'False':

            # Landowner Consent
            if check_fields_exist(self.fields,['land_owner_consent']) is True and may_update == "True":
                crispy_boxes.append(crispy_box('land_owner_consent_collapse', 'form_land_owner_consent' , 'Landowner Consent',landownerconsentdesc,landownerconsentdesc2,'land_owner_consent',))
            else:
                 try:
                    del self.fields['land_owner_consent']
                 except:
                    donothing =''

                 crispy_boxes.append(HTML('{% include "applications/application_land_owner_consent.html" %}'))

        if self.initial["workflow"]["hidden"]["deed"] == 'False':
             # Deed
             if check_fields_exist(self.fields,['deed']) is True and may_update == "True":
                 crispy_boxes.append(crispy_box('deed_collapse', 'form_deed' , 'Deed',deeddesc,'deed'))
             else:
                 try:
                    del self.fields['deed']
                 except:
                    donothing =''
                 if self.initial["workflow"]["hidden"]["deed"] == 'False':
                    crispy_boxes.append(HTML('{% include "applications/application_deed.html" %}'))
                    
        # publication
#       if 'hide_form_buttons' in self.initial["workflow"]["hidden"]:
        if self.initial["workflow"]["hidden"]["publication"] == 'False':
             crispy_boxes.append(HTML('{% include "applications/application_publication.html" %}'))
        if self.initial["workflow"]["hidden"]["stakeholdercommunication"] == 'False':
             crispy_boxes.append(HTML('{% include "applications/application_stakeholder_comms.html" %}'))

        if self.initial["workflow"]["hidden"]["referrals"] == 'False':
             crispy_boxes.append(HTML('{% include "applications/application_referrals.html" %}'))
        if self.initial["workflow"]["hidden"]["conditions"] == 'False':
             crispy_boxes.append(HTML('{% include "applications/application_conditions.html" %}'))
        # Assessment Update Step
        #if check_fields_exist(self.fields,['assessment_start_date']) is True and may_update == "True":
        if self.initial["workflow"]["hidden"]["assessments"] == 'False':
            if may_update == "True":
                crispy_boxes.append(crispy_box('assessment_collapse', 'form_assessment' , 'Assessment','assessment_start_date','document_draft',))
                crispy_boxes.append(HTML('{% include "applications/application_part5_assessment.html" %}'))
            else:
                crispy_boxes.append(HTML('{% include "applications/application_part5_assessment.html" %}'))
        

        if check_fields_exist(self.fields,['swan_river_trust_board_feedback']) is True and may_update == "True":
            crispy_boxes.append(crispy_box('boardfeedback_collapse', 'form_boardfeedback' , 'Attach Swan River Trust Board Feedback','swan_river_trust_board_feedback'))

        if check_fields_exist(self.fields,['document_draft_signed','document_final']) is True and may_update == "True":
            crispy_boxes.append(crispy_box('boardfeedback_collapse', 'form_boardfeedback' , 'Signed Draft & Final Report','document_draft_signed','document_final'))

        if check_fields_exist(self.fields,["document_new_draft_v3","document_memo"]) is True and may_update == "True":
            crispy_boxes.append(crispy_box('draft_new_collapse','form_draft_new','Attach new Draft & Memo','document_new_draft_v3','document_memo'))

        if check_fields_exist(self.fields,["document_memo_2"]) is True and may_update == "True":
            crispy_boxes.append(crispy_box('memo_2_collapse','form_new_memo_2','Memo 2','document_memo_2'))

        if check_fields_exist(self.fields,["document_final_signed"]) is True and may_update == "True":
            crispy_boxes.append(crispy_box('final_signed_collapse','form_final_signed','Attach Final Signed Report','document_final_signed'))


        if check_fields_exist(self.fields,["document_briefing_note","document_determination"]) is True and may_update == "True":
            crispy_boxes.append(crispy_box('determination_collapse','form_determination','Attached Deterimination & Breifing Notes','document_briefing_note','document_determination'))


        if "landowner_information" in self.initial["workflow"]["hidden"]:
             if self.initial["workflow"]["hidden"]["landowner_information"] == 'False':
                  # Landowner Information 
                  if check_fields_exist(self.fields,['landowner']) is True and may_update == "True":
                      crispy_boxes.append(crispy_box('landowner_info_collapse', 'form_landowner_info' , 'Landowner Information','landowner','land_description'))
                  else:
                      try:
                         del self.fields['landowner']
                         del self.fields['landowner_description']
                      except:
                         donothing =''

                      #crispy_boxes.append(HTML('{% include "applications/application_deed.html" %}'))


        if "approval_document" in self.initial["workflow"]["hidden"]:
             if self.initial["workflow"]["hidden"]["approval_document"] == 'False':
                  # Landowner Information
                  if check_fields_exist(self.fields,['approval_document']) is True and may_update == "True":
                      crispy_boxes.append(crispy_box('approval_document_info_collapse', 'form_approval_document_info' , 'Approval Document',HTML('{% include "applications/application_approval.html" %}'),))
                      del self.fields['approval_document']
                      pass
                  else:
                      try:
                         del self.fields['approval_document']
                      except:
                         donothing =''

        if "approval_document_signed" in self.initial["workflow"]["hidden"]:
             if self.initial["workflow"]["hidden"]["approval_document_signed"] == 'False':
                  # Landowner Information
                  if check_fields_exist(self.fields,['approval_document_signed']) is True and may_update == "True":
                      crispy_boxes.append(crispy_box('approval_document_signed_info_collapse', 'form_approval_document_signed_info' , 'Approval Document Unsigned',HTML('{% include "applications/application_approval_unsigned.html" %}'),'approval_document_signed'))
                      pass
                  else:
                      try:
                         del self.fields['approval_document_signed']
                      except:
                         donothing =''

                      #crispy_boxes.append(HTML('{% include "applications/application_deed.html" %}'))

 
        if check_fields_exist(self.fields,['document_determination_approved']) is True and may_update == "True":
            crispy_boxes.append(crispy_box('determination_approved_collapse','form_determination_approved','Determination Approved','document_determination_approved'))

        dynamic_selections = HTML('{% include "applications/application_form_part5_js_dynamics.html" %}')
        self.helper.layout = Layout(
                                crispy_boxes,dynamic_selections

#                            Div(crispy_heading('certificate_collapse', 'form_certificate' , 'Certificate of Title Information'),
#                                
#                         Div(Div(
#                             Fieldset(
#                              '',
 #                               'description',
 #                               'cost',
 #                               'project_no',
 #                               'river_lease_reserve_licence',
 #                               'river_lease_application_number',
 #                               'proposed_development_description',
 #                               'proposed_development_current_use_of_land',
 #                               'assessment_start_date'
 #                             ), css_class='panel-body',
 #                             ), css_class="panel-collapse collapse in",id="certificate_collapse",
 #                            ), css_class='panel panel-default'  
 #                           ),

#
#                          Fieldset('Documents',
#                                   'land_owner_consent',
#                                   'document_new_draft',
#                                   'document_draft',
#                                   'document_draft_signed',
#                                   'document_final',
#                                   'document_final_signed',
#                                   'document_determination',
#                                   'document_completion',
#                                   'river_lease_scan_of_application',
#                                   'deed',
#                                   'swan_river_trust_board_feedback',
#                                   'document_new_draft_v3',
#                                   'document_memo',
#                                   'document_determination',
#                                   'document_briefing_note',
#                                   'document_determination_approved'
#                          )
                        )

        if show_form_buttons == 'True':
#        if 'hide_form_buttons' in self.initial["workflow"]["hidden"]:
#             if self.initial["workflow"]["hidden"]["hide_form_buttons"] == 'False':
                  if 'condactions' in self.initial['workflow']:
                      if  self.initial['workflow']['condactions'] is not None:
                          for ca in self.initial['workflow']['condactions']:
                              if 'steplabel' in self.initial['workflow']['condactions'][ca]:
                                   self.helper = crispy_button(self.helper,ca,self.initial['workflow']['condactions'][ca]['steplabel'])
                      else:
                          self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
                          self.helper.add_input(Submit('cancel', 'Cancel'))

        if 'assessment_start_date' in self.fields:
            self.fields['assessment_start_date'].label = "Start Date" 
        #self.fields['applicant'].disabled = True

        self.helper.form_id = 'id_form_update_part_5'
        self.helper.form_class = 'form-horizontal form_fields'
        self.helper.attrs = {'novalidate': ''}
#        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
 #       self.helper.add_input(Submit('cancel', 'Cancel'))
   
        
class ApplicationEmergencyForm(ModelForm):


    lot = CharField(required=False)
    reserve_number = CharField(required=False)
    town_suburb = CharField(required=False)
    nearest_road_intersection = CharField(required=False)
    local_government_authority = CharField(required=False)
    street_number_and_name = CharField(required=False, label='Street Address')
    over_water = ChoiceField(choices=Application.APP_YESNO, widget=RadioSelect(attrs={'class':'radio-inline'}))

    class Meta:
        model = Application
        fields = ['title','applicant', 'organisation', 'proposed_commence', 'proposed_end','over_water']

    def __init__(self, *args, **kwargs):
        super(ApplicationEmergencyForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()
        self.helper.form_id = 'id_form_update_emergency'
        self.helper.attrs = {'novalidate': ''}

        self.fields['applicant'].disabled = True
        self.fields['applicant'].required = True
        # Add labels and help text for fields
        self.fields['proposed_commence'].label = "Start date"
        self.fields['proposed_end'].label = "Expiry date"
        self.fields['over_water'].label = "Are any proposed works, acts or activities in or over waters?"

        changeapplicantbutton = crispy_button_link('Change Applicant or Organisation',reverse('applicant_change', args=(self.initial['application_id'],)))
        crispy_boxes = crispy_empty_box()
        organisation = self.initial['organisation']

        if organisation is not None:
            applicant_info = HTML('{% include "applications/organisation_update_snippet.html" %}')
        else: 
            applicant_info = HTML('{% include "applications/applicant_update_snippet.html" %}')

        crispy_boxes.append(crispy_box('emergency_collapse', 'form_emergency' , 'Emergency Works',applicant_info,changeapplicantbutton,'organisation'))
        crispy_boxes.append(crispy_box('emergency_period_collapse', 'form_emergency_period' , 'Emergency Works Period', 'title', 'proposed_commence', 'proposed_end',))
        crispy_boxes.append(crispy_box('location_collapse', 'form_location' , 'Location','location_of_title_volume','street_number_and_name','lot','reserve_number','town_suburb','nearest_road_intersection','local_government_authority','over_water'))

        crispy_boxes.append(HTML('{% include "applications/application_conditions.html" %}'))
        dynamic_selections = HTML('{% include "applications/application_form_emergency_works_js_dynamics.html" %}')

        if 'condactions' in self.initial['workflow']:
             if  self.initial['workflow']['condactions'] is not None:
                 for ca in self.initial['workflow']['condactions']:
                     if 'steplabel' in self.initial['workflow']['condactions'][ca]:
                          self.helper = crispy_button(self.helper,ca,self.initial['workflow']['condactions'][ca]['steplabel'])
             else:
                 self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
                 #self.helper.add_input(Submit('cancel', 'Cancel'))


        del self.fields['applicant']
        del self.fields['organisation']

        for fielditem in self.initial["disabledfields"]:
            if fielditem in self.fields:
                self.fields[fielditem].disabled = True

        self.helper.layout = Layout(crispy_boxes,dynamic_selections)

class ApplicationLodgeForm(Form):
    """A basic form to submit a request to lodge an application.
    """

    def __init__(self, *args, **kwargs):
        kwargs.pop('instance')  # Don't need this because this isn't a ModelForm.
        super(ApplicationLodgeForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_lodge_application'
        self.helper.layout = Layout(
            HTML('<p>Confirm that this application should be lodged for assessment:</p>'),
            FormActions(
                Submit('lodge', 'Lodge', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )

class ApplicationReferralConditionsPart5(ModelForm):

    comments = CharField(required=False,max_length=255, widget=Textarea)
    proposed_conditions = CharField(required=False,max_length=255, widget=Textarea)
    #records = FileField(required=False, max_length=128, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'})) 
    #records = FileField(required=False, max_length=128, widget=AjaxClearableFileInput())
    records = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Documents') 

    class Meta:
        model = Application
        fields = ['applicant']

    def __init__(self, *args, **kwargs):

        # User must be passed in as a kwarg.
        super(ApplicationReferralConditionsPart5, self).__init__(*args, **kwargs)
        crispy_boxes = crispy_empty_box()
        if self.initial['response_date'] is None and int(self.initial['state']) == 3 and self.initial['referral_status'] == 1:
             pass
        else:
            if self.initial['referral_status'] != 5:
                crispy_boxes.append(HTML("<div class='alert alert-success'>Thank you,  referral completed</div>"))

        # 
        crispy_boxes.append(crispy_box('read_this_collapse','form_read_this','Read This',HTML('{% include "public/read_this_snipplet.html" %}')))

        organisation = self.initial['organisation']
        if organisation is not None:
            applicant_info = HTML('{% include "applications/organisation_update_snippet.html" %}')
        else:
            applicant_info = HTML('{% include "applications/applicant_update_snippet.html" %}')

        crispy_boxes.append(crispy_box('applicant_collapse','form_applicant','Applicant', applicant_info))
        del self.fields['applicant']

        if self.initial['comments'] is None:
               self.initial['comments'] = ''
        if self.initial['proposed_conditions'] is None:
               self.initial['proposed_conditions'] = ''
        

        crispy_boxes.append(crispy_box('title_collapse','form_title','Title',HTML('{% include "public/title.html" %}')))

        # permit
        if self.initial['application_app_type'] == 1:
                crispy_boxes.append(HTML('{% include "public/location_permit_referral_feedback.html" %}'))
        if self.initial['application_app_type'] == 1:
                crispy_boxes.append(HTML('{% include "public/other_info_permit_referral_feedback.html" %}'))
        if self.initial['application_app_type'] == 1:
                crispy_boxes.append(HTML('{% include "public/description_permit_referral_feedback.html" %}'))
        if self.initial['application_app_type'] == 1:
                crispy_boxes.append(HTML('{% include "public/landowner_consent_permit_referral_feedback.html" %}'))

        # license
        if self.initial['application_app_type'] == 2:
                 crispy_boxes.append(HTML('{% include "public/propsosed_commercial_activity_license_referral_feedback.html" %}'))
        if self.initial['application_app_type'] == 2:
                 crispy_boxes.append(HTML('{% include "public/vessel_details_license_referral_feedback.html" %}'))
        if self.initial['application_app_type'] == 2:
                 crispy_boxes.append(HTML('{% include "public/proposal_details_license_referral_feedback.html" %}'))
        if self.initial['application_app_type'] == 2:
                 crispy_boxes.append(HTML('{% include "public/other_documents_license_referral_feedback.html" %}'))
        if self.initial['application_app_type'] == 2:
                 crispy_boxes.append(HTML('{% include "public/landowner_consent_license_referral_feedback.html" %}'))

#        crispy_boxes.append(crispy_box('river_licence_collapse','river_licence_title','River Licence',HTML('{% include "public/river_reserve_licence_snippet.html" %}')))
        if self.initial['application_app_type'] == 3 or self.initial['application_app_type'] == 6:
               crispy_boxes.append(HTML('{% include "public/river_reserve_licence_snippet.html" %}'))
        if self.initial['application_app_type'] == 3 or self.initial['application_app_type'] == 6:
               crispy_boxes.append(HTML('{% include "public/details_of_proposed_develeopment_snipplet.html" %}'))

 
        # submission
        if self.initial['response_date'] is None and int(self.initial['state']) == 3 and self.initial['referral_status'] == 1:
            crispy_boxes.append(crispy_box('feedback_collapse','form_feecback','Feedback',crispy_para(self.initial['referral_name'] + ' (' + self.initial['referral_email'] + ') '),'comments','proposed_conditions','records',Submit('submitfeedback', 'Submit', css_class='btn-lg')))
        else:
            if self.initial['referral_status'] != 5:
                crispy_boxes.append(crispy_box('feedback_completed_collapse','form_completed_feecback','Feedback Completed',crispy_para_with_label('Comments',self.initial['comments']),crispy_para_with_label('Proposed Conditions',self.initial['proposed_conditions']),  HTML('{% include "public/referral_attachments.html" %}')))

        self.helper = BaseFormHelper()
        self.helper.layout = Layout(crispy_boxes,)
        self.helper.form_id = 'id_form_create_application'
        self.helper.attrs = {'novalidate': ''}


class ReferralForm(ModelForm):
    referee = forms.ModelChoiceField(
        queryset=SystemUser.objects.all().exclude(ledger_id__isnull=True),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Referral
        fields = ['period', 'details']

    def __init__(self, *args, **kwargs):
        # Application must be passed in as a kwarg.
        app = kwargs.pop('application')
        super(ReferralForm, self).__init__(*args, **kwargs)
        self.helper = PopupFormHelper(self)
        self.helper.form_id = 'id_form_modals'
        self.helper.attrs = {'novalidate': ''}
        
        # Limit the referee queryset
        referee_group = SystemGroup.objects.get(name='Statdev Referee')
        all_referees = app.referral_set.all().distinct('referee')
        referee_ids = all_referees.values_list('referee', flat=True)
        group_members_list = referee_group.get_system_group_member_ids()
        self.fields['referee'].queryset = SystemUser.objects.filter(ledger_id__in=group_members_list).exclude(id__in=referee_ids)
        
        # Define the form layout, placing the referee field at the top
        self.helper.layout = Layout(
            'referee',
            'period',
            'details',
            FormActions(
                Submit('save', 'Save', css_class='btn-lg ajax-submit'),
                Submit('cancel', 'Cancel', css_class='ajax-close')
            )
        )


class ReferralCompleteForm(ModelForm):
    class Meta:
        model = Referral
        fields = ['feedback']

    def __init__(self, *args, **kwargs):
        super(ReferralCompleteForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_referral_complete'
        self.helper.add_input(Submit('complete', 'Complete', css_class='btn-lg ajax-submit'))
        self.helper.add_input(Submit('cancel', 'Cancel', css_class='ajax-close'))


class ReferralRecallForm(Form):
    """A basic form to submit a request to lodge an application.
    """
    def __init__(self, *args, **kwargs):
        kwargs.pop('instance')  # Don't need this because this isn't a ModelForm.
        super(ReferralRecallForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_modals'
        self.helper.add_input(Submit('recall', 'Recall', css_class='btn-lg ajax-submit'))
        self.helper.add_input(Submit('cancel', 'Cancel', css_class='ajax-close'))


class ReferralRemindForm(Form):
    """Form is to allow a referral to be reminded about the outstanding feedback
    """
    def __init__(self, *args, **kwargs):
        kwargs.pop('instance')  # Don't need this because this isn't a ModelForm.
        super(ReferralRemindForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_modals'
        self.helper.add_input(Submit('remind', 'Remind', css_class='btn-lg ajax-submit'))
        self.helper.add_input(Submit('cancel', 'Cancel', css_class='ajax-close'))


class ReferralResendForm(Form):
    """Form is to allow a admin officer to resend the referral back to the referral for additional feedback
    """
    def __init__(self, *args, **kwargs):
        kwargs.pop('instance')  # Don't need this because this isn't a ModelForm.
        super(ReferralResendForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_modals'
        self.helper.add_input(Submit('remind', 'Resend', css_class='btn-lg ajax-submit'))
        self.helper.add_input(Submit('cancel', 'Cancel', css_class='ajax-close'))

class ReferralDeleteForm(Form):
    """Form is to allow a referral to be reminded about the outstanding feedback
    """
    def __init__(self, *args, **kwargs):
        kwargs.pop('instance')  # Don't need this because this isn't a ModelForm.
        super(ReferralDeleteForm, self).__init__(*args, **kwargs)
        self.helper = ButtonBaseFormHelper(self)
#       self.helper.form_id = 'id_form_referral_delete'
        self.helper.form_id = 'id_form_modals'
        self.helper.add_input(Submit('delete', 'Delete', css_class='btn-lg ajax-submit'))
        self.helper.add_input(Submit('cancel', 'Cancel', css_class='ajax-close' ))

class PersonOrgDeleteForm(Form):
    """Form is to allow a organisation to be unlinked from people 
    """
    def __init__(self, *args, **kwargs):
        kwargs.pop('instance')  # Don't need this because this isn't a ModelForm.
        super(ReferralDeleteForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_person_org_delete'
        self.helper.add_input(Submit('delete', 'Delete', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))


class VesselDeleteForm(Form):
    """Form is to allow a referral to be reminded about the outstanding feedback
    """
    def __init__(self, *args, **kwargs):
        kwargs.pop('instance')  # Don't need this because this isn't a ModelForm.
        super(VesselDeleteForm, self).__init__(*args, **kwargs)
        self.helper = PopupFormHelper(self)
        #self.helper.form_id = 'id_form_vessel_delete'
        self.helper.form_id = 'id_form_modals'
        self.helper.add_input(Submit('delete', 'Delete', css_class='btn-lg ajax-submit'))
        self.helper.add_input(Submit('cancel', 'Cancel', css_class='ajax-close' ))

class ComplianceCompleteExternal(ModelForm):
    """Compliance Complete form External
    """
    #records = FileField(required=False, max_length=128, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}))
    records = FileField(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Documents')

    class Meta:
        model = Compliance
        fields = ['comments']

    def __init__(self, *args, **kwargs):
        super(ComplianceCompleteExternal, self).__init__(*args, **kwargs)
        self.helper = FullBaseFormHelper(self)
        self.helper.attrs = {'novalidate': ''}
        #compliance_detail_external.html

        dynamic_selections = HTML('{% include "applications/compliance_detail_external.html" %}')
        self.helper.layout = Layout(dynamic_selections ,'comments','records',)

        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
        self.helper.add_input(Submit('submit', 'Submit', css_class='btn-lg'))

class ComplianceCompleteInternal(ModelForm):
    """Compliance Complete form External
    """
    ACTION = Choices((0, 'none', ('None'))  )

    #records = FileField(required=False, max_length=128, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}))
    records = FileField(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Documents')
    action = ChoiceField(choices=ACTION, widget=forms.Select())
    internal_comments = CharField(required=False, widget=Textarea, help_text='Comment is added to communication log')
    internal_documents = FileField(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Internal Documents (Comms Log)')
    external_documents = FileField(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='External Documents (holder sees)')

    class Meta:
        model = Compliance
        fields = ['external_comments']

    def __init__(self, *args, **kwargs):
        super(ComplianceCompleteInternal, self).__init__(*args, **kwargs)
        self.helper = FullBaseFormHelper(self)
        self.helper.attrs = {'novalidate': ''}
        #compliance_detail_external.html

        if self.initial['status'] == 6:
             self.fields['action'].choices = Choices((0, 'none', ('None')), (1, 'approve', ('Approve')),(4, 'assesor', ('Send to Assesor')),)
        if self.initial['status'] == 5:
             self.fields['action'].choices = Choices((0, 'none', ('None')), (1, 'approve', ('Approve')), (2, 'sendtomanager', ('Send to Manager')), (3, 'licence_holder', ('Return to licence holder')))
        self.helper.layout = Layout('action', 'external_comments','external_documents','internal_comments','internal_documents')

        self.helper.add_input(Submit('submit', 'Submit', css_class='btn-lg'))


class ComplianceComplete(ModelForm):
    """Compliance Complete form
    """
    #records = FileField(required=False, max_length=128, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}))
    records = FileField(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Documents')

    class Meta:
        model = Compliance
        fields = ['condition','comments']

    def __init__(self, *args, **kwargs):
        super(ComplianceComplete, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.attrs = {'novalidate': ''}
        self.fields['condition'].required = True
        self.fields['condition'].disabled = True
        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))

class ConditionSuspension(ModelForm):
    """Condition suspension Form
    """
    #records = FileField(required=False, max_length=128, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}))
    class Meta:
        model = Condition
        fields = ['suspend',]

    def __init__(self, *args, **kwargs):
        super(ConditionSuspension, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.attrs = {'novalidate': ''}
        del self.fields['suspend']
#        self.fields['condition'].required = True
#        self.fields['condition'].disabled = True
        self.helper.form_id = 'id_form_modals'
        if self.initial['actionkwargs'] == 'suspend': 
           self.helper.add_input(Submit('save', 'Suspend Condition', css_class='btn-lg ajax-submit'))
        else:
           self.helper.add_input(Submit('save', 'Unsuspend Condition', css_class='btn-lg ajax-submit'))

        self.helper.add_input(Submit('cancel', 'Cancel' , css_class='ajax-close'))

class ConditionCreateForm(ModelForm):
    predefined_conditions = ModelChoiceField(queryset=ConditionPredefined.objects.filter(status=1).order_by('title'), help_text="Select a predefined condition from the drop down to append condition rules to condition automtically.", widget=forms.Select(attrs={'class': 'form-control'})) 

    class Meta:
        model = Condition
        fields = ['predefined_conditions','condition_no','condition', 'due_date', 'recur_pattern', 'recur_freq','advise_no','advise']

    def __init__(self, *args, **kwargs):
        super(ConditionCreateForm, self).__init__(*args, **kwargs)
        self.helper = PopupFormHelper(self)
        self.fields['recur_pattern'].widget = forms.Select(attrs={'class': 'form-control'})
        self.fields['recur_pattern'].choices = self.fields['recur_pattern'].choices

        if self.initial['may_assessor_advise'] != True:
            self.fields['predefined_conditions'].required = False
            pass
        else:
            del self.fields['advise']
            del self.fields['predefined_conditions']

        self.fields['condition'].required = False
        self.fields['advise'].required = False

        self.helper.attrs = {'novalidate': ''}
        self.helper.form_id = 'id_form_modals'
        self.fields['condition'].required = True
        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg ajax-submit'))
        self.helper.add_input(Submit('cancel', 'Cancel', css_class='ajax-close'))

    def clean(self):
        cleaned_data = super(ConditionCreateForm, self).clean()
        condition = self.cleaned_data.get('condition')
        advise = self.cleaned_data.get('advise')
        if condition is None:
            condition = ''
        if advise is None:
            advise = ''

        if len(condition) == 0 and len(advise) == 0:
              raise forms.ValidationError('Please complete condition or advise.')
        return cleaned_data


class ConditionUpdateForm(ModelForm):
    class Meta:
        model = Condition
        fields = ['condition_no','condition', 'due_date', 'recur_pattern', 'recur_freq','advise_no','advise']

    def __init__(self, *args, **kwargs):
        super(ConditionUpdateForm, self).__init__(*args, **kwargs)
        self.helper = PopupFormHelper(self)
	# self.helper.form_id = 'id_form_condition_apply'

        if self.initial['may_assessor_advise'] != True:
            pass
        else:
            del self.fields['advise']

        self.fields['condition'].required = False
        self.fields['advise'].required = False

        self.helper.form_id = 'id_form_modals'
        self.helper.add_input(Submit('update', 'Update', css_class='btn-lg ajax-submit'))
        self.helper.add_input(Submit('cancel', 'Cancel', css_class='ajax-close' ))

    def clean(self):
        cleaned_data = super(ConditionUpdateForm, self).clean()
        condition = self.cleaned_data.get('condition')
        advise = self.cleaned_data.get('advise')
        if len(condition) == 0 and len(advise) == 0:
              raise forms.ValidationError('Please complete condition or advise.')

        return cleaned_data


class ConditionActionForm(ModelForm):
    class Meta:
        model = Condition
        fields = ['condition', 'due_date', 'recur_pattern', 'recur_freq']

    def __init__(self, *args, **kwargs):
        super(ConditionActionForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
#        self.helper.form_id = 'id_form_condition_action'
        self.helper.form_id = 'id_form_modals'
        self.fields['condition'].disabled = True
        self.fields['due_date'].disabled = True
        self.helper.add_input(Submit('update', 'Update', css_class='btn-lg ajax-submit'))
        self.helper.add_input(Submit('cancel', 'Cancel'))


class OldConditionActionForm(ConditionUpdateForm):
    """A extension of ConditionUpdateForm with the condition field disabled.
    """
    # broken for some reason end up copying ConditionUpdateForm and adjusting.  kept getting bool error on this one.
    class Meta:
        model = Condition
        fields = ['condition', 'due_date', 'recur_pattern', 'recur_freq']

    def __init__(self, *args, **kwargs):
        super(OldConditionActionForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_condition_action'
        self.fields['condition'].disabled = True
        self.fields['due_date'].disabled = True
 #       self.fields['recur_pattern'] = True
#        self.fields['recur_freq'] = True
        self.helper.add_input(Submit('update', 'Update', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))

class ApplicationAssignNextAction(ModelForm):
    """A form for assigning an application back to a group.
    """
    details = CharField(required=False, widget=Textarea, help_text='Detailed information for communication log.')
    submitter_comment = CharField(required=False, widget=Textarea, help_text='Reason to show to submitter')
    #records = FileField(required=False, max_length=128, widget=ClearableFileInput)
#    records = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}), label='Documents')
    records = FileField(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Documents (communication log only)')
    attach_to_email = Field(required=False, widget=AjaxFileUploader(attrs={}),  label='Attach to Email', help_text='')

    class Meta:
        model = Application
        fields = ['id','details','submitter_comment','referral_comment','records']

    def __init__(self, *args, **kwargs):
        super(ApplicationAssignNextAction, self).__init__(*args, **kwargs)

        self.helper = BaseFormHelper(self)

        self.helper.form_id = 'id_form_assigngroup_application'
        self.helper.attrs = {'novalidate': ''}

        submitter_input = None
        if self.initial['action'] != 'creator':
            del self.fields['submitter_comment']
        if self.initial['action'] != 'referral':
            del self.fields['referral_comment']
        if 'allow_email_attachment' in self.initial:
            if self.initial['allow_email_attachment'] == False:
                del self.fields['attach_to_email']
        else:
            del self.fields['attach_to_email']
#            submitter_input = 'sumbitter_comment'

        self.helper.layout = Layout(
            HTML('<p>Application Next Action</p>'),
            'details','submitter_comment','records','referral_comment','attach_to_email',
            FormActions(
                Submit('assign', 'Submit', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )
#        self.fields['title'].disabled = True
#        self.helper.add_input(Submit('assign', 'Assign', css_class='btn-lg'))
#        self.helper.add_input(Submit('cancel', 'Cancel'))


class AssignPersonForm(ModelForm):
    """A form for assigning an application to people with a specific group.
    """
    assignee = forms.ModelChoiceField(
        queryset=SystemUser.objects.all().exclude(ledger_id__isnull=True),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    class Meta:
        model = Application
        #fields = ['app_type', 'title', 'description', 'submit_date', 'assignee']
        fields = []

    def __init__(self, *args, **kwargs):
        super(AssignPersonForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_assign_person_application'
        self.helper.attrs = {'novalidate': ''}
        # Limit the assignee queryset.
        assigngroup = SystemGroup.objects.get(name=self.initial['assigngroup'])
        usergroups = assigngroup.get_system_group_member_ids()
        self.fields['assignee'].queryset = SystemUser.objects.filter(ledger_id__in=usergroups)
        self.fields['assignee'].required = True
        # Disable all form fields.
        for k, v in self.fields.items():
            self.fields[k].disabled = True
        # Re-enable the assignee field.
        self.fields['assignee'].disabled = False
        #self.initial["fieldstatus"]:
        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Assign this application for processing:</p>'),
            #'app_type', 'title', 'description', 'submit_date', 'assignee',
            'assignee',
            FormActions(
                Submit('assign', 'Assign', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )

class AssignCancelForm(ModelForm):
    """A form for assigning an application to people with a specific group.
    """

    class Meta:
        model = Application
        #fields = ['app_type', 'title', 'description', 'submit_date', 'assignee']
        fields = []

    def __init__(self, *args, **kwargs):
        super(AssignCancelForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_assign_cancel_application'
        self.helper.attrs = {'novalidate': ''}
        # Limit the assignee queryset.
        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Are you sure you want to cancel this application:</p>'),
            FormActions(
                Submit('cancel-application', 'Cancel Application', css_class='btn-lg'),
            )
        )


class AssignOfficerForm(ModelForm):
    """A form for assigning an application to people with a specific group.
    """
    assigned_officer = forms.ModelChoiceField(
        queryset=SystemUser.objects.all().exclude(ledger_id__isnull=True),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Application
        #fields = ['app_type', 'title', 'description', 'submit_date', 'assignee']
        fields = []

    def __init__(self, *args, **kwargs):
        super(AssignOfficerForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_assign_officer_application'
        self.helper.attrs = {'novalidate': ''}
        # Limit the assignee queryset.
        assigngroup = SystemGroup.objects.get(name=self.initial['assigngroup'])
        users_in_group = assigngroup.get_system_group_member_ids()
        self.fields['assigned_officer'].queryset = SystemUser.objects.filter(ledger_id__in=users_in_group)
        self.fields['assigned_officer'].required = True
        # Disable all form fields.
        for k, v in self.fields.items():
            self.fields[k].disabled = True
        # Re-enable the assignee field.
        self.fields['assigned_officer'].disabled = False
        #self.initial["fieldstatus"]:
        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Assign this application an officer:</p>'),
            #'app_type', 'title', 'description', 'submit_date', 'assignee',
            'assigned_officer',
            FormActions(
                Submit('assign', 'Assign', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )



class ComplianceAssignPersonForm(ModelForm):
    """A form for assigning an application to people with a specific group.
    """
    assignee = forms.ModelChoiceField(
        queryset=SystemUser.objects.all().exclude(ledger_id__isnull=True),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Application
        #fields = ['app_type', 'title', 'description', 'submit_date', 'assignee']
        fields = []

    def __init__(self, *args, **kwargs):
        super(ComplianceAssignPersonForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_assign_person_application'
        self.helper.attrs = {'novalidate': ''}
        # Limit the assignee queryset.
        assigngroup = SystemGroup.objects.get(name=self.initial['assigngroup'])
        usergroups = assigngroup.get_system_group_member_ids()
        self.fields['assignee'].queryset = SystemUser.objects.filter(ledger_id__in=usergroups)
        self.fields['assignee'].required = True
        # Disable all form fields.
        for k, v in self.fields.items():
            self.fields[k].disabled = True
        # Re-enable the assignee field.
        self.fields['assignee'].disabled = False
        #self.initial["fieldstatus"]:
        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Assign this application for processing:</p>'),
            #'app_type', 'title', 'description', 'submit_date', 'assignee',
            'assignee',
            FormActions(
                Submit('assign', 'Assign', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )

class AssignApplicantForm(ModelForm):
    """A form for assigning or change the applicant on application.
    """
    applicant = forms.ModelChoiceField(
        queryset=SystemUser.objects.all().exclude(ledger_id__isnull=True),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    class Meta:
        model = Application
        #fields = ['app_type', 'title', 'description', 'submit_date', 'assignee']
        fields = []

    def __init__(self, *args, **kwargs):
        super(AssignApplicantForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_assign_person_application'
        self.helper.attrs = {'novalidate': ''}
        # Limit the assignee queryset.
        applicant = self.initial['applicant']
        self.fields['applicant'].queryset = SystemUser.objects.filter(id=applicant)
        self.fields['applicant'].required = True
        self.fields['applicant'].disabled = True
     
        #user_orgs = [d.pk for d in Delegate.objects.filter(email_user=applicant)]
        #self.fields['organisation'].queryset = Organisation.objects.filter(pk__in=user_orgs)

        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Assign this application for processing:</p>'),
            #'app_type', 'title', 'description', 'submit_date', 'assignee',
            'applicant',
            'organisation',
            FormActions(
                Submit('assign', 'Assign Applicant', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )


class ComplianceSubmitForm(ModelForm):
    """A form for assigning or change the applicant on application.
    """

    class Meta:
        model = Application
        #fields = ['app_type', 'title', 'description', 'submit_date', 'assignee']
        fields = ['id']

    def __init__(self, *args, **kwargs):
        super(ComplianceSubmitForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_compliance_submit'
        self.helper.attrs = {'novalidate': ''}

        # Limit the assignee queryset.
#       print "action" 
#       print self.initial['action']

        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Are you sure you want submit for approval?</p>'),
            #'app_type', 'title', 'description', 'submit_date', 'assignee',
            FormActions(
                Submit('Submit', 'Submit', css_class='btn-lg'),
                Submit('Back', 'Back')
            )
        )


class ComplianceStaffForm(ModelForm):
    """A form for assigning or change the applicant on application.
    """

    class Meta:
        model = Application
        #fields = ['app_type', 'title', 'description', 'submit_date', 'assignee']
        fields = ['id']

    def __init__(self, *args, **kwargs):
        super(ComplianceStaffForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_compliance_submit'
        self.helper.attrs = {'novalidate': ''}
        # Limit the assignee queryset.
#       print "action"
#       print self.initial['action']

        preconfirmtext=''
        if self.initial['action'] == 'manager':
            preconfirmtext= 'Are you sure you want to assign to the manager group?'
        elif self.initial['action'] == 'approve':
            preconfirmtext= 'Are you sure you want to approve this clearance of condition?'
        elif self.initial['action'] == 'holder':
            preconfirmtext= 'Are you sure you want to assign to holder?'
        elif self.initial['action'] == 'assessor':
            preconfirmtext= 'Are you sure you want to assign to assessor?'

        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>'+preconfirmtext+'</p>'),
            #'app_type', 'title', 'description', 'submit_date', 'assignee',
            FormActions(
                Submit('Submit', 'Submit', css_class='btn-lg'),
                Submit('Back', 'Back')
            )
        )

class ApplicationDiscardForm(ModelForm):
    """A form for assigning or change the applicant on application.
    """

    class Meta:
        model = Application
        #fields = ['app_type', 'title', 'description', 'submit_date', 'assignee']
        fields = ['id']

    def __init__(self, *args, **kwargs):
        super(ApplicationDiscardForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_assign_person_application'
        self.helper.attrs = {'novalidate': ''}
        # Limit the assignee queryset.

        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Are  you sure you want to delete this application.</p>'),
            #'app_type', 'title', 'description', 'submit_date', 'assignee',
            FormActions(
                Submit('discard', 'Discard', css_class='btn-lg'),
                Submit('Back', 'Back')
            )
        )


class AssignApplicantFormCompany(ModelForm):
    """A form for assigning or change the applicant on application.
    """

    class Meta:
        model = Application
        #fields = ['app_type', 'title', 'description', 'submit_date', 'assignee']
        fields = ['organisation']

    def __init__(self, *args, **kwargs):
        super(AssignApplicantFormCompany, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_assign_person_application'
        self.helper.attrs = {'novalidate': ''}
        # Limit the assignee queryset.

        organisation = self.initial['organisation']
        self.fields['organisation'].queryset = Organisation.objects.filter(pk=organisation)
        self.fields['organisation'].required = True
        self.fields['organisation'].disabled = True

#        user_orgs = [d.pk for d in Delegate.objects.filter(email_user=applicant)]
 #       self.fields['organisation'].queryset = Organisation.objects.filter(pk__in=user_orgs)

        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Assign this application for processing:</p>'),
            #'app_type', 'title', 'description', 'submit_date', 'assignee',
            'applicant',
            'organisation',
            FormActions(
                Submit('assign', 'Change Applicant', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )


class AssignCustomerForm(ModelForm):
    """A form for assigning an application back to the customer.
    """
    feedback = CharField(
        required=False, widget=Textarea, help_text='Feedback to be provided to the customer.')

    class Meta:
        model = Application
        fields = ['app_type', 'title', 'description']

    def __init__(self, *args, **kwargs):
        super(AssignCustomerForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_assign_application'
        self.helper.attrs = {'novalidate': ''}
        # Disable all form fields.
        for k, v in self.fields.items():
            self.fields[k].disabled = True
        # Re-enable the feedback field.
        self.fields['feedback'].disabled = False
        self.fields['feedback'].required = True
        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Reassign this application back to the applicant, with feedback:</p>'),
            'app_type', 'title', 'description', 'feedback',
            FormActions(
                Submit('assign', 'Assign', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )


class AssignProcessorForm(ModelForm):
    """A form for assigning a processor (admin officer) to an application.
    """

    class Meta:
        model = Application
        #fields = ['app_type', 'title', 'description', 'submit_date', 'assignee']
        fields = ['assignee']

    def __init__(self, *args, **kwargs):
        super(AssignProcessorForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_assign_application'
        self.helper.attrs = {'novalidate': ''}
        # Limit the assignee queryset.
        processor = Group.objects.get(name='Statdev Processor')
        self.fields['assignee'].queryset = User.objects.filter(groups__in=[processor])
        self.fields['assignee'].required = True
        # Disable all form fields.
        for k, v in self.fields.items():
            self.fields[k].disabled = True
        # Re-enable the assignee field.
        self.fields['assignee'].disabled = False
        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Assign this application for processing:</p>'),
            #'app_type', 'title', 'description', 'submit_date', 'assignee',
            'assignee',
            FormActions(
                Submit('assign', 'Assign', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )


class AssignAssessorForm(ModelForm):
    """A form for assigning an assessor to an application.
    """
    class Meta:
        model = Application
        #fields = ['app_type', 'title', 'description', 'submit_date', 'assignee']
        fields = ['assignee']

    def __init__(self, *args, **kwargs):
        super(AssignAssessorForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_assign_application'
        self.helper.attrs = {'novalidate': ''}
        # Limit the assignee queryset.
        assessor = Group.objects.get(name='Statdev Assessor')
        self.fields['assignee'].queryset = User.objects.filter(groups__in=[assessor])
        self.fields['assignee'].required = True
        # Disable all form fields.
        for k, v in self.fields.items():
            self.fields[k].disabled = True
        # Re-enable the assignee field.
        self.fields['assignee'].disabled = False
        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Assign this application for assessment:</p>'),
            #'app_type', 'title', 'description', 'submit_date', 'assignee',
            'assignee',
            FormActions(
                Submit('assign', 'Assign', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )


class AssignApproverForm(ModelForm):
    """A form for assigning a manager to approve an application.
    """
    class Meta:
        model = Application
        #fields = ['app_type', 'title', 'description', 'submit_date', 'assignee']
        fields = ['assignee']

    def __init__(self, *args, **kwargs):
        super(AssignApproverForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_approve_application'
        self.helper.attrs = {'novalidate': ''}
        # Limit the assignee queryset.
        approver = Group.objects.get(name='Statdev Approver')
        self.fields['assignee'].queryset = User.objects.filter(groups__in=[approver])
        self.fields['assignee'].required = True
        self.fields['assignee'].label = 'Manager'
        # Disable all form fields.
        for k, v in self.fields.items():
            self.fields[k].disabled = True
        # Re-enable the assignee field.
        self.fields['assignee'].disabled = False
        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Assign this application to a manager for approval/issue:</p>'),
            #'app_type', 'title', 'description', 'submit_date', 'assignee',
            'assignee',
            FormActions(
                Submit('assign', 'Assign', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )


class AssignEmergencyForm(ModelForm):
    """A form for assigning an emergency works to a user with the Emergency group.
    """
    class Meta:
        model = Application
        fields = ['assignee']

    def __init__(self, *args, **kwargs):
        super(AssignEmergencyForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_assign_emergency_application'
        self.helper.attrs = {'novalidate': ''}
        # Limit the assignee queryset.
        emergency = Group.objects.get(name='Statdev Emergency')
        self.fields['assignee'].queryset = User.objects.filter(groups__in=[emergency])
        self.fields['assignee'].required = True
        # Disable all form fields.
        for k, v in self.fields.items():
            self.fields[k].disabled = True
        # Re-enable the assignee field.
        self.fields['assignee'].disabled = False


        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Assign this Emergency Works to a new Admin officer:</p>'),
            'assignee',
            FormActions(
                Submit('assign', 'Assign', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )


class ApplicationIssueForm(ModelForm):
    assessment = ChoiceField(choices=[
        (None, '---------'),
        ('issue', 'Issue'),
        ('decline', 'Decline'),
        # TODO: Return to assessor option.
        #('return', 'Return to assessor'),
    ])

    class Meta:
        model = Application
        fields = ['app_type', 'title', 'description', 'submit_date']

    def __init__(self, *args, **kwargs):
        super(ApplicationIssueForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_application_issue'
        self.helper.attrs = {'novalidate': ''}
        # Disable all form fields.
        for k, v in self.fields.items():
            self.fields[k].disabled = True
        # Re-enable the assessment field.
        self.fields['assessment'].disabled = False
        # Define the form layout.
        self.helper.layout = Layout(
            HTML('<p>Issue or decline this completed application:</p>'),
            'app_type', 'title', 'description', 'submit_date', 'assessment',
            FormActions(
                Submit('save', 'Save', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )


class ApplicationEmergencyIssueForm(ModelForm):
    #    assessment = ChoiceField(choices=[
    #    (None, '---------'),
    #    ('issue', 'Issue'),
    #    ('decline', 'Decline'),
    #])

    #    holder = CharField(required=False)
    #    abn = CharField(required=False)

    class Meta:
        model = Application
        fields = []

    def __init__(self, *args, **kwargs):
        super(ApplicationEmergencyIssueForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_application_issue'
        self.helper.attrs = {'novalidate': ''}
 #       self.fields['app_type'].required = False
        # Disable all form fields.
#        for k, v in self.fields.items():
#            self.fields[k].disabled = True
        # Re-enable the assessment field.
#        self.fields['assessment'].disabled = False

        crispy_boxes = crispy_empty_box()
        #crispy_boxes.append(crispy_box('emergency_collapse', 'form_emergency' , 'Emergency Works','holder', 'abn', 'issue_date', 'proposed_commence', 'proposed_end', 'assessment'))
 

        # Define the form layout.
        self.helper.layout = Layout(crispy_boxes,
            HTML('<p>Click Issue to issue this completed Emergency Works application:</p>'),
            FormActions(
                Submit('issue', 'Issue', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )

        #        self.fields['proposed_commence'].label = "Start Date"
#        self.fields['proposed_end'].label = "Expiry Date"

class ComplianceCreateForm(ModelForm):
    supporting_document = FileField(required=False, max_length=128)

    class Meta:
        model = Compliance
        fields = ['condition', 'compliance', 'supporting_document']

    def __init__(self, *args, **kwargs):
        # Application must be passed in as a kwarg.
        application = kwargs.pop('application')
        super(ComplianceCreateForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        self.fields['condition'].queryset = Condition.objects.filter(application=application)


class VesselForm(ModelForm):
#    registration = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}))
    registration = Field(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
    documents = Field(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
#MultiFileField(
 #       required=False, label='Registration & licence documents',
#        help_text='Choose multiple files to upload (if required). NOTE: this will replace any existing uploads.')

    class Meta:
        model = Vessel
        fields = ['vessel_type', 'name', 'vessel_id', 'size', 'engine', 'passenger_capacity','craft_type','number_of_crafts']

    def __init__(self, *args, **kwargs):
        # User must be passed in as a kwarg.
        super(VesselForm, self).__init__(*args, **kwargs)
        self.helper = PopupFormHelper()
        #self.helper.form_id = 'id_form_create_vessel'
        self.helper.form_id = 'id_form_modals'
        self.helper.attrs = {'novalidate': ''}
        #application_vessel_craft_js_dynamics.html
        self.fields['vessel_type'].widget.attrs.update({'class': 'form-control'})
        self.fields['name'].required = False
        self.fields['vessel_id'].required = False
        self.fields['size'].required = False
        self.fields['engine'].required = False
        self.fields['passenger_capacity'].required = False
        self.fields['craft_type'].required = False
        self.fields['number_of_crafts'].required = False

        dynamic_selections = HTML('{% include "applications/application_vessel_craft_js_dynamics.html" %}')
        self.helper.layout = Layout('vessel_type', 'name', 'vessel_id', 'size', 'engine', 'passenger_capacity','registration','craft_type','number_of_crafts','documents',dynamic_selections)

        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg ajax-submit'))
        self.helper.add_input(Submit('cancel', 'Cancel', css_class='ajax-close'))


class NewsPaperPublicationCreateForm(ModelForm):

    #records = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}))
    records = FileField(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Documents')

    class Meta:
        model = PublicationNewspaper
        fields = ['application','date','newspaper']

    def __init__(self, *args, **kwargs):
        super(NewsPaperPublicationCreateForm, self).__init__(*args, **kwargs)
        self.helper = PopupFormHelper()
#        self.helper.form_id = 'id_form_create_newspaperpublication'
        self.helper.form_id = 'id_form_modals' 
        self.helper.attrs = {'novalidate': ''}

        self.fields['application'].widget = HiddenInput()
        self.fields['date'].widget.attrs['autocomplete'] = 'off'
        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg ajax-submit'))
        self.helper.add_input(Submit('cancel', 'Cancel' , css_class='ajax-close'))


class WebsitePublicationCreateForm(ModelForm):

    original_document = FileField(required=False, max_length=128 , widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}))
    published_document = FileField(required=False, max_length=128 , widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}))

    class Meta:
        model = PublicationWebsite
#        fields = ['application','original_document','published_document']
        fields = ['application']

    def __init__(self, *args, **kwargs):
        super(WebsitePublicationCreateForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()
        self.fields['published_document'].label = 'To be published document'
        self.helper.form_id = 'id_form_create_websitepublication'
        self.helper.attrs = {'novalidate': ''}
#        self.fields['application'].widget = HiddenInput()
        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))

class WebsitePublicationForm(ModelForm):

    #original_document = FileField(required=False, max_length=128 , widget=ClearableFileInput)
    published_document = FileField(required=False, max_length=128 , widget=AjaxFileUploader())

    # original_document = IntegerField()
    class Meta:
        model = PublicationWebsite
#        fields = ['application','original_document']
        fields = ['application','published_document']
    def __init__(self, *args, **kwargs):
        super(WebsitePublicationForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()
    #    self.fields['published_document'].label = 'To be published document'
        self.helper.form_id = 'id_form_create_websitepublication'
        self.helper.attrs = {'novalidate': ''}
        self.fields['application'].widget = HiddenInput()
    #    self.fields['original_document'].widget = HiddenInput()
        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))


class FeedbackPublicationCreateForm(ModelForm):

    #records = FileField(required=False, max_length=128 , widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}))
    records = FileField(required=False, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Documents')

    class Meta:
        model = PublicationFeedback
        fields = ['application','name','address','suburb','state','postcode','phone','email','comments','status']

    def __init__(self, *args, **kwargs):
        super(FeedbackPublicationCreateForm, self).__init__(*args, **kwargs)
        self.helper = PopupFormHelper()
#        self.helper.form_id = 'id_form_create_websitepublication'
        self.helper.form_id = 'id_form_modals'
        self.helper.attrs = {'novalidate': ''}
        self.fields['application'].widget = HiddenInput()
        self.fields['status'].widget = HiddenInput()
        self.fields['state'].widget.attrs.update({'class': 'form-control'})
        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg ajax-submit'))
        self.helper.add_input(Submit('cancel', 'Cancel', css_class='ajax-close'))


class RecordCreateForm(ModelForm):
    class Meta:
        model = Record
        fields = ['upload', 'name', 'category', 'metadata']

    def __init__(self, *args, **kwargs):
        super(RecordCreateForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper()
        self.helper.form_id = 'id_form_create_document'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))


class SystemUserForm(ModelForm):

    class Meta:
        model = SystemUser
        fields = ['first_name', 'last_name', 'title', 'legal_dob', 'phone_number', 'mobile_number', 'fax_number']

    def __init__(self, *args, **kwargs):
        super(SystemUserForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_emailuser_account_update'
        self.helper.attrs = {'novalidate': ''}

        # Define the form layout.
        self.helper.layout = Layout(
            'first_name', 'last_name', 'title', 'legal_dob', 'phone_number', 'mobile_number', 'fax_number',
            FormActions(
                Submit('save', 'Save', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )


class OrganisationCertificateForm(ModelForm):
    identification = FileField(required=False, max_length=128, widget=ClearableFileInput)

    class Meta:
        model = OrganisationExtras
        fields = ['id']

    def __init__(self, *args, **kwargs):
        super(OrganisationCertificateForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_org_update'
        self.helper.attrs = {'novalidate': ''}

        # Define the form layout.
        self.helper.layout = Layout(
            'identification',
            FormActions(
                Submit('save', 'Save', css_class='btn-lg'),
                Submit('cancel', 'Cancel')
            )
        )


class AddressForm(ModelForm):

    class Meta:
        model = Address
        fields = ['line1', 'line2', 'line3', 'locality', 'state', 'country', 'postcode']

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)

        self.fields['locality'].label = 'Town/Suburb'
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_address'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))


class OrganisationAddressForm2(ModelForm):

    class Meta:
        model = OrganisationAddress
        fields = ['line1', 'line2', 'line3', 'locality', 'state', 'country', 'postcode']
#        fields = ['line1', 'line2',]
    def __init__(self, *args, **kwargs):
        super(OrganisationAddressForm2, self).__init__(*args, **kwargs)

        self.fields['locality'].label = 'Town/Suburb'
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_address'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))


class OrganisationForm(ModelForm):

    class Meta:
        model = Organisation
        fields = ['name', 'abn']

    def __init__(self, *args, **kwargs):
        super(OrganisationForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = 'Company name'
        #self.fields['identification'].label = 'Certificate of incorporation'
        #self.fields['identification'].help_text = 'Electronic copy of current certificate (e.g. image/PDF)'
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_organisation'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))

class OrganisationContactForm(ModelForm):

    class Meta:
        model = OrganisationContact
        fields = ['email', 'first_name','last_name','phone_number','mobile_number','fax_number']

    def __init__(self, *args, **kwargs):
        super(OrganisationContactForm, self).__init__(*args, **kwargs)
        #self.fields['name'].label = 'Company name'
        #self.fields['identification'].label = 'Certificate of incorporation'
        #self.fields['identification'].help_text = 'Electronic copy of current certificate (e.g. image/PDF)'
        self.helper = BaseFormHelper(self)
        self.helper.form_id = 'id_form_organisation'
        self.helper.attrs = {'novalidate': ''}
        self.helper.add_input(Submit('save', 'Save', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))


class DelegateAccessForm(Form):

    def __init__(self, *args, **kwargs):
        super(DelegateAccessForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.add_input(Submit('confirm', 'Confirm', css_class='btn-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel'))


class UnlinkDelegateForm(Form):

    def __init__(self, *args, **kwargs):
        super(UnlinkDelegateForm, self).__init__(*args, **kwargs)
        self.helper = BaseFormHelper(self)
        self.helper.add_input(Submit('unlink', 'Unlink user', css_class='btn-lg btn-danger'))
        self.helper.add_input(Submit('cancel', 'Cancel'))
