from __future__ import unicode_literals
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML, Hidden
from crispy_forms.bootstrap import FormActions
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django import forms
from django.forms import Form, ModelForm, ChoiceField, FileField, CharField, Textarea, ClearableFileInput, HiddenInput, Field, EmailField
from applications.widgets import ClearableMultipleFileInput, RadioSelectWithCaptions, AjaxFileUploader
from django_crispy_jcaptcha.widget import CaptchaImages, CaptchaValidation
from multiupload.fields import MultiFileField
# from ledger.accounts.models import EmailUser, Address, Organisation
from ledger_api_client.ledger_models import EmailUserRO as EmailUser, Address
from applications.models import Application, PublicationFeedback, Organisation
from applications.crispy_common import crispy_heading, crispy_box, crispy_empty_box, crispy_para, check_fields_exist, crispy_button_link, crispy_button, crispy_para_no_label, crispy_h1, crispy_h2, crispy_h3,crispy_h4,crispy_h5,crispy_h6

User = get_user_model()

class BaseFormHelper(FormHelper):
    form_class = 'form-horizontal'
    label_class = 'col-xs-12 col-sm-4 col-md-3 col-lg-2'
    field_class = 'col-xs-12 col-sm-8 col-md-6 col-lg-4'

class ApplicationPart5(ModelForm):
    name = CharField(required=False,max_length=255)
    address = CharField(required=False,max_length=255)
    suburb = CharField(required=False,max_length=255)
    state = ChoiceField(required=False, choices=PublicationFeedback.PUB_STATES_CHOICES) 
    post_code = CharField(required=False,max_length=4)
    phone = CharField(required=False,max_length=255)
    email = EmailField(required=False,max_length=255)
    email_confirm = EmailField(required=False,max_length=255)
    comments = CharField(required=False,max_length=255, widget=Textarea)
    #records = FileField(required=False, max_length=128 , widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'})) 
    records = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}))
    captcha = CharField(required=False,widget=CaptchaImages(attrs={}))

    class Meta:
        model = Application
#        fields = ['applicant','title', 'description','cost', 'river_lease_require_river_lease','river_lease_reserve_licence','river_lease_application_number','proposed_development_description','proposed_development_current_use_of_land','assessment_start_date']

        fields = ['applicant']
#       fields = ['status']

    def __init__(self, *args, **kwargs):
        
        # User must be passed in as a kwarg.
        super(ApplicationPart5, self).__init__(*args, **kwargs)
        crispy_boxes = crispy_empty_box()
        crispy_boxes.append(crispy_box('read_this_collapse','form_read_this','Read This',HTML('{% include "public/read_this_snipplet.html" %}')))

        organisation = self.initial['organisation']
        if organisation is not None:
            applicant_info = HTML('{% include "applications/organisation_update_snippet.html" %}')
        else:
            applicant_info = HTML('{% include "applications/applicant_update_snippet.html" %}')

        crispy_boxes.append(crispy_box('applicant_collapse','form_applicant','Applicant', applicant_info))
        del self.fields['applicant'] 


        crispy_boxes.append(crispy_box('title_collapse','form_title','Title',HTML('{% include "public/title.html" %}')))
#        crispy_boxes.append(crispy_box('river_licence_collapse','river_licence_title','River Licence',HTML('{% include "public/river_reserve_licence_snippet.html" %}')))
        # crispy_boxes.append(HTML('{% include "public/river_reserve_licence_snippet.html" %}'))
        crispy_boxes.append(HTML('{% include "public/details_of_proposed_develeopment_snipplet.html" %}'))
        if self.initial['action'] == 'determination': 
            pass
        else:
            crispy_boxes.append(crispy_box('feedback_collapse','form_feecback','Feedback','name','address','suburb','state','post_code','phone','email','email_confirm','comments','records','captcha',Submit('submitfeedback', 'Submit', css_class='btn-lg')))

#        crispy_boxes.append(HTML('{% include "public/river_reserve_licence_snippet.html" %}'))

        self.helper = BaseFormHelper()
        self.helper.layout = Layout(crispy_boxes,)
        self.helper.form_id = 'id_form_create_application'
        self.helper.attrs = {'novalidate': ''}


        

        # Purpose of the extra field (hidden) is to ensure the status dropdown is 
        # populated on form field error.  So the dropdown doesn't come through blank
        ###
#        self.helper.add_input(Submit('changestatus', 'Change Status', css_class='btn-lg'))
#        self.helper.add_input(Submit('cancel', 'Cancel'))

        # Limit the organisation queryset unless the user is a superuser.
    def clean_captcha(self):
        CaptchaValidation(self.cleaned_data['captcha'], forms) 
        return self.cleaned_data['captcha']
