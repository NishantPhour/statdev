from __future__ import unicode_literals
from datetime import datetime, date, timedelta
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail import send_mail
from django.db.models import Q, Max
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework.views import APIView
from extra_views import ModelFormSetView
from itertools import chain
from django.utils.decorators import method_decorator
import pdfkit
import re
import logging
import hashlib
from actions.models import Action
from applications import forms as apps_forms
from applications.models import (
    Application, Referral, Condition, Compliance, Vessel, Location, Record, PublicationNewspaper,
    PublicationWebsite, PublicationFeedback, Communication, Delegate, Organisation, OrganisationAddress, OrganisationContact, OrganisationPending, OrganisationExtras, CommunicationAccount,CommunicationOrganisation, ComplianceGroup,CommunicationCompliance, StakeholderComms, ApplicationLicenceFee, Booking, DiscountReason,BookingInvoice)
from applications.workflow import Flow
from applications.views_sub import Application_Part5, Application_Emergency, Application_Permit, Application_Licence, Referrals_Next_Action_Check, FormsList
from ledger_api_client.utils import get_or_create
from applications.email import sendHtmlEmail, emailGroup, emailApplicationReferrals
from applications.validationchecks import Attachment_Extension_Check, is_json
from applications.utils import get_query, random_generator
from applications import utils
# from ledger.accounts.models import EmailUser, Address, Organisation, Document, OrganisationAddress, PrivateDocument
from ledger_api_client.ledger_models import EmailUserRO as EmailUser, Address, Document, PrivateDocument
from ledger_api_client.managed_models import SystemUser, SystemUserAddress, SystemGroup
from approvals.models import Approval, CommunicationApproval
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import math
from django.shortcuts import redirect
from django.template import RequestContext
from django.template.loader import get_template
from statdev.context_processors import template_context 
import json
import os.path
from applications.views_pdf import PDFtool
import mimetypes
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404, redirect
from decimal import Decimal
# from ledger.payments.models import Invoice
# from oscar.defaults import *
from ledger_api_client.ledger_models import Invoice, Basket
# from oscar.apps.order.models import Order
# from ledger.basket.models import Basket
from applications.invoice_pdf import create_invoice_pdf_bytes
# from ledger.mixins import InvoiceOwnerMixin
from ledger_api_client.mixins import InvoiceOwnerMixin
from django.views.generic.base import View, TemplateView
import pathlib
from django.core.files.base import ContentFile
from django.utils.crypto import get_random_string
import base64
import requests
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class LoginSuccess(TemplateView):
    template_name = 'login_success.html'

    def get(self, request, *args, **kwargs):
        context = {}
        context = {'LEDGER_UI_URL' : settings.LEDGER_UI_URL}
        response = render(request, self.template_name, context)
        return response



class HomePage(TemplateView):
    # preperation to replace old homepage with screen designs..

    template_name = 'applications/home_page.html'

    def render_to_response(self, context):
        context['csrf_token_value'] = get_token(self.request)
        template = get_template(self.template_name)
        return HttpResponse(template.render(context))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = template_context(self.request)

        context['referee'] = 'no'
        context['messages'] = messages.get_messages(self.request)
        context['request'] = self.request
        context['user'] = self.request.user

        action = self.kwargs.get('action', '')
        if self.request.user.is_authenticated:
            try:
                referee_group = SystemGroup.objects.get(name='Statdev Referee')
                usergroups = self.request.user.get_system_group_permission(self.request.user.id)
                if referee_group.id in usergroups:
                    context['referee'] = 'yes'
            except SystemGroup.DoesNotExist:
                pass  # Group doesn't exist, skip

            fl = FormsList()

            if action == '':
                context = fl.get_application(self, self.request.user.id, context)
                context['home_nav_other_applications'] = 'active'
            elif action == 'approvals':
                context = fl.get_approvals(self, self.request.user.id, context)
                context['home_nav_other_approvals'] = 'active'
            elif action == 'clearance':
                context = fl.get_clearance(self, self.request.user.id, context)
                context['home_nav_other_clearance'] = 'active'
            elif action == 'referrals':
                context['home_nav_other_referral'] = 'active'
                if 'q' in self.request.GET and self.request.GET['q']:
                    query_str = self.request.GET['q']
                    query_str_split = query_str.split()
                    search_filter = Q()
                    for se_wo in query_str_split:
                        search_filter &= Q(pk__contains=se_wo) | Q(title__contains=se_wo)
                    # You might want to use this filter in the query below
                context['items'] = Referral.objects.filter(referee=self.request.user.id).exclude(status=5).order_by('-id')

        return context


class HomePageOLD(LoginRequiredMixin, TemplateView):
    # TODO: rename this view to something like UserDashboard.
    template_name = 'applications/home_page.html'

    def get_context_data(self, **kwargs):
        context = super(HomePage, self).get_context_data(**kwargs)
        if Application.objects.filter(assignee=self.request.user.id).exclude(state__in=[Application.APP_STATE_CHOICES.issued, Application.APP_STATE_CHOICES.declined]).exists():
            applications_wip = Application.objects.filter(
                assignee=self.request.user.id).exclude(state__in=[Application.APP_STATE_CHOICES.issued, Application.APP_STATE_CHOICES.declined])
            context['applications_wip'] = self.create_applist(applications_wip)
        #if Application.objects.filter(assignee=self.request.user.id).exclude(state__in=[Application.APP_STATE_CHOICES.issued, Application.APP_STATE_CHOICES.declined]).exists():
            #            userGroups = self.request.user.groups().all()

        userGroups = []
        userGroups = self.request.user.get_system_group_permission(self.request.user.id)
             
        applications_groups = Application.objects.filter(group__name__in=userGroups).exclude(state__in=[Application.APP_STATE_CHOICES.issued, Application.APP_STATE_CHOICES.declined])
        context['applications_groups'] = self.create_applist(applications_groups)

        if Application.objects.filter(applicant=self.request.user.id).exists():
            applications_submitted = Application.objects.filter(
                applicant=self.request.user.id).exclude(assignee=self.request.user.id)
            context['applications_submitted'] = self.create_applist(applications_submitted)
        if Referral.objects.filter(referee=self.request.user.id).exists():
            context['referrals'] = Referral.objects.filter(
                referee=self.request.user.id, status=Referral.REFERRAL_STATUS_CHOICES.referred)

        # TODO: any restrictions on who can create new applications?
        context['may_create'] = True
        # Processor users only: show unassigned applications.
        processor = SystemGroup.objects.get(name='Statdev Processor')
        if processor.id in userGroups or self.request.user.is_superuser:
            if Application.objects.filter(assignee__isnull=True, state=Application.APP_STATE_CHOICES.with_admin).exists():
                applications_unassigned = Application.objects.filter(
                    assignee__isnull=True, state=Application.APP_STATE_CHOICES.with_admin)
                context['applications_unassigned'] = self.create_applist(applications_unassigned)
            # Rule: admin officers may self-assign applications.
            context['may_assign_processor'] = True
        
        
        
        return context

    def create_applist(self, applications):
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        app_list = []
        for app in applications:
            row = {}
            row['may_assign_to_person'] = 'False'
            row['app'] = app
            if app.group.id in usergroups:
                if app.group is not None:
                    row['may_assign_to_person'] = 'True'
            
            if app.applicant:
                applicant = SystemUser.objects.get(ledger_id=app.applicant)
                row['applicant'] = applicant            
            
            if app.assignee:
                assignee = SystemUser.objects.get(ledger_id=app.assignee)
                row['assignee'] = assignee

            if app.submitted_by:
                submitted_by = SystemUser.objects.get(ledger_id=app.submitted_by)
                row['submitted_by'] = submitted_by            

            if app.assigned_officer:
                assigned_officer = SystemUser.objects.get(ledger_id=app.assigned_officer)
                row['assigned_officer'] = assigned_officer 
            
            app_list.append(row)
            
        return app_list



class PopupNotification(TemplateView):
    template_name = 'applications/popup-notification.html'

    def get(self, request, *args, **kwargs):
        #messages.error(self.request,"Please complete at least one phone number")
        #messages.success(self.request,"Please complete at least one phone number")
        #messages.warning(self.request,"Please complete at least one phone number")
        return super(PopupNotification, self).get(request, *args, **kwargs)


class NotificationInsidePopup(TemplateView):
    template_name = 'applications/popup-inside-notification.html'

    def get(self, request, *args, **kwargs):
        #messages.error(self.request,"Please complete at least one phone number")
        return super(NotificationInsidePopup, self).get(request, *args, **kwargs)

#TODO remove
# class FirstLoginInfo(LoginRequiredMixin,CreateView):

#     template_name = 'applications/firstlogin.html'
#     model = EmailUser
#     form_class = apps_forms.FirstLoginInfoForm

#     def get(self, request, *args, **kwargs):
#         return super(FirstLoginInfo, self).get(request, *args, **kwargs)

#     def get_initial(self):
#         initial = super(FirstLoginInfo, self).get_initial()
#         #initial['action'] = self.kwargs['action']
#         return initial

#     def post(self, request, *args, **kwargs):
#         if request.POST.get('cancel'):
#             app = self.get_object().application_set.first()
#             return HttpResponseRedirect(app.get_absolute_url())
#         return super(FirstLoginInfo, self).post(request, *args, **kwargs)

#     def form_valid(self, form):
#         self.object = form.save()
#         forms_data = form.cleaned_data
#         action = self.kwargs['action']
#         nextstep = ''
#         apply_on_behalf_of = 0
#         app = Application.objects.get(pk=self.object.pk)

#         return HttpResponseRedirect(success_url)

class setUrl():
    value = ''
    url = ''
    path = ''
    def __repr__(self):
         return self.value
#TODO remove
# class FirstLoginInfoSteps(LoginRequiredMixin,UpdateView):

#     template_name = 'applications/firstlogin.html'
#     model = EmailUser
#     form_class = apps_forms.FirstLoginInfoForm

#     def get(self, request, *args, **kwargs):
#         pk = int(kwargs['pk'])
#         if request.user.is_staff == True or request.user.is_superuser == True or request.user.id == pk:
#            donothing =""
#         else:
#            messages.error(self.request, 'Forbidden from viewing this page.')
#            return HttpResponseRedirect("/")

#         return super(FirstLoginInfoSteps, self).get(request, *args, **kwargs)

#     def get_context_data(self, **kwargs):
#         context = super(FirstLoginInfoSteps, self).get_context_data(**kwargs)
#         step = self.kwargs['step']

#         if step == '1':
#             context['step1'] = 'active'
#             context['step2'] = 'disabled'
#             context['step3'] = 'disabled'
#             context['step4'] = 'disabled'
#             context['step5'] = 'disabled'
#         elif step == '2':
#             context['step2'] = 'active'
#             context['step3'] = 'disabled'
#             context['step4'] = 'disabled'
#             context['step5'] = 'disabled'
#         elif step == '3':
#             context['step3'] = 'active'
#             context['step4'] = 'disabled'
#             context['step5'] = 'disabled'
#         elif step == '4':
#             context['step4'] = 'active'
#             context['step5'] = 'disabled'
#         elif step == '5':
#             context['step5'] = 'active'
#         return context
    
#     def get_initial(self):
#         initial = super(FirstLoginInfoSteps, self).get_initial()
#         person = self.get_object()
#         # initial['action'] = self.kwargs['action']
#         # print self.kwargs['step']
#         step = self.kwargs['step']
#         if person.identification2:
#             #person.identification2.upload.url = '/jason/jhaso'
   
#             url_data = setUrl()
#             url_data.url = "/private-ledger/view/"+str(person.identification2.id)+'-'+person.identification2.name+'.'+person.identification2.extension 
#             url_data.value = str(person.identification2.id)+'-'+person.identification2.name+'.'+person.identification2.extension
#             initial['identification2'] =  url_data
#             #initial['identification2'] = person.identification2.upload
#         if step == '3':
#             if self.object.postal_address is None:
#                 initial['country'] = 'AU'
#                 initial['state'] = 'WA'
#             else: 
#                 postal_address = Address.objects.get(id=self.object.postal_address.id)
#                 initial['line1'] = postal_address.line1
#                 initial['line2'] = postal_address.line2
#                 initial['line3'] = postal_address.line3
#                 initial['locality'] = postal_address.locality
#                 initial['state'] = postal_address.state
#                 initial['country'] = postal_address.country
#                 initial['postcode'] = postal_address.postcode

#         initial['step'] = self.kwargs['step']
#         return initial

#     def post(self, request, *args, **kwargs):
#         if request.POST.get('cancel'):
#             app = self.get_object().application_set.first()
#             return HttpResponseRedirect(app.get_absolute_url())
#         return super(FirstLoginInfoSteps, self).post(request, *args, **kwargs)

#     def form_valid(self, form):
#         self.object = form.save(commit=False)
#         forms_data = form.cleaned_data
#         step = self.kwargs['step']
#         app_id = None

#         if 'application_id' in self.kwargs:
#             app_id = self.kwargs['application_id']

#         if step == '3':
#             if self.object.postal_address is None:
#                postal_address = Address.objects.create(line1=forms_data['line1'],
#                                         line2=forms_data['line2'],
#                                         line3=forms_data['line3'],
#                                         locality=forms_data['locality'],
#                                         state=forms_data['state'],
#                                         country=forms_data['country'],
#                                         postcode=forms_data['postcode'],
#                                         user=self.object
#                                        )
#                self.object.postal_address = postal_address
#             else:
#                postal_address = Address.objects.get(id=self.object.postal_address.id)
#                postal_address.line1 = forms_data['line1']
#                postal_address.line2 = forms_data['line2']
#                postal_address.line3 = forms_data['line3']
#                postal_address.locality = forms_data['locality']
#                postal_address.state = forms_data['state']
#                postal_address.country = forms_data['country']
#                postal_address.postcode = forms_data['postcode']
#                postal_address.save()

#         if step == '4':
#             if self.object.mobile_number is None:
#                  self.object.mobile_number = ""
#             if self.object.phone_number is None: 
#                  self.object.phone_number = ""

#             if len(self.object.mobile_number) == 0 and len(self.object.phone_number) == 0:
#                 messages.error(self.request,"Please complete at least one phone number")
#                 if app_id is None:
#                 #    return HttpResponseRedirect(reverse('first_login_info_steps',args=(self.object.pk, step)))
#                     return HttpResponseRedirect('/ledger-ui/system-accounts-firsttime')
#                 else:
#                 #    return HttpResponseRedirect(reverse('first_login_info_steps_application',args=(self.object.pk, step, app_id)))
#                     return HttpResponseRedirect('/ledger-ui/system-accounts-firsttime') 

#         # Upload New Files
#         if self.request.FILES.get('identification2'):  # Uploaded new file.
#             doc = Document()
#             if Attachment_Extension_Check('single', forms_data['identification2'], ['.jpg','.png','.pdf']) is False:
#                 raise ValidationError('Identification contains and unallowed attachment extension.')
#             identification2_file = self.request.FILES['identification2']
#             data = base64.b64encode(identification2_file.read())

#             filename=forms_data['identification2'].name
#             api_key = settings.LEDGER_API_KEY
#             url = settings.LEDGER_API_URL+'/ledgergw/remote/documents/update/'+api_key+'/'
            
#             extension =''
#             if filename[-4:][:-3] == '.':
#                 extension = filename[-3:]
#             if filename[-5:][:-4] == '.':
#                 extension = filename[-4:]
            
#             base64_url = "data:"+mimetypes.types_map['.'+str(extension)]+";base64,"+data.decode()
#             myobj = {'emailuser_id' :self.object.pk,'filebase64': base64_url, 'extension': extension, 'file_group_id': 1}


#             try:
#                 resp = requests.post(url, data = myobj)
#                 # temporary until all EmailUser Updates go via api.
#                 eu_obj = EmailUser.objects.get(id=self.object.pk)
#                 self.object.identification2=eu_obj.identification2
#             except:
#                 messages.error(self.request, 'Error Saving Identification File')
#                 if app_id is None:
#                 #    return HttpResponseRedirect(reverse('first_login_info_steps',args=(self.object.pk, step)))
#                     return HttpResponseRedirect('/ledger-ui/system-accounts-firsttime')
#                 else:
#                 #    return HttpResponseRedirect(reverse('first_login_info_steps_application',args=(self.object.pk, step, app_id)))
#                     return HttpResponseRedirect('/ledger-ui/system-accounts-firsttime')

#             # temporary until all EmailUser Updates go via api.
#             eu_obj = EmailUser.objects.get(id=self.object.pk)
#             self.object.identification2=eu_obj.identification2

#             #print (image_string)
#             #doc.file = forms_data['identification2']
#             #doc.name = forms_data['identification2'].name
#             #doc.save()
#             #self.object.identification2 = doc
            
#         self.object.save()
#         nextstep = 1

# #        action = self.kwargs['action']
#         if self.request.POST.get('prev-step'):
#             if step == '1':
#                nextstep = 1
#             elif step == '2':
#                nextstep = 1
#             elif step == '3':
#                nextstep = 2
#             elif step == '4':
#                nextstep = 3
#             elif step == '5':
#                nextstep = 4
#         else:
#             if step == '1':
#                nextstep = 2
#             elif step == '2':
#                nextstep = 3
#             elif step == '3':
#                nextstep = 4
#             elif step == '4':
#                nextstep = 5
#             else:
#                nextstep = 6

     
 
#         if nextstep == 6:
#             #print forms_data['manage_permits']
#            if forms_data['manage_permits'] == 'True':
#                messages.success(self.request, 'Registration is now complete. Please now complete the company form.')
#                #return HttpResponseRedirect(reverse('company_create_link', args=(self.request.user.id,'1')))
#                if app_id is None:
#                    return HttpResponseRedirect(reverse('company_create_link', args=(self.object.pk,'1')))
#                else:
#                    return HttpResponseRedirect(reverse('company_create_link_application', args=(self.object.pk,'1',app_id))) 
#            else:
#                messages.success(self.request, 'Registration is now complete.')
#                if app_id is None:
#                    return HttpResponseRedirect(reverse('home'))
#                else:
#                    if self.request.user.is_staff is True:
#                        app = Application.objects.get(id=app_id)
#                        app.applicant = self.object
#                        app.save() 
#                    return HttpResponseRedirect(reverse('application_update', args=(app_id,)))
#         else:
#            if app_id is None:
#             #   return HttpResponseRedirect(reverse('first_login_info_steps',args=(self.object.pk, nextstep)))
#                 return HttpResponseRedirect('/ledger-ui/system-accounts-firsttime')
#            else:
#             #   return HttpResponseRedirect(reverse('first_login_info_steps_application',args=(self.object.pk, nextstep, app_id)))
#                 return HttpResponseRedirect('/ledger-ui/system-accounts-firsttime')

class CreateLinkCompany(LoginRequiredMixin,CreateView):

    template_name = 'applications/companycreatelink.html'
    model = SystemUser 
    form_class = apps_forms.CreateLinkCompanyForm

    def get(self, request, *args, **kwargs):
        return super(CreateLinkCompany, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CreateLinkCompany, self).get_context_data(**kwargs)
        step = self.kwargs['step']
        context['user_id'] = self.kwargs['pk']

        if 'po_id' in self.kwargs:
            context['po_id'] = self.kwargs['po_id']
        else:
            context['po_id'] = 0

        if step == '1':
            context['step1'] = 'active'
            context['step2'] = 'disabled'
            context['step3'] = 'disabled'
            context['step4'] = 'disabled'
            context['step5'] = 'disabled'
        elif step == '2':
            context['step2'] = 'active'
            context['step3'] = 'disabled'
            context['step4'] = 'disabled'
            context['step5'] = 'disabled'
        elif step == '3':
            context['step3'] = 'active'
            context['step4'] = 'disabled'
            context['step5'] = 'disabled'
        elif step == '4':
            context['step4'] = 'active'
            context['step5'] = 'disabled'
        elif step == '5':
            context['step5'] = 'active'

        context['messages'] = messages.get_messages(self.request)
        return context 

    def get_initial(self):
        initial = super(CreateLinkCompany, self).get_initial()
        step = self.kwargs['step']

        initial['step'] = self.kwargs['step']
        initial['company_exists'] = ''
        pending_org = None
        if 'po_id' in self.kwargs:
            po_id = self.kwargs['po_id']
            if po_id:
                 pending_org = OrganisationPending.objects.get(id=po_id)
                 initial['company_name'] = pending_org.name
                 initial['abn'] = pending_org.abn
                 initial['pin1'] = pending_org.pin1
                 initial['pin2'] = pending_org.pin2

        if step == '2':
            if 'abn' in initial:
                abn = initial['abn']
                try:
                    if Organisation.objects.filter(abn=abn).exists():
                       company = Organisation.objects.get(abn=abn) #(abn=abn)
                       if OrganisationExtras.objects.filter(organisation=company.id).exists():
                          companyextras = OrganisationExtras.objects.get(organisation=company.id)
                          initial['company_id'] = company.id
                          initial['company_exists'] = 'yes'
                          listusers = Delegate.objects.filter(organisation__id=company.id)
                          delegate_people = ''
                          for lu in listusers:
                               system_user = SystemUser.objects.get(ledger_id=lu.email_user)
                               if delegate_people == '':
                                   delegate_people = system_user.first_name + ' '+ system_user.last_name 
                               else:
                                   delegate_people = delegate_people + ', ' + system_user.first_name + ' ' + system_user.last_name
                          initial['company_delegates'] = delegate_people
                       else:
                          initial['company_exists'] = 'no'
                    else:
                       initial['company_exists'] = 'no' 

                except Organisation.DoesNotExist:
                    initial['company_exists'] = 'no'

#                    try: 
                        #                        companyextras = OrganisationExtras.objects.get(id=company.id)
 #                   except OrganisationExtras.DoesNotExist:
  #                      initial['company_exists'] = 'no'
            if pending_org is not None:
                if pending_org.identification:
                    initial['identification'] = pending_org.identification.upload

        if step == '3':
            if pending_org.pin1 and pending_org.pin2:
               if Organisation.objects.filter(abn=pending_org.abn).exists():
                   company = Organisation.objects.get(abn=pending_org.abn)
                   if OrganisationExtras.objects.filter(organisation=company, pin1=pending_org.pin1,pin2=pending_org.pin2).exists():
                       initial['postal_line1'] = company.postal_address.line1
                       initial['postal_line2'] = company.postal_address.line2
                       initial['postal_line3'] = company.postal_address.line3
                       initial['postal_locality'] = company.postal_address.locality
                       initial['postal_state'] = company.postal_address.state
                       initial['postal_country'] = company.postal_address.country
                       initial['postal_postcode'] = company.postal_address.postcode

                       initial['billing_line1'] = company.billing_address.line1
                       initial['billing_line2'] = company.billing_address.line2
                       initial['billing_line3'] = company.billing_address.line3
                       initial['billing_locality'] = company.billing_address.locality
                       initial['billing_state'] = company.billing_address.state
                       initial['billing_country'] = company.billing_address.country
                       initial['billing_postcode'] = company.billing_address.postcode

            else:
               if pending_org.postal_address is not None:
                   postal_address = OrganisationAddress.objects.get(id=pending_org.postal_address.id)
                   billing_address = OrganisationAddress.objects.get(id=pending_org.billing_address.id)
                   initial['postal_line1'] = postal_address.line1
                   initial['postal_line2'] = postal_address.line2
                   initial['postal_line3'] = postal_address.line3
                   initial['postal_locality'] = postal_address.locality
                   initial['postal_state'] = postal_address.state
                   initial['postal_country'] = postal_address.country
                   initial['postal_postcode'] = postal_address.postcode
               else:
                   initial['postal_state'] = 'WA'
                   initial['postal_country'] = 'AU'

               if pending_org.billing_address is not None:
                   initial['billing_line1'] = billing_address.line1
                   initial['billing_line2'] = billing_address.line2
                   initial['billing_line3'] = billing_address.line3
                   initial['billing_locality'] = billing_address.locality
                   initial['billing_state'] = billing_address.state
                   initial['billing_country'] = billing_address.country
                   initial['billing_postcode'] = billing_address.postcode
               else:
                  initial['billing_state'] = 'WA'
                  initial['billing_country'] = 'AU'

        if step == '4':
            initial['company_exists'] = 'no'
            if pending_org.pin1 and pending_org.pin2:
               if Organisation.objects.filter(abn=pending_org.abn).exists():
                    initial['company_exists'] = 'yes'


        return initial

    def post(self, request, *args, **kwargs):
        #messages.error(self.request, 'Invalid Pins ')
        #print request.path

        step = self.kwargs['step']
        if step == '2':
            company_exists = 'no'
            if 'company_exists' in request.POST:
                company_exists = request.POST['company_exists']

                if company_exists == 'yes':
                   company_id = request.POST['company_id']
    
                   pin1 = request.POST['pin1']
                   pin2 = request.POST['pin2']
                   pin1 = pin1.replace(" ", "")
                   pin2 = pin2.replace(" ", "")

                   comp = Organisation.objects.get(id=company_id)
                   if OrganisationExtras.objects.filter(organisation=comp, pin1=pin1,pin2=pin2).exists():
                       messages.success(self.request, 'Company Pins Correct')
                   else:
                       messages.error(self.request, 'Incorrect Company Pins')
                       return HttpResponseRedirect(request.path)

            else:
                if 'identification' in request.FILES:
                   if Attachment_Extension_Check('single', request.FILES['identification'], ['.pdf','.png','.jpg']) is False:
                      messages.error(self.request,'Identification contains and unallowed attachment extension.')
                      return HttpResponseRedirect(request.path)

        if request.POST.get('cancel'):
            app = self.get_object().application_set.first()
            return HttpResponseRedirect(app.get_absolute_url())
        return super(CreateLinkCompany, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        forms_data = form.cleaned_data
        pk = self.kwargs['pk']
        step = self.kwargs['step']
        pending_org = None

        if 'po_id' in self.kwargs:
            po_id = self.kwargs['po_id']
            if po_id:
                pending_org = OrganisationPending.objects.get(id=po_id)

        if step == '1':
            abn = self.request.POST.get('abn')
            company_name = self.request.POST.get('company_name')

            if pending_org:
                pending_org.name = company_name
                pending_org.abn = abn
                pending_org.save()
            else:
                user = SystemUser.objects.get(id=pk)
                pending_org = OrganisationPending.objects.create(name=company_name,abn=abn,email_user=user.ledger_id.id)

            action = Action(
                  content_object=pending_org, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.create,
                  action='Organisation Link/Creation Started')
            action.save()

        if step == '2':
            company_exists = forms_data['company_exists']
            if company_exists == 'yes':
                # print "COMP"
                company_id = forms_data['company_id']
                pin1 = forms_data['pin1']
                pin2 = forms_data['pin2']
                pin1 = pin1.replace(" ", "")
                pin2 = pin2.replace(" ", "")

                comp = Organisation.objects.get(id=company_id)
           
                if OrganisationExtras.objects.filter(organisation=comp, pin1=pin1,pin2=pin2).exists():
                    pending_org.pin1 = pin1
                    pending_org.pin2 = pin2
                    pending_org.company_exists = True
                    pending_org.save()

                    action = Action(
                          content_object=pending_org, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.change,
                          action='Organisation Pins Verified')
                    action.save()

                #else:
                    #print "INCORR"

                #,id=company_id)
                # print "YESYY"
                # print forms_data['pin1']
                # print forms_data['pin2']

            else:
                if forms_data['identification']:
                   doc = Record()
                   if Attachment_Extension_Check('single', forms_data['identification'], ['.pdf','.png','.jpg']) is False:
                       raise ValidationError('Identification contains and unallowed attachment extension.')

                   doc.upload = forms_data['identification']
                   doc.name = forms_data['identification'].name
                   doc.save()
                   pending_org.identification = doc
                   pending_org.company_exists = False
                   pending_org.save()
                   action = Action(
                          content_object=pending_org, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.change,
                          action='Identification Added')
                   action.save()


        if step == '3':
            if pending_org.postal_address is None or pending_org.billing_address is None:
                print ("FORMS")
                print (forms_data)
                postal_address = OrganisationAddress.objects.create(line1=forms_data['postal_line1'],
                                                        line2=forms_data['postal_line2'],
                                                        line3=forms_data['postal_line3'],
                                                        locality=forms_data['postal_locality'],
                                                        state=forms_data['postal_state'],
                                                        country=forms_data['postal_country'],
                                                        postcode=forms_data['postal_postcode']
                        )
                billing_address = OrganisationAddress.objects.create(line1=forms_data['billing_line1'],
                                                        line2=forms_data['billing_line2'],
                                                        line3=forms_data['billing_line3'],
                                                        locality=forms_data['billing_locality'],
                                                        state=forms_data['billing_state'],
                                                        country=forms_data['billing_country'],
                                                        postcode=forms_data['billing_postcode']
                        )
                pending_org.postal_address = postal_address
                pending_org.billing_address = billing_address
                pending_org.save()
                action = Action(
                      content_object=pending_org, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.change,
                      action='Address Details Added')
                action.save()

            else:
                postal_address = OrganisationAddress.objects.get(id=pending_org.postal_address.id)
                billing_address = OrganisationAddress.objects.get(id=pending_org.billing_address.id)
   
                postal_address.line1=forms_data['postal_line1']
                postal_address.line2=forms_data['postal_line2']
                postal_address.line3=forms_data['postal_line3']
                postal_address.locality=forms_data['postal_locality']
                postal_address.state=forms_data['postal_state']
                postal_address.country=forms_data['postal_country']
                postal_address.postcode=forms_data['postal_postcode']
                postal_address.save()

                billing_address.line1=forms_data['billing_line1']
                billing_address.line2=forms_data['billing_line2']
                billing_address.line3=forms_data['billing_line3']
                billing_address.locality=forms_data['billing_locality']
                billing_address.state=forms_data['billing_state']
                billing_address.country=forms_data['billing_country']
                billing_address.postcode=forms_data['postal_postcode']
                billing_address.save()

                action = Action(
                      content_object=pending_org, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.change,
                      action='Address Details Updated')
                action.save()


            #pending_org.identification 
#            try:
#                company = Organisation.objects.get(abn=abn)
#                initial['company_exists'] = 'yes'
#            except Organisation.DoesNotExist:
#                initial['company_exists'] = 'no'
#                pending_org = OrganisationPending.objects.create(name=company_name,abn=abn)
#                print pending_org

        nextstep = 1
        if self.request.POST.get('prev-step'):
            if step == '1':
               nextstep = 1
            elif step == '2':
               nextstep = 1
            elif step == '3':
               nextstep = 2
            elif step == '4':
               nextstep = 3
            elif step == '5':
               nextstep = 4
        else:
            if step == '1':
               nextstep = 2
            elif step == '2':
               nextstep = 3
            elif step == '3':
               nextstep = 4
            elif step == '4':
               nextstep = 5
            else:
               nextstep = 6

        app_id = None
        if 'application_id' in self.kwargs:
            app_id = self.kwargs['application_id']

        if nextstep == 5:
           # print pending_org.company_exists
           if pending_org.company_exists == True: 
               pending_org.status = 2
               comp = Organisation.objects.get(abn=pending_org.abn)
               Delegate.objects.create(email_user=pending_org.email_user,organisation=comp)
               #print "Approved" 
               messages.success(self.request, 'Your company has now been linked.')
               pending_org.save()
               action = Action(
                      content_object=pending_org, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.change,
                      action='Organisation Approved (Automatically)')
               action.save()
               system_user = SystemUser.objects.get(ledger_id=pending_org.email_user)
               OrganisationContact.objects.create(
                                                  email=system_user.email,
                                                  first_name=system_user.legal_first_name,
                                                  last_name=system_user.legal_last_name,
                                                  phone_number=system_user.phone_number,
                                                  mobile_number=system_user.mobile_number,
                                                  fax_number=system_user.fax_number,
                                                  organisation=comp
               )

           else:
              if self.request.user.is_staff is True:
                 pass 
              else:
                 messages.success(self.request, 'Your company has been submitted for approval and now pending attention by our Staff.')
                 action = Action(
                      content_object=pending_org, user=self.request.user.id,
                      action='Organisation is pending approval')
                 action.save()
                 emailcontext = {'pending_org': pending_org,  }
                 emailGroup('Organisation pending approval ', emailcontext, 'pending_organisation_approval.html', None, None, None, 'Statdev Assessor')
           processor = SystemGroup.objects.get(name='Statdev Processor')
           usergroups = self.request.user.get_system_group_permission(self.request.user.id)
           if processor.id in usergroups:
               if app_id is None:
                   return HttpResponseRedirect(reverse('home'))
               else:
                   return HttpResponseRedirect(reverse('organisation_access_requests_change_applicant', args=(pending_org.id,'approve',app_id)))
        else:
           if pending_org:
              #return HttpResponseRedirect(reverse('company_create_link_steps',args=(self.request.user.id, nextstep,pending_org.id)))
              if app_id is None:
                 return HttpResponseRedirect(reverse('company_create_link_steps',args=(pk, nextstep,pending_org.id)))
              else:
                 return HttpResponseRedirect(reverse('company_create_link_steps_application',args=(pk, nextstep,pending_org.id,app_id)))
           else:
              if app_id is None:
                 return HttpResponseRedirect(reverse('company_create_link',args=(pk,nextstep)))
              else:
                 return HttpResponseRedirect(reverse('company_create_link_application',args=(pk,nextstep,app_id)))
 
        return HttpResponseRedirect(reverse('home'))


class ApplicationApplicantChange(LoginRequiredMixin,DetailView):

    # form_class = apps_forms.ApplicationCreateForm
    template_name = 'applications/applicant_applicantsearch.html'
    model = Application

    def get_queryset(self):
        qs = super(ApplicationApplicantChange, self).get_queryset()
        return qs

    def get_context_data(self, **kwargs):

        #listusers =  EmailUser.objects.all()
        listorgs = []
        context = super(ApplicationApplicantChange, self).get_context_data(**kwargs)
        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            query_str_split = query_str.split()
            search_filter = Q()
            search_filter = Q(first_name__icontains=query_str) | Q(last_name__icontains=query_str) | Q(email__icontains=query_str)
            listusers = SystemUser.objects.filter(search_filter).exclude(is_staff=True)
        else:
            listusers =  SystemUser.objects.all().exclude(is_staff=True)
            
        listusers = listusers.filter(Q(legal_first_name__isnull=False) & Q(legal_last_name__isnull=False)).distinct()[:100]


        context['acc_list'] = []
        for lu in listusers:
            row = {}
            row['acc_row'] = lu
            lu.organisations = []
            lu.organisations =  Delegate.objects.filter(email_user=lu.id) 
            context['acc_list'].append(row)
        context['applicant_id'] = self.object.pk
        context['person_tab'] = 'active'

        return context

class ApplicationApplicantCompanyChange(LoginRequiredMixin,DetailView):

    # form_class = apps_forms.ApplicationCreateForm
    template_name = 'applications/applicant_applicant_company_search.html'
    model = Application

    def get_queryset(self):
        qs = super(ApplicationApplicantCompanyChange, self).get_queryset()
        return qs

    def get_context_data(self, **kwargs):

        listorgs = []
        context = super(ApplicationApplicantCompanyChange, self).get_context_data(**kwargs)
        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            query_str_split = query_str.split()
            search_filter = Q()
            list_orgs = OrganisationExtras.objects.filter(organisation__name__icontains=query_str)
#, organisation__postal_address__icontains=query_str)
        else:
            list_orgs = OrganisationExtras.objects.all()

        context['item_list'] = []
        for lu in list_orgs:
            row = {}
            row['item_row'] = lu
            context['item_list'].append(row)
        context['company_id'] = self.object.pk
        context['company_tab'] = 'active'

        return context
class ApplicationFlows(LoginRequiredMixin,TemplateView):
    #model = Application
    template_name = 'applications/application_flows.html'
    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        staff = context_processor['staff']
        if staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ApplicationFlows, self).get(request, *args, **kwargs)

#    def get_queryset(self):
#        qs = super(ApplicationFlows, self).get_queryset()
#
#        # Did we pass in a search string? If so, filter the queryset and return
#        # it.
#        if 'q' in self.request.GET and self.request.GET['q']:
#            query_str = self.request.GET['q']
#            # Replace single-quotes with double-quotes
#            query_str = query_str.replace("'", r'"')
#            # Filter by pk, title, applicant__email, organisation__name,
#            # assignee__email
#            query = get_query(
#                query_str, ['pk', 'title', 'applicant__email', 'organisation__name', 'assignee__email'])
#            qs = qs.filter(query).distinct()
#        return qs

    def get_context_data(self, **kwargs):
        context = super(ApplicationFlows, self).get_context_data(**kwargs)
        context['query_string'] = ''
        context['application_types'] = Application.APP_TYPE_CHOICES._identifier_map
        context['application_choices'] = Application.APP_TYPE_CHOICES
        
        processor = SystemGroup.objects.get(name='Statdev Processor')
        userGroups = self.request.user.get_system_group_permission(self.request.user.id)
        
        for b in Application.APP_TYPE_CHOICES._identifier_map:
           print(b)
           print(Application.APP_TYPE_CHOICES._identifier_map[b])
    

        # Rule: admin officers may self-assign applications.
        if processor.id in userGroups or self.request.user.is_superuser:
            context['may_assign_processor'] = True
        return context

class ApplicationFlowRoutes(LoginRequiredMixin,TemplateView):

    #model = Application
    template_name = 'applications/application_flow_routes.html'
    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        staff = context_processor['staff']
        if staff == True:
           donothing = ""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ApplicationFlowRoutes, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationFlowRoutes, self).get_context_data(**kwargs)
        context['query_string'] = ''
        context['application_types'] = Application.APP_TYPE_CHOICES._identifier_map
        context['application_choices'] = Application.APP_TYPE_CHOICES
        route = self.request.GET.get('route',1)
        context['route'] = route
        #processor = SystemGroup.objects.get(name='Processor')
        pk = kwargs['pk']
        print (pk)
        app_type = None
        for b in Application.APP_TYPE_CHOICES._identifier_map:
            if Application.APP_TYPE_CHOICES._identifier_map[b] == int(pk): 
                app_type = b
                print(b)

        if app_type:
            flow = Flow()
            flow.get(app_type)
            #print (kwargs)
            #print (flow.json_obj)
            #context['workflow'] = flow.json_obj
            workflow_steps = flow.json_obj
            if 'options' in workflow_steps:
                del workflow_steps['options']
            #context['workflow'] = sorted(workflow_steps.items(), key=lambda dct: float(dct[0]))
            context['workflow'] = workflow_steps.items()
            context['workflow_route'] = flow.getAllRouteConf(app_type,route)
            if 'condition_based_actions' in context['workflow_route']:
                context['workflow_route']['condition_based_actions'] = context['workflow_route']['condition-based-actions']
            else: 
                context['workflow_route']['condition_based_actions'] = ''
            print (context['workflow_route']['condition_based_actions'])

#        for b in Application.APP_TYPE_CHOICES._identifier_map:
#           print(b)
#           print(Application.APP_TYPE_CHOICES._identifier_map[b])


        # Rule: admin officers may self-assign applications.
        #if self.request.user.groups().all() or self.request.user.is_superuser:
        #    context['may_assign_processor'] = True
        return context

class ApplicationFlowDiagrams(LoginRequiredMixin,TemplateView):

    #model = Application
    template_name = 'applications/application_flow_diagrams.html'
    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        staff = context_processor['staff']
        if staff == True:
           donothing = ""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ApplicationFlowDiagrams, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationFlowDiagrams, self).get_context_data(**kwargs)
        context['query_string'] = ''
        context['application_types'] = Application.APP_TYPE_CHOICES._identifier_map
        context['application_choices'] = Application.APP_TYPE_CHOICES
        print ('DIA')
        route = self.request.GET.get('route',1)
        context['route'] = route
        print (vars(Application.APP_TYPE_CHOICES))
        #processor = SystemGroup.objects.get(name='Processor')
        pk = kwargs['pk']
        print (pk)
        context['app_type'] = pk
        context['application_type_name'] = Application.APP_TYPE_CHOICES._display_map[int(pk)]

        app_type = None
        for b in Application.APP_TYPE_CHOICES._identifier_map:
            if Application.APP_TYPE_CHOICES._identifier_map[b] == int(pk):
                app_type = b
                print(b)

        if app_type:
            print ("APP TYPE")
            flow = Flow()
            flow.get(app_type)
            #print (kwargs)
            #print (flow.json_obj)
            workflow_steps = flow.json_obj
            print (workflow_steps["1"]["title"])
            for i in workflow_steps.keys():
                 if i == "options":
                     pass
                 else:
                     
                     workflow_steps[i]['step_id'] = str(i).replace(".","_")
                     #print (workflow_steps[i]['step_id']) 
                     for a in workflow_steps[i]['actions']:
                          print (a)
                          a['route_id'] = str(a['route']).replace(".","_")
                          print (a) 
            if 'options' in workflow_steps:
                del workflow_steps['options']
#            context['workflow'] = sorted(workflow_steps.items(), key=lambda dct: float(dct[0]))
            context['workflow'] =  workflow_steps.items()
            #context['workflow'][1][0] = '2-22'
            #print (context['workflow'][1][0])
               #b = i[0].replace(".","-")
               #print (b)
               
            context['workflow_route'] = flow.getAllRouteConf(app_type,route)
            if 'condition_based_actions' in context['workflow_route']:
                context['workflow_route']['condition_based_actions'] = context['workflow_route']['condition-based-actions']
            else:
                context['workflow_route']['condition_based_actions'] = ''
            #print (context['workflow'])
        return context

class ApplicationList(LoginRequiredMixin,ListView):
    model = Application

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        staff = context_processor['staff']
        if staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ApplicationList, self).get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super(ApplicationList, self).get_queryset()

        # Did we pass in a search string? If so, filter the queryset and return
        # it.
        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            # Replace single-quotes with double-quotes
            query_str = query_str.replace("'", r'"')
            # Filter by pk, title, organisation__name,
            query = get_query(
                query_str, ['pk', 'title', 'organisation__name'])
            qs = qs.filter(query).distinct()
        return qs

    def get_context_data(self, **kwargs):
        context = super(ApplicationList, self).get_context_data(**kwargs)
        context['query_string'] = ''
        
        APP_TYPE_CHOICES = []
        APP_TYPE_CHOICES_IDS = []
        for i in Application.APP_TYPE_CHOICES:
            if i[0] in [7,8,9,10,11]:
               skip = 'yes'
            else:
               APP_TYPE_CHOICES.append(i)
               APP_TYPE_CHOICES_IDS.append(i[0])
        context['app_apptypes'] = APP_TYPE_CHOICES
        context['app_appstatus'] = Application.APP_STATUS 

        if 'action' in self.request.GET and self.request.GET['action']:
            query_str = self.request.GET['q']
            query_obj = Q(pk__contains=query_str) | Q(title__icontains=query_str) | Q(organisation__name__icontains=query_str) | Q(description__icontains=query_str) | Q(related_permits__icontains=query_str) | Q(jetties__icontains=query_str) | Q(drop_off_pick_up__icontains=query_str) | Q(sullage_disposal__icontains=query_str) | Q(waste_disposal__icontains=query_str) | Q(refuel_location_method__icontains=query_str) | Q(berth_location__icontains=query_str) | Q(anchorage__icontains=query_str) | Q(operating_details__icontains=query_str) | Q(proposed_development_description__icontains=query_str)
            user_ids = SystemUser.objects.filter(email__icontains=query_str).values_list('ledger_id', flat=True)
            if user_ids:
                query_obj |= Q(applicant__in=user_ids)
                query_obj |= Q(assignee__in=user_ids)
            if self.request.GET['apptype'] != '':
                query_obj &= Q(app_type=int(self.request.GET['apptype']))
            else:
                query_obj &= Q(app_type__in=APP_TYPE_CHOICES_IDS)

            if self.request.GET['applicant'] != '':
                query_obj &= Q(applicant=int(self.request.GET['applicant']))
            if self.request.GET['wfstatus'] != '':
                #query_obj &= Q(state=int(self.request.GET['appstatus']))
                query_obj &= Q(route_status=self.request.GET['wfstatus'])
            if self.request.GET['appstatus'] != '' and self.request.GET['appstatus'] != 'all':
                query_obj &= Q(status=self.request.GET['appstatus'])

            if 'from_date' in self.request.GET: 
                 context['from_date'] = self.request.GET['from_date']
                 context['to_date'] = self.request.GET['to_date']
                 if self.request.GET['from_date'] != '':
                     from_date_db = datetime.strptime(self.request.GET['from_date'], '%d/%m/%Y').date()
                     query_obj &= Q(submit_date__gte=from_date_db)
                 if self.request.GET['to_date'] != '':
                     to_date_db = datetime.strptime(self.request.GET['to_date'], '%d/%m/%Y').date()
                     query_obj &= Q(submit_date__lte=to_date_db)

            applications = Application.objects.filter(query_obj).distinct().order_by('-id')
            context['query_string'] = self.request.GET['q']

            if self.request.GET['apptype'] != '':
                 context['apptype'] = int(self.request.GET['apptype'])
            if self.request.GET['applicant'] != '':
                 context['applicant'] = int(self.request.GET['applicant'])

            context['appstatus'] = self.request.GET['appstatus']
            if 'appstatus' in self.request.GET:
                if self.request.GET['appstatus'] != '':
                    #context['appstatus'] = int(self.request.GET['appstatus'])
                    context['appstatus'] = self.request.GET['appstatus']

            if 'wfstatus' in self.request.GET:
                if self.request.GET['wfstatus'] != '':
                    #context['appstatus'] = int(self.request.GET['appstatus'])
                    context['wfstatus'] = self.request.GET['wfstatus']



        else:
            to_date = datetime.today()
            from_date = datetime.today() - timedelta(days=10)
            context['from_date'] = from_date.strftime('%d/%m/%Y')
            context['to_date'] = to_date.strftime('%d/%m/%Y')
            context['appstatus'] = 1
            applications = Application.objects.filter(app_type__in=APP_TYPE_CHOICES_IDS, submit_date__gte=from_date, submit_date__lte=to_date, status=1).order_by('-id')

        context['app_applicants'] = {}
        context['app_applicants_list'] = []
#       context['app_apptypes'] = list(Application.APP_TYPE_CHOICES)
        #context['app_appstatus'] = list(Application.APP_STATE_CHOICES)
        context['app_wfstatus'] = list(Application.objects.values_list('route_status',flat = True).distinct())
        context['app_appstatus'] = Application.APP_STATUS 
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        context['app_list'] = []
        for app in applications:
            row = {}
            row['may_assign_to_person'] = 'False'
            row['may_assign_to_officer'] = 'False'
            row['app'] = app

            # Create a distinct list of applicants
            if app.applicant:
                applicant = SystemUser.objects.get(ledger_id=app.applicant)
                row['applicant'] = applicant
                if applicant.ledger_id in context['app_applicants']:
                    donothing = ''
                else:
                    if(applicant.legal_first_name and applicant.legal_last_name):
                        context['app_applicants'][applicant.ledger_id] = applicant.legal_first_name + ' ' + applicant.legal_last_name
                        context['app_applicants_list'].append({"id": applicant.ledger_id.id, "name": applicant.legal_first_name + ' ' + applicant.legal_last_name  })

            # end of creation
            if app.group is not None:
                if app.group.id in usergroups:
                    row['may_assign_to_person'] = 'True'
                    row['may_assign_to_officer'] = 'True'
            
            if app.assignee:
                assignee = SystemUser.objects.get(ledger_id=app.assignee)
                row['assignee'] = assignee

            if app.submitted_by:
                submitted_by = SystemUser.objects.get(ledger_id=app.submitted_by)
                row['submitted_by'] = submitted_by            

            if app.assigned_officer:
                assigned_officer = SystemUser.objects.get(ledger_id=app.assigned_officer)
                row['assigned_officer'] = assigned_officer 

            context['app_list'].append(row)
        # TODO: any restrictions on who can create new applications?
        context['may_create'] = True
        processor = SystemGroup.objects.get(name='Statdev Processor')
        # Rule: admin officers may self-assign applications.
        if processor.id in usergroups or self.request.user.is_superuser:
            context['may_assign_processor'] = True
        return context

class EmergencyWorksList(ListView):
    model = Application
    template_name = 'applications/emergencyworks_list.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        staff = context_processor['staff']
        if staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(EmergencyWorksList, self).get(request, *args, **kwargs)
   
    def get_queryset(self):
        qs = super(EmergencyWorksList, self).get_queryset()
        # Did we pass in a search string? If so, filter the queryset and return
        # it.
        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            # Replace single-quotes with double-quotes
            query_str = query_str.replace("'", r'"')
            # Filter by pk, title
            query = get_query(
            query_str, ['pk', 'title', 'organisation__name'])
            qs = qs.filter(query).distinct()
        return qs

    def get_context_data(self, **kwargs):
        context = super(EmergencyWorksList, self).get_context_data(**kwargs)
        context['query_string'] = ''
       
        applications = Application.objects.filter(app_type=4)

        context['app_applicants'] = {}
        context['app_applicants_list'] = []
        context['app_apptypes'] = list(Application.APP_TYPE_CHOICES)

        APP_STATUS_CHOICES = []
        for i in Application.APP_STATE_CHOICES:
            if i[0] in [1,11,16]:
               APP_STATUS_CHOICES.append(i)

        context['app_appstatus'] = list(APP_STATUS_CHOICES)


        if 'action' in self.request.GET and self.request.GET['action']:
            query_str = self.request.GET['q']
            query_obj = Q(pk__contains=query_str) | Q(title__icontains=query_str) | Q(organisation__name__icontains=query_str)
            query_obj &= Q(app_type=4)

            if self.request.GET['applicant'] != '':
                query_obj &= Q(applicant=int(self.request.GET['applicant']))
            if self.request.GET['appstatus'] != '':
                query_obj &= Q(state=int(self.request.GET['appstatus']))


            applications = Application.objects.filter(query_obj)
            context['query_string'] = self.request.GET['q']

        if 'applicant' in self.request.GET:
            if self.request.GET['applicant'] != '':
               context['applicant'] = int(self.request.GET['applicant'])
            if 'appstatus' in self.request.GET:
               if self.request.GET['appstatus'] != '':
                  context['appstatus'] = int(self.request.GET['appstatus'])

        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        context['app_list'] = []
        for app in applications:
            row = {}
            row['may_assign_to_person'] = 'False'
            row['app'] = app

            # Create a distinct list of applicants
            
            if app.applicant:
                applicant = SystemUser.objects.get(ledger_id=app.applicant)
                row['applicant'] = applicant
                if applicant.ledger_id in context['app_applicants']:
                    donothing = ''
                else:
                    if(applicant.legal_first_name and applicant.legal_last_name):
                        context['app_applicants'][applicant.ledger_id] = applicant.legal_first_name + ' ' + applicant.legal_last_name
                        context['app_applicants_list'].append({"id": applicant.ledger_id.id, "name": applicant.legal_first_name + ' ' + applicant.legal_last_name  })
            # end of creation

            if app.group is not None:
                if app.group.id in usergroups:
                    row['may_assign_to_person'] = 'True'
            context['app_list'].append(row)
        # TODO: any restrictions on who can create new applications?
        context['may_create'] = True
        processor = SystemGroup.objects.get(name='Statdev Processor')
        # Rule: admin officers may self-assign applications.
        if processor.id in usergroups or self.request.user.is_superuser:
            context['may_assign_processor'] = True
        return context

class ComplianceList(TemplateView):
    #model = Compliance
    template_name = 'applications/compliance_list.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        staff = context_processor['staff']
        if staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ComplianceList, self).get(request, *args, **kwargs)

    #def get_queryset(self):
    #    qs = super(ComplianceList, self).get_queryset()
    #    # Did we pass in a search string? If so, filter the queryset and return
    #    # it.
    #    if 'q' in self.request.GET and self.request.GET['q']:
    #        query_str = self.request.GET['q']
    #        # Replace single-quotes with double-quotes
    #        query_str = query_str.replace("'", r'"')
    #        # Filter by pk, title, applicant__email, organisation__name,
    #        # assignee__email
    #        query = get_query(
    #            query_str, ['pk', 'title', 'applicant__email', 'assignee__email','approval_id'])
    #        qs = qs.filter(query).distinct()
    #    return qs

    def get_context_data(self, **kwargs):
        context = super(ComplianceList, self).get_context_data(**kwargs)
        context['query_string'] = ''

        #items = ComplianceGroup.objects.filter().order_by('due_date')

        context['app_applicants'] = {}
        context['app_applicants_list'] = []
        #context['app_apptypes'] = list(Application.APP_TYPE_CHOICES)
        #applications = ComplianceGroup.objects.filter(query_obj)

        APP_STATUS_CHOICES = []
        for i in Application.APP_STATE_CHOICES:
            if i[0] in [1,11,16]:
               APP_STATUS_CHOICES.append(i)

        context['app_appstatus'] = list(APP_STATUS_CHOICES)

        query_obj = Q()
        if 'action' in self.request.GET and self.request.GET['action']:
            if 'q' in self.request.GET and self.request.GET['q']:
               query_str = self.request.GET['q']
               query_obj = Q(pk__contains=query_str) | Q(title__icontains=query_str)
               user_ids = SystemUser.objects.filter(email__icontains=query_str).exclude(ledger_id__isnull=True).values_list('ledger_id', flat=True)
               if user_ids:
                    query_obj |= Q(applicant__in=user_ids)
                    query_obj |= Q(assignee__in=user_ids)
               #query_obj &= Q(app_type=4)
               query_obj = Q(query_obj)
            context['query_string'] = self.request.GET['q']
            #if self.request.GET['applicant'] != '':
            #    query_obj &= Q(applicant=int(self.request.GET['applicant']))
            #if self.request.GET['appstatus'] != '':
            #    query_obj &= Q(state=int(self.request.GET['appstatus']))

            if 'from_date' in self.request.GET:
                 context['from_date'] = self.request.GET['from_date']
                 context['to_date'] = self.request.GET['to_date']
                 if self.request.GET['from_date'] != '':
                     from_date_db = datetime.strptime(self.request.GET['from_date'], '%d/%m/%Y').date()
                     query_obj &= Q(due_date__gte=from_date_db)
                 if self.request.GET['to_date'] != '':
                     to_date_db = datetime.strptime(self.request.GET['to_date'], '%d/%m/%Y').date()
                     query_obj &= Q(due_date__lte=to_date_db)
        else:
            to_date = datetime.today()
            from_date = datetime.today() - timedelta(days=100)
            context['from_date'] = from_date.strftime('%d/%m/%Y')
            context['to_date'] = to_date.strftime('%d/%m/%Y')
            query_obj &= Q(due_date__gte=from_date)
            query_obj &= Q(due_date__lte=to_date)


        items = Compliance.objects.filter(query_obj).order_by('due_date')
        context['items'] = items


        if 'applicant' in self.request.GET:
            if self.request.GET['applicant'] != '':
               context['applicant'] = int(self.request.GET['applicant'])
            if 'appstatus' in self.request.GET:
               if self.request.GET['appstatus'] != '':
                  context['appstatus'] = int(self.request.GET['appstatus'])



        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        context['app_list'] = []
        for item in items:
            row = {}
            row['may_assign_to_person'] = 'False'
            row['app'] = item

            # Create a distinct list of applicants
            
            if item.applicant:
                applicant = SystemUser.objects.get(ledger_id=item.applicant)
                row['applicant'] = applicant
                if applicant.ledger_id in context['app_applicants']:
                    donothing = ''
                else:
                    if(applicant.legal_first_name and applicant.legal_last_name):
                        context['app_applicants'][applicant.ledger_id] = applicant.legal_first_name + ' ' + applicant.legal_last_name
                        context['app_applicants_list'].append({"id": applicant.ledger_id.id, "name": applicant.legal_first_name + ' ' + applicant.legal_last_name  })
                
            if item.assignee:
                assignee = SystemUser.objects.get(ledger_id=item.assignee)
                row['assignee'] = assignee
            # end of creation

            if item.group is not None:
               if item.group.id in usergroups:
                   row['may_assign_to_person'] = 'True'
            context['app_list'].append(row)
        # TODO: any restrictions on who can create new applications?
        context['may_create'] = True
        processor = SystemGroup.objects.get(name='Statdev Processor')
        # Rule: admin officers may self-assign applications.
        if processor.id in usergroups or self.request.user.is_superuser:
            context['may_assign_processor'] = True
        return context

class SearchMenu(ListView):
    model = Compliance
    template_name = 'applications/search_menu.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']

        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(SearchMenu, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(SearchMenu, self).get_context_data(**kwargs)
        return context

class OrganisationAccessRequest(ListView):
    model = OrganisationPending
    template_name = 'applications/organisation_pending.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(OrganisationAccessRequest, self).get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super(OrganisationAccessRequest, self).get_queryset()
        # Did we pass in a search string? If so, filter the queryset and return
        # it.
        processor = SystemGroup.objects.get(name='Statdev Processor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        if processor.id in usergroups:
           
            if 'q' in self.request.GET and self.request.GET['q']:
                query_str = self.request.GET['q']
                # Replace single-quotes with double-quotes
                query_str = query_str.replace("'", r'"')
                # Filter by pk
                query = get_query(
                    query_str, ['pk'])
                qs = qs.filter(query).distinct()
                return qs

    def get_context_data(self, **kwargs):
        context = super(OrganisationAccessRequest, self).get_context_data(**kwargs)
        context['orgs_pending_status'] = OrganisationPending.STATUS_CHOICES
        pending_org = OrganisationPending.objects.all().distinct('email_user')
        email_users = pending_org.values_list('email_user', flat=True)
        applicants = SystemUser.objects.filter(ledger_id__in=email_users).exclude(ledger_id__isnull=True)
        context['orgs_pending_applicants'] = applicants
        query = Q()
        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            query_str = query_str.replace("'", r'"')
            query &= Q(Q(name__icontains=query_str) | Q(abn__icontains=query_str))


        if 'applicant' in self.request.GET:
            if self.request.GET['applicant'] != '':
                query  &= Q(email_user=int(self.request.GET['applicant']))
        if 'appstatus' in self.request.GET:
            if self.request.GET['appstatus'] != '':
                query  &= Q(status=self.request.GET['appstatus'])

        orgs_pending_list = OrganisationPending.objects.filter(query)[:200]
        context['orgs_pending'] = []
        for org in orgs_pending_list:
            row = {}
            row['org'] = org
            if org.email_user:
                row['email_user'] = SystemUser.objects.get(ledger_id=org.email_user)
            if org.assignee:
                row['assignee'] = SystemUser.objects.get(ledger_id=org.assignee)
            context['orgs_pending'].append(row)
                

        if 'applicant' in self.request.GET:
           if self.request.GET['applicant'] != '':
               context['applicant'] = int(self.request.GET['applicant'])

        if 'appstatus' in self.request.GET:
           if self.request.GET['appstatus'] != '':
               context['appstatus'] = int(self.request.GET['appstatus'])
        context['query_string'] = ''
        if 'q' in self.request.GET and self.request.GET['q']:
            context['query_string'] = self.request.GET['q']

        return context

class OrganisationAccessRequestUpdate(LoginRequiredMixin,UpdateView):
    form_class = apps_forms.OrganisationAccessRequestForm
    model = OrganisationPending
    template_name = 'applications/organisation_pending_update.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(OrganisationAccessRequestUpdate, self).get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super(OrganisationAccessRequestUpdate, self).get_queryset()
        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            query_str = query_str.replace("'", r'"')
            query = get_query(
                    query_str, ['pk'])
            qs = qs.filter(query).distinct()
        return qs

    def get_initial(self):
        initial = super(OrganisationAccessRequestUpdate, self).get_initial()
        status = self.kwargs['action']
        if status == 'approve':
            initial['status'] = 2
        if status == 'decline':
            initial['status'] = 3
        return initial

    def post(self, request, *args, **kwargs):
        pk = self.kwargs['pk']
        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('organisation_access_requests_view', args=(pk,) ))
        return super(OrganisationAccessRequestUpdate, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(OrganisationAccessRequestUpdate, self).get_context_data(**kwargs)
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        forms_data = form.cleaned_data
        status = self.kwargs['action']
        app_id = None
        if 'application_id' in self.kwargs:
            app_id = self.kwargs['application_id']

        if status == 'approve':

        #      print self.object.name
        #      print self.object.abn
        #      print self.object.identification
        #       print self.object.postal_address
        #       print self.object.billing_address

            doc_identification = Record(id=self.object.identification.id)

            new_org = Organisation.objects.create(name=self.object.name,
                                                  abn=self.object.abn,
                                                  identification=None,
                                                  postal_address=self.object.postal_address,
                                                  billing_address=self.object.billing_address
                                                 )

            OrganisationExtras.objects.create(organisation=new_org,
                                              pin1=random_generator(),
                                              pin2=random_generator(),
                                              identification=doc_identification
                                             )


            Delegate.objects.create(email_user=self.object.email_user,organisation=new_org)
            if self.request.user.is_staff is True:
              if app_id:
                 app = Application.objects.get(id=app_id)
                 app.organisation = new_org   
                 app.save()


            # random_generator
            #OrganisationExtras.objects.create()
            self.object.status = 2
            system_user = SystemUser.objects.get(ledger_id=self.object.email_user)
            OrganisationContact.objects.create(
                                  email=system_user.email,
                                  first_name=system_user.first_name,
                                  last_name=system_user.last_name,
                                  phone_number=system_user.phone_number,
                                  mobile_number=system_user.mobile_number,
                                  fax_number=system_user.fax_number,
                                  organisation=new_org
            )

            action = Action(
                content_object=self.object, user=self.request.user.id,
                action='Organisation Access Request Approved')
            action.save()
        elif status == 'decline':
            self.object.status = 3
            action = Action(
                content_object=self.object, user=self.request.user.id,
                action='Organisation Access Request Declined')
            action.save()

        self.object.save()
        
        if app_id is None:
            success_url = reverse('organisation_access_requests')
        else:
            success_url = reverse('application_update',args=(app_id,))

        return HttpResponseRedirect(success_url)

class OrganisationAccessRequestView(LoginRequiredMixin,DetailView):
    model = OrganisationPending
    template_name = 'applications/organisation_pending_view.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(OrganisationAccessRequestView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(OrganisationAccessRequestView, self).get_context_data(**kwargs)
        app = self.get_object()
        try:
             context['org'] = Organisation.objects.get(abn=app.abn)
        except: 
             donothing = ''
#        context['conditions'] = Compliance.objects.filter(approval_id=app.id)
        return context

class SearchPersonList(ListView):
    model = Compliance
    template_name = 'applications/search_person_list.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(SearchPersonList, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        context = super(SearchPersonList, self).get_context_data(**kwargs)
        context['query_string'] = ''

        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            query_str_split = query_str.split()
            search_filter = Q()
            listorgs = Delegate.objects.filter(organisation__name__icontains=query_str)
            orgs = []
            for d in listorgs:
                orgs.append(d.email_user)

            for se_wo in query_str_split:
                search_filter= Q(ledger_id__id__contains=se_wo) | Q(email__icontains=se_wo) | Q(first_name__icontains=se_wo) | Q(last_name__icontains=se_wo)
            # Add Organsations Results , Will also filter out duplicates
            search_filter |= Q(pk__in=orgs)
            # Get all applicants
            listusers = SystemUser.objects.filter(search_filter).exclude(is_staff=True)
        else:
            listusers = SystemUser.objects.all().exclude(is_staff=True).order_by('-id')      

        listusers = listusers.filter(Q(legal_first_name__isnull=False) & Q(legal_last_name__isnull=False)).distinct()[:200]
        context['acc_list'] = []
        for lu in listusers:
            row = {}
            row['acc_row'] = lu
            lu.organisations = []
            lu.organisations = Delegate.objects.filter(email_user=lu.id)
            #for o in lu.organisations:
            #    print o.organisation
            context['acc_list'].append(row)

        if 'q' in self.request.GET and self.request.GET['q']:
            context['query_string'] = self.request.GET['q']

        return context


class SearchCompanyList(ListView):
    model = Compliance
    template_name = 'applications/search_company_list.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(SearchCompanyList, self).get(request, *args, **kwargs)


    def get_context_data(self, **kwargs):

        context = super(SearchCompanyList, self).get_context_data(**kwargs)
        context['query_string'] = ''

        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            query_str_split = query_str.split()
            search_filter = Q()
            #listorgs = Delegate.objects.filter(organisation__name__icontains=query_str)
            #orgs = []
            #for d in listorgs:
            #    d.email_user.id
            #    orgs.append(d.email_user.id)

            #for se_wo in query_str_split:
            #    search_filter= Q(pk__contains=se_wo) | Q(email__icontains=se_wo) | Q(first_name__icontains=se_wo) | Q(last_name__icontains=se_wo)
            # Add Organsations Results , Will also filter out duplicates
            #search_filter |= Q(pk__in=orgs)
            # Get all applicants
#            listusers = Delegate.objects.filter(organisation__name__icontains=query_str)
            listusers = OrganisationExtras.objects.filter(organisation__name__icontains=query_str)[:200]
        else:
            #            listusers = Delegate.objects.all()
            listusers = OrganisationExtras.objects.all().order_by('-id')[:200]

        context['acc_list'] = []
        for lu in listusers:
            row = {}
            # print lu.organisation.name
            row['acc_row'] = lu
#            lu.organisations = []
#            lu.organisations = Delegate.objects.filter(email_user=lu.id)
             #for o in lu.organisations:
             #    print o.organisation
            context['acc_list'].append(row)

        if 'q' in self.request.GET and self.request.GET['q']:
            context['query_string'] = self.request.GET['q']

        return context

class SearchKeywords(ListView):
    model = Compliance
    template_name = 'applications/search_keywords_list.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']

        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(SearchKeywords, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(SearchKeywords, self).get_context_data(**kwargs)

        context['APP_TYPES'] = Application.APP_TYPE_CHOICES
        context['query_string'] = ''

        APP_TYPE_CHOICES = [{"key":"applications", "value":"Applications"},{"key":"approvals","value":"Approvals"},{"key":"emergency","value":"Emergency Works"},{"key":"compliance","value":"Compliance"}]

        app_list_filter = []
        context['app_type_checkboxes'] = {}
        if len(self.request.GET) == 0:
            context['app_type_checkboxes'] = {'applications': 'checked', 'approvals': 'checked', 'emergency': 'checked','compliance': 'checked'}

        # print app_list_filter
        if "filter-applications" in self.request.GET:
            app_list_filter.append(1)
            app_list_filter.append(2)
            app_list_filter.append(3)
            context['app_type_checkboxes']['applications'] = 'checked'

            # print app_list_filter
        if "filter-emergency" in self.request.GET:
            app_list_filter.append(4)
            context['app_type_checkboxes']['emergency'] = 'checked'
        if "filter-approvals" in self.request.GET:
            context['app_type_checkboxes']['approvals'] = 'checked'
        if "filter-compliance" in self.request.GET:
            context['app_type_checkboxes']['compliance'] = 'checked'

            # print app_list_filter
        context['APP_TYPES'] = list(APP_TYPE_CHOICES)
        query_str_split = ''
        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            query_str_split = query_str.split()
            search_filter = Q()
            search_filter_app = Q(app_type__in=app_list_filter) 
           
            # Applications: 
            for se_wo in query_str_split:
               search_filter = Q(pk__contains=se_wo)
               search_filter |= Q(title__icontains=se_wo)
               search_filter |= Q(description__icontains=se_wo)
               search_filter |= Q(related_permits__icontains=se_wo)
               search_filter |= Q(address__icontains=se_wo)
               search_filter |= Q(jetties__icontains=se_wo)
               search_filter |= Q(drop_off_pick_up__icontains=se_wo)
               search_filter |= Q(sullage_disposal__icontains=se_wo)
               search_filter |= Q(waste_disposal__icontains=se_wo)
               search_filter |= Q(refuel_location_method__icontains=se_wo)
               search_filter |= Q(berth_location__icontains=se_wo)
               search_filter |= Q(anchorage__icontains=se_wo)
               search_filter |= Q(operating_details__icontains=se_wo)
               search_filter |= Q(proposed_development_current_use_of_land__icontains=se_wo)
               search_filter |= Q(proposed_development_description__icontains=se_wo)
                
            # Add Organsations Results , Will also filter out duplicates
            # search_filter |= Q(pk__in=orgs)
            # Get all applicants
           
            apps = Application.objects.filter(search_filter_app & search_filter)

            search_filter = Q()
            for se_wo in query_str_split:
                 search_filter = Q(pk__contains=se_wo)
                 search_filter |= Q(title__icontains=se_wo)

            approvals = []
            if "filter-approvals" in self.request.GET:
                 approvals = Approval.objects.filter(search_filter)

            compliance = []
            if "filter-compliance" in self.request.GET:
                compliance = Compliance.objects.filter()


        else:
            #apps = Application.objects.filter(app_type__in=[1,2,3,4])
            #approvals = Approval.objects.all()
            apps = []
            approvals = []
            compliance = []


        context['apps_list'] = []
        for lu in apps:
            row = {}
            lu.text_found = ''
            if len(query_str_split) > 0:
              for se_wo in query_str_split:
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.title)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.related_permits)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.address)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.description)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.jetties)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.drop_off_pick_up)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.sullage_disposal)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.waste_disposal)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.refuel_location_method)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.berth_location)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.anchorage)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.operating_details)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.proposed_development_current_use_of_land)
                lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.proposed_development_description)

            if lu.app_type in [1,2,3]:
                lu.app_group = 'application'
            elif lu.app_type in [4]:
                lu.app_group = 'emergency'


            row['row'] = lu
            context['apps_list'].append(row)

        for lu in approvals:
            row = {}
            lu.text_found = ''
            if len(query_str_split) > 0:
                for se_wo in query_str_split:
                    lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.title)
            lu.app_group = 'approval'
            row['row'] = lu
            context['apps_list'].append(row)

        for lu in compliance:
            row = {}
            lu.text_found = ''
            if len(query_str_split) > 0:
                for se_wo in query_str_split:
                    lu.text_found += self.slice_keyword(" "+se_wo+" ", lu.title)
            lu.app_group = 'compliance'
            row['row'] = lu
            context['apps_list'].append(row)

        if 'q' in self.request.GET and self.request.GET['q']:
            context['query_string'] = self.request.GET['q']

        return context

    def slice_keyword(self,keyword,text_string):      

        if text_string is None:
            return ''
        if len(text_string) < 1:
            return ''
        text_string = " "+ text_string.lower() + " " 
        splitr= text_string.split(keyword.lower())
        splitr_len = len(splitr)
        text_found = ''
        loopcount = 0
        if splitr_len < 2:
           return ''
        for t in splitr:
            loopcount = loopcount + 1
            text_found += t[-20:]
            if loopcount > 1:
                if loopcount == splitr_len:
                    break
            text_found += "<b>"+keyword+"</b>"
        if len(text_found) > 2:
            text_found = text_found + '...'
        return text_found

class SearchReference(ListView):
    model = Compliance
    template_name = 'applications/search_reference_list.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']

        if admin_staff == True:
           donothing = ""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(SearchReference, self).get(request, *args, **kwargs)

    def render_to_response(self, context):
        #    print "YESS"
        #    print context['form_prefix']
        #    print context['form_no']
        #    form = form_class(request.POST)

        if len(context['form_prefix']) > 0:
            if context['form_no'] > 0:
                if context['form_prefix'] == 'EW-' or context['form_prefix'] == 'WO-':
                    apps = Application.objects.filter(id=context['form_no'])
                    if len(apps) > 0:
                        return HttpResponseRedirect(reverse('application_detail', args=(context['form_no'],)))
                    else:
                        if context['form_prefix'] == 'EW-':
                            messages.error(self.request, 'Emergency Works does not exist.')
                        if context['form_prefix'] == 'WO-':
                            messages.error(self.request, 'Application does not exist.')

                        return HttpResponseRedirect(reverse('search_reference'))
                elif context['form_prefix'] == 'AP-':
                        approval = Approval.objects.filter(id=context['form_no'])
                        if len(approval) > 0:
                            return HttpResponseRedirect(reverse('approval_detail', args=(context['form_no'],)))
                        else:
                            messages.error(self.request, 'Approval does not exist.')

                elif context['form_prefix'] == 'CO-':
                    comp = Compliance.objects.filter(approval_id=context['form_no'])
                    if len(comp) > 0:
                        return HttpResponseRedirect(reverse('compliance_approval_detail', args=(context['form_no'],)))
                    else:
                        messages.error(self.request, 'Compliance does not exist.')

                elif context['form_prefix'] == 'AC-':
                    person = SystemUser.objects.filter(id=context['form_no'])
                    if len(person) > 0:
                        return HttpResponseRedirect(reverse('person_details_actions', args=(context['form_no'],'personal')))
                    else:
                        messages.error(self.request, 'Person account does not exist.')

                elif context['form_prefix'] == 'OG-':
                    org = Organisation.objects.filter(id=context['form_no'])
                    if len(org) > 0:
                        return HttpResponseRedirect(reverse('organisation_details_actions', args=(context['form_no'],'company')))
                    else:
                        messages.error(self.request, 'Organisation does not exist.')
                elif context['form_prefix'] == 'AR-':
                    org_pend = OrganisationPending.objects.filter(id=context['form_no'])
                    if len(org_pend) > 0:
                        return HttpResponseRedirect(reverse('organisation_access_requests_view', args=(context['form_no'])))
                    else:
                        messages.error(self.request, 'Company Access Request does not exist.')
                else:
                   messages.error(self.request, 'Invalid Prefix Provided,  Valid Prefix are EW- WO- AP- CO- AC- OG- AR-')
                   return HttpResponseRedirect(reverse('search_reference'))

            else:
                 messages.error(self.request, 'Invalid Prefix Provided,  Valid Prefix are EW- WO- AP- CO- AC- OG- AR-')
                 #return HttpResponseRedirect(reverse('search_reference'))
        #if len(context['form_prefix']) == 0:
        #    messages.error(self.request, 'Invalid Prefix Provided,  Valid Prefix are EW- WO- AP- CO- AC- OG- AR-')
        #    #return HttpResponseRedirect(reverse('search_reference'))
               


#        if context['form_prefix'] == 'EW-' or context['form_prefix'] == 'WO-' or) > 0:
 #              messages.error(self.request, 'Invalid Prefix Provided,  Valid Prefix EW- WO- AP- CO-')
#               return HttpResponseRedirect(reverse('search_reference'))
        # print self
        #context['messages'] = self.messages
        template = get_template(self.template_name)
        #context = RequestContext(self.request, context)
        return HttpResponse(template.render(context, request=self.request))

    def get_context_data(self, **kwargs):
        context = super(SearchReference, self).get_context_data(**kwargs)
        context.update(template_context(self.request))
        context['messages'] = messages.get_messages(self.request)
        context['query_string'] = ''
        context['form_prefix'] = ''
        context['form_no'] = 0

        query_str = self.request.GET.get('q', '').strip()
        if query_str:
            context['query_string'] = query_str
            form_prefix = query_str[:3]
            form_no_str = query_str[3:]

            context['form_prefix'] = form_prefix
            try:
                context['form_no'] = int(form_no_str)
            except ValueError:
                context['form_no'] = 0  # fallback if form_no_str is not a valid integer

        return context

class ApplicationCreateEW(LoginRequiredMixin, CreateView):
    form_class = apps_forms.ApplicationCreateForm
    template_name = 'applications/application_form.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ApplicationCreateEW, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationCreateEW, self).get_context_data(**kwargs)
        context['page_heading'] = 'Create new application'
        return context

    def get_form_kwargs(self):
        kwargs = super(ApplicationCreateEW, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        initial = {}
        initial['app_type'] = 4
        return initial

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('home'))
        return super(ApplicationCreateEW, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override form_valid to set the assignee as the object creator.
        """
        self.object = form.save(commit=False)
        # If this is not an Emergency Works set the applicant as current user
        if not (self.object.app_type == Application.APP_TYPE_CHOICES.emergency):
            self.object.applicant = self.request.user.id
        self.object.assignee = self.request.user.id
        self.object.submitted_by = self.request.user.id
        self.object.assignee = self.request.user.id
        self.object.submit_date = date.today()
        self.object.state = self.object.APP_STATE_CHOICES.draft
        self.object.app_type = 4
        processor = SystemGroup.objects.get(name='Statdev Processor')
        self.object.group = processor
        self.object.save()
        success_url = reverse('application_update', args=(self.object.pk,))
        return HttpResponseRedirect(success_url)

class ApplicationCreate(LoginRequiredMixin, CreateView):
    form_class = apps_forms.ApplicationCreateForm
    template_name = 'applications/application_form.html'

    def get_context_data(self, **kwargs):
        context = super(ApplicationCreate, self).get_context_data(**kwargs)
        context['page_heading'] = 'Create new application'
        return context

    def get_form_kwargs(self):
        kwargs = super(ApplicationCreate, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('home'))
        return super(ApplicationCreate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override form_valid to set the assignee as the object creator.
        """
        self.object = form.save(commit=False)
        # If this is not an Emergency Works set the applicant as current user
        if not (self.object.app_type == Application.APP_TYPE_CHOICES.emergency):
            self.object.applicant = self.request.user.id
        self.object.assignee = self.request.user.id
        self.object.submitted_by = self.request.user.id
        self.object.assignee = self.request.user.id
        self.object.submit_date = date.today()
        self.object.state = self.object.APP_STATE_CHOICES.new
        self.object.save()
        success_url = reverse('application_update', args=(self.object.pk,))
        return HttpResponseRedirect(success_url)

class CreateAccount(LoginRequiredMixin, CreateView):
    form_class = apps_forms.CreateAccountForm
    template_name = 'applications/create_account_form.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']

        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(CreateAccount, self).get(request, *args, **kwargs)

#    def get(self, request, *args, **kwargs):
#        #if self.request.user.groups().filter(name='Processor').exists():
#        #    app = Application.objects.create(submitted_by=self.request.user.id
#        #                                     ,submit_date=date.today()
#        #                                     ,state=Application.APP_STATE_CHOICES.new
#        #                                     )
#        #    return HttpResponseRedirect("/applications/"+str(app.id)+"/apply/apptype/")
#        return super(CreateAccount, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CreateAccount, self).get_context_data(**kwargs)
        context['page_heading'] = 'Create new account'
        return context

    def get_form_kwargs(self):
        kwargs = super(CreateAccount, self).get_form_kwargs()
        #kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):

        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        print("first this")

        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('home'))
        return super(CreateAccount, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override form_valid to set the assignee as the object creator.
        """
        self.object = form.save(commit=False)
        forms_data = form.cleaned_data
        ledger_user = get_or_create(forms_data['email'])
        
        email_user = EmailUser.objects.get(pk=ledger_user["data"]["emailuser_id"])
        self.object.ledger_id = email_user
        self.object.save()
        # If this is not an Emergency Works set the applicant as current user
#        success_url = reverse('first_login_info', args=(self.object.pk,1))
        app_id = None
        if 'application_id'  in self.kwargs:
            app_id = self.kwargs['application_id']
        path_first_time = '/ledger-ui/accounts-management/'+str(self.object.pk)+'/change'
        return HttpResponseRedirect(path_first_time)

class ApplicationApply(LoginRequiredMixin, CreateView):
    form_class = apps_forms.ApplicationApplyForm
    template_name = 'applications/application_apply_form.html'

    def get(self, request, *args, **kwargs):
        processor = SystemGroup.objects.get(name='Statdev Processor')
        assessor = SystemGroup.objects.get(name='Statdev Assessor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        if (processor.id in usergroups or 
            assessor.id in usergroups):
            app = Application.objects.create(submitted_by=self.request.user.id
                                             ,submit_date=date.today()
                                             ,state=Application.APP_STATE_CHOICES.new
                                             ,status=3

                                             #,assignee=self.request.user.id
                                             )
            return HttpResponseRedirect("/applications/"+str(app.id)+"/apply/apptype/")
        return super(ApplicationApply, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationApply, self).get_context_data(**kwargs)
        context['page_heading'] = 'Create new application'

       
        return context

    def get_form_kwargs(self):
        kwargs = super(ApplicationApply, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('home'))
        return super(ApplicationApply, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override form_valid to set the assignee as the object creator.
        """
        self.object = form.save(commit=False)
        forms_data = form.cleaned_data

        # If this is not an Emergency Works set the applicant as current user
        if not (self.object.app_type == Application.APP_TYPE_CHOICES.emergency):
            self.object.applicant = self.request.user.id
        self.object.assignee = self.request.user.id
        self.object.submitted_by = self.request.user.id
        self.object.assignee = self.request.user.id
        self.object.submit_date = date.today()
        self.object.state = self.object.APP_STATE_CHOICES.draft
        self.object.status = 3
        self.object.save()
        apply_on_behalf_of = forms_data['apply_on_behalf_of']
        if apply_on_behalf_of == '1':
            nextstep = 'apptype'
        else:
            nextstep = 'info'

        success_url = reverse('application_apply_form', args=(self.object.pk,nextstep))
        return HttpResponseRedirect(success_url)

class ApplicationApplyUpdate(LoginRequiredMixin, UpdateView):
    model = Application 
    form_class = apps_forms.ApplicationApplyUpdateForm

    def get(self, request, *args, **kwargs):
        return super(ApplicationApplyUpdate, self).get(request, *args, **kwargs)

    def get_initial(self):
        initial = super(ApplicationApplyUpdate, self).get_initial()
        initial['action'] = self.kwargs['action']
#        initial['organisations_list'] = list(i.organisation for i in Delegate.objects.filter(email_user=self.request.user.id))
        initial['organisations_list'] = []
        row = () 
        for i in Delegate.objects.filter(email_user=self.request.user.id):
            initial['organisations_list'].append((i.organisation.id,i.organisation.name))
        initial['is_staff'] = False
        if self.request.user.is_staff == True:
            initial['is_staff'] = True
        return initial

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = self.get_object().application_set.first()
            return HttpResponseRedirect(app.get_absolute_url())
        return super(ApplicationApplyUpdate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        forms_data = form.cleaned_data
        action = self.kwargs['action']
        nextstep = ''
        apply_on_behalf_of = 0
        if 'apply_on_behalf_of' in forms_data:
            apply_on_behalf_of = forms_data['apply_on_behalf_of']
        if action == 'new':
            if apply_on_behalf_of == '1':
               nextstep = 'apptype'
            else:
               nextstep = 'info'
        elif action == 'info':
            nextstep = 'apptype'
        app = Application.objects.get(pk=self.object.pk)
        if self.object.app_type == 4:
             self.object.group = SystemGroup.objects.get(name='Statdev Assessor')
             self.object.assignee = self.request.user.id
             self.object.save()
        if action == 'apptype':
            processor = SystemGroup.objects.get(name='Statdev Processor')
            assessor = SystemGroup.objects.get(name='Statdev Assessor')
            usergroups = self.request.user.get_system_group_permission(self.request.user.id)
            if processor.id in usergroups or assessor.id in usergroups:
                success_url = reverse('applicant_change', args=(self.object.pk,))
            else:
                success_url = reverse('application_update', args=(self.object.pk,))
        else:
            success_url = reverse('application_apply_form', args=(self.object.pk,nextstep))
        return HttpResponseRedirect(success_url)


class ApplicationDetail(DetailView):
    model = Application


    def get(self, request, *args, **kwargs):
        # TODO: business logic to check the application may be changed.
        app = self.get_object()

        user_id = None

        if app.state == 18:
             return HttpResponseRedirect(reverse('application_booking', args=(app.id,)))

        if request.user:
           user_id = request.user.id

        # start
        if request.user.is_staff == True:
             pass
        elif request.user.is_superuser == True:
             pass
        elif app.submitted_by == user_id:
             pass
        elif app.applicant:
             if app.applicant == user_id:
                 pass 
             else:
                 messages.error(self.request, 'Forbidden from viewing this page.')
                 return HttpResponseRedirect("/")
        elif Delegate.objects.filter(email_user=request.user.id).count() > 0:
             pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")


        # Rule: if the application status is 'draft', it can be updated.
        return super(ApplicationDetail, self).get(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(ApplicationDetail, self).get_context_data(**kwargs)
        app = self.get_object()

        context['may_update'] = "False"
        context['allow_admin_side_menu'] = "False"
        context['is_staff'] = self.request.user.is_staff
        # if app.group is not None:
        emailcontext = {'user': 'Jason'}
        if  Location.objects.filter(application_id=self.object.id).exists(): 
              context['location'] = Location.objects.get(application_id=self.object.id)
        else:
              #context['location'] = Location
              context['location'] = ''
        #sendHtmlEmail(['jason.moore@dpaw.wa.gov.au'],'HTML TEST EMAIL',emailcontext,'email.html' ,None,None,None)
        #emailGroup('HTML TEST EMAIL',emailcontext,'email.html' ,None,None,None,'Processor')
        if app.assignee is not None:
            context['application_assignee_id'] = app.assignee
            
        if app.applicant is not None:
            context['applicant'] = SystemUser.objects.get(ledger_id=app.applicant)
            context['postal_address'] = SystemUserAddress.objects.get(system_user=context['applicant'], address_type='postal_address')

        if app.assignee is not None:
            context['assignee'] = SystemUser.objects.get(ledger_id=app.assignee)

        if app.assigned_officer is not None:
            context['assigned_officer'] = SystemUser.objects.get(ledger_id=app.assigned_officer)
        
        if app.submitted_by is not None:
            context['submitted_by'] = SystemUser.objects.get(ledger_id=app.submitted_by)        
            
        context['may_assign_to_person'] = 'False'
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        context['stakeholder_communication'] = StakeholderComms.objects.filter(application=app)
        #print ("STAKE HOLDER")
        #print (context['stakeholder_communication'])
        # print app.group
        #if app.group in usergroups:
        #    if float(app.routeid) > 1:
        #        context['may_assign_to_person'] = 'True'
        if app.app_type == app.APP_TYPE_CHOICES.part5:
            self.template_name = 'applications/application_details_part5_new_application.html'
            part5 = Application_Part5()
            context = part5.get(app, self, context)
        elif app.app_type == app.APP_TYPE_CHOICES.part5cr:
            self.template_name = 'applications/application_part5_ammendment_request.html'
            part5 = Application_Part5()
            context = part5.get(app, self, context)
            #flow = Flow()
            #workflowtype = flow.getWorkFlowTypeFromApp(app)
            #flow.get(workflowtype)
            #context = flow.getAccessRights(self.request,context,app.routeid,workflowtype)
            #context = flow.getCollapse(context,app.routeid,workflowtype)
            #context = flow.getHiddenAreas(context,app.routeid,workflowtype)
            #context['workflow_actions'] = flow.getAllRouteActions(app.routeid,workflowtype)
            #context['formcomponent'] = flow.getFormComponent(app.routeid,workflowtype)
        elif app.app_type == app.APP_TYPE_CHOICES.part5amend:
            self.template_name = 'applications/application_part5_amend.html'
            part5 = Application_Part5()
            context = part5.get(app, self, context)
        elif app.app_type == app.APP_TYPE_CHOICES.emergency:
            self.template_name = 'applications/application_detail_emergency.html'
            emergency = Application_Emergency()
            context = emergency.get(app, self, context)
        elif app.app_type == app.APP_TYPE_CHOICES.permit:
            self.template_name = 'applications/application_detail_permit.html'
            permit = Application_Permit()
            context = permit.get(app, self, context)
          
        elif app.app_type == app.APP_TYPE_CHOICES.licence:
            self.template_name = 'applications/application_detail_license.html'
            licence = Application_Licence()
            context = licence.get(app, self, context)
        else:
            flow = Flow()
            workflowtype = flow.getWorkFlowTypeFromApp(app)
            flow.get(workflowtype)
            context = flow.getAccessRights(self.request,context,app.routeid,workflowtype)
            context = flow.getCollapse(context,app.routeid,workflowtype)
            context = flow.getHiddenAreas(context,app.routeid,workflowtype,self.request)
            context['workflow_actions'] = flow.getAllRouteActions(app.routeid,workflowtype)
            context['formcomponent'] = flow.getFormComponent(app.routeid,workflowtype)
#        print context['workflow_actions']
#        print context['allow_admin_side_menu']

        # context = flow.getAllGroupAccess(request,context,app.routeid,workflowtype)
        # may_update has extra business rules
        if float(app.routeid) > 0:
            if app.assignee is None:
                context['may_update'] = "False"
                context['workflow_actions'] = []
            if context['may_update'] == "True":
                if app.assignee != self.request.user.id:
                    context['may_update'] = "False"
                    context['workflow_actions'] = []
            if app.assignee != self.request.user.id:
                context['workflow_actions'] = []

        context['may_update_vessels_list'] = "False"
        context['application_history'] = self.get_application_history(app, [])
        return context


    def get_application_history(self,app,ah):
        ah = self.get_application_history_up(app,ah)
        ah = self.get_application_history_down(app,ah)
        return ah

    def get_application_history_up(self,app,ah):
        if app:
           application = Application.objects.filter(old_application=app)
           if application.count() > 0:
              ah.append({'id': application[0].id, 'title':  application[0].title})
              ah = self.get_application_history_up(application[0],ah)

        return ah

    def get_application_history_down(self,app,ah):
        if app.old_application:
            ah.append({'id': app.old_application.id, 'title':  app.old_application.title})
            ah = self.get_application_history_down(app.old_application,ah)
        return ah




class ApplicationDetailPDF(LoginRequiredMixin,ApplicationDetail):
    """This view is a proof of concept for synchronous, server-side PDF generation.
    Depending on performance and resource constraints, this might need to be
    refactored to use an asynchronous task.
    """
    template_name = 'applications/application_detail_pdf.html'

    def get(self, request, *args, **kwargs):
        response = super(ApplicationDetailPDF, self).get(request)
        options = {
            'page-size': 'A4',
            'encoding': 'UTF-8',
        }
        # Generate the PDF as a string, then use that as the response body.
        output = pdfkit.from_string(
            response.rendered_content, False, options=options)
        # TODO: store the generated PDF as a Record object.
        response = HttpResponse(output, content_type='application/pdf')
        obj = self.get_object()
        response['Content-Disposition'] = 'attachment; filename=application_{}.pdf'.format(
            obj.pk)
        return response

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = Application.objects.get(id=kwargs['pk'])
            if app.state == app.APP_STATE_CHOICES.new:
                app.delete()
                return HttpResponseRedirect(reverse('application_list'))
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ApplicationDetailPDF, self).post(request, *args, **kwargs)

class AccountActions(LoginRequiredMixin,DetailView):
    model = SystemUser 
    template_name = 'applications/account_actions.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(AccountActions, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AccountActions, self).get_context_data(**kwargs)
        obj = self.get_object()
        # TODO: define a GenericRelation field on the Application model.
        context['actions'] = Action.objects.filter(
            content_type=ContentType.objects.get_for_model(obj), object_id=obj.ledger_id.id).order_by('-timestamp')
        return context

class OrganisationActions(LoginRequiredMixin,DetailView):
    model = Organisation
    template_name = 'applications/organisation_actions.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(OrganisationActions, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(OrganisationActions, self).get_context_data(**kwargs)

        obj = self.get_object()
        # TODO: define a GenericRelation field on the Application model.
        context['actions'] = Action.objects.filter(
             content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk).order_by('-timestamp')
        return context

class OrganisationARActions(LoginRequiredMixin,DetailView):
    model = OrganisationPending
    template_name = 'applications/organisation_ar_actions.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(OrganisationARActions, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(OrganisationARActions, self).get_context_data(**kwargs)

        obj = self.get_object()
        # TODO: define a GenericRelation field on the Application model.
        context['actions'] = Action.objects.filter(
             content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk).order_by('-timestamp')
        return context

class ApplicationActions(LoginRequiredMixin,DetailView):
    model = Application
    template_name = 'applications/application_actions.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        app = self.get_object()

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context_processor = flow.getAccessRights(request, context_processor, app.routeid, workflowtype)

        #admin_staff = context_processor['admin_staff']
        may_view_action_log = context_processor['may_view_action_log']
        print ("ACTION  LOG")
        print (may_view_action_log)
        if may_view_action_log== 'True':
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ApplicationActions, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationActions, self).get_context_data(**kwargs)
        app = self.get_object()
        # context['user'] = SystemUser.objects.get(ledger_id = app.app)
        # TODO: define a GenericRelation field on the Application model.
        actions = Action.objects.filter(
            content_type=ContentType.objects.get_for_model(app), object_id=app.pk).order_by('-timestamp')

        new_actions = []
        # Updating the user field with systemuser from ledger api
        for action in actions:
            if action.user:
                new_user = SystemUser.objects.get(ledger_id = action.user)
                action.user = new_user
            new_actions.append(action)
        context['actions'] = new_actions      
                
        return context

class ApplicationComms(LoginRequiredMixin,DetailView):
    model = Application 
    template_name = 'applications/application_comms.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        #admin_staff = context_processor['admin_staff']
        #if admin_staff == True:
        app = self.get_object()

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context_processor = flow.getAccessRights(request, context_processor, app.routeid, workflowtype)
        print ("COMMS LOG")
        print (context_processor['may_view_comm_log'])
        may_view_comm_log = context_processor['may_view_comm_log']
        if may_view_comm_log== 'True':
           pass
        #elif request.user.is_staff == True:
        #   pass 
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ApplicationComms, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationComms, self).get_context_data(**kwargs)
        app = self.get_object()
        # TODO: define a GenericRelation field on the Application model.
        context['communications'] = Communication.objects.filter(application_id=app.pk).order_by('-created')
        return context

class ApplicationCommsView(LoginRequiredMixin,TemplateView):
    model = Application 
    #form_class = apps_forms.CommunicationCreateForm
    template_name = 'applications/application_comms_view.html'

    def get_context_data(self, **kwargs):
        context = super(ApplicationCommsView, self).get_context_data(**kwargs)
        context['page_heading'] = 'View communication'
        context['file_group'] =  '2003'
        context['file_group_ref_id'] = self.kwargs['pk']
        context['communication_entry'] = Communication.objects.get(pk=self.kwargs['comms_id'])
        print (context['communication_entry'])
        return context


class ApplicationCommsCreate(LoginRequiredMixin,CreateView):
    model = Communication
    form_class = apps_forms.CommunicationCreateForm
    template_name = 'applications/application_comms_create.html'
    
    def get_context_data(self, **kwargs):
        context = super(ApplicationCommsCreate, self).get_context_data(**kwargs)
        context['page_heading'] = 'Create new communication'
        context['file_group'] =  '2003'
        context['file_group_ref_id'] =  self.kwargs['pk']
        return context

    def get_initial(self):
        initial = {}
        initial['application'] = self.kwargs['pk']
        #initial['records_json'] = []
        #initial['records'] = []
        return initial

    def get_form_kwargs(self):
        kwargs = super(ApplicationCommsCreate, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
#            return HttpResponseRedirect(reverse('home'))
            app = Application.objects.get(pk=self.kwargs['pk'])
            return HttpResponseRedirect(app.get_absolute_url())
        return super(ApplicationCommsCreate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override form_valid to set the assignee as the object creator.
        """
        self.object = form.save(commit=False)
        app_id = self.kwargs['pk']

        application = Application.objects.get(id=app_id)
        self.object.application = application
        self.object.save()


        if 'records_json' in self.request.POST:
             if is_json(self.request.POST['records_json']) is True:
                  json_data = json.loads(self.request.POST['records_json'])
                  self.object.records.remove()
                  for d in self.object.records.all():
                      self.object.records.remove(d)
                  for i in json_data:
                      doc = Record.objects.get(id=i['doc_id'])
                      self.object.records.add(doc)

#        if self.request.FILES.get('records'):
#            if Attachment_Extension_Check('multi', self.request.FILES.getlist('records'), ['.pdf','.xls','.doc','.jpg','.png','.xlsx','.docx','.msg']) is False:
#                raise ValidationError('Documents attached contains and unallowed attachment extension.')
#
#            for f in self.request.FILES.getlist('records'):
#                doc = Record()
#                doc.upload = f
#                doc.name = f.name
#                doc.save()
#                self.object.records.add(doc)
        self.object.save()
        # If this is not an Emergency Works set the applicant as current user
        success_url = reverse('application_comms', args=(app_id,))
        return HttpResponseRedirect(success_url)

class AccountComms(LoginRequiredMixin,DetailView):
    model = SystemUser
    template_name = 'applications/account_comms.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(AccountComms, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AccountComms, self).get_context_data(**kwargs)
        u = self.get_object()
        # TODO: define a GenericRelation field on the Application model.
        context['communications'] = CommunicationAccount.objects.filter(user=u.ledger_id.id).order_by('-created')
        context['communications'] = CommunicationAccount.objects.filter(user=u.ledger_id.id).order_by('-created')
        return context


class AccountCommsCreate(LoginRequiredMixin,CreateView):
    model = CommunicationAccount
    form_class = apps_forms.CommunicationAccountCreateForm
    template_name = 'applications/application_comms_create.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(AccountCommsCreate, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AccountCommsCreate, self).get_context_data(**kwargs)
        context['page_heading'] = 'Create new account communication' 
        context['file_group'] =  '2004'
        context['file_group_ref_id'] =  self.kwargs['pk']
        return context

    def get_initial(self):
        initial = {}
        initial['application'] = self.kwargs['pk']
        return initial

    def get_form_kwargs(self):
        kwargs = super(AccountCommsCreate, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('home'))
        return super(AccountCommsCreate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override form_valid to set the assignee as the object creator.
        """
        self.object = form.save(commit=False)
        user_id = self.kwargs['pk']

        user = SystemUser.objects.get(id=user_id)
        self.object.user = user.ledger_id.id
        self.object.save()

        if self.request.FILES.get('records'):
            if Attachment_Extension_Check('multi', self.request.FILES.getlist('records'), None) is False:
                raise ValidationError('Documents attached contains and unallowed attachment extension.')

            for f in self.request.FILES.getlist('records'):
                doc = Record()
                doc.upload = f
                doc.name = f.name
                doc.save()
                self.object.records.add(doc)
        self.object.save()
        # If this is not an Emergency Works set the applicant as current user
        success_url = reverse('account_comms', args=(user_id,))
        return HttpResponseRedirect(success_url)

class ComplianceComms(LoginRequiredMixin,DetailView):
    model = Compliance
    template_name = 'applications/compliance_comms.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ComplianceComms, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ComplianceComms, self).get_context_data(**kwargs)
        c = self.get_object()
        # TODO: define a GenericRelation field on the Application model.
        context['communications'] = CommunicationCompliance.objects.filter(compliance=c.pk).order_by('-created')
        return context

class ComplianceCommsCreate(LoginRequiredMixin,CreateView):
    model = CommunicationCompliance 
    form_class = apps_forms.CommunicationComplianceCreateForm
    template_name = 'applications/compliance_comms_create.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']

        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ComplianceCommsCreate, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ComplianceCommsCreate, self).get_context_data(**kwargs)
        context['page_heading'] = 'Create new account communication'
        return context

    def get_initial(self):
        initial = {}
        initial['compliance'] = self.kwargs['pk']
        return initial

    def get_form_kwargs(self):
        kwargs = super(ComplianceCommsCreate, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('home'))
        return super(ComplianceCommsCreate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override form_valid to set the assignee as the object creator.
        """
        self.object = form.save(commit=False)
        c_id = self.kwargs['pk']

        c = Compliance.objects.get(id=c_id)
        self.object.compliance = c
        self.object.save()

        if self.request.FILES.get('records'):
            if Attachment_Extension_Check('multi', self.request.FILES.getlist('records'), None) is False:
                raise ValidationError('Documents attached contains and unallowed attachment extension.')
            for f in self.request.FILES.getlist('records'):
                doc = Record()
                doc.upload = f
                doc.name = f.name
                doc.save()
                self.object.records.add(doc)
        self.object.save()
        # If this is not an Emergency Works set the applicant as current user
        success_url = reverse('compliance_comms', args=(c_id,))
        return HttpResponseRedirect(success_url)

class OrganisationComms(LoginRequiredMixin,DetailView):
    model = Organisation
    template_name = 'applications/organisation_comms.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(OrganisationComms, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(OrganisationComms, self).get_context_data(**kwargs)
        org = self.get_object()
        # TODO: define a GenericRelation field on the Application model.
        context['communications'] = CommunicationOrganisation.objects.filter(org=org.pk).order_by('-created')
        return context

class ReferralList(LoginRequiredMixin,ListView):
    model = Application
    template_name = 'applications/referral_list.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ReferralList, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ReferralList, self).get_context_data(**kwargs)

        context['app_applicants'] = {}
        context['app_applicants_list'] = []
        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            query_str_split = query_str.split()
            search_filter = Q()
            for se_wo in query_str_split:  

                search_filter &= (
                    Q(pk__contains=se_wo) |
                    Q(application__title__icontains=se_wo) |
                    Q(application__description__icontains=se_wo)
                )

            items = Referral.objects.filter(referee=self.request.user.id).filter(search_filter)
        else:
            items = Referral.objects.filter(referee=self.request.user.id)
        
        context['app_list'] = []
        for item in items:
            row = {}
            row['app'] = item

            # Create a distinct list of applicants
            
            if item.application.applicant:
                applicant = SystemUser.objects.get(ledger_id=item.application.applicant)
                row['applicant'] = applicant
                if applicant.ledger_id in context['app_applicants']:
                    donothing = ''
                else:
                    if(applicant.legal_first_name and applicant.legal_last_name):
                        context['app_applicants'][applicant.ledger_id] = applicant.legal_first_name + ' ' + applicant.legal_last_name
                        context['app_applicants_list'].append({"id": applicant.ledger_id.id, "name": applicant.legal_first_name + ' ' + applicant.legal_last_name  })
                
            if item.application.submitted_by:
                submitted_by = SystemUser.objects.get(ledger_id=item.application.submitted_by)
                row['submitted_by'] = submitted_by
            # end of creation

            context['app_list'].append(row)
        return context

class ReferralConditions(UpdateView):
    """A view for updating a referrals condition feedback.
    """
    model = Application
    form_class = apps_forms.ApplicationReferralConditionsPart5
    template_name = 'public/application_form.html'

    def get(self, request, *args, **kwargs):
        # TODO: business logic to check the application may be changed.
        app = self.get_object()
        # refcount = Referral.objects.filter(referee=self.request.user.id).count()
        refcount = Referral.objects.filter(application=app,referee=self.request.user.id).exclude(status=5).count()
        if refcount == 1:
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        return super(ReferralConditions, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ReferralConditions, self).get_context_data(**kwargs)
        app_id = self.kwargs['pk']
        context['page_heading'] = 'Application for new Part 5 - '+app_id
        context['left_sidebar'] = 'yes'
        #context['action'] = self.kwargs['action']
        app = self.get_object()

        referral = Referral.objects.get(application=app,referee=self.request.user.id)
        if app.applicant is not None:
            applicant = SystemUser.objects.get(ledger_id=referral.application.applicant)
            context['applicant'] = applicant
            context['postal_address'] = SystemUserAddress.objects.get(system_user=context['applicant'], address_type='postal_address')
        multifilelist = []
        a1 = referral.records.all()
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['extension']  = b1.extension
            fileitem['file_url'] = b1.file_url()
            fileitem['file_name'] = b1.name
            multifilelist.append(fileitem)
        context['records'] = multifilelist

        if  Location.objects.filter(application_id=self.object.id).exists():
              context['location'] = Location.objects.get(application_id=app.id)
        else:
              context['location'] = {} 



        context['referral']  = Referral.objects.get(application=app,referee=self.request.user.id)
        return context

    def get_initial(self):
        initial = super(ReferralConditions, self).get_initial()
        app = self.get_object()

        # print self.request.user.email

        referral = Referral.objects.get(application=app,referee=self.request.user.id)
        referee = SystemUser.objects.get(ledger_id=self.request.user.id)
        #print referral.feedback

        initial['application_id'] = self.kwargs['pk']
        initial['application_app_type'] = app.app_type
        initial['organisation'] = app.organisation
        initial['referral_email'] = referee.email
        initial['referral_name'] = referee.first_name + ' ' + referee.last_name
        initial['referral_status'] = referral.status
        initial['proposed_conditions'] = referral.proposed_conditions
        initial['comments'] = referral.feedback
        initial['response_date'] = referral.response_date
        initial['state'] = app.state
 
        multifilelist = []
        a1 = referral.records.all()
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)

        initial['records'] = multifilelist

        return initial

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = Application.objects.get(id=kwargs['pk'])
            if app.state == app.APP_STATE_CHOICES.new:
                app.delete()
                return HttpResponseRedirect(reverse('application_list'))
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ReferralConditions, self).post(request, *args, **kwargs)


    def form_valid(self, form):
        """Override form_valid to set the state to draft is this is a new application.
        """
        forms_data = form.cleaned_data
        self.object = form.save(commit=False)
        app_id = self.kwargs['pk']
        #action = self.kwargs['action']
        status=None
       
        application = Application.objects.get(id=app_id)
        referral = Referral.objects.get(application_id=app_id,referee=self.request.user.id)
        referral.feedback = forms_data['comments'] 
        referral.proposed_conditions = forms_data['proposed_conditions']
        referral.response_date = date.today() 
        referral.status = Referral.REFERRAL_STATUS_CHOICES.responded

#        records = referral.records.all()
#        for la_co in records:
#            if 'records-clear_multifileid-' + str(la_co.id) in form.data:
#                referral.records.remove(la_co)



        if 'records_json' in self.request.POST:
             json_data = json.loads(self.request.POST['records_json'])
             print (json_data)
             referral.records.remove()
             for d in referral.records.all():
                 referral.records.remove(d)
             for i in json_data:
                 print ("RECORD REFERRALS")
                 print (i)
                 doc = Record.objects.get(id=i['doc_id'])
                 referral.records.add(doc)

#        if self.request.FILES.get('records'):
#            if Attachment_Extension_Check('multi', self.request.FILES.getlist('records'), None) is False:
#                raise ValidationError('Documents attached contains and unallowed attachment extension.')
#
#            for f in self.request.FILES.getlist('records'):
#                doc = Record()
#                doc.upload = f
#                doc.name = f.name
#                doc.save()
#                referral.records.add(doc)
        referral.save()

        refnextaction = Referrals_Next_Action_Check()
        refactionresp = refnextaction.get(application)
        if refactionresp == True:
            app_updated = refnextaction.go_next_action(application)
            # Record an action.
            action = Action(
                content_object=application,
                action='No outstanding referrals, application status set to "{}"'.format(app_updated.get_state_display()))
            action.save()

        return HttpResponseRedirect('/')

class OrganisationCommsCreate(LoginRequiredMixin,CreateView):
    model = CommunicationOrganisation
    form_class = apps_forms.CommunicationOrganisationCreateForm
    template_name = 'applications/organisation_comms_create.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(OrganisationCommsCreate, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(OrganisationCommsCreate, self).get_context_data(**kwargs)
        context['page_heading'] = 'Create new organisation communication'
        context['org_id'] = self.kwargs['pk']
        return context

    def get_initial(self):
        initial = {}
        initial['org_id'] = self.kwargs['pk']
        return initial

    def get_form_kwargs(self):
        kwargs = super(OrganisationCommsCreate, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('home'))
        return super(OrganisationCommsCreate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override form_valid to set the assignee as the object creator.
        """
        self.object = form.save(commit=False)
        org_id = self.kwargs['pk']

        org = Organisation.objects.get(id=org_id)
        self.object.org_id = org.id
        self.object.save()

        if self.request.FILES.get('records'):
            if Attachment_Extension_Check('multi', self.request.FILES.getlist('records'), None) is False:
                raise ValidationError('Documents attached contains and unallowed attachment extension.')

            for f in self.request.FILES.getlist('records'):
                doc = Record()
                doc.upload = f
                doc.name = f.name
                doc.save()
                self.object.records.add(doc)
        self.object.save()
        # If this is not an Emergency Works set the applicant as current user
        success_url = reverse('organisation_comms', args=(org_id,))
        return HttpResponseRedirect(success_url)


class ApplicationChange(LoginRequiredMixin, CreateView):
    """This view is for changes or ammendents to existing applications
    """
    #@model = Application
    form_class = apps_forms.ApplicationChange
    template_name = 'applications/application_change_form.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        action = self.kwargs['action']
        approval = Approval.objects.get(id=self.kwargs['approvalid'])
        application = Application.objects.get(id=approval.application.id)

        if action == 'requestamendment':
             app = Application.objects.create(applicant=self.request.user.id,
                                              assignee=self.request.user.id,
                                              submitted_by=self.request.user.id,
                                              app_type=5,
                                              submit_date=date.today(),
                                              state=Application.APP_STATE_CHOICES.new,
                                              approval_id=approval.id,
                                              title=approval.title,
                                              old_approval_id = approval.id
                                             )


             return HttpResponseRedirect(reverse('application_update', args=(app.id,)))

        if action == 'amend':
            if approval.app_type == 3:
                if approval.ammendment_application:
                     app = self.copy_application(approval, application)
                     app.app_type=6
                     app.save()

                     action = Action(
                         content_object=app, category=Action.ACTION_CATEGORY_CHOICES.create, user=self.request.user.id,
                         action='Application copied from application : WO-{}, Approval : AP-{}'.format(str(approval.application.id), str(approval.id)))
                     action.save()

                     return HttpResponseRedirect(reverse('application_update', args=(app.id,)))

            elif approval.app_type == 1:
                app = self.copy_application(approval, application)

                action = Action(
                    content_object=app, category=Action.ACTION_CATEGORY_CHOICES.create, user=self.request.user.id,
                    action='Application copied from application : WO-{}, Approval : AP-{}'.format(str(approval.application.id), str(approval.id)))
                action.save()

                return HttpResponseRedirect(reverse('application_update', args=(app.id,)))

            elif approval.app_type == 2:
                app = self.copy_application(approval, application)

                action = Action(
                    content_object=app, category=Action.ACTION_CATEGORY_CHOICES.create, user=self.request.user.id,
                    action='Application copied from application : WO-{}, Approval : AP-{}'.format(str(approval.application.id), str(approval.id)))
                action.save()

                return HttpResponseRedirect(reverse('application_update', args=(app.id,)))



        return super(ApplicationChange, self).get(request, *args, **kwargs)


    def copy_application(self, approval, application):

        app = Application.objects.create(applicant=approval.application.applicant,
                                     title=approval.application.title,
                                     assignee=self.request.user.id,
                                     description=approval.application.description,
                                     proposed_commence=approval.application.proposed_commence,
                                     proposed_end=approval.application.proposed_end,
                                     cost=approval.application.cost,
                                     project_no=approval.application.project_no,
                                     related_permits=approval.application.related_permits,
                                     over_water=approval.application.over_water,
                                     vessel_or_craft_details=approval.application.vessel_or_craft_details,
                                     purpose=approval.application.purpose,
                                     max_participants=approval.application.max_participants,
                                     proposed_location=approval.application.proposed_location,
                                     address=approval.application.address,
                                     jetties=approval.application.jetties,
                                     jetty_dot_approval=approval.application.jetty_dot_approval,
                                     jetty_dot_approval_expiry=approval.application.jetty_dot_approval_expiry,
                                     drop_off_pick_up=approval.application.drop_off_pick_up,
                                     food=approval.application.food,
                                     beverage=approval.application.beverage,
                                     liquor_licence=approval.application.liquor_licence,
                                     byo_alcohol=approval.application.byo_alcohol,
                                     sullage_disposal=approval.application.sullage_disposal,
                                     waste_disposal=approval.application.waste_disposal,
                                     refuel_location_method=approval.application.refuel_location_method,
                                     berth_location=approval.application.berth_location,
                                     anchorage=approval.application.anchorage,
                                     operating_details=approval.application.operating_details,
                                     river_lease_require_river_lease=approval.application.river_lease_require_river_lease,
                                     river_lease_reserve_licence=approval.application.river_lease_reserve_licence,
                                     river_lease_application_number=approval.application.river_lease_application_number,
                                     proposed_development_current_use_of_land=approval.application.proposed_development_current_use_of_land,
                                     proposed_development_description=approval.application.proposed_development_description,
                                     type_of_crafts=approval.application.type_of_crafts,
                                     number_of_crafts=approval.application.number_of_crafts,
                                     landowner=approval.application.landowner,
                                     land_description=approval.application.land_description,
                                     submitted_by=self.request.user.id,
                                     app_type=approval.application.app_type,
                                     submit_date=date.today(),
                                     state=Application.APP_STATE_CHOICES.new,
                                     approval_id=approval.id,
                                     old_application=approval.application,
                                     old_approval_id=approval.id
                                    )

        a1 = approval.application.records.all()
        for b1 in a1:
            app.records.add(b1)

        a1 = approval.application.vessels.all()
        for b1 in a1:
            app.vessels.add(b1)

        a1 = approval.application.location_route_access.all()
        for b1 in a1:
            app.location_route_access.add(b1)

        a1 = approval.application.cert_public_liability_insurance.all()
        for b1 in a1:
            app.cert_public_liability_insurance.add(b1)

        a1 = approval.application.risk_mgmt_plan.all()
        for b1 in a1:
            app.risk_mgmt_plan.add(b1)

        a1 = approval.application.safety_mgmt_procedures.all()
        for b1 in a1:
            app.safety_mgmt_procedures.add(b1)

        a1 = approval.application.brochures_itineries_adverts.all()
        for b1 in a1:
            app.brochures_itineries_adverts.add(b1)

        a1 = approval.application.other_relevant_documents.all()
        for b1 in a1:
            app.other_relevant_documents.add(b1)

        a1 = approval.application.land_owner_consent.all()
        for b1 in a1:
            app.land_owner_consent.add(b1)

        a1 = approval.application.deed.all()
        for b1 in a1:
            app.deed.add(b1)


        a1 = approval.application.river_lease_scan_of_application.all()
        for b1 in a1:
            app.river_lease_scan_of_application.add(b1)

        a1 = approval.application.proposed_development_plans.all()
        for b1 in a1:
            app.proposed_development_plans.add(b1)

        app.save()
        locobj = Location.objects.get(application_id=application.id)
        new_loc = Location()
        new_loc.application_id = app.id
        new_loc.title_volume = locobj.title_volume
        new_loc.folio = locobj.folio
        new_loc.dpd_number = locobj.dpd_number
        new_loc.location = locobj.location
        new_loc.reserve = locobj.reserve
        new_loc.street_number_name = locobj.street_number_name
        new_loc.suburb = locobj.suburb
        new_loc.lot = locobj.lot
        new_loc.intersection = locobj.intersection
        new_loc.local_government_authority = locobj.local_government_authority
        new_loc.save()

        conditions = Condition.objects.filter(application_id=application.id)
        for c in conditions:
            copied_condition=Condition.objects.create(application=app,
                                     condition_no=c.condition_no,
                                     condition=c.condition,
                                     referral=c.referral,
                                     status=c.status,
                                     due_date=c.due_date,
                                     recur_pattern=c.recur_pattern,
                                     recur_freq=c.recur_freq,
                                     suspend=c.suspend,
                                     advise_no=c.advise_no,
                                     advise=c.advise,
                                     )
            a1 = c.records.all()
            for b1 in a1:
                copied_condition.records.add(b1)
            copied_condition.save()

        referrals=Referral.objects.filter(application=application)
        for r in referrals:
            copied_referral=Referral.objects.create(application=app,
                                                    referee=r.referee,
                                                    details=r.details,
                                                    period=r.period
                                                   )
                                                    

                                     
        return app 

    def get_context_data(self, **kwargs):
        context = super(ApplicationChange, self).get_context_data(**kwargs)
        context['page_heading'] = 'Update application details'
        return context

    def get_form_kwargs(self):
         kwargs = super(ApplicationChange, self).get_form_kwargs()
         return kwargs

    def get_initial(self):
        initial = {}
        action = self.kwargs['action'] 
        approval = Approval.objects.get(id=self.kwargs['approvalid']) 
        application = Application.objects.get(id=approval.application.id)

        initial['title']  = application.title
        initial['description'] = application.description
#       initial['cost'] = application.cost

        if action == "amend":
            if approval.app_type == 3:
               if approval.ammendment_application: 
                   initial['app_type'] = 6
               else:
                   raise ValidationError('There was an error raising your Application Change.')
            elif approval.app_type == 1:
                   initial['app_type'] = 1
            elif approval.app_type == 2:
                   initial['app_type'] = 2
        elif action == 'requestamendment': 
            initial['app_type'] = 5
        elif action == 'renewlicence':
            initial['app_type'] = 5
        elif action == 'renewlicence':
            initial['app_type'] = 11
        elif action == 'renewpermit':
            initial['app_type'] = 10
        else:
            raise ValidationError('There was an error raising your Application Change.')
        return initial

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ApplicationChange, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override form_valid to set the state to draft is this is a new application.
        """
        self.object = form.save(commit=False)
        action = self.kwargs['action']
        forms_data = form.cleaned_data

        approval = Approval.objects.get(id=self.kwargs['approvalid'])
        application = Application.objects.get(id=approval.application.id)

        if action == "amend":
            if approval.ammendment_application:
                self.object.app_type = 6
            else:
                raise ValidationError('There was an error raising your Application Change.')
        elif action == 'requestamendment':
                self.object.app_type = 5
        elif action == 'renewlicence':
                self.object.app_type = 11
        elif action == 'renewpermit':
                self.object.app_type = 10
        else: 
            raise ValidationError('There was an error raising your Application Change.')

        self.object.proposed_development_description = forms_data['proposed_development_description'] 
        self.object.applicant = self.request.user.id
        self.object.assignee = self.request.user.id
        self.object.submitted_by = self.request.user.id
        self.object.assignee = self.request.user.id
        self.object.submit_date = date.today()
        self.object.state = self.object.APP_STATE_CHOICES.new
        self.object.approval_id = approval.id
        self.object.save()

        if self.request.FILES.get('proposed_development_plans'):
            if Attachment_Extension_Check('multi', self.request.FILES.getlist('proposed_development_plans'), None) is False:
                raise ValidationError('Proposed Development Plans contains and unallowed attachment extension.')
        
            for f in self.request.FILES.getlist('proposed_development_plans'):
                doc = Record()
                doc.upload = f
                doc.name = f.name
                doc.save()
                self.object.proposed_development_plans.add(doc)

#        self.object = form.save(commit=False)
        return HttpResponseRedirect(self.get_success_url())


class ApplicationConditionTable(LoginRequiredMixin, DetailView):
    """A view for updating a draft (non-lodged) application.
    """
    model = Application
    template_name = 'applications/application_conditions_table.html'

    def get(self, request, *args, **kwargs):
        # TODO: business logic to check the application may be changed.
        app = self.get_object()

        context = {}

        if app.routeid is None:
            app.routeid = 1

        if app.assignee:
           context['application_assignee_id'] = app.assignee
        else:
           context['application_assignee_id'] = None

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        #if self.request.user.groups().filter(name='Processor').exists():
        #    donothing = ''
#        if context["may_update_publication_newspaper"] != "True":
#            messages.error(self.request, 'This application cannot be updated!')
#            return HttpResponseRedirect(app.get_absolute_url())

        return super(ApplicationConditionTable, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationConditionTable, self).get_context_data(**kwargs)
        app = self.get_object()
        if app.routeid is None:
            app.routeid = 1
        request = self.request

        if app.assignee:
           context['application_assignee_id'] = app.assignee
        else:
           context['application_assignee_id'] = None

        flow = Flow()
        context['mode'] = 'update'

        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context['workflowoptions'] = flow.getWorkflowOptions()
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        if context['application_assignee_id']:
            context['workflow_actions'] = flow.getAllRouteActions(app.routeid,workflowtype)
        #part5 = Application_Part5()
        #context = part5.get(app, self, context)
        return context

    def get_success_url(self,app):
        return HttpResponseRedirect(app.get_absolute_url())

class ApplicationReferTable(LoginRequiredMixin, DetailView):
    """A view for updating a draft (non-lodged) application.
    """
    model = Application
    template_name = 'applications/application_referrals_table.html'

    def get(self, request, *args, **kwargs):
        # TODO: business logic to check the application may be changed.
        app = self.get_object()

        context = {}

        if app.routeid is None:
            app.routeid = 1

        if app.assignee:
           context['application_assignee_id'] = app.assignee
        else:
           context['application_assignee_id'] = None

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        #if self.request.user.groups().filter(name='Processor').exists():
        #    donothing = ''
#        if context["may_update_publication_newspaper"] != "True":
#            messages.error(self.request, 'This application cannot be updated!')
#            return HttpResponseRedirect(app.get_absolute_url())

        return super(ApplicationReferTable, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationReferTable, self).get_context_data(**kwargs)
        app = self.get_object()
        if app.routeid is None:
            app.routeid = 1
        request = self.request

        if app.assignee:
           context['application_assignee_id'] = app.assignee
        else:
           context['application_assignee_id'] = None

        context['mode'] = 'update'

        flow = Flow()

        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context['workflowoptions'] = flow.getWorkflowOptions()
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        if context['application_assignee_id']:
              context['workflow_actions'] = flow.getAllRouteActions(app.routeid,workflowtype)

        #part5 = Application_Part5()
        #context = part5.get(app, self, context)
        return context

    def get_success_url(self,app):
        return HttpResponseRedirect(app.get_absolute_url())


class ApplicationVesselTable(LoginRequiredMixin, DetailView):
    """A view for updating a draft (non-lodged) application.
    """
    model = Application
    template_name = 'applications/application_vessels_table.html'

    def get(self, request, *args, **kwargs):
        # TODO: business logic to check the application may be changed.
        app = self.get_object()

        context = {}


        user_id = None
        if request.user:
           user_id = request.user.id

        # start
        if request.user.is_staff == True:
             pass
        elif request.user.is_superuser == True:
             pass
        elif app.submitted_by == user_id:
             pass
        elif app.applicant:
             if app.applicant == user_id:
                 pass
             else:
                 messages.error(self.request, 'Forbidden from viewing this page.')
                 return HttpResponseRedirect("/")
        elif Delegate.objects.filter(email_user=request.user.id).count() > 0:
             pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect('/')



        if app.routeid is None:
            app.routeid = 1

        if app.assignee:
           context['application_assignee_id'] = app.assignee
        else:
            if float(app.routeid) == 1 and app.assignee is None:
                context['application_assignee_id'] = self.request.user.id
            else:
                context['application_assignee_id'] = None

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        #if self.request.user.groups().filter(name='Processor').exists():
        #    donothing = ''
        #if context['may_update_vessels_list'] != "True":
        #    messages.error(self.request, 'Forbidden from updating vessels')
        #    return HttpResponseRedirect(reverse('popup_error'))

        return super(ApplicationVesselTable, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationVesselTable, self).get_context_data(**kwargs)
        #context['page_heading'] = 'Update application details'
        #context['left_sidebar'] = 'yes'
        app = self.get_object()

        # if app.app_type == app.APP_TYPE_CHOICES.part5:
        if app.routeid is None:
            app.routeid = 1
        request = self.request

        if app.assignee:
           context['application_assignee_id'] = app.assignee
        else:
            if float(app.routeid) == 1 and app.assignee is None:
                context['application_assignee_id'] = self.request.user.id
            else:
                context['application_assignee_id'] = None

        flow = Flow()

        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context['workflowoptions'] = flow.getWorkflowOptions()
       
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        #context = flow.getCollapse(context,app.routeid,workflowtype)
        #context['workflow_actions'] = flow.getAllRouteActions(app.routeid,workflowtype)
        #context['condactions'] = flow.getAllConditionBasedRouteActions(app.routeid)
        #context['workflow'] = flow.getAllRouteConf(workflowtype,app.routeid)

        return context

    def get_success_url(self,app):
        return HttpResponseRedirect(app.get_absolute_url())


class NewsPaperPublicationTable(LoginRequiredMixin, DetailView):
    """A view for updating a draft (non-lodged) application.
    """
    model = Application
    template_name = 'applications/application_publication_newspaper_table.html'

    def get(self, request, *args, **kwargs):
        # TODO: business logic to check the application may be changed.
        app = self.get_object()

        context = {}

        if app.routeid is None:
            app.routeid = 1

        if app.assignee:
           context['application_assignee_id'] = app.assignee
        else:
           context['application_assignee_id'] = None

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        #if self.request.user.groups().filter(name='Processor').exists():
        #    donothing = ''
        #if context["may_update_publication_newspaper"] != "True":
        #    messages.error(self.request, 'This application cannot be updated!')
        #    return HttpResponseRedirect(app.get_absolute_url())

        return super(NewsPaperPublicationTable, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(NewsPaperPublicationTable, self).get_context_data(**kwargs)
        app = self.get_object()
        if app.routeid is None:
            app.routeid = 1
        request = self.request

        if app.assignee:
           context['application_assignee_id'] = app.assignee
        else:
           context['application_assignee_id'] = None

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context['workflowoptions'] = flow.getWorkflowOptions()
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        part5 = Application_Part5()
        context = part5.get(app, self, context)
        return context

    def get_success_url(self,app):
        return HttpResponseRedirect(app.get_absolute_url())

class FeedbackTable(LoginRequiredMixin, DetailView):
    """A view for updating a draft (non-lodged) application.
    """
    model = Application
    template_name = 'applications/application_feedback_draft_table.html'

    def get(self, request, *args, **kwargs):
        # TODO: business logic to check the application may be changed.
        app = self.get_object()

        context = {}
       
        if app.routeid is None:
            app.routeid = 1

        if app.assignee:
           context['application_assignee_id'] = app.assignee
        else:
           context['application_assignee_id'] = None

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        #if self.request.user.groups().filter(name='Processor').exists():
        #    donothing = ''
#        if context["may_update_publication_newspaper"] != "True":
#            messages.error(self.request, 'This application cannot be updated!')
#            return HttpResponseRedirect(app.get_absolute_url())

        return super(FeedbackTable, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(FeedbackTable, self).get_context_data(**kwargs)
        app = self.get_object()
        if app.routeid is None:
            app.routeid = 1
        request = self.request

        if app.assignee:
           context['application_assignee_id'] = app.assignee
        else:
           context['application_assignee_id'] = None

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context['workflowoptions'] = flow.getWorkflowOptions()
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        context['action'] = self.kwargs['action']

        if context['action'] == 'review':
             self.template_name = 'applications/application_feedback_draft_review.html'
        elif context['action'] == 'draft':
             self.template_name = 'applications/application_feedback_draft_table.html'
        elif context['action'] == 'final':
             self.template_name = 'applications/application_feedback_final_table.html'
        elif context['action'] == 'determination':
             self.template_name = 'applications/application_feedback_determination_table.html'
         

        part5 = Application_Part5()
        context = part5.get(app, self, context)
        return context

    def get_success_url(self,app):
        return HttpResponseRedirect(app.get_absolute_url())

class ApplicationUpdate(LoginRequiredMixin, UpdateView):
    """A view for updating a draft (non-lodged) application.
    """
    model = Application

    def get(self, request, *args, **kwargs):
        # TODO: business logic to check the application may be changed.
        app = self.get_object()

        if app.state == 18:
             return HttpResponseRedirect(reverse('application_booking', args=(app.id,)))

        if request.user.is_staff == True or request.user.is_superuser == True or app.submitted_by == request.user.id or app.applicant == request.user.id or Delegate.objects.filter(email_user=request.user.id).count() > 0:
              donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        if app.status == 1 or app.status == 3:
            pass
        else:
            messages.error(self.request, 'Application is not active')
            return HttpResponseRedirect("/")

        if app.assignee is None and float(app.routeid) > 1:
             messages.error(self.request, 'Must be assigned to you before any changes can be made.')
             return HttpResponseRedirect("/")

        # Rule: if the application status is 'draft', it can be updated.
        context = {}
        if app.assignee:
            context['application_assignee_id'] = app.assignee
        else:
            if float(app.routeid) == 1 and app.assignee is None:
                context['application_assignee_id'] = request.user.id
            else:
                context['application_assignee_id'] = None
#        if app.app_type == app.APP_TYPE_CHOICES.part5:
        if app.routeid is None:
            app.routeid = 1

       
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        
        if float(app.routeid) > 0:
            if app.assignee is None:
                context['may_update'] = "False"


            if context['may_update'] == "True":
                if app.assignee != self.request.user.id:
                    context['may_update'] = "False"
         

        #if context['may_update'] != "True":
        #    messages.error(self.request, 'This application cannot be updated!')
        #    return HttpResponseRedirect(app.get_absolute_url())
 #       else:
 #           if app.state != app.APP_STATE_CHOICES.draft and app.state != app.APP_STATE_CHOICES.new:
 #               messages.error(self.request, 'This application cannot be updated!')
 #               return HttpResponseRedirect(app.get_absolute_url())
        return super(ApplicationUpdate, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationUpdate, self).get_context_data(**kwargs)
        context['page_heading'] = 'Update application details'
        context['left_sidebar'] = 'yes'
        context['mode']  = 'update' 
        app = self.get_object()

        if app.assignee:
            context['application_assignee_id'] = app.assignee
        else:
            if float(app.routeid) == 1 and app.assignee is None:
                context['application_assignee_id'] = self.request.user.id
            else:
                context['application_assignee_id'] = None


        # if app.app_type == app.APP_TYPE_CHOICES.part5:
        if app.routeid is None:
            app.routeid = 1
        request = self.request
        flow = Flow()
        
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context['workflowoptions'] = flow.getWorkflowOptions()
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        context = flow.getCollapse(context,app.routeid,workflowtype)
        context['workflow_actions'] = flow.getAllRouteActions(app.routeid,workflowtype)
        context['condactions'] = flow.getAllConditionBasedRouteActions(app.routeid)
        context['workflow'] = flow.getAllRouteConf(workflowtype,app.routeid)
        context['stakeholder_communication'] = StakeholderComms.objects.filter(application=app)


        if app.assignee is None:
           context['workflow_actions'] = []
           
        if app.applicant is not None:
            context['applicant'] = SystemUser.objects.get(ledger_id=app.applicant)
            context['postal_address'] = SystemUserAddress.objects.get(system_user=context['applicant'], address_type='postal_address')
       
        if app.assignee is not None:
            context['assignee'] = SystemUser.objects.get(ledger_id=app.assignee)

        if app.assigned_officer is not None:
            context['assigned_officer'] = SystemUser.objects.get(ledger_id=app.assigned_officer)
        
        if app.submitted_by is not None:
            context['submitted_by'] = SystemUser.objects.get(ledger_id=app.submitted_by)  
        
            
        if app.app_type == app.APP_TYPE_CHOICES.part5:
            part5 = Application_Part5()
            context = part5.get(app, self, context)
        elif app.app_type == app.APP_TYPE_CHOICES.part5cr:
            part5 = Application_Part5()
            context = part5.get(app, self, context)
            #flow = Flow()
            #workflowtype = flow.getWorkFlowTypeFromApp(app)
            #flow.get(workflowtype)
            #context = flow.getAccessRights(self.request,context,app.routeid,workflowtype)
            #context = flow.getCollapse(context,app.routeid,workflowtype)
            #context = flow.getHiddenAreas(context,app.routeid,workflowtype)
            #context['workflow_actions'] = flow.getAllRouteActions(app.routeid,workflowtype)
            #context['formcomponent'] = flow.getFormComponent(app.routeid,workflowtype)
        elif app.app_type == app.APP_TYPE_CHOICES.part5amend:
            part5 = Application_Part5()
            context = part5.get(app, self, context)
        elif app.app_type == app.APP_TYPE_CHOICES.emergency:
            emergency = Application_Emergency()
            context = emergency.get(app, self, context)

        elif app.app_type == app.APP_TYPE_CHOICES.permit:
            permit = Application_Permit()
            context = permit.get(app, self, context)

        elif app.app_type == app.APP_TYPE_CHOICES.licence:
            licence = Application_Licence()
            context = licence.get(app, self, context)

        try:
            LocObj = Location.objects.get(application_id=app.id)
            if LocObj:
                context['certificate_of_title_volume'] = LocObj.title_volume
                context['folio'] = LocObj.folio
                context['diagram_plan_deposit_number'] = LocObj.dpd_number
                context['location'] = LocObj.location
                context['reserve_number'] = LocObj.reserve
                context['street_number_and_name'] = LocObj.street_number_name
                context['town_suburb'] = LocObj.suburb
                context['lot'] = LocObj.lot
                context['nearest_road_intersection'] = LocObj.intersection
                context['local_government_authority'] = LocObj.local_government_authority
        except ObjectDoesNotExist:
            donothing = ''
        context['application_approval'] = " fdadsfdsa"
        if Approval.objects.filter(application=app).count() > 0:
              context['application_approval'] = Approval.objects.filter(application=app)[0]
        return context

    def get_success_url(self,app):
        return HttpResponseRedirect(app.get_absolute_url())

    def get_form_class(self):
        if self.object.app_type == self.object.APP_TYPE_CHOICES.licence:
            return apps_forms.ApplicationLicencePermitForm
        elif self.object.app_type == self.object.APP_TYPE_CHOICES.permit:
            return apps_forms.ApplicationPermitForm
        elif self.object.app_type == self.object.APP_TYPE_CHOICES.part5:
            return apps_forms.ApplicationPart5Form
        elif self.object.app_type == self.object.APP_TYPE_CHOICES.emergency:
            return apps_forms.ApplicationEmergencyForm
        elif self.object.app_type == self.object.APP_TYPE_CHOICES.permitamend:
            return apps_forms.ApplicationPermitForm
        elif self.object.app_type == self.object.APP_TYPE_CHOICES.licenceamend:
            return apps_forms.ApplicationLicencePermitForm
        else:
            # Add default forms.py and use json workflow to filter and hide fields
            return apps_forms.ApplicationPart5Form

    def get_initial(self):
        initial = super(ApplicationUpdate, self).get_initial()
        initial['application_id'] = self.kwargs['pk']


        app = self.get_object()
        initial['organisation'] = app.organisation
#        if app.app_type == app.APP_TYPE_CHOICES.part5:
        if app.routeid is None:
            app.routeid = 1

        request = self.request
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        flowcontent = {}
        if app.assignee:
            flowcontent['application_assignee_id'] = app.assignee
        else:
            flowcontent['application_assignee_id'] = None

        flowcontent = flow.getFields(flowcontent, app.routeid, workflowtype)
        flowcontent = flow.getAccessRights(request, flowcontent, app.routeid, workflowtype)
        flowcontent = flow.getHiddenAreas(flowcontent,app.routeid,workflowtype,request)
        flowcontent['condactions'] = flow.getAllConditionBasedRouteActions(app.routeid)
        initial['disabledfields'] = flow.getDisabled(flowcontent,app.routeid,workflowtype) 
        flowcontent['formcomponent'] = flow.getFormComponent(app.routeid, workflowtype)
        initial['fieldstatus'] = []

        if "fields" in flowcontent:
            initial['fieldstatus'] = flowcontent['fields']
        initial['fieldrequired'] = []
        flowcontent = flow.getRequired(flowcontent, app.routeid, workflowtype)

        if "formcomponent" in flowcontent:
            if "update" in flowcontent['formcomponent']:
                if "required" in flowcontent['formcomponent']['update']:
                    initial['fieldrequired'] = flowcontent['formcomponent']['update']['required']

        initial["workflow"] = flowcontent
        if float(app.routeid) > 1:
            if app.assignee is None:
                initial["workflow"]['may_update'] = "False"

            if initial["workflow"]['may_update'] == "True":
                if app.assignee != self.request.user.id:
                    initial["workflow"]['may_update'] = "False"



        initial["may_change_application_applicant"] = flowcontent["may_change_application_applicant"]
        if app.route_status == 'Draft':
            initial['submitter_comment'] = app.submitter_comment
        initial['state'] = app.state

        multifilelist = []
        a1 = app.land_owner_consent.all()
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['land_owner_consent'] = multifilelist

        a1 = app.proposed_development_plans.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['proposed_development_plans'] = multifilelist

        a1 = app.other_relevant_documents.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['other_relevant_documents'] = multifilelist

        a1 = app.brochures_itineries_adverts.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['brochures_itineries_adverts'] = multifilelist
        #initial['address'] = "THISIIII TETS"
        #if 'brochures_itineries_adverts_json' in self.request.POST:
        #       initial['brochures_itineries_adverts'] = self.request.POST['brochures_itineries_adverts_json']

        a1 = app.location_route_access.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['location_route_access'] = multifilelist

        a1 = app.document_new_draft.all()
        multifilelist = []
        for b1 in a1:  
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['document_new_draft'] = multifilelist


        a1 = app.document_memo.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['document_memo'] = multifilelist

        a1 = app.document_memo_2.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['document_memo_2'] = multifilelist

        a1 = app.document_new_draft_v3.all()
        multifilelist = []
        for b1 in a1:  
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['document_new_draft_v3'] = multifilelist

        a1 = app.document_draft_signed.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['document_draft_signed'] = multifilelist

        a1 = app.document_draft.all()
        multifilelist = []
        for b1 in a1:  
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['document_draft'] = multifilelist

        a1 = app.document_final_signed.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['document_final_signed'] = multifilelist

        a1 = app.document_briefing_note.all()
        multifilelist = []
        for b1 in a1:  
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['document_briefing_note'] = multifilelist

        a1 = app.document_determination_approved.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['document_determination_approved'] = multifilelist

        a1 = app.proposed_development_plans.all()
        multifilelist = []
        for b1 in a1:  
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['proposed_development_plans'] = multifilelist

        a1 = app.deed.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['deed'] = multifilelist

        a1 = app.swan_river_trust_board_feedback.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['swan_river_trust_board_feedback'] = multifilelist

        a1 = app.document_final.all()
        multifilelist = []
        for b1 in a1:  
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['document_final'] = multifilelist

        a1 = app.document_determination.all()
        multifilelist = []
        for b1 in a1:  
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['document_determination'] = multifilelist


        a1 = app.document_completion.all()
        multifilelist = []
        for b1 in a1:   
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['document_completion'] = multifilelist

        a1 = app.cert_survey.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['cert_survey'] = multifilelist

        a1 = app.cert_public_liability_insurance.all()
        multifilelist = []
        for b1 in a1:  
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['cert_public_liability_insurance'] = multifilelist

        a1 = app.risk_mgmt_plan.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['risk_mgmt_plan'] = multifilelist

        a1 = app.safety_mgmt_procedures.all()
        multifilelist = []
        for b1 in a1:  
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['safety_mgmt_procedures'] = multifilelist

        a1 = app.river_lease_scan_of_application.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['river_lease_scan_of_application'] = multifilelist

        a1 = app.supporting_info_demonstrate_compliance_trust_policies.all()
        multifilelist = []
        for b1 in a1:  
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['supporting_info_demonstrate_compliance_trust_policies'] = multifilelist

        if app.approval_document_signed:
            initial['approval_document_signed'] = app.approval_document_signed

        if app.approval_document:
            initial['approval_document'] = app.approval_document

#        if Approval.objects.filter(application=app).count() > 1:
#              initial['application_approval'] = Approval.objects.filter(application=app)

        #initial['publication_newspaper'] = PublicationNewspaper.objects.get(application_id=self.object.id)

        ####### Record FK fields:

        try:
            LocObj = Location.objects.get(application_id=self.object.id)
            if LocObj:
                initial['certificate_of_title_volume'] = LocObj.title_volume
                initial['folio'] = LocObj.folio
                initial['diagram_plan_deposit_number'] = LocObj.dpd_number
                initial['location'] = LocObj.location
                initial['reserve_number'] = LocObj.reserve
                initial['street_number_and_name'] = LocObj.street_number_name
                initial['town_suburb'] = LocObj.suburb
                initial['lot'] = LocObj.lot
                initial['nearest_road_intersection'] = LocObj.intersection
                initial['local_government_authority'] = LocObj.local_government_authority
        except ObjectDoesNotExist:
            donothing = ''
        return initial

    def post(self, request, *args, **kwargs):
        app = self.get_object()
        context = {}
        if app.assignee:
            context['application_assignee_id'] = app.assignee
        else:
            context['application_assignee_id'] = None
#        if app.app_type == app.APP_TYPE_CHOICES.part5:
#        if app.routeid is None:
#            app.routeid = 1

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context = flow.getAccessRights(request, context, app.routeid, workflowtype)
        
        if float(app.routeid) > 1:
            if app.assignee is None:
                context['may_update'] = "False"

            if context['may_update'] == "True":
                if app.assignee != self.request.user.id:
                    context['may_update'] = "False"

        if context['may_update'] != 'True': 
           messages.error(self.request, 'You do not have permissions to update this form.')
           return HttpResponseRedirect(self.get_object().get_absolute_url())

        if request.POST.get('cancel'):
            app = Application.objects.get(id=kwargs['pk'])
            if app.state == app.APP_STATE_CHOICES.new:
                app.delete()
                return HttpResponseRedirect(reverse('application_list'))
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ApplicationUpdate, self).post(request, *args, **kwargs)


    def form_valid(self, form):
        """Override form_valid to set the state to draft is this is a new application.
        """
        forms_data = form.cleaned_data
        self.object = form.save(commit=False)
        # ToDO remove dupes of this line below. doesn't need to be called
        # multiple times
        application = Application.objects.get(id=self.object.id)
        
        try:
            new_loc = Location.objects.get(application_id=self.object.id)
        except:
            new_loc = Location()
            new_loc.application_id = self.object.id

        if 'other_relevant_documents_json' in self.request.POST:
             json_data = json.loads(self.request.POST['other_relevant_documents_json'])
             for d in self.object.other_relevant_documents.all():
                 self.object.other_relevant_documents.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.other_relevant_documents.add(doc)

        if 'brochures_itineries_adverts_json' in self.request.POST:
             if is_json(self.request.POST['brochures_itineries_adverts_json']) is True:
                 json_data = json.loads(self.request.POST['brochures_itineries_adverts_json'])
                 for d in self.object.brochures_itineries_adverts.all():
                    self.object.brochures_itineries_adverts.remove(d)
                 for i in json_data:
                    doc = Record.objects.get(id=i['doc_id'])
                    self.object.brochures_itineries_adverts.add(doc)

        if 'land_owner_consent_json' in self.request.POST:
             if is_json(self.request.POST['land_owner_consent_json']) is True:
                 json_data = json.loads(self.request.POST['land_owner_consent_json'])
                 for d in self.object.land_owner_consent.all():
                     self.object.land_owner_consent.remove(d)
                 for i in json_data:
                     doc = Record.objects.get(id=i['doc_id'])
                     self.object.land_owner_consent.add(doc)

        if 'proposed_development_plans_json' in self.request.POST:
             json_data = json.loads(self.request.POST['proposed_development_plans_json'])
             self.object.proposed_development_plans.remove()
             for d in self.object.proposed_development_plans.all():
                 self.object.proposed_development_plans.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.proposed_development_plans.add(doc)

        if 'supporting_info_demonstrate_compliance_trust_policies_json' in self.request.POST:
             json_data = json.loads(self.request.POST['supporting_info_demonstrate_compliance_trust_policies_json'])
             self.object.supporting_info_demonstrate_compliance_trust_policies.remove()
             for d in self.object.supporting_info_demonstrate_compliance_trust_policies.all():
                 self.object.supporting_info_demonstrate_compliance_trust_policies.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.supporting_info_demonstrate_compliance_trust_policies.add(doc)


        if 'location_route_access_json' in self.request.POST:
             json_data = json.loads(self.request.POST['location_route_access_json'])
             self.object.location_route_access.remove()
             for d in self.object.location_route_access.all():
                 self.object.location_route_access.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.location_route_access.add(doc)



        if 'document_final_json' in self.request.POST:
             json_data = json.loads(self.request.POST['document_final_json'])
             self.object.document_final.remove()
             for d in self.object.document_final.all():
                 self.object.document_final.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.document_final.add(doc)



        if 'safety_mgmt_procedures_json' in self.request.POST:
             json_data = json.loads(self.request.POST['safety_mgmt_procedures_json'])
             self.object.safety_mgmt_procedures.remove()
             for d in self.object.safety_mgmt_procedures.all():
                 self.object.safety_mgmt_procedures.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.safety_mgmt_procedures.add(doc)



        if 'risk_mgmt_plan_json' in self.request.POST:
             json_data = json.loads(self.request.POST['risk_mgmt_plan_json'])
             self.object.risk_mgmt_plan.remove()
             for d in self.object.risk_mgmt_plan.all():
                 self.object.risk_mgmt_plan.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.risk_mgmt_plan.add(doc)

        if 'cert_public_liability_insurance_json' in self.request.POST:
             json_data = json.loads(self.request.POST['cert_public_liability_insurance_json'])
             self.object.cert_public_liability_insurance.remove()
             for d in self.object.cert_public_liability_insurance.all():
                 self.object.cert_public_liability_insurance.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.cert_public_liability_insurance.add(doc)

        if 'cert_survey_json' in self.request.POST:
             json_data = json.loads(self.request.POST['cert_survey_json'])
             self.object.cert_survey.remove()
             for d in self.object.cert_survey.all():
                 self.object.cert_survey.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.cert_survey.add(doc)

        if 'document_determination_approved_json' in self.request.POST:
             json_data = json.loads(self.request.POST['document_determination_approved_json'])
             self.object.document_determination_approved.remove()
             for d in self.object.document_determination_approved.all():
                 self.object.document_determination_approved.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.document_determination_approved.add(doc)

        if 'document_determination_json' in self.request.POST:
             json_data = json.loads(self.request.POST['document_determination_json'])
             self.object.document_determination.remove()
             for d in self.object.document_determination.all():
                 self.object.document_determination.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.document_determination.add(doc)

        if 'document_briefing_note_json' in self.request.POST:
             json_data = json.loads(self.request.POST['document_briefing_note_json'])
             self.object.document_briefing_note.remove()
             for d in self.object.document_briefing_note.all():
                 self.object.document_briefing_note.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.document_briefing_note.add(doc)


        if 'document_new_draft_v3_json' in self.request.POST:
             json_data = json.loads(self.request.POST['document_new_draft_v3_json'])
             self.object.document_new_draft_v3.remove()
             for d in self.object.document_new_draft_v3.all():
                 self.object.document_new_draft_v3.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.document_new_draft_v3.add(doc)

        if 'document_memo_json' in self.request.POST:
             json_data = json.loads(self.request.POST['document_memo_json'])
             self.object.document_memo.remove()
             for d in self.object.document_memo.all():
                 self.object.document_memo.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.document_memo.add(doc)

        if 'document_memo_2_json' in self.request.POST:
             json_data = json.loads(self.request.POST['document_memo_2_json'])
             self.object.document_memo_2.remove()
             for d in self.object.document_memo_2.all():
                 self.object.document_memo_2.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.document_memo_2.add(doc)

        if 'deed_json' in self.request.POST:
             if is_json(self.request.POST['deed_json']) is True:
                json_data = json.loads(self.request.POST['deed_json'])
                self.object.deed.remove()
                for d in self.object.deed.all():
                    self.object.deed.remove(d)
                for i in json_data:
                    doc = Record.objects.get(id=i['doc_id'])
                    self.object.deed.add(doc)

        if 'swan_river_trust_board_feedback_json' in self.request.POST:
             json_data = json.loads(self.request.POST['swan_river_trust_board_feedback_json'])
             self.object.swan_river_trust_board_feedback.remove()
             for d in self.object.swan_river_trust_board_feedback.all():
                 self.object.swan_river_trust_board_feedback.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.swan_river_trust_board_feedback.add(doc)

        if 'river_lease_scan_of_application_json' in self.request.POST:
             json_data = json.loads(self.request.POST['river_lease_scan_of_application_json'])
             self.object.river_lease_scan_of_application.remove()
             for d in self.object.river_lease_scan_of_application.all():
                 self.object.river_lease_scan_of_application.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.river_lease_scan_of_application.add(doc)


        if 'document_draft_signed_json' in self.request.POST:
             json_data = json.loads(self.request.POST['document_draft_signed_json'])
             self.object.document_draft_signed.remove()
             for d in self.object.document_draft_signed.all():
                 self.object.document_draft_signed.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.document_draft_signed.add(doc)


        if 'document_final_signed_json' in self.request.POST:
             json_data = json.loads(self.request.POST['document_final_signed_json'])
             self.object.document_final_signed.remove()
             for d in self.object.document_final_signed.all():
                 self.object.document_final_signed.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.document_final_signed.add(doc)

        if 'document_draft_json' in self.request.POST:
             json_data = json.loads(self.request.POST['document_draft_json'])
             self.object.document_draft.remove()
             for d in self.object.document_draft.all():
                 self.object.document_draft.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.document_draft.add(doc)


        if 'approval_document_json' in self.request.POST:
           self.object.approval_document = None
           if is_json(self.request.POST['approval_document_json']) is True:
                json_data = json.loads(self.request.POST['approval_document_json'])
                new_doc = Record.objects.get(id=json_data['doc_id'])
                self.object.approval_document = new_doc

        if 'approval_document_signed_json' in self.request.POST:
           self.object.approval_document_signed = None
           if is_json(self.request.POST['approval_document_signed_json']) is True:
                json_data = json.loads(self.request.POST['approval_document_signed_json'])
                new_doc = Record.objects.get(id=json_data['doc_id'])
                self.object.approval_document_signed = new_doc


        if 'certificate_of_title_volume' in forms_data:
            new_loc.title_volume = forms_data['certificate_of_title_volume']
        if 'folio' in forms_data:
            new_loc.folio = forms_data['folio']
        if 'diagram_plan_deposit_number' in forms_data:
            new_loc.dpd_number = forms_data['diagram_plan_deposit_number']
        if 'location' in forms_data:
            new_loc.location = forms_data['location']
        if 'reserve_number' in forms_data:
            new_loc.reserve = forms_data['reserve_number']
        if 'street_number_and_name' in forms_data:
            new_loc.street_number_name = forms_data['street_number_and_name']
        if 'town_suburb' in forms_data:
            new_loc.suburb = forms_data['town_suburb']
        if 'lot' in forms_data:
            new_loc.lot = forms_data['lot']
        if 'nearest_road_intersection' in forms_data:
            new_loc.intersection = forms_data['nearest_road_intersection']
        if 'local_government_authority' in forms_data:
            new_loc.local_government_authority = forms_data['local_government_authority']

        if self.object.state == Application.APP_STATE_CHOICES.new:
            self.object.state = Application.APP_STATE_CHOICES.draft

        if self.object.jetty_dot_approval is None:
             self.object.jetty_dot_approval = None 
        if self.object.vessel_or_craft_details == '':
             self.object.vessel_or_craft_details =None
        if self.object.beverage == '':
             self.object.beverage = None
        if self.object.byo_alcohol == '':
             self.object.byo_alcohol = None
        if self.object.liquor_licence == '':
             self.object.liquor_licence = None        

        self.object.save()
        new_loc.save()

        if self.object.app_type == self.object.APP_TYPE_CHOICES.licence:
            form.save_m2m()
#        if self.request.POST.get('nextstep') or self.request.POST.get('prevstep'):
            # print self.request.POST['nextstep']          
            # if self.request.POST.get('prevstep'):
            # print self.request.POST['nextstep']
            # print "CONDITION ROUTING"

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(application)
        flow.get(workflowtype)
        conditionactions = flow.getAllConditionBasedRouteActions(application.routeid)
        if conditionactions:
             for ca in conditionactions:
                 for fe in self.request.POST:
                     if ca == fe:
                         for ro in conditionactions[ca]['routeoptions']:
                             if ro['field'] in self.request.POST:
                                 if ro['fieldvalue'] == self.request.POST[ro['field']]:
                                     if "routeurl" in ro:
                                        if ro["routeurl"] == "application_lodge":
                                            return HttpResponseRedirect(reverse(ro["routeurl"],kwargs={'pk':self.object.id}))
                                        if ro["routeurl"] == "application_issue":
                                            return HttpResponseRedirect(reverse(ro["routeurl"],kwargs={'pk':self.object.id}))

                                     self.object.routeid = ro['route']
                                     self.object.state = ro['state']
                                     self.object.route_status = flow.json_obj[ro['route']]['title']
                                     self.object.save()

                                     routeurl = "application_update" 
                                     if "routeurl" in ro:
                                         routeurl = ro["routeurl"]
                                     return HttpResponseRedirect(reverse(routeurl,kwargs={'pk':self.object.id}))
        self.object.save()
        return HttpResponseRedirect(self.object.get_absolute_url()+'update/')
        #return HttpResponseRedirect(self.get_success_url(self.object))

class ApplicationLodge(LoginRequiredMixin, UpdateView):
    model = Application
    form_class = apps_forms.ApplicationLodgeForm
    template_name = 'applications/application_lodge.html'

    def get_context_data(self, **kwargs):
        context = super(ApplicationLodge, self).get_context_data(**kwargs)
        app = self.get_object()

        if app.app_type == app.APP_TYPE_CHOICES.part5:
            self.template_name = 'applications/application_lodge_part5.html'
        if app.routeid is None:
            app.routeid = 1
        return context

    def get(self, request, *args, **kwargs):
        # TODO: business logic to check the application may be lodged.
        # Rule: application state must be 'draft'.
        app = self.get_object()
        flowcontext = {}
        error_messages = False 

        if app.assignee: 
            flowcontext['application_assignee_id'] = app.assignee
        else:
            flowcontext['application_assignee_id'] = None

        workflowtype = ''

        if app.routeid is None:
            app.routeid = 1
        request = self.request
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)

        if flowcontext['may_lodge'] == "True":
            route = flow.getNextRouteObj('lodge', app.routeid, workflowtype)
            flowcontext = flow.getRequired(flowcontext, app.routeid, workflowtype)

            if route is not None: 
                if 'required' in route:
                    for fielditem in route["required"]:
                         if hasattr(app, fielditem):
                            if getattr(app, fielditem) is None:
                                messages.error(self.request, 'Required Field ' + fielditem + ' is empty,  Please Complete')
                                error_messages = True
                                #return HttpResponseRedirect(app.get_absolute_url()+'update/')
                            appattr = getattr(app, fielditem)
                            python3 = False
                            try:
                                 unicode('test')
                            except:
                                 python3 = True
                                 pass
                            if python3 is True:
                                if isinstance(appattr, str):
                                    if len(appattr) == 0:
                                        messages.error(self.request, 'Required Field ' + fielditem + ' is empty,  Please Complete')
                                        error_messages = True
                            else: 
                                if isinstance(appattr, unicode) or isinstance(appattr, str):
                                    if len(appattr) == 0:
                                        messages.error(self.request, 'Required Field ' + fielditem + ' is empty,  Please Complete')
                                        error_messages = True
                    if error_messages is True:
                        return HttpResponseRedirect(app.get_absolute_url()+'update/')
                    donothing = ""
            else:
                messages.error(self.request, 'This application has no matching routes.')
                return HttpResponseRedirect(app.get_absolute_url())
        else:
            messages.error(self.request, 'This application cannot be lodged!')
            return HttpResponseRedirect(app.get_absolute_url())

        return super(ApplicationLodge, self).get(request, *args, **kwargs)

    def get_success_url(self):
        #return reverse('application_list')
        return reverse('home')

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            #return HttpResponseRedirect(self.get_object().get_absolute_url())
            return HttpResponseRedirect(self.get_object().get_absolute_url()+'update/')
        return super(ApplicationLodge, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override form_valid to set the submit_date and status of the new application.
        """
        print ("FORM VALID")
        app = self.get_object()
        flowcontext = {}
        error_messages = False
        # if app.app_type == app.APP_TYPE_CHOICES.part5:
        if app.routeid is None:
            app.routeid = 1
 
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        nextroute = flow.getNextRoute('lodge', app.routeid, workflowtype)
        route = flow.getNextRouteObj('lodge', app.routeid, workflowtype)
        app.routeid = nextroute
        flowcontext = flow.getRequired(flowcontext, app.routeid, workflowtype)
        if "required" in route:
            for fielditem in route["required"]:
                if hasattr(app, fielditem):
                    if getattr(app, fielditem) is None:
                        messages.error(self.request, 'Required Field ' + fielditem + ' is empty,  Please Complete')
                        error_messages = True
                        #return HttpResponseRedirect(app.get_absolute_url()+'update/')
                    appattr = getattr(app, fielditem)
                    python3 = False
                    try:
                         unicode('test')
                    except:
                         python3 = True

                    if python3 is True:
                        if isinstance(appattr, str):
                            if len(appattr) == 0:
                                messages.error(self.request, 'Required Field ' + fielditem + ' is empty,  Please Complete')
                                error_messages = True
                    else:
                        if isinstance(appattr, unicode) or isinstance(appattr, str):
                            if len(appattr) == 0:
                                messages.error(self.request, 'Required Field ' + fielditem + ' is empty,  Please Complete')
                                error_messages = True
            if error_messages is True:
                 return HttpResponseRedirect(app.get_absolute_url()+'update/')
        groupassignment = SystemGroup.objects.get(name=DefaultGroups['grouplink'][route['lodgegroup']])
        app.group = groupassignment

        #app.state = app.APP_STATE_CHOICES.with_admin
        app.state  = route['state']
        app.status = 1
        self.object.submit_date = date.today()
        app.assignee = None
        app.save()

        # this get uses the new route id to get title of new route and updates the route_status.
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        app.route_status = flow.json_obj[app.routeid]['title']
        app.save()


        # Generate a 'lodge' action:
        action = Action(
            content_object=app, category=Action.ACTION_CATEGORY_CHOICES.lodge,
            user=self.request.user.id, action='Application lodgement')
        action.save()
        # Success message.
        #msg = """Your {0} application has been successfully submitted. The application
        #number is: <strong>WO-{1}</strong>.<br>
        #Please note that routine applications take approximately 4-6 weeks to process.<br>
        #If any information is unclear or missing, Parks and Wildlife may return your
        #application to you to amend or complete.<br>
        #The assessment process includes a 21-day external referral period. During this time
        #your application may be referred to external departments, local government
        #agencies or other stakeholders. Following this period, an internal report will be
        #produced by an officer for approval by the Manager, Rivers and Estuaries Division,
        #to determine the outcome of your application.<br>
        #You will be notified by email once your {0} application has been determined and/or
        #further action is required.""".format(app.get_app_type_display(), app.pk)
        #messages.success(self.request, msg)


        #emailcontext = {}
        #emailcontext['app'] = self.object

        #emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
        #emailcontext['person'] = app.submitted_by
        #emailcontext['body'] = msg 
        #sendHtmlEmail([app.submitted_by.email], emailcontext['application_name'] + ' application submitted ', emailcontext, 'application-lodged.html', None, None, None)

        if float(route['state']) == float("18"):
            if "payment_redirect" in route:
                 if route["payment_redirect"] == "True":
                      return HttpResponseRedirect(reverse('application_booking', args=(app.id,)))


        return HttpResponseRedirect(self.get_success_url())

class ApplicationRefer(LoginRequiredMixin, CreateView):
    """A view to create a Referral object on an Application (if allowed).
    """
    model = Referral
    form_class = apps_forms.ReferralForm

    def get(self, request, *args, **kwargs):
        # TODO: business logic to check the application may be referred.
        # Rule: application state must be 'with admin' or 'with referee'
        app = Application.objects.get(pk=self.kwargs['pk'])

        flowcontext = {}
      #  if app.app_type == app.APP_TYPE_CHOICES.part5:
        if app.routeid is None:
            app.routeid = 1

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)

        if flowcontext['may_refer'] != "True":
            messages.error(self.request, 'Can not modify referrals on this application!')
            return HttpResponseRedirect(app.get_absolute_url())

#        else:
#            if app.state not in [app.APP_STATE_CHOICES.with_admin, app.APP_STATE_CHOICES.with_referee]:
#               # TODO: better/explicit error response.
#                messages.error(
#                    self.request, 'This application cannot be referred!')
#                return HttpResponseRedirect(app.get_absolute_url())
        return super(ApplicationRefer, self).get(request, *args, **kwargs)

    def get_success_url(self):
        """Override to redirect to the referral's parent application detail view.
        """
        #messages.success(self.request, 'Referral has been added! ')
        #TODO check this
        return reverse('home')

    def get_context_data(self, **kwargs):
        context = super(ApplicationRefer, self).get_context_data(**kwargs)
        context['application'] = Application.objects.get(pk=self.kwargs['pk'])
        context['application_referrals'] = Referral.objects.filter(application=self.kwargs['pk'])
        app = Application.objects.get(pk=self.kwargs['pk'])
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        context = flow.getAccessRights(self.request, context, app.routeid, workflowtype)
        return context

    def get_initial(self):
        initial = super(ApplicationRefer, self).get_initial()
        # TODO: set the default period value based on application type.
        initial['period'] = 21
        return initial

    def get_form_kwargs(self):
        kwargs = super(ApplicationRefer, self).get_form_kwargs()
        kwargs['application'] = Application.objects.get(pk=self.kwargs['pk'])
        return kwargs

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = Application.objects.get(pk=self.kwargs['pk'])
            return HttpResponseRedirect(app.get_absolute_url())
        return super(ApplicationRefer, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        app = Application.objects.get(pk=self.kwargs['pk'])
#        if app.app_type == app.APP_TYPE_CHOICES.part5:
#            flow = Flow()
#            flow.get('part5')
#            nextroute = flow.getNextRoute('referral',app.routeid,"part5")
#            app.routeid = nextroute

        self.object = form.save(commit=False)
        referee = form.cleaned_data['referee'].ledger_id.id
        self.object.referee = referee
        self.object.application = app
        #self.object.sent_date = date.today()
        self.object.save()
        # Set the application status to 'with referee'.
#        app.state = app.APP_STATE_CHOICES.with_referee
#        app.save()
        # TODO: the process of sending the application to the referee.
        # Generate a 'refer' action on the application:
        action = Action(
            content_object=app, category=Action.ACTION_CATEGORY_CHOICES.refer,
            user=self.request.user.id, action='Added Referral {}'.format(self.object.referee))
        action.save()
        return super(ApplicationRefer, self).form_valid(form)

class ApplicationAssignNextAction(LoginRequiredMixin, UpdateView):
    """A view to allow an application to be assigned to an internal user or back to the customer.
    The ``action`` kwarg is used to define the new state of the application.
    """
    model = Application

    def get(self, request, *args, **kwargs):
        app = self.get_object()

        if app.assignee is None:
            messages.error(self.request, 'Please Allocate an Assigned Person First')
            return HttpResponseRedirect(app.get_absolute_url())

        action = self.kwargs['action']
        actionid = self.kwargs['actionid']

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)
        flowcontext = flow.getRequired(flowcontext, app.routeid, workflowtype)
        #route = flow.getNextRouteObj(action, app.routeid, workflowtype)
        route = flow.getNextRouteObjViaId(int(actionid), app.routeid, workflowtype)
        #allow_email_attachment
        if action == "creator":
            if flowcontext['may_assign_to_creator'] != "True":
                messages.error(self.request, 'This application cannot be reassigned, Unknown Error')
                return HttpResponseRedirect(app.get_absolute_url())
        else:
            # nextroute = flow.getNextRoute(action,app.routeid,"part5")
            assign_action = flow.checkAssignedAction(action, flowcontext)
            if assign_action != True:
                if action in DefaultGroups['grouplink']:
                    messages.error(self.request, 'This application cannot be reassign to ' + DefaultGroups['grouplink'][action])
                    return HttpResponseRedirect(app.get_absolute_url())
                else:
                    messages.error(self.request, 'This application cannot be reassign, Unknown Error')
                    return HttpResponseRedirect(app.get_absolute_url())

        if action == 'referral':
            app_refs = Referral.objects.filter(application=app).count()
            #Referral.objects.filter(application=app).update(status=5)
            Referral.objects.filter(application=app).update(status=Referral.REFERRAL_STATUS_CHOICES.referred, response_date=None)
            if app_refs == 0:
                messages.error(self.request, 'Unable to complete action as you have no referrals! ')
                return HttpResponseRedirect(app.get_absolute_url())

        if "required" in route:
            for fielditem in route["required"]:
                if hasattr(app, fielditem):
                    if getattr(app, fielditem) is None:
                        messages.error(self.request, 'Required Field ' + fielditem + ' is empty,  Please Complete')
                        return HttpResponseRedirect(reverse('application_update', args=(app.pk,)))
                    appattr = getattr(app, fielditem)
                    try:
                        if isinstance(appattr, unicode) or isinstance(appattr, str):
                            if len(appattr) == 0:
                                messages.error(self.request, 'Required Field ' + fielditem + ' is empty,  Please Complete')
                                return HttpResponseRedirect(reverse('application_update', args=(app.pk,)))
                    except:
                        if isinstance(appattr, str):
                            if len(appattr) == 0:
                                messages.error(self.request, 'Required Field ' + fielditem + ' is empty,  Please Complete')
                                return HttpResponseRedirect(reverse('application_update', args=(app.pk,)))


        return super(ApplicationAssignNextAction, self).get(request, *args, **kwargs)

    def get_initial(self):
        initial = super(ApplicationAssignNextAction, self).get_initial()
        app = self.get_object()

        action = self.kwargs['action']
        actionid = self.kwargs['actionid']

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        route = flow.getNextRouteObjViaId(int(actionid), app.routeid, workflowtype)
        print ("ROUTE")
        print ("flow.getNextRouteObjViaId")
        print (route)
        #allow_email_attachment
        allow_email_attachment = False
        if 'allow_email_attachment' in route:
            if route['allow_email_attachment'] == 'True':
                allow_email_attachment = True

        initial['allow_email_attachment'] = allow_email_attachment
        initial['action'] = self.kwargs['action'] 
        initial['records'] = None
        return initial

# action = self.kwargs['action']
    def get_form_class(self):
        return apps_forms.ApplicationAssignNextAction

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ApplicationAssignNextAction, self).post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('application_list')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        forms_data = form.cleaned_data
        app = self.get_object()
        action = self.kwargs['action']
        actionid = self.kwargs['actionid']

        # Upload New Files
        # doc = None
        # if self.request.FILES.get('records'):  # Uploaded new file.
        #    doc = Record()
        #    doc.upload = forms_data['records']
        #    doc.name = forms_data['records'].name
        #    doc.save()
        # print doc
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        DefaultGroups = flow.groupList()
        FriendlyGroupList = flow.FriendlyGroupList()
        flow.get(workflowtype)
        assessed_by = None

        if action == "creator":
            groupassignment = None
            assignee = app.submitted_by
        elif action == 'referral':
            groupassignment = SystemGroup.objects.get(name=DefaultGroups['grouplink']['assess'])
            assignee = None
        else:
            assignee = None
            assessed_by = self.request.user.id 
            groupassignment = SystemGroup.objects.get(name=DefaultGroups['grouplink'][action])
            if app.assigned_officer:
                assigned_officer = EmailUser.objects.get(id=app.assigned_officer)
                usergroups = assigned_officer.get_system_group_permission(assigned_officer.id)
                if groupassignment.id in usergroups:
                    assignee = app.assigned_officer


        #route = flow.getNextRouteObj(action, app.routeid, workflowtype)
        route = flow.getNextRouteObjViaId(int(actionid), app.routeid, workflowtype)   
        if route is None:
            messages.error(self.request, 'Error In Assigning Next Route, No routes Found')
            return HttpResponseRedirect(app.get_absolute_url())
        if route["route"] is None:
            messages.error(self.request, 'Error In Assigning Next Route, No routes Found')
            return HttpResponseRedirect(app.get_absolute_url())

        self.object.routeid = route["route"]
        self.object.state = route["state"]
        self.object.group = groupassignment
        self.object.assignee = assignee
        self.object.save()


        # this get uses the new route id to get title of new route and updates the route_status.
        workflowtype = flow.getWorkFlowTypeFromApp(self.object)
        flow.get(workflowtype)
        self.object.route_status = flow.json_obj[self.object.routeid]['title']
        self.object.save()

        comms = Communication()
        comms.application = app
        comms.comms_from = str(self.request.user.email)

        if action == 'creator': 
           comms.comms_to = "Form Creator"
        else:
           comms.comms_to = FriendlyGroupList['grouplink'][action] 
        
        if self.object.state == '8':
             pass
        else:
            comms.subject = route["title"]
            comms.details = forms_data['details']
            comms.state = route["state"]
            comms.comms_type = 4
        comms.save()
        print ("COMMS")
        if 'records_json' in self.request.POST:
            if is_json(self.request.POST['records_json']) is True:
                print (self.request.POST['records_json'])
                json_data = json.loads(self.request.POST['records_json'])
                for i in json_data:
                    doc = Record.objects.get(id=i['doc_id'])
                    comms.records.add(doc)
                    #comms.save_m2m()
                    comms.save()


#        if self.request.FILES.get('records'):
#            if Attachment_Extension_Check('multi', self.request.FILES.getlist('other_relevant_documents'), None) is False:
#                raise ValidationError('Other relevant documents contains and unallowed attachment extension.')
#
#            for f in self.request.FILES.getlist('records'):
#                doc = Record()
#                doc.upload = f
#                doc.name = f.name
#                doc.save()
#                comms.records.add(doc)
#        if doc:
#            comms.records.add(doc)

        if "stake_holder_communication" in route:
             self.send_stake_holder_comms(app) 

        emailcontext = {}
        emailcontext['app'] = self.object

        if action != "creator" and action != 'referral':
            emailcontext['groupname'] = DefaultGroups['grouplink'][action]
            emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
            emailGroup('Application Assignment to Group ' + DefaultGroups['grouplink'][action], emailcontext, 'application-assigned-to-group.html', None, None, None, DefaultGroups['grouplink'][action])
            if self.object.state != '14' and self.object.state != '19':
                if app.assignee:
                    assignee = SystemUser.objects.get(ledger_id=app.assignee)
                    emailcontext = {}
                    emailcontext['app'] = self.object
                    emailcontext = {'person': assignee}
                    emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
                    sendHtmlEmail([assignee.email], emailcontext['application_name'] + ' application assigned to you ', emailcontext, 'application-assigned-to-person.html', None, None, None)
        elif action == "creator":
            emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
            emailcontext['person'] = assignee
            emailcontext['admin_comment'] = forms_data['submitter_comment']
            sendHtmlEmail([assignee], emailcontext['application_name'] + ' application requires more information ', emailcontext, 'application-assigned-to-submitter.html', None, None, None)
        elif action == "referral":
            emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
            emailApplicationReferrals(app.id, 'Application for Feedback ', emailcontext, 'application-assigned-to-referee.html', None, None, None)


        if self.object.state == '14' or self.object.state == '19':
        # Form Commpleted & Create Approval
            self.complete_application(app, self.object.state)

        #if self.object.state == 19:
        #    self.complete_application_part5_not_supported(app)

        if self.object.state == '10': 
            self.ammendment_approved(app) 
        if self.object.state == '8':
            self.decline_notification(app, forms_data)
        if 'process' in route:
            if 'draft_completed' in route['process']:
                self.draft_completed(app)
            if 'final_completed' in route['process']:
                self.final_completed(app)
            if 'temp_approval' in route['process']:
                self.temp_approval(app)

        # Record an action on the application:
        action = Action(
            content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.action, user=self.request.user.id,
            action='Next Step Application Assigned to group ({}) with action title ({}) and route id ({}) '.format(groupassignment, route['title'], self.object.routeid))
        action.save()
        #if app.app_type == 4:
        #     return HttpResponseRedirect(reverse('emergencyworks_list'))
        return HttpResponseRedirect(self.get_success_url())

    def send_stake_holder_comms(self,app):
        # application-stakeholder-comms.html 
        # get applicant contact emails 
        if app.organisation:
           org_dels = Delegate.objects.filter(organisation=app.organisation) 
           for od in org_dels:
                # get all organisation contact emails and names
                system_user = SystemUser.objects.get(ledger_id=od.email_user)
                StakeholderComms.objects.create(application=app,
                                                email=system_user.email,
                                                name=system_user.first_name + ' '+ system_user.last_name,
                                                sent_date=date.today(),
                                                role=1,
                                                comm_type=1
                )
                emailcontext = {'person': system_user.first_name + ' '+ system_user.last_name}    
                sendHtmlEmail([system_user.email], 'Appplication has progressed', emailcontext, 'application-stakeholder-comms.html', None, None, None)
             
        elif app.applicant:
               applicant = SystemUser.objects.get(ledger_id=app.applicant)
               StakeholderComms.objects.create(application=app,
                                                email=applicant.email,
                                                name=applicant.legal_first_name + ' '+ applicant.legal_last_name,
                                                sent_date=date.today(),
                                                role=1,
                                                comm_type=1
               )
               emailcontext = {'person': applicant.legal_first_name + ' '+ applicant.legal_last_name}
               sendHtmlEmail([applicant.email], 'Appplication has progressed', emailcontext, 'application-stakeholder-comms.html', None, None, None)

               # get only applicant name and email
        
        # Get Sumitter information
        # submitter = app.submitted_by
        
        
        if app.applicant != app.submitted_by:
            submitter = SystemUser.objects.get(ledger_id=app.submitted_by)
            StakeholderComms.objects.create(application=app,
                                       email=submitter.email,
                                       name=submitter.first_name + ' '+ submitter.last_name,
                                       sent_date=date.today(),
                                       role=2,
                                       comm_type=1
            )
            emailcontext = {'person': submitter.first_name + ' '+ submitter.last_name}
            sendHtmlEmail([submitter.email], 'Appplication has progressed', emailcontext, 'application-stakeholder-comms.html', None, None, None)


        public_feedback =  PublicationFeedback.objects.filter(application=app)
        for pf in public_feedback:
            StakeholderComms.objects.create(application=app,
                                       email=pf.email,
                                       name=pf.name,
                                       sent_date=date.today(),
                                       role=4,
                                       comm_type=1
            )
            emailcontext = {'person': pf.name}
            sendHtmlEmail([pf.email], 'Appplication has progressed', emailcontext, 'application-stakeholder-comms.html', None, None, None)


        # Get feedback
        # PublicationFeedback 
        refs = Referral.objects.filter(application=app)
        for ref in refs:
            referee = SystemUser.objects.get(ledger_id=ref.referee)
            StakeholderComms.objects.create(application=app,
                                       email=referee.email,
                                       name=referee.first_name + ' ' + referee.last_name,
                                       sent_date=date.today(),
                                       role=3,
                                       comm_type=1
            )
            emailcontext = {'person': referee.first_name + ' ' + referee.last_name}
            sendHtmlEmail([referee.email], 'Appplication has progressed', emailcontext, 'application-stakeholder-comms.html', None, None, None)


        # Get Referrals
        # Referral
        # app.pfpfpf        


    def draft_completed(self,app):
         submitted_by = SystemUser.objects.get(ledger_id=app.submitted_by)
         emailcontext = {}
         emailcontext['app'] = app
         emailcontext['applicant'] = SystemUser.objects.get(ledger_id=app.applicant) 
#        if app.app_type == 3:
         emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
         emailcontext['person'] = app.submitted_by
         emailcontext['EXTERNAL_URL'] = settings.EXTERNAL_URL
         sendHtmlEmail([submitted_by.email], 'Draft Report - Part 5 - '+str(app.id), emailcontext, 'application-part5-draft-report.html', None, None, None)

    def final_completed(self,app):
         emailcontext = {}
         emailcontext['app'] = app

         if app.app_type == 3:
            emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
            if app.submitted_by:
                submitted_by = SystemUser.objects.get(ledger_id = app.submitted_by)
                emailcontext['person'] = submitted_by
            emailcontext['person'] = submitted_by
            emailcontext['EXTERNAL_URL'] = settings.EXTERNAL_URL
            sendHtmlEmail([submitted_by.email], 'Final Report - Part  - '+str(app.id), emailcontext, 'application-part5-final-report.html', None, None, None)

    def decline_notification(self,app,forms_data):
         submitted_by = SystemUser.objects.get(ledger_id=app.submitted_by)
         attachment1 = None
         if 'attach_to_email_json' in self.request.POST:
             if is_json(self.request.POST['attach_to_email_json']) is True:
                json_data = json.loads(self.request.POST['attach_to_email_json'])
                doc = Record.objects.get(id=json_data['doc_id'])
                attachment1 = doc.upload.path
         emailcontext = {}
         emailcontext['app'] = app

         emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
         emailcontext['person'] = submitted_by
         emailcontext['communication_details'] =  forms_data['details']
         sendHtmlEmail([submitted_by.email], Application.APP_TYPE_CHOICES[app.app_type]+' application declined - '+str(app.id), emailcontext, 'application-declined.html', None, None, None, attachment1)


    def temp_approval(self,app):
        approval = Approval.objects.create(
                                  app_type=app.app_type,
                                  title=app.title,
                                  applicant=app.applicant,
                                  organisation=app.organisation,
                                  application=app,
                                  start_date=app.assessment_start_date,
                                  expiry_date=app.expire_date,
                                  status=7
                                  )

    def complete_application_part5(self,app):

        if Approval.objects.filter(application=app).count() > 0:
              approval = Approval.objects.filter(application=app)[0]
              approval.approval_document = app.approval_document_signed 
              approval.save()


    def complete_application(self,app, state): 
        """Once and application is complete and approval needs to be created in the approval model.
        """
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   

        approval = None
        if Approval.objects.filter(application=app).count() > 0:
              from django.core.files.base import ContentFile
              from django.core.files.base import File 
              approval = Approval.objects.filter(application=app)[0]
              r = Record.objects.create(upload=app.approval_document_signed.upload.path, 
                                        name=app.approval_document_signed.name, 
                                        category=9, 
                                        metadata=app.approval_document_signed.metadata,
                                        text_content=app.approval_document_signed.text_content,
                                        file_group=2005,
                                        file_group_ref_id=approval.id, 
                                        extension=app.approval_document_signed.extension
                                       ) 

              import pathlib
              app_file_bytes = pathlib.Path(os.path.join(app.approval_document_signed.upload.path)).read_bytes()

              #app_file = open(os.path.join(app.approval_document_signed.upload.path), 'rb'             )
              #with open(os.path.join(app.approval_document_signed.upload.path), "rb") as f:
              #f = open(os.path.join(app.approval_document_signed.upload.path), "rb")
              #     app_file_bytes = f.read(1)
              #     while app_file_bytes != "":
              #         # Do stuff with byte.
              #         app_file_bytes = f.read(1)

              #app_file_bytes = app_file.encode(encoding='UTF-8')


              r.upload.save(app.approval_document_signed.name, ContentFile(app_file_bytes), save=False)

              approval.approval_document = r

              if app.app_type == 3: 
                  approval.start_date = app.assessment_start_date
              if int(state) == 19:
                  approval.status = 8
              else:
                  approval.status = 1
              print (approval.status)
              approval.save()
              

        else:
             approval = Approval.objects.create(
                                               app_type=app.app_type,
                                               title=app.title,
                                               applicant=app.applicant,
                                               organisation=app.organisation,
                                               application=app,
                                               start_date=app.assessment_start_date,
                                               expiry_date=app.expire_date,
                                               status=1
                                               )
             if app.app_type==4:
                 approval.start_date = app.proposed_commence
                 approval.expiry_date = app.proposed_end
                 approval.save()


        if app.old_application:
              app.old_application.status=2
              app.old_application.save()
              old_approval = Approval.objects.get(id=app.old_approval_id) 
              old_approval.status = 3
              old_approval.save()

              action = Action(
                  content_object=app.old_application, category=Action.ACTION_CATEGORY_CHOICES.cancel, user=self.request.user.id,
                  action='Application cancelled due to amendment. New application : WO-{}, New Approval : AP-{}'.format(str(app.id), str(approval.id)))
              action.save()

              action = Action(
                  content_object=old_approval, category=Action.ACTION_CATEGORY_CHOICES.cancel, user=self.request.user.id,
                  action='Approval cancelled due to amendment. New application : WO-{}, New Approval : AP-{}'.format(str(app.id), str(approval.id)))
              action.save()



        emailcontext = {}
        emailcontext['app'] = app
        emailcontext['approval'] = approval
        pdftool = PDFtool()
        submitted_by = SystemUser.objects.get(ledger_id=app.submitted_by)
        # applications/email/application-permit-proposal.html
        approval_pdf = BASE_DIR+'/pdfs/approvals/'+str(approval.id)+'-approval.pdf'
        # email send after application completed..(issued)
        if app.app_type == 1:
           # Permit Proposal
           pdftool.generate_permit(approval)
           emailcontext['person'] = submitted_by 
           emailcontext['conditions_count'] = Condition.objects.filter(application=app).count()
           sendHtmlEmail([submitted_by.email], 'Permit - '+app.title, emailcontext, 'application-permit-proposal.html', None, None, None, approval_pdf)

        elif app.app_type == 2:
           # Licence Proposal
           pdftool.generate_licence(approval)
           emailcontext['person'] = submitted_by
           emailcontext['vessels'] = app.vessels.all()
           emailcontext['approval'] = approval
           sendHtmlEmail([submitted_by.email], 'Licence Permit - '+app.title, emailcontext, 'application-licence-permit-proposal.html', None, None, None, approval_pdf)
        elif app.app_type == 3:

           emailcontext['person'] = submitted_by
           emailcontext['approval'] = approval
           approval_pdf = approval.approval_document.upload.path
           sendHtmlEmail([submitted_by.email], 'Part 5 - '+app.title, emailcontext, 'application-licence-permit-proposal.html', None, None, None, approval_pdf)

        elif app.app_type == 4:
           pdftool.generate_emergency_works(approval)
           emailcontext['person'] = app.submitted_by
           emailcontext['conditions_count'] = Condition.objects.filter(application=app).count()
           sendHtmlEmail([submitted_by.email], 'Emergency Works - '+app.title, emailcontext, 'application-permit-proposal.html', None, None, None, approval_pdf)


        elif app.app_type == 6:            

           emailcontext['person'] = submitted_by
           emailcontext['approval'] = approval
           approval_pdf = approval.approval_document.upload.path
           sendHtmlEmail([submitted_by.email], 'Section 84 - '+app.title, emailcontext, 'application-licence-permit-proposal.html', None, None, None, approval_pdf)

        elif app.app_type == 10 or app.app_type == 11:
           # Permit & Licence Renewal 
           emailcontext['person'] = submitted_by
           sendHtmlEmail([submitted_by.email], 'Draft Report - Part 5 - '+str(app.id)+' - location - description of works - applicant', emailcontext, 'application-licence-permit-proposal.html', None, None, None)

        ####################
        # Disabling compliance creationg after approval ( this is now handle by cron script as we are not creating all future compliance all at once but only the next due complaince.
        return
        ################### 
        

        # For compliance ( create clearance of conditions )
        # get all conditions 
        conditions = Condition.objects.filter(application=app)

        # print conditions
        # create clearance conditions
        for c in conditions:
            
            start_date = app.proposed_commence
            end_date = c.due_date
            if c.recur_pattern == 1:
                  num_of_weeks = (end_date - start_date).days / 7.0
                  num_of_weeks_whole = str(num_of_weeks).split('.')
                  num_of_weeks_whole = num_of_weeks_whole[0]
                  week_freq = num_of_weeks / c.recur_freq
                  week_freq_whole = int(str(week_freq).split('.')[0])
                  loopcount = 1
                  loop_start_date = start_date
                  while loopcount <= week_freq_whole:
                      loopcount = loopcount + 1
                      week_date_plus = timedelta(weeks = c.recur_freq)

                      new_week_date = loop_start_date + week_date_plus
                      loop_start_date = new_week_date
                      compliance = Compliance.objects.create(
                                      app_type=app.app_type,
                                      title=app.title,
                                      condition=c,
                                      approval_id=approval.id,
                                      applicant=approval.applicant,
                                      assignee=None,
                                      assessed_by=None,
                                      assessed_date=None,
                                      due_date=new_week_date,
                                      status=Compliance.COMPLIANCE_STATUS_CHOICES.future
                                     )
                  
                  if week_freq > week_freq_whole:
                      compliance = Compliance.objects.create(
                                      app_type=app.app_type,
                                      title=app.title,
                                      condition=c,
                                      approval_id=approval.id,
                                      applicant=approval.applicant,
                                      assignee=None,
                                      assessed_by=None,
                                      assessed_date=None,
                                      due_date=c.due_date,
                                      status=Compliance.COMPLIANCE_STATUS_CHOICES.future
                                     )
            if c.recur_pattern == 2:
                 r = relativedelta(end_date, start_date)
                 num_of_months = float(r.years * 12 + r.months) / c.recur_freq
                 loopcount = 0
                 loop_start_date = start_date

                 while loopcount < int(num_of_months):
                      months_date_plus = loop_start_date + relativedelta(months=c.recur_freq)
                      loop_start_date = months_date_plus
                      loopcount = loopcount + 1
                      compliance = Compliance.objects.create(
                                      app_type=app.app_type,
                                      title=app.title,
                                      condition=c,
                                      approval_id=approval.id,
                                      applicant=approval.applicant,
                                      assignee=None,
                                      assessed_by=None,
                                      assessed_date=None,
                                      due_date=months_date_plus,
                                      status=Compliance.COMPLIANCE_STATUS_CHOICES.future
                                     )

                 if num_of_months > loopcount:
                      compliance = Compliance.objects.create(
                                      app_type=app.app_type,
                                      title=app.title,
                                      condition=c,
                                      approval_id=approval.id,
                                      applicant=approval.applicant,
                                      assignee=None,
                                      assessed_by=None,
                                      assessed_date=None,
                                      due_date=end_date,
                                      status=Compliance.COMPLIANCE_STATUS_CHOICES.future
                                   )

            if c.recur_pattern == 3: 
              
                 r = relativedelta(end_date, start_date)
                 if r.years > 0:
                     loopcount = 0
                     loop_start_date = start_date
                     while loopcount < int(r.years):
                           years_date_plus = loop_start_date + relativedelta(years=c.recur_freq)
                           loop_start_date = years_date_plus
                           loopcount = loopcount + 1
 
                           compliance = Compliance.objects.create(
                                      app_type=app.app_type,
                                      title=app.title,
                                      condition=c,
                                      approval_id=approval.id,
                                      applicant=approval.applicant,
                                      assignee=None,
                                      assessed_by=None,
                                      assessed_date=None,
                                      due_date=years_date_plus,
                                      status=Compliance.COMPLIANCE_STATUS_CHOICES.future
                                     )


                 if r.months > 0 or r.days > 0:
                     compliance = Compliance.objects.create(
                                      app_type=app.app_type,
                                      title=app.title,
                                      condition=c,
                                      approval_id=approval.id,
                                      applicant=approval.applicant,
                                      assignee=None,
                                      assessed_by=None,
                                      assessed_date=None,
                                      due_date=end_date,
                                      status=Compliance.COMPLIANCE_STATUS_CHOICES.future
                                   )

            #print c.iii


    def ammendment_approved(self,app):
        if app.approval_id: 
            approval = Approval.objects.get(id=app.approval_id)
            approval.ammendment_application = app
            approval.save()
        return

class ApplicationAssignPerson(LoginRequiredMixin, UpdateView):
    """A view to allow an application applicant to be assigned to a person 
    """
    model = Application

    def get(self, request, *args, **kwargs):
        app = self.get_object()

        if app.state == 14:
           messages.error(self.request, 'This application is completed and cannot be assigned.')
           return HttpResponseRedirect("/")
             

        if app.group is None:
            messages.error(self.request, 'Unable to set Person Assignments as No Group Assignments Set!')
            return HttpResponseRedirect(app.get_absolute_url())

        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == app.app_type:
                  app_type_short_name = i


        flow = Flow()
        flow.get(app_type_short_name)
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)
        print (flowcontext["may_assign_to_person"])
        if flowcontext["may_assign_to_person"] == "True":
            pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        return super(ApplicationAssignPerson, self).get(request, *args, **kwargs)

    def get_form_class(self):
        # Return the specified form class
        return apps_forms.AssignPersonForm

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ApplicationAssignPerson, self).post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('application_update', args=(self.object.pk,))

    def form_valid(self, form):
        self.object = form.save(commit=False)  # Do not commit the save yet

        assignee = form.cleaned_data['assignee'].ledger_id.id  # Get the selected assignee from the form
        self.object.assignee = assignee  # Assign the selected assignee to the application
        self.object.save()  # Save the application
        
        app = self.object

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        DefaultGroups = flow.groupList()
        flow.get(workflowtype)
        assignee = SystemUser.objects.get(ledger_id=app.assignee)
        emailcontext = {'person': assignee}
        emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
        if self.request.user.id != app.assignee:
            sendHtmlEmail([assignee.email], emailcontext['application_name'] + ' application assigned to you ', emailcontext, 'application-assigned-to-person.html', None, None, None)
        

        # Record an action on the application:
        action = Action(
            content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
            action='Assigned application to {} {} (status: {})'.format(assignee.first_name, assignee.last_name, self.object.get_state_display()))
        action.save()
        if self.request.user.id != app.assignee:
            messages.success(self.request, 'Assign person completed')
            return HttpResponseRedirect(reverse('application_list'))
        else:
            messages.success(self.request, 'Assign person completed')
            return HttpResponseRedirect(self.get_success_url())

    def get_initial(self):
        initial = super(ApplicationAssignPerson, self).get_initial()
        app = self.get_object()
        if app.routeid is None:
            app.routeid = 1
        initial['assigngroup'] = app.group
        return initial


class ApplicationAssignOfficer(LoginRequiredMixin, UpdateView):
    """A view to allow an application applicant to be assigned to a person
    """
    model = Application

    def get(self, request, *args, **kwargs):
        app = self.get_object()

        if app.state == 14:
           messages.error(self.request, 'This application is completed and cannot be assigned.')
           return HttpResponseRedirect("/")


        if app.group is None:
            messages.error(self.request, 'Unable to set Person Assignments as No Group Assignments Set!')
            return HttpResponseRedirect(app.get_absolute_url())

        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == app.app_type:
                  app_type_short_name = i


        flow = Flow()
        flow.get(app_type_short_name)
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)
        if flowcontext["may_assign_to_officer"] == "True":
            pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        return super(ApplicationAssignOfficer, self).get(request, *args, **kwargs)

    def get_form_class(self):
        # Return the specified form class
        return apps_forms.AssignOfficerForm

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ApplicationAssignOfficer, self).post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('application_update', args=(self.object.pk,))

    def form_valid(self, form):
        
        self.object = form.save(commit=False)
        assigned_officer = form.cleaned_data['assigned_officer'].ledger_id.id
        self.object.assigned_officer = assigned_officer
        app = self.object
        self.object.save()

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        DefaultGroups = flow.groupList()
        flow.get(workflowtype)

        # Record an action on the application:
        assigned_officer = SystemUser.objects.get(ledger_id=self.object.assigned_officer)
        action = Action(
            content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
            action='Application assigned officer to {} {}'.format(assigned_officer.first_name, assigned_officer.last_name))
        action.save()
        if self.request.user.id != app.assignee:
            messages.success(self.request, 'Assign officer completed')
            return HttpResponseRedirect(reverse('application_list'))
        else:
            messages.success(self.request, 'Assign officer completed')
            return HttpResponseRedirect(self.get_success_url())

    def get_initial(self):
        initial = super(ApplicationAssignOfficer, self).get_initial()
        app = self.get_object()
        if app.routeid is None:
            app.routeid = 1
        initial['assigngroup'] = app.group
        return initial



class ApplicationCancel(LoginRequiredMixin, UpdateView):
    """A view to allow an application applicant to be assigned to a person
    """
    model = Application
    template_name = 'applications/application_cancel_form.html'

    def get(self, request, *args, **kwargs):
        app = self.get_object()

        if app.state == 14:
           messages.error(self.request, 'This application is completed and cannot be cancelled.')
           return HttpResponseRedirect("/")

        #if app.group is None:
        #    messages.error(self.request, 'Unable to set Person Assignments as No Group Assignments Set!')
        #    return HttpResponseRedirect(app.get_absolute_url())

        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == app.app_type:
                  app_type_short_name = i


        #flow = Flow()
        #flow.get(app_type_short_name)
        #flowcontext = {}
        #flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)
        processor = SystemGroup.objects.get(name='Statdev Processor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        if processor.id in usergroups:
            pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        return super(ApplicationCancel, self).get(request, *args, **kwargs)

    def get_form_class(self):
        # Return the specified form class
        return apps_forms.AssignCancelForm

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ApplicationCancel, self).post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('application_list', args=(self.object.pk,))

    def form_valid(self, form):
        self.object = form.save(commit=True)
        app = self.object
        app.status = 2
        app.save()
        # Record an action on the application:
        action = Action(
            content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.cancel, user=self.request.user.id,
            action='Application cancelled')
        action.save()

        messages.success(self.request, 'Application cancelled')
        return HttpResponseRedirect(reverse('application_list'))

    def get_initial(self):
        initial = super(ApplicationCancel, self).get_initial()
        return initial

class ComplianceAssignPerson(LoginRequiredMixin, UpdateView):
    """A view to allow an application applicant to be assigned to a person
    """
    model = Compliance 

    def get(self, request, *args, **kwargs):
        app = self.get_object()

#        if app.state == 14:
#           messages.error(self.request, 'This compliance is approved and cannot be assigned.')
#           return HttpResponseRedirect("/")

        return super(ComplianceAssignPerson, self).get(request, *args, **kwargs)

    def get_form_class(self):
        # Return the specified form class
        return apps_forms.ComplianceAssignPersonForm

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ComplianceAssignPerson, self).post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('compliance_approval_update_internal', args=(self.object.pk,))

    def form_valid(self, form):
        self.object = form.save(commit=False)  # Do not commit the save yet

        assignee = form.cleaned_data['assignee'].ledger_id.id  # Get the selected assignee from the form
        self.object.assignee = assignee  # Assign the selected assignee to the application
        self.object.save()  # Save the application
        self.object = form.save(commit=True)
        app = self.object

        #flow = Flow()
        #workflowtype = flow.getWorkFlowTypeFromApp(app)
        #DefaultGroups = flow.groupList()
        #flow.get(workflowtype)
        #emailcontext = {'person': app.assignee}
        #emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
        #if self.request.user.id != app.assignee:
        #    sendHtmlEmail([app.assignee.email], emailcontext['application_name'] + ' application assigned to you ', emailcontext, 'application-assigned-to-person.html', None, None, None)


        # Record an action on the application:
        assignee = SystemUser.objects.get(ledger_id=self.object.assignee)
        action = Action(
            content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
            action='Assigned application to {} {} (status: {})'.format(assignee.first_name, assignee.last_name, self.object.get_status_display()))
        action.save()
        if self.request.user.id != app.assignee:
            messages.success(self.request, 'Assign person completed')
            return HttpResponseRedirect(reverse('application_list'))
        else:
            messages.success(self.request, 'Assign person completed')
            return HttpResponseRedirect(self.get_success_url())

    def get_initial(self):
        initial = super(ComplianceAssignPerson, self).get_initial()
        app = self.get_object()
        initial['assigngroup'] = app.group
        return initial
        #if app.routeid is None:
        #    app.routeid = 1

class ApplicationAssignApplicantCompany(LoginRequiredMixin, UpdateView):
    """A view to allow an application applicant to be assigned to a company holder
    """ 
    model = Application

    def get(self, request, *args, **kwargs):
        app = self.get_object()
        context_processor = template_context(self.request)
        staff_access = context_processor['admin_assessor_staff']
        if staff_access == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        #if app.group is None:
        #    messages.error(self.request, 'Unable to set Person Assignments as No Group Assignments Set!')
        #    return HttpResponseRedirect(app.get_absolute_url())
        return super(ApplicationAssignApplicantCompany, self).get(request, *args, **kwargs)

    def get_form_class(self):
        # Return the specified form class
        return apps_forms.AssignApplicantFormCompany

    def get_success_url(self, application_id):
        return reverse('application_update', args=(application_id,))

    def post(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        staff_access = context_processor['admin_assessor_staff']
        if staff_access == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ApplicationAssignApplicantCompany, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=True)
        self.object.applicant = None
        self.object.save()

        app = self.object

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        DefaultGroups = flow.groupList() 
        flow.get(workflowtype)
        emailcontext = {}
        emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
        if self.object.assignee:
            assignee = SystemUser.objects.get(ledger_id=self.object.assignee)
            emailcontext['person'] = assignee
            action = Action(
                content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
                action='Assigned application to {} {} (status: {})'.format(assignee.first_name, assignee.last_name, self.object.get_state_display()))
            action.save()
        return HttpResponseRedirect(self.get_success_url(self.kwargs['pk']))

    def get_initial(self):
        initial = super(ApplicationAssignApplicantCompany, self).get_initial()
        app = self.get_object()
        initial['organisation'] = self.kwargs['organisation_id']
        return initial

class ApplicationAssignApplicant(LoginRequiredMixin, UpdateView):
    """A view to allow an application applicant details to be reassigned to a different applicant name and 
       is only can only be set by and admin officer.
    """
    model = Application

    def get(self, request, *args, **kwargs):
        app = self.get_object()
        context_processor = template_context(self.request)

        staff_access = context_processor['admin_assessor_staff']
        if staff_access == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        #if app.group is None:
        #    messages.error(self.request, 'Unable to set Person Assignments as No Group Assignments Set!')
        #    return HttpResponseRedirect(app.get_absolute_url())
        return super(ApplicationAssignApplicant, self).get(request, *args, **kwargs)

    def get_form_class(self):
        # Return the specified form class
        return apps_forms.AssignApplicantForm


    def get_success_url(self, application_id):
        return reverse('application_update', args=(application_id,))

    def post(self, request, *args, **kwargs):

        context_processor = template_context(self.request)
        staff_access = context_processor['admin_assessor_staff']
        if staff_access == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")


        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ApplicationAssignApplicant, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)  # Do not commit the save yet
        applicant = form.cleaned_data['applicant'].ledger_id.id  # Get the selected assignee from the form
        self.object.applicant = applicant  # Assign the selected assignee to the application
        self.object.organisation = None
        self.object.save()

        app = self.object

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        DefaultGroups = flow.groupList()
        flow.get(workflowtype)
        emailcontext = {}
        emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
#        if self.request.user.id != app.assignee:
#            sendHtmlEmail([app.assignee.email], emailcontext['application_name'] + ' application assigned to you ', emailcontext, 'application-assigned-to-person.html', None, None, None)

        # Record an action on the application:
        if self.object.assignee:
            assignee = SystemUser.objects.get(ledger_id=self.object.assignee)
            emailcontext['person'] = assignee
            action = Action(
                content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
                action='Assigned application to {} {} (status: {})'.format(assignee.first_name, assignee.last_name, self.object.get_state_display()))
            action.save()
        return HttpResponseRedirect(self.get_success_url(self.kwargs['pk']))

    def get_initial(self):
        initial = super(ApplicationAssignApplicant, self).get_initial()
        app = self.get_object()
        initial['applicant'] = self.kwargs['applicantid']
        return initial

class ApplicationAssign(LoginRequiredMixin, UpdateView):
    """A view to allow an application to be assigned to an internal user or back to the customer.
    The ``action`` kwarg is used to define the new state of the application.
    """
    model = Application

    def get(self, request, *args, **kwargs):
        app = self.get_object()
        if self.kwargs['action'] == 'customer':
            # Rule: application can go back to customer when only status is
            # 'with admin'.
            if app.state != app.APP_STATE_CHOICES.with_admin:
                messages.error(
                    self.request, 'This application cannot be returned to the customer!')
                return HttpResponseRedirect(app.get_absolute_url())
        if self.kwargs['action'] == 'assess':
            # Rule: application can be assessed when status is 'with admin',
            # 'with referee' or 'with manager'.
            if app.app_type == app.APP_TYPE_CHOICES.part5:
                flow = Flow()
                flow.get('part5')
                flowcontext = {}
                flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, 'part5')
                if flowcontext["may_assign_assessor"] != "True":
                    messages.error(self.request, 'This application cannot be assigned to an assessor!')
                    return HttpResponseRedirect(app.get_absolute_url())
            else:
                if app.state not in [app.APP_STATE_CHOICES.with_admin, app.APP_STATE_CHOICES.with_referee, app.APP_STATE_CHOICES.with_manager]:
                    messages.error(self.request, 'This application cannot be assigned to an assessor!')
                    return HttpResponseRedirect(app.get_absolute_url())
        # Rule: only the assignee (or a superuser) can assign for approval.
        if self.kwargs['action'] == 'approve':
            if app.app_type == app.APP_TYPE_CHOICES.part5:
                flow = Flow()
                flow.get('part5')
                flowcontext = {}
                flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, 'part5')

                if flowcontext["may_submit_approval"] != "True":
                    messages.error(self.request, 'This application cannot be assigned to an assessor!')
                    return HttpResponseRedirect(app.get_absolute_url())
            else:
                if app.state != app.APP_STATE_CHOICES.with_assessor:
                    messages.error(self.request, 'You are unable to assign this application for approval/issue!')
                    return HttpResponseRedirect(app.get_absolute_url())
                if app.assignee != request.user.id and not request.user.is_superuser:
                    messages.error(self.request, 'You are unable to assign this application for approval/issue!')
                    return HttpResponseRedirect(app.get_absolute_url())
        return super(ApplicationAssign, self).get(request, *args, **kwargs)

    def get_form_class(self):
        # Return the specified form class
        if self.kwargs['action'] == 'customer':
            return apps_forms.AssignCustomerForm
        elif self.kwargs['action'] == 'process':
            return apps_forms.AssignProcessorForm
        elif self.kwargs['action'] == 'assess':
            return apps_forms.AssignAssessorForm
        elif self.kwargs['action'] == 'approve':
            return apps_forms.AssignApproverForm
        elif self.kwargs['action'] == 'assign_emergency':
            return apps_forms.AssignEmergencyForm

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ApplicationAssign, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        app = self.object
        assignee = SystemUser.objects.get(ledger_id=self.object.assignee)
        if self.kwargs['action'] == 'customer':
            messages.success(self.request, 'Application {} has been assigned back to customer'.format(self.object.pk))
        else:
            messages.success(self.request, 'Application {} has been assigned to {} {}'.format(self.object.pk, assignee.first_name, assignee.last_name))
        if self.kwargs['action'] == 'customer':
            # Assign the application back to the applicant and make it 'draft'
            # status.
            self.object.assignee = self.object.applicant
            self.object.state = self.object.APP_STATE_CHOICES.draft
            # TODO: email the feedback back to the customer.
        if self.kwargs['action'] == 'assess':
            if app.app_type == app.APP_TYPE_CHOICES.part5:
                flow = Flow()
                flow.get('part5')
                nextroute = flow.getNextRoute('assess', app.routeid, "part5")
                self.object.routeid = nextroute
            self.object.state = self.object.APP_STATE_CHOICES.with_assessor
        if self.kwargs['action'] == 'approve':
            if app.app_type == app.APP_TYPE_CHOICES.part5:
                flow = Flow()
                flow.get('part5')
                nextroute = flow.getNextRoute('manager', app.routeid, "part5")
                self.object.routeid = nextroute
            self.object.state = self.object.APP_STATE_CHOICES.with_manager
        if self.kwargs['action'] == 'process':
            if app.app_type == app.APP_TYPE_CHOICES.part5:
                flow = Flow()
                flow.get('part5')
                nextroute = flow.getNextRoute('admin', app.routeid, "part5")
                self.object.routeid = nextroute

            self.object.state = self.object.APP_STATE_CHOICES.with_manager
        self.object.save()
        if self.kwargs['action'] == 'customer':
            # Record the feedback on the application:
            d = form.cleaned_data
            action = Action(
                content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.communicate, user=self.request.user.id,
                action='Feedback provided to applicant: {}'.format(d['feedback']))
            action.save()
        # Record an action on the application:
        action = Action(
            content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
            action='Assigned application to {} {} (status: {})'.format(assignee.first_name, assignee.last_name, self.object.get_state_display()))
        action.save()
        return HttpResponseRedirect(self.get_success_url())

# have disbled the url..  this should be covered in the workflow.
class ApplicationDiscard(LoginRequiredMixin, UpdateView):
    """Allows and applicant to discard the application.
    """
    model = Application

    def get(self, request, *args, **kwargs):
        app = self.get_object()

        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']

        if app.state == 1:
           if request.user.id == app.assignee:
               donothing = ""
           elif admin_staff is True:
               donothing = ""
           else:
               messages.error(self.request, 'Sorry you are not authorised')
               return HttpResponseRedirect(self.get_success_url())
        else:
           messages.error(self.request, 'Sorry you are not authorised')
           return HttpResponseRedirect(self.get_success_url())        
        #if app.group is None:
        #    messages.error(self.request, 'Unable to set Person Assignments as No Group Assignments Set!')
        #    return HttpResponseRedirect(app.get_absolute_url())
        return super(ApplicationDiscard, self).get(request, *args, **kwargs)

    def get_form_class(self):
        # Return the specified form class
        return apps_forms.ApplicationDiscardForm

    def get_success_url(self):
        return reverse('home')

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ApplicationDiscard, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.state = 17
        self.object.route_status = "Deleted"
        self.object.save()

        # Record an action on the application:
        action = Action(
           content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
               action='Application Discard')
        action.save()
        messages.success(self.request, "Your application has been discard")
        return HttpResponseRedirect(self.get_success_url())

    def get_initial(self):
        initial = super(ApplicationDiscard, self).get_initial()
        app = self.get_object()
        return initial

class ComplianceActions(DetailView):
    model = Compliance 
    template_name = 'applications/compliance_actions.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ComplianceActions, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ComplianceActions, self).get_context_data(**kwargs)
        app = self.get_object()
        # TODO: define a GenericRelation field on the Application model.
        context['actions'] = Action.objects.filter(
            content_type=ContentType.objects.get_for_model(app), object_id=app.pk).order_by('-timestamp')
        return context

class ComplianceSubmit(LoginRequiredMixin, UpdateView):
    """Allows and applicant to discard the application.
    """
    model = Compliance

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        org = Delegate.objects.filter(email_user=self.request.user.id, organisation=self.object.organisation).count()
        assessor = SystemGroup.objects.get(name='Statdev Assessor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        if admin_staff == True:
           pass
        elif assessor.id in usergroups:
           pass
        elif self.request.user.id == self.object.applicant:
           pass
        elif org == 1:
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ComplianceSubmit, self).get(request, *args, **kwargs)

    def get_form_class(self):
        return apps_forms.ComplianceSubmitForm

    def get_success_url(self):
        return reverse('compliance_condition_complete', args=(self.object.id,))

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ComplianceSubmit, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.status = 9
        self.object.submit_date = datetime.now()
        self.object.submitted_by = self.request.user.id 
        assigngroup = SystemGroup.objects.get(name='Statdev Assessor')
        self.object.group = assigngroup
        self.object.save() 
        # Record an action on the application:
        action = Action(
           content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
               action='Compliance Submitted')
        action.save()
        messages.success(self.request, "Your compliance has beeen submitted for approval")

        emailcontext = {}
        #emailcontext['groupname'] = DefaultGroups['grouplink'][action]
        emailcontext['clearance_id'] = self.object.id
        emailGroup('New Clearance of Condition Submitted', emailcontext, 'clearance-of-condition-submitted.html', None, None, None, 'Statdev Assessor')

        return HttpResponseRedirect(self.get_success_url())

    def get_initial(self):
        initial = super(ComplianceSubmit, self).get_initial()
        app = self.get_object()
        return initial


class ComplianceStaff(LoginRequiredMixin, UpdateView):
    """Allows and applicant to discard the application.
    """
    model = Compliance

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        assessor = SystemGroup.objects.get(name='Statdev Assessor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        if admin_staff == True:
           pass
        elif assessor.id in usergroups:
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        return super(ComplianceStaff, self).get(request, *args, **kwargs)

    def get_form_class(self):
        return apps_forms.ComplianceStaffForm

    def get_success_url(self):
        return reverse('home')

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ComplianceStaff, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)

        action = self.kwargs['action']
        submitted_by = SystemUser.objects.get(ledger_id=self.object.submitted_by)
        if action == 'approve':
             self.object.status = 4
             self.object.assessed_by = self.request.user.id
             self.object.assessed_date = date.today()
             self.object.assignee = None
             messages.success(self.request, "Compliance has been approved.")
             action = Action(
                  content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
                  action='Compliance has been approved')
             action.save()
             
             emailcontext = {}
             emailcontext['app'] = self.object
             emailcontext['person'] = submitted_by
             emailcontext['body'] = "Your clearance of condition has been approved"
             sendHtmlEmail([submitted_by.email], 'Clearance of condition has been approved', emailcontext, 'clearance-approved.html', None, None, None)

        elif action == 'manager':
             self.object.status = 6
             #self.object.group
             approver = SystemGroup.objects.get(name='Statdev Approver')
             self.object.assignee = None
             self.object.group = approver
             messages.success(self.request, "Compliance has been assigned to the manager group.")
             action = Action(
                  content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
                  action='Compliance assigned to Manager')
             action.save()
 
             emailcontext = {}
             emailcontext['clearance_id'] = self.object.id
             emailGroup('Clearance of Condition Assigned to Manager Group', emailcontext, 'clearance-of-condition-assigned-groups.html', None, None, None, 'Statdev Approver')

        elif action == 'holder':
             self.object.status = 7
             self.object.group = None
             self.object.assignee = None
             messages.success(self.request, "Compliance has been assigned to the holder.") 
             action = Action(
                  content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
                  action='Compliance has been return to holder')
             action.save()

             emailcontext = {}
             emailcontext['app'] = self.object
             emailcontext['person'] = submitted_by
             emailcontext['body'] = "Your clearance of condition requires additional information."
             sendHtmlEmail([submitted_by.email], 'Your clearance of condition requires additional information please login and resubmit with additional information.', emailcontext, 'clearance-holder.html', None, None, None)

        elif action == 'assessor':
             self.object.status = 5
             self.object.group = None
             self.object.assignee = None
             assigngroup = SystemGroup.objects.get(name='Statdev Assessor')
             self.object.group = assigngroup
             messages.success(self.request, "Compliance has been assigned to the assessor.")
             action = Action(
                  content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
                  action='Compliance has been return to holder')
             action.save()

             emailcontext = {}
             emailcontext['clearance_id'] = self.object.id
             emailGroup('Clearance of Condition Assigned to Assessor Group', emailcontext, 'clearance-of-condition-assigned-groups.html', None, None, None, 'Statdev Assessor')

    
        self.object.save()
        # Record an action on the application:
        return HttpResponseRedirect(self.get_success_url())

    def get_initial(self):
        initial = super(ComplianceStaff, self).get_initial()
        app = self.get_object()
        initial['action'] = self.kwargs['action']
        return initial

class ApplicationIssue(LoginRequiredMixin, UpdateView):
    """A view to allow a manager to issue an assessed application.
    """
    model = Application

    def get(self, request, *args, **kwargs):
        # Rule: only the assignee (or a superuser) can perform this action.
        app = self.get_object()
        if app.assignee == request.user.id or request.user.is_superuser:
            return super(ApplicationIssue, self).get(request, *args, **kwargs)
        messages.error(
            self.request, 'You are unable to issue this application!')
        return HttpResponseRedirect(app.get_absolute_url())

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url()+'update/')
        return super(ApplicationIssue, self).post(request, *args, **kwargs)

    def get_form_class(self):
        app = self.get_object()

        if app.app_type == app.APP_TYPE_CHOICES.emergency:
            return apps_forms.ApplicationEmergencyIssueForm
        else:
            return apps_forms.ApplicationIssueForm

    def get_initial(self):
        initial = super(ApplicationIssue, self).get_initial()
        app = self.get_object()

        if app.app_type == app.APP_TYPE_CHOICES.emergency:
            if app.organisation:
                initial['holder'] = app.organisation.name
                initial['abn'] = app.organisation.abn
            elif app.applicant:
                applicant = SystemUser.objects.get(ledger_id=app.applicant)
                initial['holder'] = applicant.legal_first_name + " " + applicant.legal_last_name

        return initial

    def form_valid(self, form):
        self.object = form.save(commit=False)
        d = form.cleaned_data
        if self.request.POST.get('issue') == 'Issue':
            self.object.state = self.object.APP_STATE_CHOICES.current
            self.object.assignee = None
            # Record an action on the application:
            action = Action(
                content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.issue,
                user=self.request.user.id, action='Application issued')
            action.save()
            if self.object.app_type == self.object.APP_TYPE_CHOICES.emergency:
                self.object.issue_date = date.today()

                msg = """<strong>The emergency works has been successfully issued.</strong><br />
                <br />
                <strong>Emergency Works:</strong> \tEW-{0}<br />
                <strong>Date / Time:</strong> \t{1}<br />
                <br />
                <a href="{2}">{3}</a>
                <br />
                """
                if self.object.applicant:
                    msg = msg + """The Emergency Works has been emailed."""
                else:
                    msg = msg + """The Emergency Works needs to be printed and posted."""
                messages.success(self.request, msg.format(self.object.pk, self.object.issue_date.strftime('%d/%m/%Y'),
                                                          self.get_success_url() + "pdf", 'EmergencyWorks.pdf'))
            else:
                messages.success(
                    self.request, 'Application {} has been issued'.format(self.object.pk))
        elif self.request.POST.get('decline') == 'Decline':
            self.object.state = self.object.APP_STATE_CHOICES.declined
            self.object.assignee = None
            # Record an action on the application:
            action = Action(
                content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.decline,
                user=self.request.user.id, action='Application declined')
            action.save()
            messages.warning(
                self.request, 'Application {} has been declined'.format(self.object.pk))
        self.object.save()

        # TODO: logic around emailing/posting the application to the customer.
        return HttpResponseRedirect(self.get_success_url())

class OLDComplianceAssignPerson(LoginRequiredMixin, UpdateView):
    """A view to allow an application applicant to be assigned to a person
    """
    model = Compliance 

    def get(self, request, *args, **kwargs):
        app = self.get_object()
        if app.group is None:
            messages.error(self.request, 'Unable to set Person Assignments as No Group Assignments Set!')
            return HttpResponseRedirect(app.get_absolute_url())
        return super(ApplicationAssignPerson, self).get(request, *args, **kwargs)

    def get_form_class(self):
        # Return the specified form class
        return apps_forms.AssignPersonForm

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(ComplianceAssignPerson, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=True)
        app = self.object
        assignee = SystemUser.objects.get(ledger_id=app.assignee)
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        DefaultGroups = flow.groupList()
        flow.get(workflowtype)
        emailcontext = {'person': assignee}
        emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
        if self.request.user.id != app.assignee:
            sendHtmlEmail([assignee.email], emailcontext['application_name'] + ' application assigned to you ', emailcontext, 'application-assigned-to-person.html', None, None, None)

        # Record an action on the application:
#        action = Action(
#            content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
#            action='Assigned application to {} (status: {})'.format(self.object.assignee.get_full_name(), self.object.get_state_display()))
#        action.save()
        if self.request.user.id != app.assignee:
            return HttpResponseRedirect(reverse('application_list'))
        else:
            return HttpResponseRedirect(self.get_success_url())

    def get_initial(self):
        initial = super(ComplianceAssignPerson, self).get_initial()
        app = self.get_object()
        if app.routeid is None:
            app.routeid = 1
        initial['assigngroup'] = app.group
        return initial
#TODO check this
class ReferralComplete(LoginRequiredMixin, UpdateView):
    """A view to allow a referral to be marked as 'completed'.
    """
    model = Referral
    form_class = apps_forms.ReferralCompleteForm

    def get(self, request, *args, **kwargs):
        app = self.get_object()
        refcount = Referral.objects.filter(application=app,referee=self.request.user.id).count()
        if refcount == 1:
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        # Rule: can't mark a referral completed more than once.
#        if referral.response_date:
        if referral.status != Referral.REFERRAL_STATUS_CHOICES.referred:
            messages.error(self.request, 'This referral is already completed!')
            return HttpResponseRedirect(referral.application.get_absolute_url())
        # Rule: only the referee (or a superuser) can mark a referral
        # "complete".
        if referral.referee == request.use.id or request.user.is_superuser:
            return super(ReferralComplete, self).get(request, *args, **kwargs)
        messages.error(
            self.request, 'You are unable to mark this referral as complete!')
        return HttpResponseRedirect(referral.application.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super(ReferralComplete, self).get_context_data(**kwargs)
        self.template_name = 'applications/referral_complete_form.html'
        context['application'] = self.get_object().application
        return context

    def post(self, request, *args, **kwargs):
        app = self.get_object()
        refcount = Referral.objects.filter(application=app,referee=self.request.user.id).count()
        if refcount == 1:
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().application.get_absolute_url())
        return super(ReferralComplete, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.response_date = date.today()
        self.object.status = Referral.REFERRAL_STATUS_CHOICES.responded
        self.object.save()
        app = self.object.application
        # Record an action on the referral's application:
        #TODO test
        action = Action(
            content_object=app, user=self.request.user.id,
            action='Referral to {} marked as completed'.format(self.object.referee))
        action.save()
        # If there are no further outstanding referrals, then set the
        # application status to "with admin".
#        if not Referral.objects.filter(
#                application=app, status=Referral.REFERRAL_STATUS_CHOICES.referred).exists():
#            app.state = Application.APP_STATE_CHOICES.with_admin
#            app.save()
        refnextaction = Referrals_Next_Action_Check()
        refactionresp = refnextaction.get(app)
        if refactionresp == True:
            app_updated = refnextaction.go_next_action(app)
            # Record an action.
            action = Action(
                content_object=app,
                action='No outstanding referrals, application routed to nextstep "{}"'.format(app_updated.get_state_display()), category=3)
            action.save()

        return HttpResponseRedirect(app.get_absolute_url())


class ReferralRecall(LoginRequiredMixin, UpdateView):
    model = Referral
    form_class = apps_forms.ReferralRecallForm
    template_name = 'applications/referral_recall.html'

    def get(self, request, *args, **kwargs):
        referral = self.get_object()
        context_processor = template_context(self.request)
        app = referral.application


        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == referral.application.app_type:
                  app_type_short_name = i


        flow = Flow()
        flow.get(app_type_short_name)
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)

        if flowcontext["may_recall_resend"] == "True":
            pass
        #admin_staff = context_processor['admin_staff']

        #if admin_staff == True:
        #   pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        # Rule: can't recall a referral that is any other status than
        # 'referred'.
        if referral.status != Referral.REFERRAL_STATUS_CHOICES.referred:
            messages.error(self.request, 'This referral is already completed!')
            return HttpResponseRedirect(referral.application.get_absolute_url())
        return super(ReferralRecall, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ReferralRecall, self).get_context_data(**kwargs)
        context['referral'] = self.get_object()
        return context

    def post(self, request, *args, **kwargs):
        referral = self.get_object()
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']

        app = referral.application

        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == referral.application.app_type:
                  app_type_short_name = i

        flow = Flow()
        flow.get(app_type_short_name)
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)

        if flowcontext["may_recall_resend"] == "True":
            pass
        #if admin_staff == True:
        #   pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().application.get_absolute_url())
        return super(ReferralRecall, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        ref = self.get_object()
        ref.status = Referral.REFERRAL_STATUS_CHOICES.recalled
        ref.save()
        # Record an action on the referral's application:
        action = Action(
            content_object=ref.application, user=self.request.user.id,
            action='Referral to {} recalled'.format(ref.referee), category=3)
        action.save()

        #  check to see if there is any uncompleted/unrecalled referrals
        #  If no more pending referrals than more to next step in workflow
        refnextaction = Referrals_Next_Action_Check()
        refactionresp = refnextaction.get(ref.application)

        if refactionresp == True:
            refnextaction.go_next_action(ref.application)
            action = Action(
                content_object=ref.application, user=self.request.user.id,
                action='All Referrals Completed, Progress to next Workflow Action {} '.format(ref.referee), category=3)
            action.save()

        return HttpResponseRedirect(ref.application.get_absolute_url())


class ReferralResend(LoginRequiredMixin, UpdateView):
    model = Referral
    form_class = apps_forms.ReferralResendForm
    template_name = 'applications/referral_resend.html'

    def get(self, request, *args, **kwargs):
        referral = self.get_object()
        context_processor = template_context(self.request)

        app = referral.application
        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == referral.application.app_type:
                  app_type_short_name = i

        flow = Flow()
        flow.get(app_type_short_name)
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)
        if flowcontext["may_referral_resend"] == "True":
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        if referral.status != Referral.REFERRAL_STATUS_CHOICES.recalled & referral.status != Referral.REFERRAL_STATUS_CHOICES.responded:
            messages.error(self.request, 'This referral is already completed!' + str(referral.status) + str(Referral.REFERRAL_STATUS_CHOICES.responded))
            return HttpResponseRedirect(referral.application.get_absolute_url())
        return super(ReferralResend, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ReferralResend, self).get_context_data(**kwargs)
        context['referral'] = self.get_object()
        return context

    def post(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        referral = self.get_object()
        app = referral.application
        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == referral.application.app_type:
                  app_type_short_name = i

        flow = Flow()
        flow.get(app_type_short_name)
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)
        if flowcontext["may_referral_resend"] == "True":
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")


        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().application.get_absolute_url())
        return super(ReferralResend, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        ref = self.get_object()
        ref.status = Referral.REFERRAL_STATUS_CHOICES.referred
        ref.save()
        # Record an action on the referral's application:
        action = Action(
            content_object=ref.application, user=self.request.user.id,
            action='Referral to {} resend '.format(ref.referee), category=3)
        action.save()

        return HttpResponseRedirect(ref.application.get_absolute_url())


class ReferralSend(LoginRequiredMixin, UpdateView):
    model = Referral
    form_class = apps_forms.ReferralResendForm
    template_name = 'applications/referral_resend.html'

    def get(self, request, *args, **kwargs):
        referral = self.get_object()
        context_processor = template_context(self.request)

        app = referral.application
        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == referral.application.app_type:
                  app_type_short_name = i

        flow = Flow()
        flow.get(app_type_short_name)
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)
        if flowcontext["may_referral_resend"] == "True":
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        if referral.status != Referral.REFERRAL_STATUS_CHOICES.with_admin:
            messages.error(self.request, 'This referral is already sent for referral!' + str(referral.status) + str(Referral.REFERRAL_STATUS_CHOICES.responded))
            return HttpResponseRedirect(referral.application.get_absolute_url())
        return super(ReferralSend, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ReferralSend, self).get_context_data(**kwargs)
        context['referral'] = self.get_object()
        return context

    def get_success_url(self, application_id):
        return reverse('application_refer', args=(application_id,))

    def post(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        referral = self.get_object()
        app = referral.application
        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == referral.application.app_type:
                  app_type_short_name = i

        flow = Flow()
        flow.get(app_type_short_name)
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)
        if flowcontext["may_referral_resend"] == "True":
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")


        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().application.get_absolute_url())
        return super(ReferralSend, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        ref = self.get_object()
        ref.status = Referral.REFERRAL_STATUS_CHOICES.referred
        if ref.sent_date is None:
            ref.sent_date = date.today()
            ref.expire_date = ref.sent_date + timedelta(days=ref.period)
        ref.save()
        referee = SystemUser.objects.get(ledger_id=ref.referee)
        emailcontext = {}
        emailcontext['person'] = referee
        emailcontext['application_id'] = ref.application.id
        emailcontext['application_name'] = Application.APP_TYPE_CHOICES[ref.application.app_type]
        sendHtmlEmail([referee.email], 'Application for Feedback', emailcontext, 'application-assigned-to-referee.html', None, None, None)
        
        # Record an action on the referral's application:
        action = Action(
            content_object=ref.application, user=self.request.user.id,
            action='Referral to {} sent '.format(ref.referee), category=3)
        action.save()

        return HttpResponseRedirect(ref.application.get_absolute_url())

class ReferralRemind(LoginRequiredMixin, UpdateView):
    model = Referral
    form_class = apps_forms.ReferralRemindForm
    template_name = 'applications/referral_remind.html'

    def get(self, request, *args, **kwargs):
        referral = self.get_object()

        context_processor = template_context(self.request)
        #admin_staff = context_processor['admin_staff']

        app = referral.application
        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == referral.application.app_type:
                  app_type_short_name = i

        flow = Flow()
        flow.get(app_type_short_name)
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)
        if flowcontext["may_recall_resend"] == "True":
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")


        if referral.status != Referral.REFERRAL_STATUS_CHOICES.referred:
            messages.error(self.request, 'This referral is already completed!')
            return HttpResponseRedirect(referral.application.get_absolute_url())
        return super(ReferralRemind, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ReferralRemind, self).get_context_data(**kwargs)
        context['referral'] = self.get_object()
        return context

    def post(self, request, *args, **kwargs):
        referral = self.get_object()
        context_processor = template_context(self.request)

        app = referral.application
        print ('STEP 1')
        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == referral.application.app_type:
                  app_type_short_name = i

        flow = Flow()
        flow.get(app_type_short_name)
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)

        print ('test')
        print (flowcontext)
        if flowcontext["may_recall_resend"] == "True":
           #admin_staff = context_processor['admin_staff']
           #if admin_staff == True:
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().application.get_absolute_url())
        return super(ReferralRemind, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        ref = self.get_object()
        referee = SystemUser.objects.get(ledger_id=ref.referee)
        emailcontext = {}
        emailcontext['person'] = referee
        emailcontext['application_id'] = ref.application.id
        emailcontext['application_name'] = Application.APP_TYPE_CHOICES[ref.application.app_type]

        sendHtmlEmail([referee.email], 'Application for Feedback Reminder', emailcontext, 'application-assigned-to-referee.html', None, None, None)

        action = Action(
            content_object=ref.application, user=self.request.user.id,
            action='Referral to {} reminded'.format(ref.referee), category=3)
        action.save()
        return HttpResponseRedirect(self.get_success_url(ref.application.id))
        #ref.application.get_absolute_url())


class ReferralDelete(LoginRequiredMixin, UpdateView):
    model = Referral
    form_class = apps_forms.ReferralDeleteForm
    template_name = 'applications/referral_delete.html'

    def get(self, request, *args, **kwargs):
        referral = self.get_object()
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        app = referral.application

        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == referral.application.app_type:
                  app_type_short_name = i

          
        flow = Flow()
        flow.get(app_type_short_name)
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)
        if flowcontext["may_referral_delete"] == "True":
             return super(ReferralDelete, self).get(request, *args, **kwargs)
        else:
             if admin_staff == True:
                return super(ReferralDelete, self).get(request, *args, **kwargs)
             else:
                messages.error(self.request, 'Forbidden from viewing this page.')
                return HttpResponseRedirect("/")

 #       if referral.status != Referral.REFERRAL_STATUS_CHOICES.with_admin:
 #           messages.error(self.request, 'This referral is already completed!')
 #           return HttpResponseRedirect(referral.application.get_absolute_url())
 #       return super(ReferralDelete, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ReferralDelete, self).get_context_data(**kwargs)
        context['referral'] = self.get_object()
        referee = SystemUser.objects.get(ledger_id=self.get_object().referee)
        context['referee'] = referee
        return context

    def get_success_url(self, application_id):
        return reverse('application_refer', args=(application_id,))

    def post(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        referral = self.get_object()
        app = referral.application
 
        app_type_short_name = None
        for i in Application.APP_TYPE_CHOICES._identifier_map:
             if Application.APP_TYPE_CHOICES._identifier_map[i] == referral.application.app_type:
                  app_type_short_name = i

        flow = Flow()
        flow.get(app_type_short_name)
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, app_type_short_name)

        if flowcontext["may_referral_delete"] == "True":
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")

        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().application.get_absolute_url())
        return super(ReferralDelete, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        ref = self.get_object()
        application_id = ref.application.id
        ref.delete()
        # Record an action on the referral's application:
        action = Action(
            content_object=ref.application, user=self.request.user.id,
            action='Referral to {} delete'.format(ref.referee), category=3)
        action.save()
        return HttpResponseRedirect(self.get_success_url(application_id))


#class ComplianceList(ListView):
#    model = Compliance
#
#    def get_queryset(self):
#        qs = super(ComplianceList, self).get_queryset()
#        # Did we pass in a search string? If so, filter the queryset and return
#        # it.
#        if 'q' in self.request.GET and self.request.GET['q']:
#            query_str = self.request.GET['q']
#            # Replace single-quotes with double-quotes
#            query_str = query_str.replace("'", r'"')
#            # Filter by applicant__email, assignee__email, compliance
#            query = get_query(
#                query_str, ['applicant__email', 'assignee__email', 'compliance'])
#            qs = qs.filter(query).distinct()
#        return qs

class ComplianceCompleteExternal(LoginRequiredMixin,UpdateView):
    model = Compliance
    template_name = 'applications/compliance_update_external.html'
    form_class = apps_forms.ComplianceCompleteExternal


    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        org = Delegate.objects.filter(email_user=self.request.user.id, organisation=self.object.organisation).count()
        assessor = SystemGroup.objects.get(name='Statdev Assessor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        if admin_staff == True:
           pass
        elif assessor.id in usergroups:
           pass
        elif self.request.user.id == self.object.applicant:
           pass
        elif org == 1:
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        if self.object.status != 2 and self.object.status != 8 and self.object.status != 7:
           if self.object.status == 3: 
                 messages.error(self.request, 'The clearance of condition is not due yet.')
           else:
               messages.error(self.request, 'Unable to complete clearance of condition.')
           return HttpResponseRedirect(reverse("home_page_tabs", args=('clearance',)))
 
        return super(ComplianceCompleteExternal, self).get(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(ComplianceCompleteExternal, self).get_context_data(**kwargs)
        app = self.get_object()
        context['conditions'] = Compliance.objects.filter(id=app.id)
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
           compliance = Compliance.objects.get(id=kwargs['pk'])
           return HttpResponseRedirect(reverse("home_page_tabs", args=('clearance',)))
        return super(ComplianceCompleteExternal, self).post(request, *args, **kwargs)

    def get_initial(self):
        initial = super(ComplianceCompleteExternal, self).get_initial()
        multifilelist = []

        #records = self.object.records.all()
        #for b1 in records:
        #    fileitem = {}
        #    fileitem['fileid'] = b1.id
        #    fileitem['path'] = b1.upload.name
        #    fileitem['extension']  = b1.extension
        #    multifilelist.append(fileitem)
        records = self.object.records.all()
        multifilelist = []
        for b1 in records:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['records'] = multifilelist
        return initial

    def form_valid(self, form):
        self.object = form.save(commit=False)

        if 'records_json' in self.request.POST:
             if is_json(self.request.POST['records_json']) is True:
                  json_data = json.loads(self.request.POST['records_json'])
                  self.object.records.remove()
                  for d in self.object.records.all():
                      self.object.records.remove(d)
                  for i in json_data:
                      doc = Record.objects.get(id=i['doc_id'])
                      self.object.records.add(doc)

        self.object.save()
        if self.request.POST.get('save'):
            messages.success(self.request, 'Successfully Saved')
            return HttpResponseRedirect(reverse("compliance_approval_update_external", args=(self.object.id,)))

        group = SystemGroup.objects.get(name='Statdev Assessor')
        self.object.group = group

        self.object.status = 5
        self.object.save()
        return HttpResponseRedirect(reverse("home_page_tabs", args=('clearance',)))

class ComplianceViewExternal(LoginRequiredMixin,DetailView):
    # model = Approval
    model = Compliance
    template_name = 'applications/compliance_view_external.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        org = Delegate.objects.filter(email_user=self.request.user.id, organisation=self.object.organisation).count()
        assessor = SystemGroup.objects.get(name='Statdev Assessor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)

        if admin_staff == True:
           pass
        elif assessor.id in usergroups:
           pass
        elif self.request.user.id == self.object.applicant:
           pass
        elif org == 1:
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ComplianceViewExternal, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ComplianceViewExternal, self).get_context_data(**kwargs)
        app = self.get_object()
        # context['conditions'] = Compliance.objects.filter(approval_id=app.id)
        context['conditions'] = Compliance.objects.filter(id=app.id)
        return context

class ComplianceApprovalInternal(LoginRequiredMixin,UpdateView):
    model = Compliance
    template_name = 'applications/compliance_update_internal.html'
    form_class = apps_forms.ComplianceCompleteInternal

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        org = Delegate.objects.filter(email_user=self.request.user.id, organisation=self.object.organisation).count()
        assessor = SystemGroup.objects.get(name='Statdev Assessor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        if admin_staff == True:
           pass
        elif assessor.id in usergroups:
           pass
        elif self.request.user.id == self.object.applicant:
           pass
        elif org == 1:
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ComplianceApprovalInternal, self).get(request, *args, **kwargs)

    def get_initial(self):
        initial = super(ComplianceApprovalInternal, self).get_initial()
        multifilelist = []

        initial['status'] = self.object.status
        print ("STATUS")
        print (initial['status'])

        external_documents = self.object.external_documents.all()
        print ("EXTERNAL DOC")
        print (external_documents)
        multifilelist = []
        for b1 in external_documents:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['external_documents'] = multifilelist
        
        return initial

    def get_context_data(self, **kwargs):
        context = super(ComplianceApprovalInternal, self).get_context_data(**kwargs)
        app = self.get_object()
        # context['conditions'] = Compliance.objects.filter(approval_id=app.id)
        context['conditions'] = Compliance.objects.filter(id=app.id)
        
        if app.applicant is not None:
            context['applicant'] = SystemUser.objects.get(ledger_id=app.applicant)
        
        if app.assignee is not None:
            context['assignee'] = SystemUser.objects.get(ledger_id=app.assignee)
        
        if app.submitted_by is not None:
            context['submitted_by'] = SystemUser.objects.get(ledger_id=app.submitted_by) 
        
        if app.assessed_by is not None:
            context['assessed_by'] = SystemUser.objects.get(ledger_id=app.assessed_by) 
        
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
           return HttpResponseRedirect(reverse("compliance_list",))
        return super(ComplianceApprovalInternal, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        submitted_by = SystemUser.objects.get(ledger_id=self.object.submitted_by)
        action = self.request.POST.get('action')
        external_comments = self.request.POST.get('external_comments','')
        internal_comments = self.request.POST.get('internal_comments','')
        internal_documents = self.request.POST.get('internal_documents')

        if action == '1':
             self.object.status = 4
             self.object.assessed_by = self.request.user.id
             self.object.assessed_date = date.today()
             self.object.assignee = None
             messages.success(self.request, "Compliance has been approved.")
             action = Action(
                  content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
                  action='Compliance has been approved')
             action.save()

             if len(internal_comments) > 0:
                 approval = Approval.objects.get(id=self.object.approval_id)
                 comms = CommunicationApproval.objects.create(approval=approval,comms_type=4,comms_to=str('Approved'), comms_from='', subject='internal comment', details=internal_comments)
                 if 'internal_documents_json' in self.request.POST:
                      if is_json(self.request.POST['internal_documents_json']) is True:
                           json_data = json.loads(self.request.POST['internal_documents_json'])
                           for i in json_data:
                               doc = Record.objects.get(id=i['doc_id'])
                               comms.records.add(doc)
                 comms.save()



             emailcontext = {}
             emailcontext['app'] = self.object
             emailcontext['person'] = submitted_by
             emailcontext['body'] = "Your clearance of condition has been approved"
             sendHtmlEmail([submitted_by.email], 'Clearance of condition has been approved', emailcontext, 'clearance-approved.html', None, None, None)

        elif action == '2':
             self.object.status = 6
             #self.object.group
             approver = SystemGroup.objects.get(name='Statdev Approver')
             self.object.assignee = None
             self.object.group = approver
             messages.success(self.request, "Compliance has been assigned to the manager group.")

             action = Action(
                  content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
                  action='Compliance assigned to Manager')
             action.save()

             if len(internal_comments) > 0:
                 approval = Approval.objects.get(id=self.object.approval_id)
                 comms = CommunicationApproval.objects.create(approval=approval,comms_type=4,comms_to=str('Sent to Manager'), comms_from='', subject='internal comment', details=internal_comments)
                 if 'internal_documents_json' in self.request.POST:
                      if is_json(self.request.POST['internal_documents_json']) is True:
                           json_data = json.loads(self.request.POST['internal_documents_json'])
                           for i in json_data:
                               doc = Record.objects.get(id=i['doc_id'])
                               comms.records.add(doc)

                 comms.save()


             emailcontext = {}
             emailcontext['clearance_id'] = self.object.id
             emailGroup('Clearance of Condition Assigned to Manager Group', emailcontext, 'clearance-of-condition-assigned-groups.html', None, None, None, 'Statdev Approver')

        elif action == '3':
             self.object.status = 7
             self.object.group = None
             self.object.assignee = None
             messages.success(self.request, "Compliance has been assigned to the holder.")

             action = Action(
                  content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
                  action='Compliance has been return to holder')
             action.save()

             if len(external_comments) > 0:
                 approval = Approval.objects.get(id=self.object.approval_id)
                 comms = CommunicationApproval.objects.create(approval=approval,comms_type=4,comms_to=str('Return to licence holder'), comms_from='', subject='external comment', details=external_comments)
                 comms.save()

             if len(internal_comments) > 0:
                 approval = Approval.objects.get(id=self.object.approval_id)
                 comms = CommunicationApproval.objects.create(approval=approval,comms_type=4,comms_to=str('Sent to Manager'), comms_from='', subject='internal comment', details=internal_comments)
                 if 'internal_documents_json' in self.request.POST:
                      if is_json(self.request.POST['internal_documents_json']) is True:
                           json_data = json.loads(self.request.POST['internal_documents_json'])
                           for i in json_data:
                               doc = Record.objects.get(id=i['doc_id'])

                               comms.records.add(doc)

                 comms.save()


             emailcontext = {}
             emailcontext['app'] = self.object
             emailcontext['person'] = submitted_by
             emailcontext['body'] = "Your clearance of condition requires additional information."
             sendHtmlEmail([submitted_by.email], 'Your clearance of condition requires additional information please login and resubmit with additional information.', emailcontext, 'clearance-holder.html', None, None, None)


        elif action == '4':
             self.object.status = 5
             self.object.group = None
             self.object.assignee = None
             assigngroup = SystemGroup.objects.get(name='Statdev Assessor')
             self.object.group = assigngroup
             messages.success(self.request, "Compliance has been assigned to the assessor.")
             action = Action(
                  content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.assign, user=self.request.user.id,
                  action='Compliance has been returned to assessor')
             action.save()

             if len(internal_comments) > 0:
                 approval = Approval.objects.get(id=self.object.approval_id)
                 comms = CommunicationApproval.objects.create(approval=approval,comms_type=4,comms_to=str('Return to assessor'), comms_from='', subject='internal comment', details=internal_comments)
                 if 'internal_documents_json' in self.request.POST:
                      if is_json(self.request.POST['internal_documents_json']) is True:
                           json_data = json.loads(self.request.POST['internal_documents_json'])
                           for i in json_data:
                               doc = Record.objects.get(id=i['doc_id'])
                               comms.records.add(doc)

                 comms.save()

             emailcontext = {}
             emailcontext['clearance_id'] = self.object.id
             emailGroup('Clearance of condition assigned to Assessor Group', emailcontext, 'clearance-of-condition-assigned-groups.html', None, None, None, 'Statdev Assessor')
        else: 
            raise ValidationError("ERROR,  no action found: "+str(action))

        
        if 'external_documents_json' in self.request.POST:
             if is_json(self.request.POST['external_documents_json']) is True:
                  json_data = json.loads(self.request.POST['external_documents_json'])
                  self.object.external_documents.remove()
                  for d in self.object.external_documents.all():
                      self.object.external_documents.remove(d)
                  for i in json_data:
                      doc = Record.objects.get(id=i['doc_id'])
                      doc.file_group = 2006
                      doc.save()
                      self.object.external_documents.add(doc)

        self.object.save()
        return HttpResponseRedirect(reverse("compliance_list",))






class ComplianceApprovalDetails(LoginRequiredMixin,DetailView):
    # model = Approval
    model = Compliance
    template_name = 'applications/compliance_detail.html' 

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        org = Delegate.objects.filter(email_user=self.request.user.id, organisation=self.object.organisation).count()
        assessor = SystemGroup.objects.get(name='Statdev Assessor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        if admin_staff == True:
           pass
        elif assessor.id in usergroups:
           pass
        elif self.request.user.id == self.object.applicant:
           pass
        elif org == 1: 
           pass
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ComplianceApprovalDetails, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ComplianceApprovalDetails, self).get_context_data(**kwargs)
        app = self.get_object()
        # context['conditions'] = Compliance.objects.filter(approval_id=app.id)
        
        if app.applicant is not None:
            context['applicant'] = SystemUser.objects.get(ledger_id=app.applicant)
        
        if app.assignee is not None:
            context['assignee'] = SystemUser.objects.get(ledger_id=app.assignee)
        
        if app.submitted_by is not None:
            context['submitted_by'] = SystemUser.objects.get(ledger_id=app.submitted_by) 
        
        if app.assessed_by is not None:
            context['assessed_by'] = SystemUser.objects.get(ledger_id=app.assessed_by) 
        
        context['conditions'] = Compliance.objects.filter(id=app.id)
        return context

class ComplianceSubmitComplete(LoginRequiredMixin,DetailView):
#   model = Approval
    model = Compliance
    template_name = 'applications/compliance_complete.html'

    def get_context_data(self, **kwargs):
        context = super(ComplianceSubmitComplete, self).get_context_data(**kwargs)
        app = self.get_object()
        # context['conditions'] = Compliance.objects.filter(approval_id=app.id)
        context['conditions'] = Compliance.objects.filter(id=app.id)
        return context

class ComplianceComplete(LoginRequiredMixin,UpdateView):
    model = Compliance
    template_name = 'applications/compliance_update.html'
    form_class = apps_forms.ComplianceComplete

    def get_context_data(self, **kwargs):
        context = super(ComplianceComplete, self).get_context_data(**kwargs)
        app = self.get_object()
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
           compliance = Compliance.objects.get(id=kwargs['pk'])
           return HttpResponseRedirect(reverse("compliance_approval_detail", args=(compliance.approval_id,)))
        return super(ComplianceComplete, self).post(request, *args, **kwargs)

    def get_initial(self):
        initial = super(ComplianceComplete, self).get_initial()
        multifilelist = []

        records = self.object.records.all()
        for b1 in records:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['records'] = multifilelist
        return initial

    def form_valid(self, form):
        self.object = form.save(commit=False)

        if 'records_json' in self.request.POST:
             if is_json(self.request.POST['records_json']) is True:
                  json_data = json.loads(self.request.POST['records_json'])
                  self.object.records.remove()
                  for d in self.object.records.all():
                      self.object.records.remove(d)
                  for i in json_data:
                      doc = Record.objects.get(id=i['doc_id'])
                      self.object.records.add(doc)


        #for filelist in self.object.records.all():
        #     if 'records-clear_multifileid-' + str(filelist.id) in form.data:
        #           self.object.records.remove(filelist)

        #if self.request.FILES.get('records'):

        #    if Attachment_Extension_Check('multi', self.request.FILES.getlist('records'), None) is False:
        #        raise ValidationError('Documents contains and unallowed attachment extension.')

        #    for f in self.request.FILES.getlist('records'):
        #        doc = Record()
        #        doc.upload = f
        #        doc.name = f.name
        #        # print f.name
        #        doc.save()
        #        self.object.records.add(doc)
        #        # print self.object.records
        self.object.save()
        #form.save()
        #form.save_m2m()
        return HttpResponseRedirect(reverse("compliance_approval_detail", args=(self.object.id,)))

# this is theory shoudl be able to be deleted.  need to chekc first.
class ComplianceCreate(LoginRequiredMixin, ModelFormSetView):
    model = Compliance
    form_class = apps_forms.ComplianceCreateForm
    template_name = 'applications/compliance_formset.html'
    fields = ['condition', 'compliance']

    def get_application(self):
        return Application.objects.get(pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super(ComplianceCreate, self).get_context_data(**kwargs)
        app = self.get_application()
        context['application'] = app
        return context

    def get_initial(self):
        # Return a list of dicts, each containing a reference to one condition.
        app = self.get_application()
        conditions = app.condition_set.all()
        return [{'condition': c} for c in conditions]

    def get_factory_kwargs(self):
        kwargs = super(ComplianceCreate, self).get_factory_kwargs()
        app = self.get_application()
        conditions = app.condition_set.all()
        # Set the number of forms in the set to equal the number of conditions.
        kwargs['extra'] = len(conditions)
        return kwargs

    def get_extra_form_kwargs(self):
        kwargs = super(ComplianceCreate, self).get_extra_form_kwargs()
        kwargs['application'] = self.get_application()
        return kwargs

    def formset_valid(self, formset):
        for form in formset:
            data = form.cleaned_data
            # If text has been input to the compliance field, create a new
            # compliance object.
            if 'compliance' in data and data.get('compliance', None):
                new_comp = form.save(commit=False)
                new_comp.applicant = self.request.user.id
                new_comp.application = self.get_application()
                new_comp.submit_date = date.today()
                # TODO: handle the uploaded file.
                new_comp.save()
                # Record an action on the compliance request's application:
                action = Action(
                    content_object=new_comp.application, user=self.request.user.id,
                    action='Request for compliance created')
                action.save()
        messages.success(
            self.request, 'New requests for compliance have been submitted.')
        return super(ComplianceCreate, self).formset_valid(formset)

    def get_success_url(self):
        return reverse('application_detail', args=(self.get_application().pk,))


class WebPublish(LoginRequiredMixin, UpdateView):
    model = Application
    form_class = apps_forms.ApplicationWebPublishForm
    template_name = "applications/application_publish_form.html"
        
    def get(self, request, *args, **kwargs):
        app = Application.objects.get(pk=self.kwargs['pk'])
        return super(WebPublish, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('application_update', args=(self.kwargs['pk'],))

    def get_context_data(self, **kwargs):
        context = super(WebPublish,
                        self).get_context_data(**kwargs)
        context['application'] = Application.objects.get(pk=self.kwargs['pk'])
        #context['file_group'] =  '2003'
        #context['file_group_ref_id'] = self.kwargs['pk']

        return context

    def get_initial(self):
        initial = super(WebPublish, self).get_initial()
        initial['application'] = self.kwargs['pk']

        current_date = datetime.now().strftime('%d/%m/%Y')

        publish_type = self.kwargs['publish_type']
        if publish_type in 'received':
            initial['publish_documents'] = current_date
        elif publish_type in 'draft':
            initial['publish_draft_report'] = current_date
        elif publish_type in 'final':
            initial['publish_final_report'] = current_date
        elif publish_type in 'determination':
            initial['publish_determination_report'] = current_date

        initial['publish_type'] = self.kwargs['publish_type']
        # try:
        #    pub_news = PublicationNewspaper.objects.get(
        #    application=self.kwargs['pk'])
        # except:
        #    pub_news = None
        return initial

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = Application.objects.get(pk=self.kwargs['pk'])
            return HttpResponseRedirect(app.get_absolute_url())
        return super(WebPublish, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        forms_data = form.cleaned_data
        self.object = form.save(commit=True)
        publish_type = self.kwargs['publish_type']

        current_date = datetime.now().strftime('%Y-%m-%d')

        if publish_type in 'received':
            self.object.publish_documents = current_date
           
            action = Action(
               content_object=self.object, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.publish,
               action='Application Publish (Received) expiring ('+self.object.publish_documents_expiry.strftime('%m/%d/%Y %H:%M')+')')
            action.save()

        elif publish_type in 'draft':
            action = Action(
               content_object=self.object, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.publish,
               action='Application Published (Draft) expiring ('+self.object.publish_draft_expiry.strftime('%m/%d/%Y %H:%M')+')')
            action.save()  

            self.object.publish_draft_report = current_date
        elif publish_type in 'final': 
            action = Action(
               content_object=self.object, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.publish,
               action='Application Published (Final) expiring ('+self.object.publish_final_expiry.strftime('%m/%d/%Y %H:%M')+')')
            action.save()
            self.object.publish_final_report = current_date
        elif publish_type in 'determination':
            action = Action(
               content_object=self.object, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.publish,
               action='Application Published (Determination)')
            action.save()
            self.object.publish_determination_report = current_date

        return super(WebPublish, self).form_valid(form)


class NewsPaperPublicationCreate(LoginRequiredMixin, CreateView):
    model = PublicationNewspaper
    form_class = apps_forms.NewsPaperPublicationCreateForm

    def get(self, request, *args, **kwargs):
        app = Application.objects.get(pk=self.kwargs['pk'])
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)


#       if flowcontext.state != app.APP_STATE_CHOICES.draft:
        if flowcontext["may_update_publication_newspaper"] != "True":
                    messages.error(
                          self.request, "Can't add new newspaper publication to this application")
                    return HttpResponseRedirect(app.get_absolute_url())
        return super(NewsPaperPublicationCreate, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('application_detail', args=(self.kwargs['pk'],))

    def get_context_data(self, **kwargs):
        context = super(NewsPaperPublicationCreate,
                       self).get_context_data(**kwargs)
        context['application'] = Application.objects.get(pk=self.kwargs['pk'])
        return context

    def get_initial(self):
        initial = super(NewsPaperPublicationCreate, self).get_initial()
        initial['application'] = self.kwargs['pk']

           # try:
                #    pub_news = PublicationNewspaper.objects.get(
                #    application=self.kwargs['pk'])
                # except:
                #    pub_news = None
        return initial

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = Application.objects.get(pk=self.kwargs['pk'])
            return HttpResponseRedirect(app.get_absolute_url())    
    
        return super(NewsPaperPublicationCreate, self).post(request, *args, **kwargs)
    def form_valid(self, form):
        forms_data = form.cleaned_data
        self.object = form.save(commit=True)
        #if self.request.FILES.get('records'):
        #    for f in self.request.FILES.getlist('records'):
        #        doc = Record()
        #        doc.upload = f
        #        doc.save()
        #        self.object.records.add(doc)

        if 'records_json' in self.request.POST:
             if is_json(self.request.POST['records_json']) is True:
                json_data = json.loads(self.request.POST['records_json'])
                self.object.records.remove()
                for d in self.object.records.all():
                    self.object.records.remove(d)
                for i in json_data:
                    doc = Record.objects.get(id=i['doc_id'])
                    self.object.records.add(doc)



        action = Action(
            content_object=self.object.application, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.create,
            action='Newspaper Publication ({} {}) '.format(self.object.newspaper, self.object.date) )
        action.save()

        return super(NewsPaperPublicationCreate, self).form_valid(form)


class NewsPaperPublicationUpdate(LoginRequiredMixin, UpdateView):
    model = PublicationNewspaper
    form_class = apps_forms.NewsPaperPublicationCreateForm

    def get(self, request, *args, **kwargs):
        #app = self.get_object().application_set.first()

        PubNew = PublicationNewspaper.objects.get(pk=self.kwargs['pk'])
        app = Application.objects.get(pk=PubNew.application.id)
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)

        if flowcontext["may_update_publication_newspaper"] != "True":
            messages.error(self.request, "Can't update newspaper publication to this application")
            return HttpResponseRedirect(app.get_absolute_url())
        # Rule: can only change a vessel if the parent application is status
        # 'draft'.
            # if app.state != Application.APP_STATE_CHOICES.draft:
            #    messages.error(
            #        self.request, 'You can only change a publication details when the application is "draft" status')
#        return HttpResponseRedirect(app.get_absolute_url())
        return super(NewsPaperPublicationUpdate, self).get(request, *args, **kwargs)

    def get_initial(self):
        initial = super(NewsPaperPublicationUpdate, self).get_initial()
#       initial['application'] = self.kwargs['pk']
        pub_news = None
        try:
            pub_news = PublicationNewspaper.objects.get(pk=self.kwargs['pk'])
        except:
            pub_news = None
        
        multifilelist = []
        a1 = pub_news.records.all() 
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['records'] = multifilelist
        
        return initial

    def get_context_data(self, **kwargs):
        context = super(NewsPaperPublicationUpdate, self).get_context_data(**kwargs)
        context['page_heading'] = '' #'Update Newspaper Publication details'
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
 #           print self.get_object().application.pk
#            app = self.get_object().application_set.first()
            return HttpResponseRedirect(reverse('application_detail', args=(self.get_object().application.pk,)))
        return super(NewsPaperPublicationUpdate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        app = Application.objects.get(pk=self.object.application.id)

        pub_news = PublicationNewspaper.objects.get(pk=self.kwargs['pk'])

        records = pub_news.records.all()
        for filelist in records:
            if 'records-clear_multifileid-' + str(filelist.id) in form.data:
                 pub_news.records.remove(filelist)

        #if self.request.FILES.get('records'):
        #    for f in self.request.FILES.getlist('records'):
        #        doc = Record()
        #        doc.upload = f
        #        doc.save()
        #        self.object.records.add(doc)


        if 'records_json' in self.request.POST:
             json_data = json.loads(self.request.POST['records_json'])
             self.object.records.remove()
             for d in self.object.records.all():
                 self.object.records.remove(d)
             for i in json_data:
                 doc = Record.objects.get(id=i['doc_id'])
                 self.object.records.add(doc)


        action = Action(
            content_object=self.object.application, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.change,
            action='Newspaper Publication ({} {}) '.format(self.object.newspaper, self.object.date) )
        action.save()


        return HttpResponseRedirect(app.get_absolute_url())


class NewsPaperPublicationDelete(LoginRequiredMixin, DeleteView):
    model = PublicationNewspaper

    def get(self, request, *args, **kwargs):
        modelobject = self.get_object()
        PubNew = PublicationNewspaper.objects.get(pk=self.kwargs['pk'])
        app = Application.objects.get(pk=PubNew.application.id)
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)
        if flowcontext["may_update_publication_newspaper"] != "True":
            messages.error(self.request, "Can't delete newspaper publication to this application")
            return HttpResponseRedirect(app.get_absolute_url())
            # Rule: can only delete a condition if the parent application is status
        return super(NewsPaperPublicationDelete, self).get(request, *args, **kwargs)
        #    else:
        #       messages.warning(self.request, 'You cannot delete this condition')
        #      return HttpResponseRedirect(condition.application.get_absolute_url())
    def get_success_url(self):
        return reverse('application_detail', args=(self.get_object().application.pk,))

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
           return HttpResponseRedirect(self.get_success_url())
        # Generate an action.
        modelobject = self.get_object()
        action = Action(
            content_object=modelobject.application, user=self.request.user.id,
            action='Delete Newspaper Publication {} deleted (status: {})'.format(modelobject.pk, 'delete'))
        action.save()
        messages.success(self.request, 'Newspaper Publication {} has been deleted'.format(modelobject.pk))
        return super(NewsPaperPublicationDelete, self).post(request, *args, **kwargs)

class WebsitePublicationChange(LoginRequiredMixin, CreateView):
    model = PublicationWebsite
    form_class = apps_forms.WebsitePublicationForm

    def get(self, request, *args, **kwargs):
        app = Application.objects.get(pk=self.kwargs['pk'])
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)

        if flowcontext["may_update_publication_website"] != "True":
            messages.error(self.request, "Can't update ebsite publication to this application")
            return HttpResponseRedirect(app.get_absolute_url())
        return super(WebsitePublicationChange, self).get(request, *args, **kwargs)
    def get_success_url(self):
        return reverse('application_detail', args=(self.kwargs['pk'],))

        #    def get_success_url(self):
        #        print self.kwargs['pk']
        #        return reverse('application_detail', args=(self.get_object().application.pk,))
        #        return reverse('application_detail', args=(self.kwargs['pk']))

    def get_context_data(self, **kwargs):
        context = super(WebsitePublicationChange,self).get_context_data(**kwargs)
        context['application'] = Application.objects.get(pk=self.kwargs['pk'])
        return context

    def get_initial(self):
        initial = super(WebsitePublicationChange, self).get_initial()
        initial['application'] = self.kwargs['pk']
        #        doc = Record.objects.get(pk=self.kwargs['docid'])
        #        print self.kwargs['docid']      
        #        print PublicationWebsite.objects.get(original_document_id=self.kwargs['docid']) 
        try:
            pub_web = PublicationWebsite.objects.get(original_document_id=self.kwargs['docid'])
        except:
            pub_web = None
        if pub_web:
                initial['published_document'] = pub_web.published_document


                #filelist = [] 
                #if pub_web: 
                #    if pub_web.published_document:
                #        # records = pub_news.records.all()
                #        fileitem = {} 
                #        fileitem['fileid'] = pub_web.published_document.id
                #        fileitem['path'] = pub_web.published_document.upload.name
                #        fileitem['name'] = pub_web.published_document.name
                #        fileitem['short_name'] = pub_web.published_document.upload.name[19:]  
                #        filelist.append(fileitem)

                #if pub_web:
                #    if pub_web.id:
                #        initial['id'] = pub_web.id
                #        print "hello"

                #initial['published_document'] = filelist
                #doc = Record.objects.get(pk=self.kwargs['docid'])
                #initial['original_document'] = doc
        return initial

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = Application.objects.get(pk=self.kwargs['pk'])
            return HttpResponseRedirect(app.get_absolute_url())
        return super(WebsitePublicationChange, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        forms_data = form.cleaned_data
        self.object = form.save(commit=False)
        pub_web = None
#        print "THE"
        try:
            pub_web = PublicationWebsite.objects.get(original_document_id=self.kwargs['docid'])
        except:
            pub_web = None

        #        if pub_web:
        #            self.object.id = pub_web.id
        #            self.object.published_document = pub_web.published_document

        #            if pub_web.published_document:
        #                if 'published_document-clear_multifileid-' + str(pub_web.published_document.id) in self.request.POST:
        #                    self.object.published_document = None


        orig_doc = Record.objects.get(id=self.kwargs['docid'])
        self.object.original_document = orig_doc
        # print "SSS"
        # print self.request.FILES.get('published_document')
        # print self.request.POST
        if 'published_document_json' in self.request.POST:
            if is_json(self.request.POST['published_document_json']) is True: 
                  json_data = json.loads(self.request.POST['published_document_json'])
                  if 'doc_id' in json_data:
                      try:
                          pub_obj = PublicationWebsite.objects.get(original_document_id=self.kwargs['docid'])                 
                          pub_obj.delete()
                      except: 
                          pass
   
                      new_doc = Record.objects.get(id=json_data['doc_id'])
                      self.object.published_document = new_doc
                  else:
                      pub_obj = PublicationWebsite.objects.get(original_document_id=self.kwargs['docid'])
                      pub_obj.delete()


#             else:
 #                self.object.remove()

     # print json_data
     # self.object.published_document.remove()
    # for d in self.object.published_document.all():
     #    self.object.published_document.remove(d)
     # for i in json_data:
     #    doc = Record.objects.get(id=i['doc_id'])
#             self.object.published_document = i['doc_id']
#             self.object.save()
#        if self.request.FILES.get('published_document'):
#            for f in self.request.FILES.getlist('published_document'):
 #               doc = Record()
  #              doc.upload = f
   #             doc.save()
    #            self.object.published_document = doc
        app = Application.objects.get(pk=self.kwargs['pk'])
        action = Action(
              content_object=app, user=self.request.user.id, category=Action.ACTION_CATEGORY_CHOICES.change,
        action='Publish New Web Documents for Doc ID: {}'.format(self.kwargs['docid']))
        action.save()
        return super(WebsitePublicationChange, self).form_valid(form)

class FeedbackPublicationCreate(LoginRequiredMixin, CreateView):
    model = PublicationFeedback
    form_class = apps_forms.FeedbackPublicationCreateForm

    def get(self, request, *args, **kwargs):
        app = Application.objects.get(pk=self.kwargs['pk'])
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)
        if flowcontext["may_update_publication_feedback_review"] == "True":
           return super(FeedbackPublicationCreate, self).get(request, *args, **kwargs)
        elif flowcontext["may_update_publication_feedback_draft"] == "True":
           return super(FeedbackPublicationCreate, self).get(request, *args, **kwargs)
        elif flowcontext["may_update_publication_feedback_final"] == "True":
           return super(FeedbackPublicationCreate, self).get(request, *args, **kwargs)
        elif flowcontext["may_update_publication_feedback_determination"] == "True":
           return super(FeedbackPublicationCreate, self).get(request, *args, **kwargs)
        else:
             messages.error(
                 self.request, "Can't add new newspaper publication to this application")
             return HttpResponseRedirect(app.get_absolute_url())

#        if app.state != app.APP_STATE_CHOICES.draft:
 #           messages.errror(
  #              self.request, "Can't add new feedback publication to this application")
   #         return HttpResponseRedirect(app.get_absolute_url())
#        return super(FeedbackPublicationCreate, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('application_detail', args=(self.kwargs['pk'],))

    def get_context_data(self, **kwargs):
        context = super(FeedbackPublicationCreate,
                        self).get_context_data(**kwargs)
        context['application'] = Application.objects.get(pk=self.kwargs['pk'])
        return context

    def get_initial(self):
        initial = super(FeedbackPublicationCreate, self).get_initial()
        initial['application'] = self.kwargs['pk']

        if self.kwargs['status'] == 'review':
            initial['status'] = 'review'
        elif self.kwargs['status'] == 'final':
            initial['status'] = 'final'
        elif self.kwargs['status'] == 'determination':
            initial['status'] = 'determination'
        else:
            initial['status'] = 'draft'
        return initial

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = Application.objects.get(pk=self.kwargs['pk'])
            return HttpResponseRedirect(app.get_absolute_url())
        return super(FeedbackPublicationCreate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=True)
#       print self.object.records

        if 'records_json' in self.request.POST:
             if is_json(self.request.POST['records_json']) is True:
                  json_data = json.loads(self.request.POST['records_json'])
                  self.object.records.remove()
                  for d in self.object.records.all():
                      self.object.records.remove(d)
                  for i in json_data:
                      doc = Record.objects.get(id=i['doc_id'])
                      self.object.records.add(doc)

        #if self.request.FILES.get('records'):
        #    for f in self.request.FILES.getlist('records'):
        #        doc = Record()
        #        doc.upload = f
        #        doc.save()
        #        self.object.records.add(doc)

        return super(FeedbackPublicationCreate, self).form_valid(form)

class FeedbackPublicationView(LoginRequiredMixin, DetailView):
    model = PublicationFeedback
    template_name = 'applications/application_feedback_view.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden Access.')
           return HttpResponseRedirect("/")
        return super(FeedbackPublicationView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('application_detail', args=(self.kwargs['application'],))

    def get_context_data(self, **kwargs):
        context = super(FeedbackPublicationView,
                        self).get_context_data(**kwargs)
        context['application'] = Application.objects.get(pk=self.kwargs['application'])
        return context

class FeedbackPublicationUpdate(LoginRequiredMixin, UpdateView):
    model = PublicationFeedback
    form_class = apps_forms.FeedbackPublicationCreateForm

    def get(self, request, *args, **kwargs):
        modelobject = self.get_object()
        app = modelobject.application

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)
        if flowcontext["may_update_publication_feedback_review"] == "True":
           return super(FeedbackPublicationUpdate, self).get(request, *args, **kwargs) 
        elif flowcontext["may_update_publication_feedback_draft"] == "True":
           return super(FeedbackPublicationUpdate, self).get(request, *args, **kwargs)
        elif flowcontext["may_update_publication_feedback_final"] == "True":
           return super(FeedbackPublicationUpdate, self).get(request, *args, **kwargs)
        elif flowcontext["may_update_publication_feedback_determination"] == "True":
           return super(FeedbackPublicationUpdate, self).get(request, *args, **kwargs)
        else:
             messages.error(
                 self.request, "Can't change feedback publication for this application")
             return HttpResponseRedirect(app.get_absolute_url())
#        return HttpResponseRedirect(app.get_absolute_url())
        # app = Application.objects.get(pk=self.kwargs['application'])
        # if app.state != app.APP_STATE_CHOICES.draft:
        #    messages.errror(
        #       self.request, "Can't add new newspaper publication to this application")
        #  return HttpResponseRedirect(app.get_absolute_url())
#        return super(FeedbackPublicationUpdate, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('application_detail', args=(self.kwargs['application'],))

    def get_context_data(self, **kwargs):
        context = super(FeedbackPublicationUpdate,
                        self).get_context_data(**kwargs)
        context['application'] = Application.objects.get(pk=self.kwargs['application'])
        return context

    def get_initial(self):
        initial = super(FeedbackPublicationUpdate, self).get_initial()
        initial['application'] = self.kwargs['application']
        try:
            pub_feed = PublicationFeedback.objects.get(
                pk=self.kwargs['pk'])
        except:
            pub_feed = None

        #multifilelist = []
        #if pub_feed:
        #    records = pub_feed.records.all()
        #    for b1 in records:
        #        fileitem = {}
        #        fileitem['fileid'] = b1.id
        #        fileitem['path'] = b1.upload.name
        #        fileitem['extension']  = b1.extension
        #        multifilelist.append(fileitem)
        #initial['records'] = multifilelist



        multifilelist = []
        a1 = pub_feed.records.all()
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['records'] = multifilelist

        return initial

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = Application.objects.get(pk=self.kwargs['application'])
            return HttpResponseRedirect(app.get_absolute_url())
        return super(FeedbackPublicationUpdate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        app = Application.objects.get(pk=self.object.application.id)

        pub_feed = PublicationFeedback.objects.get(pk=self.kwargs['pk'])

        if 'records_json' in self.request.POST:
             if is_json(self.request.POST['records_json']) is True:
                  json_data = json.loads(self.request.POST['records_json'])
                  self.object.records.remove()
                  for d in self.object.records.all():
                      self.object.records.remove(d)
                  for i in json_data:
                      doc = Record.objects.get(id=i['doc_id'])
                      self.object.records.add(doc)

        #records = pub_feed.records.all()
        #for filelist in records:
        #    if 'records-clear_multifileid-' + str(filelist.id) in form.data:
        #        pub_feed.records.remove(filelist)

        #if self.request.FILES.get('records'):
        #    for f in self.request.FILES.getlist('records'):
        #        doc = Record()
        #        doc.upload = f
        #        doc.save()
        #        self.object.records.add(doc)

        return super(FeedbackPublicationUpdate, self).form_valid(form)


class FeedbackPublicationDelete(LoginRequiredMixin, DeleteView):
    model = PublicationFeedback

    def get(self, request, *args, **kwargs):
        modelobject = self.get_object()
        app = modelobject.application

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)

        if flowcontext["may_update_publication_feedback_review"] == "True":
           return super(FeedbackPublicationDelete, self).get(request, *args, **kwargs)
        elif flowcontext["may_update_publication_feedback_draft"] == "True":
           return super(FeedbackPublicationDelete, self).get(request, *args, **kwargs)
        elif flowcontext["may_update_publication_feedback_final"] == "True":
           return super(FeedbackPublicationDelete, self).get(request, *args, **kwargs)
        elif flowcontext["may_update_publication_feedback_determination"] == "True":
           return super(FeedbackPublicationDelete, self).get(request, *args, **kwargs)
        else:
             messages.error(
                 self.request, "Can't delete feedback publication for this application")
             return HttpResponseRedirect(app.get_absolute_url())

        return super(FeedbackPublicationDelete, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('application_detail', args=(self.get_object().application.pk,))

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_success_url())
        # Generate an action.
        modelobject = self.get_object()
        action = Action(
            content_object=modelobject.application, user=self.request.user.id,
            action='Delete Feedback Publication {} deleted (status: {})'.format(modelobject.pk, 'delete'))
        action.save()
        messages.success(self.request, 'Newspaper Feedback {} has been deleted'.format(modelobject.pk))
        return super(FeedbackPublicationDelete, self).post(request, *args, **kwargs)


class ConditionCreate(LoginRequiredMixin, CreateView):
    """A view for a referee or an internal user to create a Condition object
    on an Application.
    """
    model = Condition
    form_class = apps_forms.ConditionCreateForm

    def get(self, request, *args, **kwargs):
        app = Application.objects.get(pk=self.kwargs['pk'])
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)

        if flowcontext["may_create_condition"] != "True":
            messages.error(
                self.request, "Can't add new newspaper publication to this application")
            return HttpResponseRedirect(app.get_absolute_url())


        # Rule: conditions can be created when the app is with admin, with
        # referee or with assessor.
        #if app.app_type == app.APP_TYPE_CHOICES.emergency:
        #    if app.state != app.APP_STATE_CHOICES.draft or app.assignee != self.request.user.id:
        #        messages.error(
        #            self.request, 'New conditions cannot be created for this application!')
        #        return HttpResponseRedirect(app.get_absolute_url())
        #elif app.state not in [app.APP_STATE_CHOICES.with_admin, app.APP_STATE_CHOICES.with_referee, app.APP_STATE_CHOICES.with_assessor]:
        #    messages.error(
        #        self.request, 'New conditions cannot be created for this application!')
        #    return HttpResponseRedirect(app.get_absolute_url())
        return super(ConditionCreate, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ConditionCreate, self).get_context_data(**kwargs)
        context['page_heading'] = 'Create a new condition'
        return context

    def get_initial(self):
        initial = super(ConditionCreate, self).get_initial()
        app = Application.objects.get(pk=self.kwargs['pk'])

        condition_no_max = 1
        advise_no_max = 1

        condition_no_obj = Condition.objects.filter(application=app).aggregate(Max('condition_no'))
        advise_no_obj = Condition.objects.filter(application=app).aggregate(Max('advise_no'))

        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(self.request, flowcontext, app.routeid, workflowtype)

        if condition_no_obj['condition_no__max'] is not None:
            condition_no_max = condition_no_obj['condition_no__max'] + 1
        if advise_no_obj['advise_no__max'] is not None:
            advise_no_max = advise_no_obj['advise_no__max'] + 1

#        condition = self.get_object()
#        print condition.application.id
        #flow = Flow()
        #workflowtype = flow.getWorkFlowTypeFromApp(condition.application)
        #flow.get(workflowtype)
        #DefaultGroups = flow.groupList()
        #flowcontext = {}
        #flowcontext = flow.getAccessRights(self.request, flowcontext, condition.application.routeid, workflowtype)
        initial['may_assessor_advise'] = flowcontext["may_assessor_advise"]
        #initial['may_assessor_advise'] = 'df'
        initial['assessor_staff'] = False
        assessor = SystemGroup.objects.get(name='Statdev Assessor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)        
        
        if assessor.id in usergroups:
             initial['assessor_staff'] = True
        initial['condition_no'] = condition_no_max
        initial['advise_no'] = advise_no_max
        return initial

    def get_success_url(self):
        """Override to redirect to the condition's parent application detail view.
        """
        return "/"
        return reverse('application_update', args=(self.object.application.pk,))

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = Application.objects.get(pk=self.kwargs['pk'])
            return HttpResponseRedirect(app.get_absolute_url())
        return super(ConditionCreate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        app = Application.objects.get(pk=self.kwargs['pk'])
        self.object = form.save(commit=False)
        self.object.application = app
        # If a referral exists for the parent application for this user,
        # link that to the new condition.
        if Referral.objects.filter(application=app, referee=self.request.user.id).exists():
            self.object.referral = Referral.objects.get(
                application=app, referee=self.request.user.id)
        # If the request user is not in the "Referee" group, then assume they're an internal user
        # and set the new condition to "applied" status (default = "proposed").
        referee = SystemGroup.objects.get(name='Statdev Processor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        if referee.id not in usergroups:
            self.object.status = Condition.CONDITION_STATUS_CHOICES.applied
        self.object.save()
        # Record an action on the application:
        action = Action(
            content_object=app, category=Action.ACTION_CATEGORY_CHOICES.create, user=self.request.user.id,
            action='Created condition {} (status: {})'.format(self.object.pk, self.object.get_status_display()))
        action.save()
        messages.success(self.request, 'Condition {} Created'.format(self.object.pk))

        return super(ConditionCreate, self).form_valid(form)


class ConditionUpdate(LoginRequiredMixin, UpdateView):
    """A view to allow an assessor to update a condition that might have been
    proposed by a referee.
    The ``action`` kwarg is used to define the new state of the condition.
    """
    model = Condition

    def get(self, request, *args, **kwargs):
        condition = self.get_object()

        app = condition.application
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)

        if flowcontext["may_create_condition"] != "True":
            messages.error(
                self.request, "Can't add new newspaper publication to this application")
            return HttpResponseRedirect(app.get_absolute_url())

        # Rule: can only change a condition if the parent application is status
        # 'with assessor' or 'with_referee' unless it is an emergency works.
        if condition.application.app_type == Application.APP_TYPE_CHOICES.emergency:
            if condition.application.state != Application.APP_STATE_CHOICES.draft:
                messages.error(
                    self.request, 'You can not change conditions when the application has been issued')
                return HttpResponseRedirect(condition.application.get_absolute_url())
            elif condition.application.assignee != self.request.user.id:
                messages.error(
                    self.request, 'You can not change conditions when the application is not assigned to you')
                return HttpResponseRedirect(condition.application.get_absolute_url())
            else:
                return super(ConditionUpdate, self).get(request, *args, **kwargs)
        #elif condition.application.state not in [Application.APP_STATE_CHOICES.with_assessor, Application.APP_STATE_CHOICES.with_referee]:
        #    messages.error(
        #        self.request, 'You can only change conditions when the application is "with assessor" or "with referee" status')
        #    return HttpResponseRedirect(condition.application.get_absolute_url())
        # Rule: can only change a condition if the request user is an Assessor
        # or they are assigned the referral to which the condition is attached
        # and that referral is not completed.
        assessor = SystemGroup.objects.get(name='Statdev Assessor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        ref = condition.referral
        if assessor.id in usergroups or (ref and ref.referee == request.user.id and ref.status == Referral.REFERRAL_STATUS_CHOICES.referred):
            messages.success(self.request, 'Condition Successfully added')
            return super(ConditionUpdate, self).get(request, *args, **kwargs)
        else:
            messages.warning(self.request, 'You cannot update this condition')
            return super(ConditionUpdate, self).get(request, *args, **kwargs)
            return HttpResponseRedirect(condition.application.get_absolute_url())

    def get_initial(self):
        initial = super(ConditionUpdate, self).get_initial()
        condition = self.get_object()
#        print condition.application.id
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(condition.application)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(self.request, flowcontext, condition.application.routeid, workflowtype)
        initial['may_assessor_advise'] = flowcontext["may_assessor_advise"]

        initial['assessor_staff'] = False
        
        assessor = SystemGroup.objects.get(name='Statdev Assessor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        
        if assessor.id in usergroups:
             initial['assessor_staff'] = True
        return initial

    def get_success_url(self):
        """Override to redirect to the condition's parent application detail view.
        """
        return "/"

    def get_form_class(self):
        # Updating the condition as an 'action' should not allow the user to
        # change the condition text.
        if 'action' in self.kwargs:
            return apps_forms.ConditionActionForm
        return apps_forms.ConditionUpdateForm

    def get_context_data(self, **kwargs):
        context = super(ConditionUpdate, self).get_context_data(**kwargs)
        if 'action' in self.kwargs:
            if self.kwargs['action'] == 'apply':
                context['page_heading'] = 'Apply a proposed condition'
            elif self.kwargs['action'] == 'reject':
                context['page_heading'] = 'Reject a proposed condition'
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().application.get_absolute_url())
        return super(ConditionUpdate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if 'action' in self.kwargs:
            if self.kwargs['action'] == 'apply':
                self.object.status = Condition.CONDITION_STATUS_CHOICES.applied
            elif self.kwargs['action'] == 'reject':
                self.object.status = Condition.CONDITION_STATUS_CHOICES.rejected
            # Generate an action:
            action = Action(
                content_object=self.object.application, user=self.request.user.id,
                action='Condition {} updated (status: {})'.format(self.object.pk, self.object.get_status_display()))
            action.save()
        self.object.save()

        messages.success(self.request, "Successfully Applied")
        #return HttpResponseRedirect("/")
        return super(ConditionUpdate, self).form_valid(form)
        return HttpResponseRedirect(self.object.application.get_absolute_url()+'')

class ConditionDelete(LoginRequiredMixin, DeleteView):
    model = Condition

    def get(self, request, *args, **kwargs):
        condition = self.get_object()

        app = condition.application
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)

        if flowcontext["may_create_condition"] != "True":
            messages.error(
                self.request, "Can't add new newspaper publication to this application")
            return HttpResponseRedirect(app.get_absolute_url())

        return super(ConditionDelete, self).get(request, *args, **kwargs)
        # Rule: can only delete a condition if the parent application is status
        # 'with referral' or 'with assessor'. Can also delete if you are the user assigned
        # to an Emergency Works
        #if condition.application.app_type != Application.APP_TYPE_CHOICES.emergency:
        #    if condition.application.state not in [Application.APP_STATE_CHOICES.with_assessor, Application.APP_STATE_CHOICES.with_referee]:
        #        messages.warning(self.request, 'You cannot delete this condition')
        #        return HttpResponseRedirect(condition.application.get_absolute_url())
        #    # Rule: can only delete a condition if the request user is an Assessor
        #    # or they are assigned the referral to which the condition is attached
        #    # and that referral is not completed.
        #    assessor = SystemGroup.objects.get(name='Statdev Assessor')
        #    ref = condition.referral
        #    if assessor in self.request.user.groups().all() or (ref and ref.referee == request.user.id and ref.status == Referral.REFERRAL_STATUS_CHOICES.referred):
        #        return super(ConditionDelete, self).get(request, *args, **kwargs)
        #    else:
        #        messages.warning(self.request, 'You cannot delete this condition')
        #        return HttpResponseRedirect(condition.application.get_absolute_url())
        #else:
            # Rule: can only delete a condition if the request user is the assignee and the application
            # has not been issued.
            #if condition.application.assignee == request.user.id and condition.application.state != Application.APP_STATE_CHOICES.issued:
            #    return super(ConditionDelete, self).get(request, *args, **kwargs)
            #else:
            #    messages.warning(self.request, 'You cannot delete this condition')
            #    return HttpResponseRedirect(condition.application.get_absolute_url())

    def get_success_url(self):
        return reverse('application_detail', args=(self.get_object().application.pk,))

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_success_url())
        # Generate an action.
        condition = self.get_object()
        action = Action(
            content_object=condition.application, user=self.request.user.id,
            action='Condition {} deleted (status: {})'.format(condition.pk, condition.get_status_display()))
        action.save()
        #messages.success(self.request, 'Condition {} has been deleted'.format(condition.pk))
        return super(ConditionDelete, self).post(request, *args, **kwargs)

class ConditionSuspension(LoginRequiredMixin, UpdateView):
    model = Condition
    form_class = apps_forms.ConditionSuspension

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden Access.')
           return HttpResponseRedirect("/")
        return super(ConditionSuspension, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('application_detail', args=(self.get_object().application.pk,))

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_success_url())
        # Generate an action.
        return super(ConditionSuspension, self).post(request, *args, **kwargs)

    def get_initial(self):
        initial = super(ConditionSuspension, self).get_initial()
        initial['actionkwargs'] = self.kwargs['action']
        return initial

    def form_valid(self, form):

        self.object = form.save(commit=False)

        actionkwargs = self.kwargs['action']
        if actionkwargs == 'suspend':
            self.object.suspend = True
        elif actionkwargs == 'unsuspend':
            self.object.suspend = False

        action = Action(
            content_object=self.object, user=self.request.user.id,
            action='Condition {} suspend (status: {})'.format(self.object.pk, self.object.get_status_display()))
        action.save()

        messages.success(self.request, 'Condition {} has been suspended'.format(self.object.pk))

        return super(ConditionSuspension, self).form_valid(form)


class VesselCreate(LoginRequiredMixin, CreateView):
    model = Vessel
    form_class = apps_forms.VesselForm

    def get(self, request, *args, **kwargs):
        app = Application.objects.get(pk=self.kwargs['pk'])
#        action = self.kwargs['action']

        flow = Flow()
        flowcontext = {}
        if app.assignee:
           flowcontext['application_assignee_id'] = app.assignee
        else:
           flowcontext['application_assignee_id'] = None
       
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)
        flowcontext = flow.getRequired(flowcontext, app.routeid, workflowtype)
        processor = SystemGroup.objects.get(name='Statdev Processor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        
        if processor.id in usergroups:
            donothing = ''
        elif flowcontext["may_update_vessels_list"] != "True":
#        if app.state != app.APP_STATE_CHOICES.draft:
            messages.error(
                self.request, "Can't add new vessels to this application")
            return HttpResponseRedirect(app.get_absolute_url())
        return super(VesselCreate, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('application_update', args=(self.kwargs['pk'],))

    def get_context_data(self, **kwargs):
        context = super(VesselCreate, self).get_context_data(**kwargs)
        context['page_heading'] = 'Create new vessel details'
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = Application.objects.get(pk=self.kwargs['pk'])
            return HttpResponseRedirect(app.get_absolute_url())
        return super(VesselCreate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        app = Application.objects.get(pk=self.kwargs['pk'])
        self.object = form.save()
        app.vessels.add(self.object.id)
        app.save()

        if 'registration_json' in self.request.POST:
             if is_json(self.request.POST['registration_json']) is True:
                 json_data = json.loads(self.request.POST['registration_json'])
                 for d in self.object.registration.all():
                     self.object.registration.remove(d)
                 for i in json_data:
                     doc = Record.objects.get(id=i['doc_id'])
                     self.object.registration.add(doc)

        if 'documents_json' in self.request.POST:
             if is_json(self.request.POST['documents_json']) is True:
                 json_data = json.loads(self.request.POST['documents_json'])
                 for d in self.object.documents.all():
                     self.object.documents.remove(d)
                 for i in json_data:
                     doc = Record.objects.get(id=i['doc_id'])
                     self.object.documents.add(doc)
                     

        # Registration document uploads.
#        if self.request.FILES.get('registration'):
#            for f in self.request.FILES.getlist('registration'):
#                doc = Record()
#                doc.upload = f
#                doc.save()
#                self.object.registration.add(doc)

        return HttpResponseRedirect(reverse('inside_popup_notification'),)

        #return super(VesselCreate, self).form_valid(form)


class VesselDelete(LoginRequiredMixin, UpdateView):
    model = Vessel 
    form_class = apps_forms.VesselDeleteForm
    template_name = 'applications/vessel_delete.html'

    def get(self, request, *args, **kwargs):
        vessel = self.get_object()
        app = self.get_object().application_set.first()
        flow = Flow()
        flowcontext = {}
        if app.assignee:
           flowcontext['application_assignee_id'] = app.assignee
        else:
            if float(app.routeid) == 1 and app.assignee is None:
                flowcontext['application_assignee_id'] = self.request.user.id
            else:
                flowcontext['application_assignee_id'] = None

#        flowcontext['application_assignee_id'] = app.assignee
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)
        flowcontext = flow.getRequired(flowcontext, app.routeid, workflowtype)
        if flowcontext["may_update_vessels_list"] != "True":
#        if app.state != app.APP_STATE_CHOICES.draft:
            messages.error(
                self.request, "Can't add new vessels to this application")
            return HttpResponseRedirect(reverse('popup-error'))
        #if referral.status != Referral.REFERRAL_STATUS_CHOICES.referred:
        #    messages.error(self.request, 'This delete is already completed!')
        #    return HttpResponseRedirect(referral.application.get_absolute_url())
        return super(VesselDelete, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(VesselDelete, self).get_context_data(**kwargs)
        context['vessel'] = self.get_object()
        return context

    def get_success_url(self, application_id):
        return reverse('application_update', args=(application_id,))

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_object().application.get_absolute_url())
        return super(VesselDelete, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        vessel = self.get_object()
#        application_id = vessel.application.id
        app = self.object.application_set.first()
        vessel.delete()
        # Record an action on the referral's application:
        action = Action(
            content_object=app, user=self.request.user.id,
            action='Vessel to {} delete'.format(vessel.id))
        action.save()
        return HttpResponseRedirect(reverse('inside_popup_notification'),)

class VesselUpdate(LoginRequiredMixin, UpdateView):
    model = Vessel
    form_class = apps_forms.VesselForm

    def get(self, request, *args, **kwargs):
        app = self.get_object().application_set.first()
        # Rule: can only change a vessel if the parent application is status
        # 'draft'.
        #if app.state != Application.APP_STATE_CHOICES.draft:
        #    messages.error(
        #        self.request, 'You can only change a vessel details when the application is "draft" status')
        #    return HttpResponseRedirect(app.get_absolute_url())
        flowcontext = {}
        if app.assignee:
            flowcontext['application_assignee_id'] = app.assignee
        else:
            if float(app.routeid) == 1 and app.assignee is None:
                flowcontext['application_assignee_id'] = self.request.user.id
            else:
                flowcontext['application_assignee_id'] = None



        flow = Flow()
        #flowcontext = {}
        # flowcontext['application_assignee_id'] = app.assignee
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)
        flowcontext = flow.getRequired(flowcontext, app.routeid, workflowtype)
        if flowcontext["may_update_vessels_list"] != "True":
#        if app.state != app.APP_STATE_CHOICES.draft:
            messages.error(
                self.request, "Can't add new vessels to this application")
            return HttpResponseRedirect(reverse('notification_popup'))
        return super(VesselUpdate, self).get(request, *args, **kwargs)

    def get_success_url(self,app_id):
        return reverse('application_update', args=(app_id,))

    def get_context_data(self, **kwargs):
        context = super(VesselUpdate, self).get_context_data(**kwargs)
        context['page_heading'] = 'Update vessel details'
        return context

    def get_initial(self):
        initial = super(VesselUpdate, self).get_initial()
#        initial['application_id'] = self.kwargs['pk']
        vessels = self.get_object()
        a1 = vessels.registration.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['registration'] = multifilelist

        a1 = vessels.documents.all()
        multifilelist = []
        for b1 in a1:
            fileitem = {}
            fileitem['fileid'] = b1.id
            fileitem['path'] = b1.upload.name
            fileitem['name'] = b1.name
            fileitem['extension']  = b1.extension
            multifilelist.append(fileitem)
        initial['documents'] = multifilelist

        return initial
    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = self.get_object().application_set.first()
            return HttpResponseRedirect(app.get_absolute_url())
        return super(VesselUpdate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        # Registration document uploads.
#        rego = self.object.registration.all()

        if 'registration_json' in self.request.POST:
             if is_json(self.request.POST['registration_json']) is True:
                 json_data = json.loads(self.request.POST['registration_json'])
                 for d in self.object.registration.all():
                     self.object.registration.remove(d)
                 for i in json_data:
                     doc = Record.objects.get(id=i['doc_id'])
                     self.object.registration.add(doc)


        if 'documents_json' in self.request.POST:
             if is_json(self.request.POST['documents_json']) is True:
                 json_data = json.loads(self.request.POST['documents_json'])
                 for d in self.object.documents.all():
                     self.object.documents.remove(d)
                 for i in json_data:
                     doc = Record.objects.get(id=i['doc_id'])
                     self.object.documents.add(doc)

        #for filelist in rego:
        #    if 'registration-clear_multifileid-' + str(filelist.id) in form.data:
        #         self.object.registration.remove(filelist)

#
#        if self.request.FILES.get('registration'):
#            for f in self.request.FILES.getlist('registration'):
#                doc = Record()
#                doc.upload = f
#                doc.save()
#                self.object.registration.add(doc)

        app = self.object.application_set.first()
        #return HttpResponseRedirect(self.get_success_url(app.id),)
        return HttpResponseRedirect(reverse('inside_popup_notification'),)


#class RecordCreate(LoginRequiredMixin, CreateView):
#    form_class = apps_forms.RecordCreateForm
#    template_name = 'applications/document_form.html'
#
#    def get_context_data(self, **kwargs):
#        context = super(RecordCreate, self).get_context_data(**kwargs)
#        context['page_heading'] = 'Create new Record'
#        return context

#    def post(self, request, *args, **kwargs):
#        if request.POST.get('cancel'):
#            return HttpResponseRedirect(reverse('home'))
#        return super(RecordCreate, self).post(request, *args, **kwargs)
#
#    def form_valid(self, form):
#        """Override form_valid to set the assignee as the object creator.
#        """
#        self.object = form.save(commit=False)
#        self.object.save()
#        success_url = reverse('document_list', args=(self.object.pk,))
#        return HttpResponseRedirect(success_url)


#class RecordList(ListView):
#    model = Record


#class UserAccount(LoginRequiredMixin, DetailView):
#    model = EmailUser
#    template_name = 'accounts/user_account.html'
#
#    def get_object(self, queryset=None):
#        """Override get_object to always return the request user.
#        """
#        return self.request.user
#
#    def get_context_data(self, **kwargs):
#        context = super(UserAccount, self).get_context_data(**kwargs)
#        context['organisations'] = [i.organisation for i in Delegate.objects.filter(email_user=self.request.user.id)]
#        return context

class UserAccountUpdate(LoginRequiredMixin, UpdateView):
    form_class = apps_forms.SystemUserForm
    template_name = 'accounts/systemuser_form.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        elif self.request.user.id == int(self.kwargs['pk']):
           donothing =""
        else:
           messages.error(self.request, 'Forbidden Access.')
           return HttpResponseRedirect("/")
        return super(UserAccountUpdate, self).get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if 'pk' in self.kwargs:
            system_user = SystemUser.objects.get(ledger_id=self.request.user.id)
            processor = SystemGroup.objects.get(name='Statdev Processor')
            usergroups = self.request.user.get_system_group_permission(self.request.user.id)
            
            if processor.id in usergroups:
               user = SystemUser.objects.get(ledger_id=self.kwargs['pk'])
               return user
            elif system_user.id == int(self.kwargs['pk']):
                user = SystemUser.objects.get(ledger_id=self.kwargs['pk'])
                return user
            else:
                messages.error(
                  self.request, "Forbidden Access")
                return HttpResponseRedirect("/")
        else:
            return self.request.user

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
#            return HttpResponseRedirect(reverse('user_account'))
             return HttpResponseRedirect(reverse('person_details_actions', args=(self.kwargs['pk'],'personal')))     
        return super(UserAccountUpdate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override to set first_name and last_name on the EmailUser object.
        """
        self.obj = form.save(commit=False)
        # If identification has been uploaded, then set the id_verified field to None.
        #if 'identification' in data and data['identification']:
        #    self.obj.id_verified = None
        self.obj.save()
#        return HttpResponseRedirect(reverse('user_account'))
        # Record an action on the application:
#        print self.object.all()
#        print serializers.serialize('json', self.object)
#        from django.core import serializers
#        forms_data = form.cleaned_data
#        print serializers.serialize('json', [ forms_data ])

        action = Action(
            content_object=self.object, category=Action.ACTION_CATEGORY_CHOICES.change, user=self.request.user.id,
            action='Updated Personal Details')
        action.save()
        return HttpResponseRedirect(reverse('person_details_actions', args=(self.obj.pk,'personal')))
from django.db.models.fields.files import FieldFile

class OrganisationCertificateUpdate(LoginRequiredMixin, UpdateView):
    model = OrganisationExtras
    form_class = apps_forms.OrganisationCertificateForm

    def get(self, request, *args, **kwargs):
        # Rule: request user must be a delegate (or superuser).
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        org_extras = self.get_object()
        org =org_extras.organisation

        if Delegate.objects.filter(email_user=request.user.id, organisation=org).exists():
            pass
        else:
           if admin_staff is True:
               return super(OrganisationCertificateUpdate, self).get(request, *args, **kwargs)
           else:
               messages.error(self.request, 'You are not authorised.')
               return HttpResponseRedirect(reverse('home'))

        return super(OrganisationCertificateUpdate, self).get(request, *args, **kwargs)

#    def get_object(self, queryset=None):
#        if 'pk' in self.kwargs:
#            if self.request.user.groups().filter(name='Processor').exists():
#                #user = EmailUser.objects.get(pk=self.kwargs['pk'])
#               return self 
#            else:
#                messages.error(
#                  self.request, "Forbidden Access")
#                return HttpResponseRedirect("/")
#        else:
#            return self.request.user

    def post(self, request, *args, **kwargs):
        if 'identification' in request.FILES:
            if Attachment_Extension_Check('single', request.FILES['identification'], ['.pdf','.png','.jpg']) is False:
               messages.error(self.request,'You have added and unallowed attachment extension.')
               return HttpResponseRedirect(request.path)


        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.kwargs['pk'],'certofincorp')))
        return super(OrganisationCertificateUpdate, self).post(request, *args, **kwargs)

    def get_initial(self):
        initial = super(OrganisationCertificateUpdate, self).get_initial()
        org = self.get_object()
        #print org.identification
        if self.object.identification:
           initial['identification'] = self.object.identification.upload
           
        return initial

    def form_valid(self, form):
        """Override to set first_name and last_name on the EmailUser object.
        """
        self.obj = form.save(commit=False)
        forms_data = form.cleaned_data

        # If identification has been uploaded, then set the id_verified field to None.
        # if 'identification' in data and data['identification']:
        #    self.obj.id_verified = None
        if self.request.POST.get('identification-clear'):
            self.obj.identification = None

        if self.request.FILES.get('identification'):
            if Attachment_Extension_Check('single', forms_data['identification'], ['.pdf','.png','.jpg']) is False:
                raise ValidationError('Identification contains and unallowed attachment extension.')
        new_doc = Record()
        if(self.request.FILES.get('identification')):  
            extension = self.request.FILES.get('identification').name.split('.')
            att_ext = str("."+extension[1]).lower()
            new_doc.name = self.request.FILES['identification'].name
            new_doc.file_group = 2002
            new_doc.file_group_ref_id = self.obj.organisation.pk
            new_doc.extension = att_ext   
        if forms_data['identification']:
            if isinstance(forms_data['identification'], FieldFile):
                return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.obj.organisation.pk,'certofincorp')))
            else:
                new_doc.upload = self.request.FILES['identification']
        else:
            new_doc.upload = None
        new_doc.save()
        self.obj.identification = new_doc

        self.obj.save()
        return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.obj.organisation.pk,'certofincorp')))

class AddressCreate(LoginRequiredMixin, CreateView):
    """A view to create a new address for an EmailUser.
    """
    form_class = apps_forms.AddressForm
    template_name = 'accounts/address_form.html'

    def get(self, request, *args, **kwargs):
#        # Rule: request user must be a delegate (or superuser).
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        self.object = SystemUser.objects.get(ledger_id=self.kwargs['userid']) 
#
        if admin_staff is True:
             return super(AddressCreate, self).get(request, *args, **kwargs)
        elif request.user.id == self.object.ledger_id:
             return super(AddressCreate, self).get(request, *args, **kwargs)
        else:
             messages.error(self.request, 'You are not authorised to view.')
        return HttpResponseRedirect(reverse('home'))
#        return super(AddressCreate, self).get(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Rule: the ``type`` kwarg must be 'postal' or 'billing'
        if self.kwargs['type'] not in ['postal', 'billing']:
            messages.error(self.request, 'Invalid address type!')
            return HttpResponseRedirect(reverse('user_account'))
        return super(AddressCreate, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AddressCreate, self).get_context_data(**kwargs)
        context['address_type'] = self.kwargs['type']
        context['action'] = 'Create'
        if 'userid' in self.kwargs:
            user = SystemUser.objects.get(ledger_id=self.kwargs['userid'])
            context['principal'] = user.email
        else:
            context['principal'] = self.request.user.email
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('user_account'))
        return super(AddressCreate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        if 'userid' in self.kwargs:
            u = SystemUser.objects.get(ledger_id=self.kwargs['userid'])
        else:
            u = self.request.user

        self.obj = form.save(commit=False)
        self.obj.user = u.id
        self.obj.save()
        # Attach the new address to the user's profile.
        if self.kwargs['type'] == 'postal':
            u.postal_address = self.obj
        elif self.kwargs['type'] == 'billing':
            u.billing_address = self.obj
        u.save()

#        if 'userid' in self.kwargs:
            #    if self.request.user.is_staff is True:
        action = Action(
           content_object=u, category=Action.ACTION_CATEGORY_CHOICES.change, user=self.request.user.id,
           action='New '+self.kwargs['type']+' address created')
        action.save()

        return HttpResponseRedirect(reverse('person_details_actions', args=(u.id,'address')))
        #    else:
        #        return HttpResponseRedirect(reverse('user_account'))
 #       else:
  #          return HttpResponseRedirect(reverse('user_account'))

#class AAOrganisationAddressUpdate(LoginRequiredMixin, UpdateView):
#
#    model = OrganisationAddress
#    form_class = apps_forms.OrganisationAddressForm
#    template_name = 'accounts/address_form.html'
#
#    def get(self, request, *args, **kwargs):
#        context_processor = template_context(self.request)
#        admin_staff = context_processor['admin_ddstaff']
#
#        address = self.get_object()
#
#TODO good to test
class OrganisationAddressUpdate(LoginRequiredMixin, UpdateView):
    model = OrganisationAddress
    form_class = apps_forms.AddressForm
    success_url = reverse_lazy('user_account')
    template_name = 'accounts/address_form.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']

        address = self.get_object()
        u = request.user
        # User addresses: only the user can change an address.
        if u.postal_address == address or u.billing_address == address:
            return super(OrganisationAddressUpdate, self).get(request, *args, **kwargs)

        # Organisational addresses: find which org uses this address, and if
        # the user is a delegate for that org then they can change it.
        org_list = list(chain(address.org_postal_address.all(), address.org_billing_address.all()))
        if Delegate.objects.filter(email_user=u.id, organisation__in=org_list).exists():
            return super(OrganisationAddressUpdate, self).get(request, *args, **kwargs)
#        elif u.is_staff is True:
        elif admin_staff is True:
            return super(OrganisationAddressUpdate, self).get(request, *args, **kwargs)
        else:
            messages.error(self.request, 'You cannot update this address!')
            return HttpResponseRedirect(reverse('home'))

    def get_context_data(self, **kwargs):
        context = super(OrganisationAddressUpdate, self).get_context_data(**kwargs)
        context['action'] = 'Update'
        address = self.get_object()
        u = self.request.user
        if u.postal_address == address:
            context['action'] = 'Update postal'
            context['principal'] = u.email
        if u.billing_address == address:
            context['action'] = 'Update billing'
            context['principal'] = u.email
        # TODO: include context for Organisation addresses.
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            #return HttpResponseRedirect(self.success_url)
            obj = self.get_object()
            u = obj.user

            if 'org_id' in self.kwargs:
                return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.kwargs['org_id'],'address')))
            else:
                return HttpResponseRedirect(reverse('person_details_actions', args=(u.id,'address')))
        #if self.request.user.is_staff is True:
        #    obj = self.get_object()
        #    u = obj.user
        #    return HttpResponseRedirect(reverse('person_details_actions', args=(u.id,'address')))
        #else:
        return super(OrganisationAddressUpdate, self).post(request, *args, **kwargs)


    def form_valid(self, form):
        self.obj = form.save()
        obj = self.get_object()
        #u = obj.user

        if 'org_id' in self.kwargs:
            org =Organisation.objects.get(id= self.kwargs['org_id'])
            action = Action(
                content_object=org, category=Action.ACTION_CATEGORY_CHOICES.change, user=self.request.user.id,
                action='Organisation address updated')
            action.save()
            return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.kwargs['org_id'],'address')))

        else:
            action = Action(
                content_object=u, category=Action.ACTION_CATEGORY_CHOICES.change, user=self.request.user.id,
                action='Person address updated')
            action.save()

            return HttpResponseRedirect(reverse('person_details_actions', args=(u.id,'address')))




class AddressUpdate(LoginRequiredMixin, UpdateView):
    model = Address
    form_class = apps_forms.AddressForm
    success_url = reverse_lazy('user_account')


    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']

        address = self.get_object()
        u = request.user
        # User addresses: only the user can change an address.
        if u.postal_address == address or u.billing_address == address:
            return super(AddressUpdate, self).get(request, *args, **kwargs)
        
        # Organisational addresses: find which org uses this address, and if
        # the user is a delegate for that org then they can change it.
        org_list = list(chain(address.org_postal_address.all(), address.org_billing_address.all()))
        if Delegate.objects.filter(email_user=u.id, organisation__in=org_list).exists():
            return super(AddressUpdate, self).get(request, *args, **kwargs)
#        elif u.is_staff is True: 
        elif admin_staff is True:
            return super(AddressUpdate, self).get(request, *args, **kwargs)
        else:
            messages.error(self.request, 'You cannot update this address!')
            return HttpResponseRedirect(reverse('home'))

    def get_context_data(self, **kwargs):
        context = super(AddressUpdate, self).get_context_data(**kwargs)
        context['action'] = 'Update'
        address = self.get_object()
        u = self.request.user
        if u.postal_address == address:
            context['action'] = 'Update postal'
            context['principal'] = u.email
        if u.billing_address == address:
            context['action'] = 'Update billing'
            context['principal'] = u.email
        # TODO: include context for Organisation addresses.
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            #return HttpResponseRedirect(self.success_url)
            obj = self.get_object()
            u = obj.user
            
            if 'org_id' in self.kwargs:
                return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.kwargs['org_id'],'address')))
            else:
                return HttpResponseRedirect(reverse('person_details_actions', args=(u.id,'address')))
        #if self.request.user.is_staff is True:
        #    obj = self.get_object()
        #    u = obj.user
        #    return HttpResponseRedirect(reverse('person_details_actions', args=(u.id,'address')))
        #else:
        return super(AddressUpdate, self).post(request, *args, **kwargs)


    def form_valid(self, form):
        self.obj = form.save()
        obj = self.get_object()
        u = obj.user
        if 'org_id' in self.kwargs:
            org =Organisation.objects.get(id= self.kwargs['org_id'])
            action = Action(
                content_object=org, category=Action.ACTION_CATEGORY_CHOICES.change, user=self.request.user.id,
                action='Organisation address updated')
            action.save()
            return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.kwargs['org_id'],'address')))

        else:
            action = Action(
                content_object=u, category=Action.ACTION_CATEGORY_CHOICES.change, user=self.request.user.id,
                action='Person address updated')
            action.save()

            return HttpResponseRedirect(reverse('person_details_actions', args=(u.id,'address')))


#class AddressDelete(LoginRequiredMixin, DeleteView):
#    """A view to allow the deletion of an address. Not currently in use,
#    because the ledge Address model can cause the linked EmailUser object to
#    be deleted along with the Address object :/
#    """
#    model = Address
#    success_url = reverse_lazy('user_account')
#
#    def get(self, request, *args, **kwargs):
#        address = self.get_object()
#        u = self.request.user
#        delete_address = False
#        # Rule: only the address owner can delete an address.
#        if u.postal_address == address or u.billing_address == address:
#            delete_address = True
#        # Organisational addresses: find which org uses this address, and if
#        # the user is a delegate for that org then they can delete it.
#        #org_list = list(chain(address.org_postal_address.all(), address.org_billing_address.all()))
#        #for org in org_list:
#        #    if profile in org.delegates.all():
#        #        delete_address = True
#        if delete_address:
#            return super(AddressDelete, self).get(request, *args, **kwargs)
#        else:
#            messages.error(self.request, 'You cannot delete this address!')
#            return HttpResponseRedirect(self.success_url)
#
#    def post(self, request, *args, **kwargs):
#        if request.POST.get('cancel'):
#            return HttpResponseRedirect(self.success_url)
#        return super(AddressDelete, self).post(request, *args, **kwargs)


#class OrganisationList(LoginRequiredMixin, ListView):
#    model = Organisation
#
#    def get_queryset(self):
#        qs = super(OrganisationList, self).get_queryset()
#        # Did we pass in a search string? If so, filter the queryset and return it.
#        if 'q' in self.request.GET and self.request.GET['q']:
#            query_str = self.request.GET['q']
#            # Replace single-quotes with double-quotes
#            query_str = query_str.replace("'", r'"')
#            # Filter by name and ABN fields.
#            query = get_query(query_str, ['name', 'abn'])
#            qs = qs.filter(query).distinct()
#        return qs

class PersonDetails(LoginRequiredMixin, DetailView):
    model = SystemUser 
    template_name = 'applications/person_details.html'

    def get(self, request, *args, **kwargs):
        # Rule: request user must be a delegate (or superuser).
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        self.object = self.get_object()
        if admin_staff is True:
             return super(PersonDetails, self).get(request, *args, **kwargs)
        elif request.user.id == self.object.ledger_id:
             return super(PersonDetails, self).get(request, *args, **kwargs)
        else:
               messages.error(self.request, 'You are not authorised to view.')
        return HttpResponseRedirect(reverse('home'))
    
    def get_object(self, queryset=None):
        """
        Return the object the view is displaying.
        """
        if queryset is None:
            queryset = self.get_queryset()

        ledger_id = self.kwargs.get('pk')
        if ledger_id is not None:
            queryset = queryset.filter(ledger_id=ledger_id)
        else:
            raise AttributeError(
                "Generic detail view %s must be called with an object "
                "ledger_id in the URLconf." % self.__class__.__name__
            )
        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404("No matching object found")
        return obj

    def get_queryset(self):
        qs = super(PersonDetails, self).get_queryset()
        # Did we pass in a search string? If so, filter the queryset and return it.
        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            # Replace single-quotes with double-quotes
            query_str = query_str.replace("'", r'"')
            # Filter by name and ABN fields.
            query = get_query(query_str, ['name', 'abn'])
            qs = qs.filter(query).distinct()
        return qs

    def get_context_data(self, **kwargs):
        context = super(PersonDetails, self).get_context_data(**kwargs)
        context['postal_address'] = SystemUserAddress.objects.get(system_user=context['systemuser'], address_type='postal_address')
        org = self.get_object()
#        context['user_is_delegate'] = Delegate.objects.filter(email_user=self.request.user.id, organisation=org).exists()
        context['nav_details'] = 'active'

        if "action" in self.kwargs:
             action=self.kwargs['action']
             # Navbar
             if action == "personal":
                 context['nav_details_personal'] = "active"
             elif action == "identification":
                 context['nav_details_identification'] = "active"
                 #context['person'] = SystemUser.objects.get(ledger_id=self.kwargs['pk'])
                 

             elif action == "address":
                 context['nav_details_address'] = "active"
             elif action == "contactdetails":
                 context['nav_details_contactdetails'] = "active"
             elif action == "companies":
                 context['nav_details_companies'] = "active"
                 user = SystemUser.objects.get(ledger_id=self.kwargs['pk'])
                 context['organisations'] = Delegate.objects.filter(email_user=user.ledger_id.id)

        return context

#class PersonOrgDelete(LoginRequiredMixin, UpdateView):
#    model = Organisation 
#    form_class = apps_forms.PersonOrgDeleteForm
#    template_name = 'applications/referral_delete.html'
#
#    def get(self, request, *args, **kwargs):
#        referral = self.get_object()
#        return super(PersonOrgDelete, self).get(request, *args, **kwargs)
#
#    def get_success_url(self, org_id):
#        return reverse('person_details_actions', args=(org_id,'companies'))
#
#    def post(self, request, *args, **kwargs):
#        if request.POST.get('cancel'):
#            return HttpResponseRedirect(reverse('person_details_actions', args=(self.kwargs['pk'],'companies')))
#        return super(PersonOrgDelete, self).post(request, *args, **kwargs)
#
#    def form_valid(self, form):
#        org = self.get_object()
#        org_id = org.id
#        org.delete()
#        # Record an action on the referral's application:
#        action = Action(
#            content_object=ref.application, user=self.request.user.id,
#            action='Organisation {} deleted'.format(org_id))
#        action.save()
#        return HttpResponseRedirect(self.get_success_url(self.pk))

class PersonOther(LoginRequiredMixin, DetailView):
    model = SystemUser
    template_name = 'applications/person_details.html'
    
    def get_object(self, queryset=None):
        """
        Return the object the view is displaying.
        """
        if queryset is None:
            queryset = self.get_queryset()

        ledger_id = self.kwargs.get('pk')
        if ledger_id is not None:
            queryset = queryset.filter(ledger_id=ledger_id)
        else:
            raise AttributeError(
                "Generic detail view %s must be called with an object "
                "ledger_id in the URLconf." % self.__class__.__name__
            )
        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404("No matching object found")
        return obj

    def get(self, request, *args, **kwargs):
        # Rule: request user must be a delegate (or superuser).
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        self.object = self.get_object()

        if admin_staff is True:
             return super(PersonOther, self).get(request, *args, **kwargs)
        #elif request.user.id == self.object.ledger_id:
        #     return super(PersonOther, self).get(request, *args, **kwargs)
        else:
               messages.error(self.request, 'You are not authorised')
        return HttpResponseRedirect(reverse('home'))

#    def get_queryset(self):
#        qs = super(PersonOther, self).get_queryset()
#        # Did we pass in a search string? If so, filter the queryset and return it.
#        if 'q' in self.request.GET and self.request.GET['q']:
#            query_str = self.request.GET['q']
#            # Replace single-quotes with double-quotes
#            query_str = query_str.replace("'", r'"')
#            # Filter by name and ABN fields.
#            query = get_query(query_str, ['name', 'abn'])
#            qs = qs.filter(query).distinct()
        #print self.template_name
#        return qs

    def get_context_data(self, **kwargs):
        context = super(PersonOther, self).get_context_data(**kwargs)

        org = self.get_object()
#       context['user_is_delegate'] = Delegate.objects.filter(email_user=self.request.user.id, organisation=org).exists()
        context['nav_other'] = 'active'

        if "action" in self.kwargs:
             action=self.kwargs['action']
             # Navbar
             if action == "applications":
                 user = SystemUser.objects.get(ledger_id=self.kwargs['pk'])
                 delegate = Delegate.objects.filter(email_user=user.ledger_id.id).values('organisation__id')

                 context['nav_other_applications'] = "active"
                 context['app'] = ''

                 APP_TYPE_CHOICES = []
                 APP_TYPE_CHOICES_IDS = []
                 for i in Application.APP_TYPE_CHOICES:
                     if i[0] in [5,6,7,8,9,10,11]:
                         skip = 'yes'
                     else:
                         APP_TYPE_CHOICES.append(i)
                         APP_TYPE_CHOICES_IDS.append(i[0])
                 context['app_apptypes'] = APP_TYPE_CHOICES

                 #context['app_appstatus'] = list(Application.APP_STATE_CHOICES)
                 context['app_appstatus'] = Application.APP_STATUS
                 search_filter = Q(applicant=self.kwargs['pk']) | Q(organisation__in=delegate)
                 if 'searchaction' in self.request.GET and self.request.GET['searchaction']:
                      query_str = self.request.GET['q']
                      query_obj = Q(pk__contains=query_str) | Q(title__icontains=query_str) | Q(organisation__name__icontains=query_str)
                      user_ids = SystemUser.objects.filter(email__icontains=query_str).exclude(ledger_id__isnull=True).values_list('ledger_id', flat=True)
                      if user_ids:
                          query_obj |= Q(applicant__in=user_ids)
                          query_obj |= Q(assignee__in=user_ids)
                      if self.request.GET['apptype'] != '':
                          search_filter &= Q(app_type=int(self.request.GET['apptype']))
                      else:
                          end = ''
                          # search_filter &= Q(app_type__in=APP_TYPE_CHOICES_IDS)

                      if self.request.GET['appstatus'] != '':
                           search_filter &= Q(status=int(self.request.GET['appstatus']))

                      if self.request.GET['wfstatus'] != '':
                           search_filter &= Q(route_status=self.request.GET['wfstatus'])
                           
                      #if self.request.GET['appstatus'] != '':
                      #    search_filter &= Q(state=int(self.request.GET['appstatus']))

#                      applications = Application.objects.filter(query_obj)
                      context['query_string'] = self.request.GET['q']

                      if self.request.GET['apptype'] != '':
                          context['apptype'] = int(self.request.GET['apptype'])
                      if 'appstatus' in self.request.GET:
                          if self.request.GET['appstatus'] != '':
                              context['appstatus'] = int(self.request.GET['appstatus'])
                      if 'wfstatus' in self.request.GET:
                          if self.request.GET['wfstatus'] != '':
                                context['wfstatus'] = self.request.GET['wfstatus']

                      if 'q' in self.request.GET and self.request.GET['q']:
                          query_str = self.request.GET['q']
                          query_str_split = query_str.split()
                          for se_wo in query_str_split:
                              search_filter &= Q(pk__contains=se_wo) | Q(title__contains=se_wo)

                      if 'from_date' in self.request.GET:
                           context['from_date'] = self.request.GET['from_date']
                           context['to_date'] = self.request.GET['to_date']
                           if self.request.GET['from_date'] != '':
                               from_date_db = datetime.strptime(self.request.GET['from_date'], '%d/%m/%Y').date()
                               search_filter &= Q(submit_date__gte=from_date_db)
                           if self.request.GET['to_date'] != '':
                               to_date_db = datetime.strptime(self.request.GET['to_date'], '%d/%m/%Y').date()
                               search_filter &= Q(submit_date__lte=to_date_db)


#                 print Q(Q(state__in=APP_TYPE_CHOICES_IDS) & Q(search_filter)) 
                 applications = Application.objects.filter(Q(app_type__in=APP_TYPE_CHOICES_IDS) & Q(search_filter) )[:200]
                 context['app_wfstatus'] = list(Application.objects.values_list('route_status',flat = True).distinct())
                 usergroups = self.request.user.get_system_group_permission(self.request.user.id)
                 context['app_list'] = []

                 for app in applications:
                      row = {}
                      row['may_assign_to_person'] = 'False'
                      row['app'] = app

            # Create a distinct list of applicants
            
            # if app.applicant:
            #     applicant = SystemUser.objects.get(ledger_id=app.applicant)
            #     if applicant.ledger_id in context['app_applicants']:
            #         donothing = ''
            #     else:
            #         context['app_applicants'][applicant.ledger_id] = applicant.legal_first_name + ' ' + applicant.legal_last_name
            #         context['app_applicants_list'].append({"id": applicant.ledger_id.id, "name": applicant.legal_first_name + ' ' + applicant.legal_last_name  })
            
            # end of creation

                      if app.group is not None:
                          if app.group.id in usergroups:
                              row['may_assign_to_person'] = 'True'
                      if app.applicant:
                        applicant = SystemUser.objects.get(ledger_id=app.applicant)
                        row['applicant'] = applicant            
                
                      if app.assignee:
                        assignee = SystemUser.objects.get(ledger_id=app.assignee)
                        row['assignee'] = assignee

                      if app.submitted_by:
                        submitted_by = SystemUser.objects.get(ledger_id=app.submitted_by)
                        row['submitted_by'] = submitted_by 
                      context['app_list'].append(row)
      

             elif action == "approvals":
                 context['nav_other_approvals'] = "active"
                 user = SystemUser.objects.get(ledger_id=self.kwargs['pk'])
                 delegate = Delegate.objects.filter(email_user=user.ledger_id.id).values('id')

                 search_filter = Q(applicant=self.kwargs['pk'], status=1 ) | Q(organisation__in=delegate)

                 APP_TYPE_CHOICES = []
                 APP_TYPE_CHOICES_IDS = []
                 for i in Application.APP_TYPE_CHOICES:
                     if i[0] in [5,6,7,8,9,10,11]:
                          skip = 'yes'
                     else:
                          APP_TYPE_CHOICES.append(i)
                          APP_TYPE_CHOICES_IDS.append(i[0])
                 context['app_apptypes']= APP_TYPE_CHOICES


                 if 'action' in self.request.GET and self.request.GET['action']:
                    query_str = self.request.GET['q']
                    search_filter = Q(pk__contains=query_str) | Q(title__icontains=query_str)
                    user_ids = SystemUser.objects.filter(email__icontains=query_str).exclude(ledger_id__isnull=True).values_list('ledger_id', flat=True)
                    if user_ids:
                        search_filter |= Q(applicant__in=user_ids)
                    if self.request.GET['apptype'] != '':
                        search_filter &= Q(app_type=int(self.request.GET['apptype']))
                    else:
                        search_filter &= Q(app_type__in=APP_TYPE_CHOICES_IDS)
 
                    if self.request.GET['appstatus'] != '':
                        search_filter &= Q(status=int(self.request.GET['appstatus']))

                    context['query_string'] = self.request.GET['q']

                    if self.request.GET['apptype'] != '':
                        context['apptype'] = int(self.request.GET['apptype'])
                    if 'appstatus' in self.request.GET:
                        if self.request.GET['appstatus'] != '':
                            context['appstatus'] = int(self.request.GET['appstatus'])

                    if 'q' in self.request.GET and self.request.GET['q']:
                       query_str = self.request.GET['q']
                       query_str_split = query_str.split()
                       for se_wo in query_str_split:
                           search_filter= Q(pk__contains=se_wo) | Q(title__contains=se_wo)

                    if 'from_date' in self.request.GET:
                         context['from_date'] = self.request.GET['from_date']
                         context['to_date'] = self.request.GET['to_date']
                         if self.request.GET['from_date'] != '':
                             from_date_db = datetime.strptime(self.request.GET['from_date'], '%d/%m/%Y').date()
                             search_filter &= Q(issue_date__gte=from_date_db)
                         if self.request.GET['to_date'] != '':
                             to_date_db = datetime.strptime(self.request.GET['to_date'], '%d/%m/%Y').date()
                             search_filter &= Q(issue_date__lte=to_date_db)
                           
                 approval = Approval.objects.filter(search_filter)[:200]

                 context['app_list'] = []
                 context['app_applicants'] = {}
                 context['app_applicants_list'] = []
                 context['app_appstatus'] = list(Approval.APPROVAL_STATE_CHOICES)

                 for app in approval:
                     row = {}
                     row['app'] = app
                     if app.applicant:
                         applicant = SystemUser.objects.get(ledger_id=app.applicant)
                         if applicant.ledger_id in context['app_applicants']:
                             donothing = ''
                         else:
                             if(applicant.legal_first_name and applicant.legal_last_name):
                                context['app_applicants'][app.applicant] = applicant.legal_first_name + ' ' + applicant.legal_last_name
                                context['app_applicants_list'].append({"id": applicant.ledger_id.id, "name": applicant.legal_first_name + ' ' + applicant.legal_last_name})

                     context['app_list'].append(row)

             elif action == "emergency":
                 context['nav_other_emergency'] = "active"
                 action=self.kwargs['action']
             # Navbar
                 context['app'] = ''

                 APP_TYPE_CHOICES = []
                 APP_TYPE_CHOICES_IDS = []
#                 for i in Application.APP_TYPE_CHOICES:
                     #                     if i[0] in [4,5,6,7,8,9,10,11]:
                         #                         skip = 'yes'
#                     else:
                         #                         APP_TYPE_CHOICES.append(i)
#                         APP_TYPE_CHOICES_IDS.append(i[0])

                 APP_TYPE_CHOICES.append('4')
                 APP_TYPE_CHOICES_IDS.append('4')
                 context['app_apptypes']= APP_TYPE_CHOICES

                 context['app_appstatus'] = list(Application.APP_STATE_CHOICES)
                 user = SystemUser.objects.get(ledger_id=self.kwargs['pk'])
                 delegate = Delegate.objects.filter(email_user=user.ledger_id.id).values('id')

                 search_filter = Q(applicant=self.kwargs['pk'], app_type=4) | Q(organisation__in=delegate)

                 if 'searchaction' in self.request.GET and self.request.GET['searchaction']:
                      query_str = self.request.GET['q']
                      query_obj = Q(pk__contains=query_str) | Q(title__icontains=query_str) | Q(organisation__name__icontains=query_str)
                      user_ids = SystemUser.objects.filter(email__icontains=query_str).exclude(ledger_id__isnull=True).values_list('ledger_id', flat=True)
                      if user_ids:
                            search_filter |= Q(applicant__in=user_ids)
                            search_filter |= Q(assignee__in=user_ids)
                      context['query_string'] = self.request.GET['q']

                      if self.request.GET['appstatus'] != '':
                          search_filter &= Q(state=int(self.request.GET['appstatus']))


                      if 'appstatus' in self.request.GET:
                          if self.request.GET['appstatus'] != '':
                              context['appstatus'] = int(self.request.GET['appstatus'])


                      if 'q' in self.request.GET and self.request.GET['q']:
                          query_str = self.request.GET['q']
                          query_str_split = query_str.split()
                          for se_wo in query_str_split:
                              search_filter= Q(pk__contains=se_wo) | Q(title__contains=se_wo)
               
                 applications = Application.objects.filter(search_filter)[:200]

#                print applications
                 usergroups = self.request.user.get_system_group_permission(self.request.user.id)
                 context['app_list'] = []
                 for app in applications:
                      row = {}
                      row['may_assign_to_person'] = 'False'
                      row['app'] = app

                    # Create a distinct list of applicants
                    
                    # if app.applicant:
                    #     applicant = SystemUser.objects.get(ledger_id=app.applicant)
                    #     if applicant.ledger_id in context['app_applicants']:
                    #         donothing = ''
                    #     else:
                    #         context['app_applicants'][applicant.ledger_id] = applicant.legal_first_name + ' ' + applicant.legal_last_name
                    #         context['app_applicants_list'].append({"id": applicant.ledger_id.id, "name": applicant.legal_first_name + ' ' + applicant.legal_last_name  })
                    
                    # end of creation

                      if app.group is not None:
                          if app.group.id in usergroups:
                              row['may_assign_to_person'] = 'True'
                      if app.applicant:
                        applicant = SystemUser.objects.get(ledger_id=app.applicant)
                        row['applicant'] = applicant 
                      context['app_list'].append(row)

             elif action == "clearance":
                 context['nav_other_clearance'] = "active"
                 if 'q' in self.request.GET and self.request.GET['q']:
                      context['query_string'] = self.request.GET['q']

                 user = SystemUser.objects.get(ledger_id=self.kwargs['pk'])
                 delegate = Delegate.objects.filter(email_user=user.ledger_id.id).values('id')
                 search_filter = Q(applicant=self.kwargs['pk']) | Q(organisation__in=delegate)

                 #items = Compliance.objects.filter(applicant=self.kwargs['pk']).order_by('due_date')

                 context['app_applicants'] = {}
                 context['app_applicants_list'] = []
                 context['app_apptypes'] = list(Application.APP_TYPE_CHOICES)

                 APP_STATUS_CHOICES = []
                 for i in Application.APP_STATE_CHOICES:
                     if i[0] in [1,11,16]:
                         APP_STATUS_CHOICES.append(i)

                 context['app_appstatus'] = list(APP_STATUS_CHOICES)

                 if 'action' in self.request.GET and self.request.GET['action']:
                      query_str = self.request.GET['q']

                      if 'q' in self.request.GET and self.request.GET['q']:
                          query_str = self.request.GET['q']
                          query_str_split = query_str.split()
                          for se_wo in query_str_split:
                              search_filter &= Q(pk__contains=se_wo) | Q(title__contains=se_wo)
                             
                      
                      if 'from_date' in self.request.GET:
                           context['from_date'] = self.request.GET['from_date']
                           context['to_date'] = self.request.GET['to_date']
                           if self.request.GET['from_date'] != '':
                               from_date_db = datetime.strptime(self.request.GET['from_date'], '%d/%m/%Y').date()
                               search_filter &= Q(due_date__gte=from_date_db)
                           if self.request.GET['to_date'] != '':
                               to_date_db = datetime.strptime(self.request.GET['to_date'], '%d/%m/%Y').date()
                               search_filter &= Q(due_date__lte=to_date_db) 
                 

                 items = Compliance.objects.filter(search_filter).order_by('due_date')[:100]
                 context['compliance'] = []
                 for compliance in items:
                      row = {}
                      row['compliance'] = compliance
                      if compliance.applicant:
                        applicant = SystemUser.objects.get(ledger_id=compliance.applicant)
                        row['applicant'] = applicant
                      context['compliance'].append(row)


                 #     query_obj = Q(pk__contains=query_str) | Q(title__icontains=query_str) | Q(applicant__email__icontains=query_str) | Q(assignee__email__icontains=query_str)
                 #     query_obj &= Q(app_type=4)

                 #     if self.request.GET['applicant'] != '':
                 #         query_obj &= Q(applicant=int(self.request.GET['applicant']))
                 #     if self.request.GET['appstatus'] != '':
                 #         query_obj &= Q(state=int(self.request.GET['appstatus']))

                 #     applications = Compliance.objects.filter(query_obj)
                 #     context['query_string'] = self.request.GET['q']

                 #if 'applicant' in self.request.GET:
                 #     if self.request.GET['applicant'] != '':
                 #         context['applicant'] = int(self.request.GET['applicant'])
                 #if 'appstatus' in self.request.GET:
                 #     if self.request.GET['appstatus'] != '':
                 #         context['appstatus'] = int(self.request.GET['appstatus'])
 
                 #usergroups = self.request.user.groups().all()
                 #context['app_list'] = []
                 #for item in items:
                 #     row = {}
                 #     row['may_assign_to_person'] = 'False'
                 #     row['app'] = item
                 #context['may_create'] = True
                 #processor = SystemGroup.objects.get(name='Processor')
                 # Rule: admin officers may self-assign applications.
                 #if processor in self.request.user.groups().all() or self.request.user.is_superuser:
                 #    context['may_assign_processor'] = True

        return context

class OrganisationDetails(LoginRequiredMixin, DetailView):
    model = Organisation
    template_name = 'applications/organisation_details.html'

    def get_organisation(self):
        return Organisation.objects.get(pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        # Rule: request user must be a delegate (or superuser).
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        org = self.get_organisation()

        if Delegate.objects.filter(email_user=request.user.id, organisation=org).exists():
           donothing = ""
        else:
           if admin_staff is True:
               return super(OrganisationDetails, self).get(request, *args, **kwargs)
           else:
               messages.error(self.request, 'You are not authorised to view this organisation.')
               return HttpResponseRedirect(reverse('home'))

        return super(OrganisationDetails, self).get(request, *args, **kwargs)


    def get_queryset(self):
        qs = super(OrganisationDetails, self).get_queryset()
        # Did we pass in a search string? If so, filter the queryset and return it.
        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            # Replace single-quotes with double-quotes
            query_str = query_str.replace("'", r'"')
            # Filter by name and ABN fields.
            query = get_query(query_str, ['name', 'abn'])
            qs = qs.filter(query).distinct()
        return qs

    def get_context_data(self, **kwargs):
        context = super(OrganisationDetails, self).get_context_data(**kwargs)
        org = self.get_object()
        context['user_is_delegate'] = Delegate.objects.filter(email_user=self.request.user.id, organisation=org).exists()
        context['nav_details'] = 'active'

        if "action" in self.kwargs:
             action=self.kwargs['action']
             # Navbar
             if action == "company":
                 context['nav_details_company'] = "active"
             elif action == "certofincorp":
                 context['nav_details_certofincorp'] = "active"
                 org = Organisation.objects.get(id=self.kwargs['pk'])
                 if OrganisationExtras.objects.filter(organisation=org.id).exists():
                     context['org_extras'] = OrganisationExtras.objects.get(organisation=org.id)
                 context['org'] = org
             elif action == "address":
                 context['nav_details_address'] = "active"
             elif action == "contactdetails":
                 context['nav_details_contactdetails'] = "active"
                 org = Organisation.objects.get(id=self.kwargs['pk'])
                 context['organisation_contacts'] = OrganisationContact.objects.filter(organisation=org)
             elif action == "linkedperson":
                 context['nav_details_linkedperson'] = "active"
                 org = Organisation.objects.get(id=self.kwargs['pk'])
                 linkedpersons = Delegate.objects.filter(organisation=org)
                 if OrganisationExtras.objects.filter(organisation=org.id).exists():
                    context['org_extras'] = OrganisationExtras.objects.get(organisation=org.id)

                # Recreate the linkedpersons list with an additional 'user' key
                 context['linkedpersons'] = []
                 for lp in linkedpersons:
                     if lp.email_user:
                        try:
                            user = SystemUser.objects.get(ledger_id=lp.email_user)
                        except SystemUser.DoesNotExist:
                            user = None  # Handle the case where no SystemUser is found
                        context['linkedpersons'].append({
                            'delegate': lp,
                            'user': user
                        })

        return context


class OrganisationOther(LoginRequiredMixin, DetailView):
    model = Organisation
    template_name = 'applications/organisation_details.html'

    def get(self, request, *args, **kwargs):
        # Rule: request user must be a delegate (or superuser).
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        org = self.get_object()

        if Delegate.objects.filter(email_user=request.user.id, organisation=org).exists():
           donothing = ""
        else:
           if admin_staff is True:
               return super(OrganisationOther, self).get(request, *args, **kwargs)
           else:
               messages.error(self.request, 'You are not authorised to view this organisation.')
               return HttpResponseRedirect(reverse('home'))

        return super(OrganisationOther, self).get(request, *args, **kwargs)

    # def get_queryset(self):
    #     qs = super(OrganisationOther, self).get_queryset()
    #     # Did we pass in a search string? If so, filter the queryset and return it.
    #     if 'q' in self.request.GET and self.request.GET['q']:
    #         query_str = self.request.GET['q']
    #         # Replace single-quotes with double-quotes
    #         query_str = query_str.replace("'", r'"')
    #         # Filter by name and ABN fields.
    #         query = get_query(query_str, ['name', 'abn'])
    #         qs = qs.filter(query).distinct()
    #     #print self.template_name
    #     return qs

    def get_context_data(self, **kwargs):
        context = super(OrganisationOther, self).get_context_data(**kwargs)
        org = self.get_object()
        context['user_is_delegate'] = Delegate.objects.filter(email_user=self.request.user.id, organisation=org).exists()
        context['nav_other'] = 'active'

        if "action" in self.kwargs:
             action=self.kwargs['action']

             # Navbar
             if action == "applications":
                 context['nav_other_applications'] = "active"
                 context['app'] = ''

                 APP_TYPE_CHOICES = []
                 APP_TYPE_CHOICES_IDS = []
                 for i in Application.APP_TYPE_CHOICES:
                     if i[0] in [4,5,6,7,8,9,10,11]:
                         skip = 'yes'
                     else:
                         APP_TYPE_CHOICES.append(i)
                         APP_TYPE_CHOICES_IDS.append(i[0])
                 context['app_apptypes'] = APP_TYPE_CHOICES

                 context['app_appstatus'] = list(Application.APP_STATE_CHOICES)
                 search_filter = Q(organisation=self.kwargs['pk'])
                 
                 if 'searchaction' in self.request.GET and self.request.GET['searchaction']:
                      query_str = self.request.GET['q']
                      query_obj = Q(pk__contains=query_str) | Q(title__icontains=query_str) | Q(organisation__name__icontains=query_str)
                      user_ids = SystemUser.objects.filter(email__icontains=query_str).exclude(ledger_id__isnull=True).values_list('ledger_id', flat=True)
                      if user_ids:
                            query_obj |= Q(applicant__in=user_ids)
                            query_obj |= Q(assignee__in=user_ids)
                      if self.request.GET['apptype'] != '':
                          search_filter &= Q(app_type=int(self.request.GET['apptype']))
                      else:
                          end = ''
                          # search_filter &= Q(app_type__in=APP_TYPE_CHOICES_IDS)


                      if self.request.GET['appstatus'] != '':
                          search_filter &= Q(state=int(self.request.GET['appstatus']))

#                      applications = Application.objects.filter(query_obj)
                      context['query_string'] = self.request.GET['q']

                      if self.request.GET['apptype'] != '':
                          context['apptype'] = int(self.request.GET['apptype'])
                      if 'appstatus' in self.request.GET:
                          if self.request.GET['appstatus'] != '':
                              context['appstatus'] = int(self.request.GET['appstatus'])

                      if 'q' in self.request.GET and self.request.GET['q']:
                          query_str = self.request.GET['q']
                          query_str_split = query_str.split()
                          for se_wo in query_str_split:
                              search_filter = Q(pk__contains=se_wo) | Q(title__contains=se_wo)
                 applications = Application.objects.filter(search_filter)[:200]
                 usergroups = self.request.user.get_system_group_permission(self.request.user.id)
                 context['app_list'] = []

                 for app in applications:
                      row = {}
                      row['may_assign_to_person'] = 'False'
                      row['app'] = app

                      if app.group is not None:
                          if app.group.id in usergroups:
                              row['may_assign_to_person'] = 'True'
                      if app.applicant is not None:
                        context['applicant'] = SystemUser.objects.get(ledger_id=app.applicant)
                      if app.assignee is not None:
                        context['assignee'] = SystemUser.objects.get(ledger_id=app.assignee)

                      context['app_list'].append(row)
                      

             elif action == "approvals":
                 context['nav_other_approvals'] = "active"
                 search_filter = Q(organisation__in=self.kwargs['pk'], status=1)

                 APP_TYPE_CHOICES = []
                 APP_TYPE_CHOICES_IDS = []
                 for i in Application.APP_TYPE_CHOICES:
                     if i[0] in [4,5,6,7,8,9,10,11]:
                          skip = 'yes'
                     else:
                          APP_TYPE_CHOICES.append(i)
                          APP_TYPE_CHOICES_IDS.append(i[0])
                 context['app_apptypes']= APP_TYPE_CHOICES


                 if 'action' in self.request.GET and self.request.GET['action']:
                    query_str = self.request.GET['q']
                    search_filter = Q(pk__contains=query_str) | Q(title__icontains=query_str)
                    user_ids = SystemUser.objects.filter(email__icontains=query_str).exclude(ledger_id__isnull=True).values_list('ledger_id', flat=True)
                    if user_ids:
                        query_obj |= Q(applicant__in=user_ids)
                    if self.request.GET['apptype'] != '':
                        search_filter &= Q(app_type=int(self.request.GET['apptype']))
                    else:
                        search_filter &= Q(app_type__in=APP_TYPE_CHOICES_IDS)

                    if self.request.GET['appstatus'] != '':
                        search_filter &= Q(status=int(self.request.GET['appstatus']))

                    context['query_string'] = self.request.GET['q']

                    if self.request.GET['apptype'] != '':
                        context['apptype'] = int(self.request.GET['apptype'])
                    if 'appstatus' in self.request.GET:
                        if self.request.GET['appstatus'] != '':
                            context['appstatus'] = int(self.request.GET['appstatus'])

                    if 'q' in self.request.GET and self.request.GET['q']:
                       query_str = self.request.GET['q']
                       query_str_split = query_str.split()
                       for se_wo in query_str_split:
                           search_filter= Q(pk__contains=se_wo) | Q(title__contains=se_wo)
                 approval = Approval.objects.filter(search_filter)[:200]

                 context['app_list'] = []
                 context['app_applicants'] = {}
                 context['app_applicants_list'] = []
                 context['app_appstatus'] = list(Approval.APPROVAL_STATE_CHOICES)
                 for app in approval:
                     row = {}
                     row['app'] = app
                     row['approval_url'] = app.approval_url
                     
                    # Create a distinct list of applicants
                     if app.applicant:
                        applicant = SystemUser.objects.get(ledger_id=app.applicant)
                        if applicant.ledger_id in context['app_applicants']:
                            donothing = ''
                        else:
                            if(applicant.legal_first_name and applicant.legal_last_name):
                                context['app_applicants'][applicant.ledger_id] = applicant.legal_first_name + ' ' + applicant.legal_last_name
                                context['app_applicants_list'].append({"id": applicant.ledger_id.id, "name": applicant.legal_first_name + ' ' + applicant.legal_last_name  })
                    # end of creation

                     context['app_list'].append(row)

             elif action == "emergency":
                 context['nav_other_emergency'] = "active"
                 action=self.kwargs['action']
                 context['app'] = ''

                 APP_TYPE_CHOICES = []
                 APP_TYPE_CHOICES_IDS = []
                 APP_TYPE_CHOICES.append('4')
                 APP_TYPE_CHOICES_IDS.append('4')
                 context['app_apptypes']= APP_TYPE_CHOICES
                 context['app_appstatus'] = list(Application.APP_STATE_CHOICES)
                 #user = EmailUser.objects.get(id=self.kwargs['pk'])
                 #delegate = Delegate.objects.filter(email_user=user).values('id')
                 search_filter = Q(organisation=self.kwargs['pk'], app_type=4)

                 if 'searchaction' in self.request.GET and self.request.GET['searchaction']:
                      query_str = self.request.GET['q']
                      query_obj = Q(pk__contains=query_str) | Q(title__icontains=query_str) | Q(organisation__name__icontains=query_str)
                      user_ids = SystemUser.objects.filter(email__icontains=query_str).exclude(ledger_id__isnull=True).values_list('ledger_id', flat=True)
                      if user_ids:
                            query_obj |= Q(applicant__in=user_ids)
                            query_obj |= Q(assignee__in=user_ids)
                      context['query_string'] = self.request.GET['q']

                      if self.request.GET['appstatus'] != '':
                          search_filter &= Q(state=int(self.request.GET['appstatus']))


                      if 'appstatus' in self.request.GET:
                          if self.request.GET['appstatus'] != '':
                              context['appstatus'] = int(self.request.GET['appstatus'])


                      if 'q' in self.request.GET and self.request.GET['q']:
                          query_str = self.request.GET['q']
                          query_str_split = query_str.split()
                          for se_wo in query_str_split:
                              search_filter= Q(pk__contains=se_wo) | Q(title__contains=se_wo)

                 applications = Application.objects.filter(search_filter)[:200]

#                print applications
                 usergroups = self.request.user.get_system_group_permission(self.request.user.id)
                 context['app_list'] = []
                 for app in applications:
                      row = {}
                      row['may_assign_to_person'] = 'False'
                      row['app'] = app

                      if app.group is not None:
                          if app.group.id in usergroups:
                              row['may_assign_to_person'] = 'True'
                      if app.applicant is not None:
                        context['applicant'] = SystemUser.objects.get(ledger_id=app.applicant)
                      if app.assignee is not None:
                        context['assignee'] = SystemUser.objects.get(ledger_id=app.assignee)
                      
                      context['app_list'].append(row)

             elif action == "clearance":
                 context['nav_other_clearance'] = "active"
                 context['query_string'] = ''

                 if 'q' in self.request.GET:
                     context['query_string'] = self.request.GET['q']

                 search_filter = Q(organisation=self.kwargs['pk']) 

                 items = Compliance.objects.filter(applicant=self.kwargs['pk']).order_by('due_date')

                 context['app_applicants'] = {}
                 context['app_applicants_list'] = []
                 context['app_apptypes'] = list(Application.APP_TYPE_CHOICES)

                 APP_STATUS_CHOICES = []
                 for i in Application.APP_STATE_CHOICES:
                     if i[0] in [1,11,16]:
                         APP_STATUS_CHOICES.append(i)

                 context['app_appstatus'] = list(APP_STATUS_CHOICES)
                 context['compliance'] = []
                 for compliance in items:
                      row = {}
                      row['compliance'] = compliance
                      if compliance.applicant:
                        applicant = SystemUser.objects.get(ledger_id=compliance.applicant)
                        row['applicant'] = applicant
                      if compliance.assignee:
                        assignee = SystemUser.objects.get(ledger_id=compliance.assignee)
                        row['assignee'] = assignee
                      context['compliance'].append(row)


        return context


#class OrganisationCreate(LoginRequiredMixin, CreateView):
#    """A view to create a new Organisation.
#    """
#    form_class = apps_forms.OrganisationForm
#    template_name = 'accounts/organisation_form.html'
#
#    def get_context_data(self, **kwargs):
#        context = super(OrganisationCreate, self).get_context_data(**kwargs)
#        context['action'] = 'Create'
#        return context
#
#    def post(self, request, *args, **kwargs):
#        if request.POST.get('cancel'):
#            return HttpResponseRedirect(reverse('organisation_list'))
#        return super(OrganisationCreate, self).post(request, *args, **kwargs)
#
#    def form_valid(self, form):
#        self.obj = form.save()
#        # Assign the creating user as a delegate to the new organisation.
#        Delegate.objects.create(email_user=self.request.user.id, organisation=self.obj)
#        messages.success(self.request, 'New organisation created successfully!')
#        return HttpResponseRedirect(reverse('organisation_detail', args=(self.obj.pk,)))


#class OrganisationUserCreate(LoginRequiredMixin, CreateView):
#    """A view to create a new Organisation.
#    """
#    form_class = apps_forms.OrganisationForm
#    template_name = 'accounts/organisation_form.html'
#
#    def get_context_data(self, **kwargs):
#        context = super(OrganisationUserCreate, self).get_context_data(**kwargs)
#        context['action'] = 'Create'
#        return context
#
#    def post(self, request, *args, **kwargs):
#        if request.POST.get('cancel'):
#            return HttpResponseRedirect(reverse('organisation_list'))
#        return super(OrganisationUserCreate, self).post(request, *args, **kwargs)
#
#    def form_valid(self, form):
#        self.obj = form.save()
#        # Assign the creating user as a delegate to the new organisation.
#        user = EmailUser.objects.get(id=self.kwargs['pk'])
#        Delegate.objects.create(email_user=user, organisation=self.obj)
#        messages.success(self.request, 'New organisation created successfully!')
#        return HttpResponseRedirect(reverse('organisation_detail', args=(self.obj.pk,)))

#class OrganisationDetail(LoginRequiredMixin, DetailView):
#    model = Organisation
#
#    def get_context_data(self, **kwargs):
#        context = super(OrganisationDetail, self).get_context_data(**kwargs)
#        org = self.get_object()
#        context['user_is_delegate'] = Delegate.objects.filter(email_user=self.request.user.id, organisation=org).exists()
#        return context

class OrganisationUpdate(LoginRequiredMixin, UpdateView):
    """A view to update an Organisation object.
    """
    model = Organisation
    form_class = apps_forms.OrganisationForm

    def get(self, request, *args, **kwargs):
        # Rule: request user must be a delegate (or superuser).
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        org = self.get_object()

        if Delegate.objects.filter(email_user=request.user.id, organisation=org).exists():
            pass 
        else:
           if admin_staff is True:
               return super(OrganisationUpdate, self).get(request, *args, **kwargs)
           else:
               messages.error(self.request, 'You are not authorised.')
               return HttpResponseRedirect(reverse('home'))

        return super(OrganisationUpdate, self).get(request, *args, **kwargs)


#    def get(self, request, *args, **kwargs):
#        # Rule: only a delegated user can update an organisation.
#        if not Delegate.objects.filter(email_user=request.user.id, organisation=self.get_object()).exists():
#            messages.warning(self.request, 'You are not authorised to update this organisation. Please request delegated authority if required.')
#            return HttpResponseRedirect(self.get_success_url())
#        return super(OrganisationUpdate, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(OrganisationUpdate, self).get_context_data(**kwargs)
        context['action'] = 'Update'
        return context

    def get_success_url(self):
        return reverse('organisation_details_actions', args=(self.kwargs['pk'],'company'))

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.kwargs['pk'],'company')))
        return super(OrganisationUpdate, self).post(request, *args, **kwargs)

class OrganisationContactCreate(LoginRequiredMixin, CreateView):
    """A view to update an Organisation object.
    """
    #model = OrganisationContact
    form_class = apps_forms.OrganisationContactForm
    template_name = 'applications/organisation_contact_form.html'

    def get(self, request, *args, **kwargs):
        # Rule: request user must be a delegate (or superuser).
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        org = Organisation.objects.get(id=self.kwargs['pk'])

        if Delegate.objects.filter(email_user=request.user.id, organisation=org).exists():
            pass
        else:
           if admin_staff is True:
               return super(OrganisationContactCreate, self).get(request, *args, **kwargs)
           else:
               messages.error(self.request, 'You are not authorised.')
               return HttpResponseRedirect(reverse('home'))

        return super(OrganisationContactCreate, self).get(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(OrganisationContactCreate, self).get_context_data(**kwargs)
        context['action'] = 'Create'
#        print self.get_object().pk
#        context['organisation'] = self.get_object().pk 
        return context

    def get_initial(self):
        initial = super(OrganisationContactCreate, self).get_initial()
        initial['organisation'] = self.kwargs['pk']
        # print 'dsf dsaf dsa'
        return initial

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.kwargs['pk'],'contactdetails')))
        return super(OrganisationContactCreate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.obj = form.save(commit=False)
        org = Organisation.objects.get(id=self.kwargs['pk'])
        self.obj.organisation = org
        self.obj.save()
        # Assign the creating user as a delegate to the new organisation.
        messages.success(self.request, 'Organisation contact created successfully!')
        return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.kwargs['pk'], 'contactdetails')))

class OrganisationContactUpdate(LoginRequiredMixin, UpdateView):
    """A view to update an Organisation object.
    """
    model = OrganisationContact
    form_class = apps_forms.OrganisationContactForm
    template_name = 'applications/organisation_contact_form.html'


    def get(self, request, *args, **kwargs):
        # Rule: request user must be a delegate (or superuser).
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        self.object = self.get_object()

        if Delegate.objects.filter(email_user=request.user.id, organisation=self.object.organisation).exists():
            pass
        else:
           if admin_staff is True:
               return super(OrganisationContactUpdate, self).get(request, *args, **kwargs)
           else:
               messages.error(self.request, 'You are not authorised.')
               return HttpResponseRedirect(reverse('home'))

        return super(OrganisationContactUpdate, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(OrganisationContactUpdate, self).get_context_data(**kwargs)
        context['action'] = 'Update'
        return context

    def get_initial(self):
        initial = super(OrganisationContactUpdate, self).get_initial()
        return initial

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.get_object().organisation.id,'contactdetails')))
        return super(OrganisationContactUpdate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.obj = form.save()
        # Assign the creating user as a delegate to the new organisation.
        messages.success(self.request, 'Organisation contact updated successfully!')
        return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.get_object().organisation.id, 'contactdetails')))



class OrganisationAddressCreate(LoginRequiredMixin, CreateView):
    """A view to create a new address for an Organisation.
    """
    model = OrganisationAddress
    form_class = apps_forms.OrganisationAddressForm2
    template_name = 'accounts/address_form.html'

    def get_context_data(self, **kwargs):
        context = super(OrganisationAddressCreate, self).get_context_data(**kwargs)
        org = Organisation.objects.get(pk=self.kwargs['pk'])
        context['principal'] = org.name
        return context

    def form_valid(self, form):
        self.obj = form.save(commit=False)
        # Attach the new address to the organisation.
        org = Organisation.objects.get(pk=self.kwargs['pk'])
        # ledger has a manadorary userfield. ( Mandatory should probably be removed)
        self.obj.user = self.request.user.id
        self.obj.organisation = org
        self.obj.save()
        
        if self.kwargs['type'] == 'postal':
            org.postal_address = self.obj
        elif self.kwargs['type'] == 'billing':
            org.billing_address = self.obj
        org.save()
        return HttpResponseRedirect(reverse('organisation_details_actions', args=(self.kwargs['pk'],'address')))
        #return HttpResponseRedirect(reverse('organisation_detail', args=(org.pk,)))


#class RequestDelegateAccess(LoginRequiredMixin, FormView):
#    """A view to allow a user to request to be added to an organisation as a delegate.
#    This view sends an email to all current delegates, any of whom may confirm the request.
#    """
#    form_class = apps_forms.DelegateAccessForm
#    template_name = 'accounts/request_delegate_access.html'
#
#    def get_organisation(self):
#        return Organisation.objects.get(pk=self.kwargs['pk'])
#
#    def get(self, request, *args, **kwargs):
#        # Rule: redirect if the user is already a delegate.
#        org = self.get_organisation()
#        if Delegate.objects.filter(email_user=request.user.id, organisation=org).exists():
#            messages.warning(self.request, 'You are already a delegate for this organisation!')
#            return HttpResponseRedirect(self.get_success_url())
#        return super(RequestDelegateAccess, self).get(request, *args, **kwargs)
#
#    def get_context_data(self, **kwargs):
#        context = super(RequestDelegateAccess, self).get_context_data(**kwargs)
#        context['organisation'] = self.get_organisation()
#        return context
#
#    def get_success_url(self):
#        return reverse('organisation_detail', args=(self.get_organisation().pk,))
#
#    def post(self, request, *args, **kwargs):
#        if request.POST.get('cancel'):
#            return HttpResponseRedirect(self.get_success_url())
#        # For each existing organisation delegate user, send an email that
#        # contains a unique URL to confirm the request. The URL consists of the
#        # requesting user PK (base 64-encoded) plus a unique token for that user.
#        org = self.get_organisation()
#        delegates = Delegate.objects.filter(email_user=request.user.id, organisation=org)
#        if not delegates.exists():
#            # In the event that an organisation has no delegates, the request
#            # will be sent to all users in the "Processor" group.
#            processor = SystemGroup.objects.get(name='Processor')
#            recipients = [i.email for i in EmailUser.objects.filter(groups__in=[processor])]
#        else:
#            recipients = [i.emailuser.email for i in delegates]
#        user = self.request.user
#        uid = urlsafe_base64_encode(force_bytes(user.pk))
#        # Note that the token generator uses the requesting user object to generate a hash.
#        # This means that if the user object changes (e.g. they log out and in again),
#        # the hash will be invalid. Therefore, this request/response needs to occur
#        # fairly promptly to work.
#        token = default_token_generator.make_token(user)
#        url = reverse('confirm_delegate_access', args=(org.pk, uid, token))
#        url = request.build_absolute_uri(url)
#        subject = 'Delegate access request for {}'.format(org.name)
#        message = '''The following user has requested delegate access for {}: {}\n
#        Click here to confirm and grant this access request:\n{}'''.format(org.name, user, url)
#        html_message = '''<p>The following user has requested delegate access for {}: {}</p>
#        <p><a href="{}">Click here</a> to confirm and grant this access request.</p>'''.format(org.name, user, url)
#        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False, html_message=html_message)
#        # Send a request email to the recipients asynchronously.
#        # NOTE: the lines below should remain commented until (if) async tasking is implemented in prod.
#        #from django_q.tasks import async
#        #async(
#        #    'django.core.mail.send_mail', subject, message,
#        #    settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=True, html_message=html_message,
#        #    hook='log_task_result')
#        #messages.success(self.request, 'An email requesting delegate access for {} has been sent to existing delegates.'.format(org.name))
#        # Generate an action record:
#        action = Action(content_object=org, user=user, action='Requested delegate access')
#        action.save()
#        return super(RequestDelegateAccess, self).post(request, *args, **kwargs)


#class ConfirmDelegateAccess(LoginRequiredMixin, FormView):
#    form_class = apps_forms.DelegateAccessForm
#    template_name = 'accounts/confirm_delegate_access.html'
#
#    def get_organisation(self):
#        return Organisation.objects.get(pk=self.kwargs['pk'])
#
#    def get(self, request, *args, **kwargs):
#        # Rule: request user must be an existing delegate.
#        org = self.get_organisation()
#        delegates = Delegate.objects.filter(email_user=request.user.id, organisation=org)
#        if delegates.exists():
#            uid = urlsafe_base64_decode(self.kwargs['uid'])
#            user = EmailUser.objects.get(pk=uid)
#            token = default_token_generator.check_token(user, self.kwargs['token'])
#            if token:
#                return super(ConfirmDelegateAccess, self).get(request, *args, **kwargs)
#            else:
#                messages.warning(self.request, 'The request delegate token is no longer valid.')
#        else:
#            messages.warning(self.request, 'You are not authorised to confirm this request!')
#        return HttpResponseRedirect(reverse('user_account'))
#
#    def get_context_data(self, **kwargs):
#        context = super(ConfirmDelegateAccess, self).get_context_data(**kwargs)
#        context['organisation'] = self.get_organisation()
#        uid = urlsafe_base64_decode(self.kwargs['uid'])
#        context['requester'] = EmailUser.objects.get(pk=uid)
#        return context
#
#    def get_success_url(self):
#        return reverse('organisation_detail', args=(self.get_organisation().pk,))
#
#    def post(self, request, *args, **kwargs):
#        uid = urlsafe_base64_decode(self.kwargs['uid'])
#        req_user = EmailUser.objects.get(pk=uid)
#        token = default_token_generator.check_token(req_user, self.kwargs['token'])
#        # Change the requesting user state to expire the token.
#        req_user.last_login = req_user.last_login + timedelta(seconds=1)
#        req_user.save()
#        if request.POST.get('cancel'):
#            return HttpResponseRedirect(self.get_success_url())
#        if token:
#            org = self.get_organisation()
#            Delegate.objects.create(email_user=req_user, organisation=org)
#            messages.success(self.request, '{} has been added as a delegate for {}.'.format(req_user, org.name))
#        else:
#            messages.warning(self.request, 'The request delegate token is no longer valid.')
#        return HttpResponseRedirect(self.get_success_url())


class UnlinkDelegate(LoginRequiredMixin, FormView):
    form_class = apps_forms.UnlinkDelegateForm
    template_name = 'accounts/confirm_unlink_delegate.html'

    def get_organisation(self):
        return Organisation.objects.get(pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        # Rule: request user must be a delegate (or superuser).
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']

        org = self.get_organisation()
        if Delegate.objects.filter(email_user=self.kwargs['user_id'], organisation=org).exists():
           pass 
        else:
           messages.error(self.request, 'User not found')
           return HttpResponseRedirect(self.get_success_url())

        if Delegate.objects.filter(email_user=request.user.id, organisation=org).exists():
           donothing = ""
        else:
           if admin_staff is True:
               return super(UnlinkDelegate, self).get(request, *args, **kwargs)
           else:
               messages.error(self.request, 'You are not authorised to unlink a delegated user for {}'.format(org.name))
               return HttpResponseRedirect(self.get_success_url())

        return super(UnlinkDelegate, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UnlinkDelegate, self).get_context_data(**kwargs)
        context['delegate'] = SystemUser.objects.get(ledger_id=self.kwargs['user_id'])
        return context

    def get_success_url(self):
        return reverse('organisation_details_actions', args=(self.get_organisation().pk,'linkedperson'))

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(self.get_success_url())
        return super(UnlinkDelegate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        # Unlink the specified user from the organisation.
        org = self.get_organisation()
        user = SystemUser.objects.get(ledger_id=self.kwargs['user_id'])
        delegateorguser = Delegate.objects.get(email_user=user.ledger_id.id, organisation=org)
        delegateorguser.delete()
#        Delegate.objects.delete(email_user=user, organisation=org)
        messages.success(self.request, '{} has been removed as a delegate for {}.'.format(user, org.name))
        # Generate an action record:
        action = Action(content_object=org, user=self.request.user.id,
            action='Unlinked delegate access for {} {}'.format(user.legal_first_name, user.legal_last_name))
        action.save()
        return HttpResponseRedirect(self.get_success_url())

class BookingSuccessView(TemplateView):
    template_name = 'applications/success.html'

    def get(self, request, booking_id, *args, **kwargs):
        print ("BOOKING SUCCESS")
        
        context_processor = template_context(self.request)
        basket = None
        context = {}
        print ("START TEST")
        if 'test' in request.session:
            print (request.session['test'])
    
        print ("END TEST")
        # print (request.session['basket_id'])    
        print (request.session['application_id'])
        checkout_routeid  = request.session['routeid']

        app = Application.objects.get(id=request.session['application_id'])
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()
        flowcontext = {}
        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)
        flowcontext = flow.getRequired(flowcontext, app.routeid, workflowtype)
        actions = flow.getAllRouteActions(app.routeid, workflowtype)

        route = {} 
        if app.routeid == checkout_routeid:
            for a in actions:
                 if a['payment'] == 'success':
                     route = a 
            #route = flow.getNextRouteObj('payment', app.routeid, workflowtype)
            print ("PAYMENT ROUTE")
            print (route)
            groupassignment = SystemGroup.objects.get(name=DefaultGroups['grouplink'][route['routegroup']])
            app.routeid = route["route"]
            app.state = route["state"]
            app.group = groupassignment
            app.assignee = None
            app.route_status = flow.json_obj[route["route"]]['title']
            app.save()

        
        utils.application_lodgment_info(self.request,app)
        ## Success message.
        #msg = """Your {0} application has been successfully submitted. The application
        #number is: <strong>WO-{1}</strong>.<br>
        #Please note that routine applications take approximately 4-6 weeks to process.<br>
        #If any information is unclear or missing, Parks and Wildlife may return your
        #application to you to amend or complete.<br>
        #The assessment process includes a 21-day external referral period. During this time
        #your application may be referred to external departments, local government
        #agencies or other stakeholders. Following this period, an internal report will be
        #produced by an officer for approval by the Manager, Rivers and Estuaries Division,
        #to determine the outcome of your application.<br>
        #You will be notified by email once your {0} application has been determined and/or
        #further action is required.""".format(app.get_app_type_display(), app.pk)
        #messages.success(self.request, msg)
        #emailcontext = {}
        #emailcontext['app'] = app
        #emailcontext['application_name'] = Application.APP_TYPE_CHOICES[app.app_type]
        #emailcontext['person'] = app.submitted_by
        #emailcontext['body'] = msg
        #sendHtmlEmail([app.submitted_by.email], emailcontext['application_name'] + ' application submitted ', emailcontext, 'application-lodged.html', None, None, None)

        return render(request, self.template_name, context)


class BookingSuccessViewPreload(APIView):
    def get(self, request, booking_id, booking_hash):
        #booking_hash=request.GET.get('booking_hash',None)
        #booking_id = request.GET.get('booking_id', None)
        jsondata={"status": "error completing booking"}
        if booking_hash:
            try: 
                    booking = Booking.objects.get(id=booking_id,booking_hash=booking_hash)
                    basket = Basket.objects.filter(status='Submitted', booking_reference=settings.BOOKING_PREFIX+'-'+str(booking.id)).order_by('-id')[:1]
                    #TODO: check this booking_reference for statdev
                    if basket.count() > 0:
                        pass
                    else:
                        raise ValidationError('Error unable to find basket')
                    jsondata={"status": "success"}
            except Exception as e:
                print ("EXCEPTION")
                print (e)
                jsondata={"status": "error binding"}
        response = HttpResponse(json.dumps(jsondata), content_type='application/json')
        return response


class InvoicePDFView(InvoiceOwnerMixin,View):

    def get(self, request, *args, **kwargs):
        invoice = get_object_or_404(Invoice, reference=self.kwargs['reference'])
        response = HttpResponse(content_type='application/pdf')
        tc = template_context(request)
        response.write(create_invoice_pdf_bytes('invoice.pdf',invoice, request, tc))
        return response

    def get_object(self):
        invoice = get_object_or_404(Invoice, reference=self.kwargs['reference'])
        return invoice

class ApplicationBooking(LoginRequiredMixin, FormView):

    model = Application 
    form_class = apps_forms.PaymentDetailForm
    template_name = 'applications/application_payment_details_form.html'

    def render_page(self, request, booking, form, show_errors=False):
        booking_mooring = None
        booking_total = '0.00'
        #application_fee = ApplicationLicenceFee.objects.filter(app_type=booking['app'].app_type)
        to_date = datetime.now()
        application_fee = None
        if ApplicationLicenceFee.objects.filter(app_type=booking['app'].app_type,start_dt__lte=to_date, end_dt__gte=to_date).count() > 0:
            application_fee = ApplicationLicenceFee.objects.filter(app_type=booking['app'].app_type,start_dt__lte=to_date, end_dt__gte=to_date)[0]
            
        print ("APPLICATION FEE") 
        
        #lines.append(booking_change_fees)
        return render(request, self.template_name, {
            'form': form,
            'booking': booking,
            'application_fee': application_fee
        })

    def get_context_data(self, **kwargs):
        context = super(ApplicationBooking, self).get_context_data(**kwargs)
        application_fee = None

        to_date = datetime.now()
        pk=self.kwargs['pk']
        app = Application.objects.get(pk=pk)
        booking = {'app': app}
        fee_total = '0.00'

        print (ApplicationLicenceFee.objects.filter(app_type=booking['app'].app_type,start_dt__lte=to_date, end_dt__gte=to_date))
        if ApplicationLicenceFee.objects.filter(app_type=booking['app'].app_type,start_dt__lte=to_date, end_dt__gte=to_date).count() > 0:
            print ("APLICATIO FEE")
            application_fee = ApplicationLicenceFee.objects.filter(app_type=booking['app'].app_type,start_dt__lte=to_date, end_dt__gte=to_date)[0]
            fee_total = application_fee.licence_fee
        context['application_fee'] = fee_total
        context['override_reasons'] = DiscountReason.objects.all() 
        context['page_heading'] = 'Licence Fees'
        
        processor = SystemGroup.objects.get(name='Statdev Processor')
        assessor = SystemGroup.objects.get(name='Statdev Assessor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)
        context['allow_overide_access'] = (
            processor.id in usergroups or 
            assessor.id in usergroups)
        return context

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        context_data = self.get_context_data(**kwargs)
        print ("CCCC")
        print (context_data)
        #app = self.get_object()
        pk=self.kwargs['pk']
        app = Application.objects.get(pk=pk)
        flow = Flow()
        workflowtype = flow.getWorkFlowTypeFromApp(app)
        flow.get(workflowtype)
        DefaultGroups = flow.groupList()

        flowcontext = {}
        flowcontext['application_submitter_id']  = app.submitted_by
        if app.applicant:
            if app.applicant == request.user.id:
                flowcontext['application_owner'] = True

        if Delegate.objects.filter(email_user=request.user.id).count() > 0:
            flowcontext['application_owner'] = True

        flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)
        flowcontext = flow.getRequired(flowcontext, app.routeid, workflowtype)
        if flowcontext['may_payment'] == "False":
           messages.error(self.request, 'You do not have permission to perform this action. AB')
           return HttpResponseRedirect('/')
        
        booking = {'app': app}
        form = apps_forms.PaymentDetailForm 
        print ("TEMPLATE")
        print (self.template_name,)
        # if amount is zero automatically push appplication step.
        print ("APPLCIATION FEES GET")
        if float(context_data['application_fee']) > 0:
           pass
           # continue with rest of code logic
        else:
           # We dont need to ask for any money,  proceed to next step automatically
           flow = Flow()
           workflowtype = flow.getWorkFlowTypeFromApp(app)
           flow.get(workflowtype)
           DefaultGroups = flow.groupList()
           flowcontext = {}
           flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)
           flowcontext = flow.getRequired(flowcontext, app.routeid, workflowtype)
           actions = flow.getAllRouteActions(app.routeid, workflowtype)

           route = {}
           for a in actions:
                if 'payment' in a:
                    if a['payment'] == 'success':
                        route = a
           groupassignment = SystemGroup.objects.get(name=DefaultGroups['grouplink'][route['routegroup']])
           app.routeid = route["route"]
           app.state = route["state"]
           app.group = groupassignment
           app.assignee = None
           app.route_status = flow.json_obj[route["route"]]['title']
           app.save()
           utils.application_lodgment_info(self.request,app)
           return HttpResponseRedirect('/')
           #####        



        return super(ApplicationBooking, self).get(request, *args, **kwargs)
        return self.render_page(request, booking, form)

    def post(self, request, *args, **kwargs):

        pk=self.kwargs['pk']
        app = Application.objects.get(pk=pk)
        overridePrice = request.POST.get('overridePrice','0.00')
        overrideReason = request.POST.get('overrideReason', None)
        overrideDetail = request.POST.get('overrideDetail', None)
        override_checkbox = request.POST.get('override_checkbox', 'off')

        booking = {'app': app}
        to_date = datetime.now()
        application_fee = None
        fee_total = '0.00'
        if ApplicationLicenceFee.objects.filter(app_type=booking['app'].app_type,start_dt__lte=to_date, end_dt__gte=to_date).count() > 0:
            application_fee = ApplicationLicenceFee.objects.filter(app_type=booking['app'].app_type,start_dt__lte=to_date, end_dt__gte=to_date)[0]
            fee_total = application_fee.licence_fee
        else:
            raise ValidationError("Unable to find licence fees")

        if override_checkbox == 'on': 
            fee_total = Decimal(overridePrice)
        if Booking.objects.filter(customer=app.applicant,application=app).count() > 0:
            booking_obj = Booking.objects.filter(customer=app.applicant,application=app)[0]
            if override_checkbox == 'on':
                booking_obj.override_price = Decimal(overridePrice)
                booking_obj.override_reason = DiscountReason.objects.get(id=overrideReason)
                booking_obj.override_reason_info = overrideDetail
            booking_obj.customer=app.applicant
            booking_obj.cost_total=fee_total
            booking_obj.application=app
            booking_obj.save()
        else:
            if override_checkbox == 'on':
                booking_obj = Booking.objects.create(customer=app.applicant,cost_total=fee_total,application=app,override_price=Decimal(overridePrice),override_reason_info=overrideDetail, override_reason=DiscountReason.objects.get(id=overrideReason))
            else:
                booking_obj = Booking.objects.create(customer=app.applicant,cost_total=fee_total,application=app,override_price=None,override_reason_info=None, override_reason=None)
        booking_obj.booking_hash = hashlib.sha256(str(booking_obj.pk).encode('utf-8')).hexdigest()
        booking_obj.save()
        booking['booking'] = booking_obj
        invoice_text = u"Your licence {} ".format('fees')
        
        lines = []
        lines.append({'ledger_description':booking['app'].get_app_type_display(),"quantity":1,"price_incl_tax": float(fee_total), "price_excl_tax": float(fee_total), "oracle_code":'00123sda', 'line_status': 1})
        checkout_response = utils.checkout(
                    request,
                    booking,
                    lines,
                    booking_reference=str(booking['booking'].id),
                    invoice_text=invoice_text,
                )
        return checkout_response

def getPDFapplication(request,application_id):

  if request.user.is_superuser:
      app = Application.objects.get(id=application_id)

      filename = 'pdfs/applications/'+str(app.id)+'-application.pdf'
      if os.path.isfile(filename) is False:
#      if app.id:
          pdftool = PDFtool()
          if app.app_type == 4:
              approval = Approval.objects.get(application = app)
              pdftool.generate_emergency_works(approval)

      if os.path.isfile(filename) is True:
          pdf_file = open(filename, 'rb')
          pdf_data = pdf_file.read()
          pdf_file.close()
          return HttpResponse(pdf_data, content_type='application/pdf')

def getLedgerAppFile(request,file_id,extension):
  allow_access = False
 #file_group_ref_id
  pd = PrivateDocument.objects.filter(id=file_id)
  if pd.count() > 0:
       pd_object = pd[0]
        
       context_processor = template_context(request)

       admin_staff = context_processor['admin_staff']
       if admin_staff is True:
            allow_access = True

       if request.user.is_authenticated: 
           if pd_object.file_group_ref_id == request.user.id:
                  allow_access = True    
       if request.user.is_superuser:
           allow_access = True
      
       if allow_access is True:
           # configs
           api_key = settings.LEDGER_API_KEY
           url = settings.LEDGER_API_URL+'/ledgergw/remote/documents/get/'+api_key+'/'
           myobj = {'private_document_id': file_id}
           # send request to server to get file
           resp = requests.post(url, data = myobj)
           image_64_decode = base64.b64decode(resp.json()['data'])
           extension = resp.json()['extension']

           if extension == 'msg':
               return HttpResponse(image_64_decode, content_type="application/vnd.ms-outlook")
           if extension == 'eml':
               return HttpResponse(image_64_decode, content_type="application/vnd.ms-outlook")


           return HttpResponse(image_64_decode, content_type=mimetypes.types_map['.'+str(extension)])
       else:
           return HttpResponse("Permission Denied", content_type="plain/html")
  else:
           return HttpResponse("Error loading document", content_type="plain/html")
    
  

def getAppFile(request,file_id,extension):
  allow_access = False
  #if request.user.is_superuser:
  file_record = Record.objects.get(id=file_id)
  app_id = file_record.file_group_ref_id 
  app_group = file_record.file_group
  if (file_record.file_group > 0 and file_record.file_group < 12) or (file_record.file_group == 2003):
      app = Application.objects.get(id=app_id)
      if app.id == file_record.file_group_ref_id:
            flow = Flow()
            workflowtype = flow.getWorkFlowTypeFromApp(app)
            flow.get(workflowtype)

            flowcontext = {}
            if app.assignee:
                flowcontext['application_assignee_id'] = app.assignee
            if app.submitted_by:
                flowcontext['application_submitter_id'] = app.submitted_by

            #flowcontext['application_owner'] = app.
            if app.applicant:
                if app.applicant == request.user.id:
                   flowcontext['application_owner'] = True
            if request.user.is_authenticated:
                if Delegate.objects.filter(email_user=request.user.id).count() > 0:
                     flowcontext['application_owner'] = True


            flowcontext = flow.getAccessRights(request, flowcontext, app.routeid, workflowtype)
            if flowcontext['allow_access_attachments'] == "True":
                allow_access = True
            if allow_access is False:
                if request.user.is_authenticated:
                    refcount = Referral.objects.filter(application=app,referee=request.user.id).exclude(status=5).count()
                    if refcount > 0:
                       allow_access = True
                       ref = Referral.objects.filter(application=app,referee=request.user.id).exclude(status=5)[0]                  

                   
                   #for i in ref.records.all():
                   #    if int(file_id) == i.id:
                   #       allow_access = True

            
  if file_record.file_group == 2002:
      org = OrganisationContact.objects.get(organisation__id=file_record.file_group_ref_id)
      if org.email:
           user_email = SystemUser.objects.get(ledger_id=request.user.id)
           if org.email == user_email.email or request.user.is_staff is True:
                  allow_access = True

  if file_record.file_group == 2005:
      app = Approval.objects.get(id=app_id)
      if app.applicant:
           if app.applicant == request.user.id or request.user.is_staff is True:
                  allow_access = True

  if file_record.file_group == 2007:
      app = Approval.objects.get(id=app_id)
      if app.applicant:
           if request.user.is_staff is True:
                  allow_access = True

  if file_record.file_group == 2006:
      app = Compliance.objects.get(id=app_id)
      if app.applicant:
           if app.applicant == request.user.id or request.user.is_staff is True:
                  allow_access = True
 
  
  if allow_access == True:
      file_record = Record.objects.get(id=file_id)
      file_name_path = file_record.upload.path
      if os.path.isfile(file_name_path) is True:
              the_file = open(file_name_path, 'rb')
              the_data = the_file.read()
              the_file.close()
              if extension == 'msg': 
                  return HttpResponse(the_data, content_type="application/vnd.ms-outlook")
              if extension == 'eml':
                  return HttpResponse(the_data, content_type="application/vnd.ms-outlook")


              return HttpResponse(the_data, content_type=mimetypes.types_map['.'+str(extension)])
  else:
              return HttpResponse("Error loading attachment", content_type="plain/html")
              return



#      filename = 'pdfs/applications/'+str(app.id)+'-application.pdf'
#      if os.path.isfile(filename) is False:
##      if app.id:
#          pdftool = PDFtool()
#          if app.app_type == 4:
#              pdftool.generate_emergency_works(app)
#
#      if os.path.isfile(filename) is True:
#          pdf_file = open(filename, 'rb')
#          pdf_data = pdf_file.read()
#          pdf_file.close()
#          return HttpResponse(pdf_data, content_type='application/pdf')


