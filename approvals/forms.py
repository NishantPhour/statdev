from __future__ import unicode_literals
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML, Hidden
from crispy_forms.bootstrap import FormActions
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.forms import Form, ModelForm, ChoiceField, FileField, CharField, Textarea, ClearableFileInput, HiddenInput, Field
from multiupload.fields import MultiFileField
from applications.widgets import ClearableMultipleFileInput, RadioSelectWithCaptions, AjaxFileUploader
from applications.models import Organisation

# from ledger.accounts.models import EmailUser, Address, Organisation
from ledger_api_client.ledger_models import EmailUserRO as EmailUser, Address
from .models import Approval, CommunicationApproval

User = get_user_model()

class BaseFormHelper(FormHelper):
    form_class = 'form-horizontal'
    label_class = 'col-xs-12 col-sm-4 col-md-3 col-lg-2'
    field_class = 'col-xs-12 col-sm-8 col-md-6 col-lg-4'

class ApprovalChangeStatus(ModelForm):

    class Meta:
        model = Approval
        fields = ['status','expiry_date','start_date','cancellation_date','surrender_date','suspend_from_date','suspend_to_date','reinstate_date','details']
#       fields = ['status']

    def __init__(self, *args, **kwargs):
        
        # User must be passed in as a kwarg.
        super(ApprovalChangeStatus, self).__init__(*args, **kwargs)

        # print self.initial['status']
        status = Approval.APPROVAL_STATE_CHOICES[self.initial['status']]

#        self.fields['status'].initial =3
#        print self.fields['status'].initial

        if status == "Expired":
            del self.fields['start_date']
            del self.fields['cancellation_date']
            del self.fields['surrender_date']
            del self.fields['suspend_from_date']
            del self.fields['suspend_to_date']
            del self.fields['reinstate_date']
            self.fields['expiry_date'].required = True
        elif status == "Suspended": 
            del self.fields['start_date']
            del self.fields['cancellation_date']
            del self.fields['surrender_date']
        #   del self.fields['suspend_from_date']
            del self.fields['expiry_date']
            del self.fields['reinstate_date']
            self.fields['suspend_from_date'].required = True
            self.fields['suspend_to_date'].required = True
        elif status == "Reinstate":
            del self.fields['start_date']
            del self.fields['cancellation_date']
            del self.fields['surrender_date']
            del self.fields['suspend_from_date']
            del self.fields['expiry_date']
            del self.fields['suspend_to_date']
            self.fields['reinstate_date'].required = True
        elif status == "Surrendered":
            del self.fields['start_date']
            del self.fields['cancellation_date']
            del self.fields['reinstate_date']
            del self.fields['suspend_from_date']
            del self.fields['expiry_date']
            del self.fields['suspend_to_date']
            self.fields['surrender_date'].required = True
        elif status == "Cancelled":
            del self.fields['start_date']
            del self.fields['surrender_date']
            del self.fields['reinstate_date']
            del self.fields['suspend_from_date']
            del self.fields['expiry_date']
            del self.fields['suspend_to_date']
            self.fields['cancellation_date'].required = True

        self.helper = BaseFormHelper()
        self.helper.form_id = 'id_form_create_application'
        self.helper.attrs = {'novalidate': ''}
        self.fields['status'].widget.attrs['disabled'] = True
        self.fields['status'].required = False

        # Purpose of the extra field (hidden) is to ensure the status dropdown is 
        # populated on form field error.  So the dropdown doesn't come through blank
        self.helper.add_input(Hidden('status',self.initial['status']))
        ###
        self.helper.add_input(Submit('cancel', 'Cancel'))
        self.helper.add_input(Submit('changestatus', 'Change Status'))
        

        # Limit the organisation queryset unless the user is a superuser.

class CommunicationCreateForm(ModelForm):
    #records = Field(required=False, widget=ClearableMultipleFileInput(attrs={'multiple':'multiple'}),  label='Documents')
    records = FileField(required=False, max_length=128, widget=AjaxFileUploader(attrs={'multiple':'multiple'}), label='Documents')
    class Meta:
        model = CommunicationApproval
        fields = ['comms_to','comms_from','subject','comms_type','details','records','details']

    def __init__(self, *args, **kwargs):
        # User must be passed in as a kwarg.
        user = kwargs.pop('user')
        #application = kwargs.pop('application')
        super(CommunicationCreateForm, self).__init__(*args, **kwargs)

        self.fields['comms_to'].required = True
        self.fields['comms_from'].required = True
        self.fields['subject'].required = True
        self.fields['comms_type'].required = True

        self.helper = BaseFormHelper()
        self.helper.form_id = 'id_form_create_communication'
        self.helper.attrs = {'novalidate': ''}
        
        self.helper.add_input(Submit('cancel', 'Cancel'))
        self.helper.add_input(Submit('save', 'Create'))
        # Add labels for fields
        #self.fields['app_type'].label = "Application Type"

