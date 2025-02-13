from django.shortcuts import render
from applications.models import Application, PublicationFeedback, Record, PublicationWebsite
from approvals.models import Approval 
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.db.models import Q
from public import forms as apps_forms
from django.urls import reverse
from django.utils.safestring import SafeText
from applications.validationchecks import Attachment_Extension_Check, is_json
from datetime import datetime, date, timedelta
from django.contrib import messages

import json

class PublicApplicationsList(TemplateView):
    #model = appmodel.Application

    template_name = "public/home_page.html"
    def get_context_data(self, **kwargs):

        context = super(PublicApplicationsList, self).get_context_data(**kwargs)
        # app = self.get_object()
        # print self.req
        action =  self.kwargs['action']
        context['action'] = action
        search = None
        query_obj = None
        current_datetime = datetime.now()

        if action == 'review':
            query_obj = Q(publish_documents__isnull=False,publish_draft_report__isnull=True, publish_documents_expiry__gte=current_datetime) & Q(app_type__in=[3])
            context['home_nav_review'] = 'active'
        elif action == 'draft':
            query_obj = Q(publish_documents__isnull=False, publish_draft_report__isnull=False,publish_final_report__isnull=True,publish_draft_expiry__gte=current_datetime ) & Q(app_type__in=[3])
            context['home_nav_draft'] = 'active'
        elif action == 'final':
            query_obj = Q(publish_documents__isnull=False, publish_draft_report__isnull=False,publish_final_report__isnull=False, publish_determination_report__isnull=True,publish_final_expiry__gte=current_datetime) & Q(app_type__in=[3])
            context['home_nav_final'] = 'active'
        elif action == 'determination':
            query_obj = Q(Q(publish_documents__isnull=False, publish_draft_report__isnull=False, publish_final_report__isnull=False,publish_determination_report__isnull=False) & Q(app_type__in=[3])) |  Q(Q(publish_determination_report__isnull=False) & Q(app_type__in=[6]))
            context['home_nav_determination'] = 'active'
        else:
            query_obj = Q(publish_documents__isnull=False, publish_draft_report__isnull=False,publish_final_report__isnull=False) & Q(app_type__in=[3])
            #query_obj = Q(publish_documents__isnull=False) & Q(app_type__in=[3])

        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            query_obj = Q(Q(pk__contains=query_str) | Q(title__icontains=query_str) | Q(applicant__email__icontains=query_str) | Q(organisation__name__icontains=query_str) |  Q(assignee__email__icontains=query_str)) & query_obj
            

        if action is not None: 
            context['items'] = Application.objects.filter(query_obj)

        return context


class PublicApplicationFeedback(UpdateView):
    """A view for updating a draft (non-lodged) application.
    """
    model = Application
    form_class = apps_forms.ApplicationPart5
    template_name = 'public/application_form.html'

    def get(self, request, *args, **kwargs):
        # TODO: business logic to check the application may be changed.
        app = self.get_object()
        action = self.kwargs['action']
        app_id = self.kwargs['pk']
        query_obj = Q()
        current_datetime = datetime.now()
        if action == 'review':
            query_obj = Q(publish_documents__isnull=False,publish_draft_report__isnull=True, publish_documents_expiry__gte=current_datetime) & Q(app_type__in=[3]) & Q(id=app_id)
        elif action == 'draft':
            query_obj = Q(publish_documents__isnull=False, publish_draft_report__isnull=False,publish_final_report__isnull=True,publish_draft_expiry__gte=current_datetime ) & Q(app_type__in=[3]) & Q(id=app_id)
        elif action == 'final':
            query_obj = Q(publish_documents__isnull=False, publish_draft_report__isnull=False,publish_final_report__isnull=False, publish_determination_report__isnull=True,publish_final_expiry__gte=current_datetime) & Q(app_type__in=[3]) & Q(id=app_id)
        elif action == 'determination':
            query_obj = Q(Q(publish_documents__isnull=False, publish_draft_report__isnull=False, publish_final_report__isnull=False,publish_determination_report__isnull=False) & Q(app_type__in=[3]) & Q(id=app_id)) | Q(Q(publish_determination_report__isnull=False) & Q(app_type__in=[6]) & Q(id=app_id))
        else:
            messages.error(self.request, 'Forbidden from viewing this page.')
            return HttpResponseRedirect("/")
        if Application.objects.filter(query_obj).count() > 0:
             pass
        else:
            messages.error(self.request, 'Forbidden from viewing this page.')
            return HttpResponseRedirect("/")


        return super(PublicApplicationFeedback, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PublicApplicationFeedback, self).get_context_data(**kwargs)
        app_id = self.kwargs['pk']
        context['page_heading'] = 'Application for new Part 5 - '+app_id
        context['left_sidebar'] = 'yes'
        context['action'] = self.kwargs['action']
        app = self.get_object()

        doclist = app.proposed_development_plans.all()
        context['proposed_development_plans_list'] = []

        for doc in doclist:
            pub_web = None
            try:
               pub_web = PublicationWebsite.objects.get(original_document_id=doc.id,application=self.kwargs['pk'])
#               print PublicationWebsite.objects.get(original_document_id=doc.id)
            except:
               pub_web = None

            fileitem = {}
            if pub_web is None:
               fileitem['fileid'] = doc.id
               fileitem['path'] = doc.upload.name
               fileitem['path_short'] = SafeText(doc.upload.name)[19:]
               fileitem['name'] = doc.name
               fileitem['file_url'] = doc.file_url()
               context['proposed_development_plans_list'].append(fileitem)
            else:
               fileitem['fileid'] = pub_web.published_document.id
               fileitem['path'] = pub_web.published_document.upload.name
               fileitem['path_short'] = SafeText(pub_web.published_document.upload.name)[19:]
               fileitem['name'] = pub_web.published_document.name
               fileitem['file_url'] = pub_web.published_document.file_url()
               context['proposed_development_plans_list'].append(fileitem)

        if app.river_lease_scan_of_application:
            pub_web = None
            try:
               pub_web = PublicationWebsite.objects.get(original_document_id=app.river_lease_scan_of_application.id,application=self.kwargs['pk'])
#               print PublicationWebsite.objects.get(original_document_id=doc.id)
            except:
               pub_web = None
#            print pub_web
            if pub_web is None:
              context['river_lease_scan_of_application'] = app.river_lease_scan_of_application
            else:
#               print pub_web.published_document
              context['river_lease_scan_of_application'] = pub_web.published_document

        context['approval'] = []
        approval = Approval.objects.filter(application=app)
        if approval.count() > 0:
             context['approval'] = approval[0]

        return context

    def get_initial(self):
        initial = super(PublicApplicationFeedback, self).get_initial()
        app = self.get_object()
       
        initial['application_id'] = self.kwargs['pk']
        initial['organisation'] = app.organisation
        initial['captcha'] = 'CaPtA'
        initial['action'] = self.kwargs['action']

        if app.river_lease_scan_of_application:
            pub_web = None
            try:
               pub_web = PublicationWebsite.objects.get(original_document_id=app.river_lease_scan_of_application.id,application=self.kwargs['pk'])
#               print PublicationWebsite.objects.get(original_document_id=doc.id)
            except:
               pub_web = None
            #if pub_web is None:
            #   initial['river_lease_scan_of_application'] = app.river_lease_scan_of_application.upload
            #else:
            #   print "HERE"
            #   print pub_web.published_document
            #   initial['river_lease_scan_of_application'] = pub_web.published_document
        return initial

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            app = Application.objects.get(id=kwargs['pk'])
            if app.state == app.APP_STATE_CHOICES.new:
                app.delete()
                return HttpResponseRedirect(reverse('application_list'))
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(PublicApplicationFeedback, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override form_valid to set the state to draft is this is a new application.
        """
        forms_data = form.cleaned_data
        self.object = form.save(commit=False)
        app_id = self.kwargs['pk']
        action = self.kwargs['action']
        status=None
        application = Application.objects.get(id=app_id)
     
        if action == 'review':
             status= 'review'
        elif action == 'draft':
             status='draft'
        elif action == 'final': 
             status='final' 
        elif action == 'determination':
             status='determination'

        # ToDO remove dupes of this line below. doesn't need to be called
        # multiple times
        pfcreate = PublicationFeedback.objects.create(application=application,
						      name=forms_data['name'],
                                                      address=forms_data['address'],
                                                      suburb=forms_data['suburb'],
                                                      state=forms_data['state'],
                                                      postcode=forms_data['post_code'],
                                                      phone=forms_data['phone'],
                                                      email=forms_data['email'],
                                                      comments=forms_data['comments'],
                                                      status=status
	)

        if 'records_json' in self.request.POST:
             if is_json(self.request.POST['records_json']) is True:
                  json_data = json.loads(self.request.POST['records_json'])
                  for i in json_data:
                      doc = Record.objects.get(id=i['doc_id'])
                      pfcreate.records.add(doc)
                  pfcreate.save()


        #if self.request.FILES.get('records'):
        #    for f in self.request.FILES.getlist('records'):
        #        doc = Record()
        #        doc.upload = f
        #        doc.save()
        #        pfcreate.records.add(doc)



#    name = CharField(required=False,max_length=255)
#    address = CharField(required=False,max_length=255)
#    suburb = CharField(required=False,max_length=255)
#    post_code = CharField(required=False,max_length=255)
#    phone = CharField(required=False,max_length=255)
#    email = EmailField(required=False,max_length=255)
#    email_confirm = EmailField(required=False,max_length=255)
#    comments = CharField(required=False,max_length=255, widget=Textarea)




#        application = Application.objects.get(id=self.object.id)
 #       self.object.save()
        return HttpResponseRedirect(reverse('public_application_list', args=(action,)))

