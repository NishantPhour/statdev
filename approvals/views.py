from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, UpdateView, DetailView, CreateView
from django.urls import reverse
from .models import Approval as ApprovalModel, CommunicationApproval 
from django.db.models import Q
from django.contrib.auth.models import Group
from applications.utils import get_query
from . import forms as apps_forms
from actions.models import Action
from django.contrib.contenttypes.models import ContentType
from applications.models import Application, Record, Delegate
from applications.validationchecks import Attachment_Extension_Check
from django.http import HttpResponse, HttpResponseRedirect
from statdev.context_processors import template_context
from django.contrib import messages
from applications.views_pdf import PDFtool
from applications.email import sendHtmlEmail, emailGroup, emailApplicationReferrals
from datetime import datetime, date, timedelta
from ledger_api_client.managed_models import SystemUser, SystemUserAddress, SystemGroup

import os.path
import os 

class ApprovalList(ListView):
    model = ApprovalModel

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        staff = context_processor['staff']
        if staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ApprovalList, self).get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super(ApprovalList, self).get_queryset()
        # Did we pass in a search string? If so, filter the queryset and return
        # it.
        if 'q' in self.request.GET and self.request.GET['q']:
            query_str = self.request.GET['q']
            # Replace single-quotes with double-quotes
            query_str = query_str.replace("'", r'"')
            # Filter by pk, title
            query = get_query(
                query_str, ['pk', 'title'])
            system_user_ids = SystemUser.objects.filter(email__icontains=query_str).values_list('ledger_id', flat=True)
            qs= qs.filter(query) | qs.filter(applicant__in=system_user_ids)
            qs = qs.distinct()
        return qs

    def get_context_data(self, **kwargs):
        context = super(ApprovalList, self).get_context_data(**kwargs)

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
            query_obj = Q(pk__contains=query_str) | Q(title__icontains=query_str)
            user_ids = SystemUser.objects.filter(email__icontains=query_str).values_list('ledger_id', flat=True)
            if user_ids:
                query_obj |= Q(applicant__in=user_ids)
            if self.request.GET['apptype'] != '':
                query_obj &= Q(app_type=int(self.request.GET['apptype']))
            else:
                query_obj &= Q(app_type__in=APP_TYPE_CHOICES_IDS)

            # if self.request.GET['applicant'] != '':
            #     query_obj &= Q(applicant=int(self.request.GET['applicant']))
            if self.request.GET['appstatus'] != '':
                query_obj &= Q(status=int(self.request.GET['appstatus']))

            objlist = ApprovalModel.objects.filter(query_obj).distinct().order_by('-id')
            context['query_string'] = self.request.GET['q']

            if self.request.GET['apptype'] != '':
                 context['apptype'] = int(self.request.GET['apptype'])
            if self.request.GET['applicant'] != '':
                 context['applicant'] = int(self.request.GET['applicant'])
            if 'appstatus' in self.request.GET:
                if self.request.GET['appstatus'] != '':
                    context['appstatus'] = int(self.request.GET['appstatus'])


            if 'from_date' in self.request.GET:
                 context['from_date'] = self.request.GET['from_date']
                 context['to_date'] = self.request.GET['to_date']
                 if self.request.GET['from_date'] != '':
                     from_date_db = datetime.strptime(self.request.GET['from_date'], '%d/%m/%Y').date()
                     query_obj &= Q(issue_date__gte=from_date_db)
                 if self.request.GET['to_date'] != '':
                     to_date_db = datetime.strptime(self.request.GET['to_date'], '%d/%m/%Y').date()
                     query_obj &= Q(issue_date__lte=to_date_db)
#        if 'q' in self.request.GET and self.request.GET['q']:
 #           query_str = self.request.GET['q']
  #          objlist = ApprovalModel.objects.filter(Q(pk__contains=query_str) | Q(title__icontains=query_str) | Q(applicant__email__icontains=query_str))
        else:
            to_date = datetime.today()
            from_date = datetime.today() - timedelta(days=10)
            context['from_date'] = from_date.strftime('%d/%m/%Y')
            context['to_date'] = to_date.strftime('%d/%m/%Y')
            objlist = ApprovalModel.objects.filter(issue_date__gte=from_date,issue_date__lte=to_date).order_by('-id')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)

        context['app_list'] = []
        context['app_applicants'] = {}
        context['app_applicants_list'] = []
        context['app_appstatus'] = list(ApprovalModel.APPROVAL_STATE_CHOICES)

        for app in objlist.order_by('title'):
            row = {}
            row['app'] = app
            row['approval_url'] = app.approval_url
            
            if app.applicant is not None:
                row['applicant'] = SystemUser.objects.get(ledger_id=app.applicant)

        #    if app.group is not None:

            #if app.applicant:
            #    if app.applicant.id in context['app_applicants']:
            #        donothing = ''
            #    else:
            #        context['app_applicants'][app.applicant.id] = app.applicant.first_name + ' ' + app.applicant.last_name
            #        context['app_applicants_list'].append({"id": app.applicant.id, "name": app.applicant.first_name + ' ' + app.applicant.last_name})


            context['app_list'].append(row)


#       context['app_list'] = context['app_list'].order_by('title')

        # TODO: any restrictions on who can create new applications?
        processor = SystemGroup.objects.get(name='Statdev Processor')
        usergroups = self.request.user.get_system_group_permission(self.request.user.id)

        # Rule: admin officers may self-assign applications.
        if processor.id in usergroups or self.request.user.is_superuser:
            context['may_assign_processor'] = True

        return context

class ApprovalDetails(LoginRequiredMixin,DetailView):
    model = ApprovalModel

    def get_context_data(self, **kwargs):
        context = super(ApprovalDetails, self).get_context_data(**kwargs)
        app = self.get_object()
        context_processor = template_context(self.request)
        context['admin_staff'] = context_processor['admin_staff']
        context['approval_history'] = self.get_approval_history(app, [])
        if app.applicant is not None:
            context['applicant'] = SystemUser.objects.get(ledger_id=app.applicant)
            context['postal_address'] = SystemUserAddress.objects.get(system_user=context['applicant'], address_type='postal_address')
        
        
        
        return context

    def get_approval_history(self,app,approvals):
        approvals = self.get_approval_history_up(app,approvals)
        approvals = self.get_approval_history_down(app,approvals)

        return approvals

    def get_approval_history_up(self,app,approvals):
        if app:
           application = Application.objects.filter(old_approval_id=app.id)
           if application.count() > 0:

                app = ApprovalModel.objects.filter(application=application[0])
                if app.count() > 0:
                    approvals.append({'id': app[0].id, 'title':  app[0].title})

                    approvals = self.get_approval_history_up(app[0],approvals)
        return approvals

    def get_approval_history_down(self,app,approvals):
        if app.application.old_approval_id:
            app_old = ApprovalModel.objects.filter(id=app.application.old_approval_id)
            approvals.append({'id': app_old[0].id, 'title':  app_old[0].title} )
            app = ApprovalModel.objects.get(id=app.application.old_approval_id)
            approvals = self.get_approval_history_down(app,approvals) 

        return approvals




class ApprovalStatusChange(LoginRequiredMixin,UpdateView):
    model = ApprovalModel
    form_class = apps_forms.ApprovalChangeStatus
    template_name = 'applications/application_form.html'

    def get(self, request, *args, **kwargs):
        modelobject = self.get_object()
        return super(ApprovalStatusChange, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('approval_list', args=())

    def get_context_data(self, **kwargs):
        context = super(ApprovalStatusChange,self).get_context_data(**kwargs)
        self.object = self.get_object()
        context['title'] = self.object.title
        return context

    def get_initial(self):
        initial = super(ApprovalStatusChange, self).get_initial()
        approval = self.get_object()
        status = self.kwargs['status']
        initial['status'] = ApprovalModel.APPROVAL_STATE_CHOICES.__getattr__(status)
        return initial

    def post(self, request, *args, **kwargs):
        #        self.initial = self.get_initial()
        self.object = self.get_object()
        #self.object.status = 2
        #print self.initial['status']
        if request.POST.get('cancel'):
            app = Application.objects.get(pk=self.kwargs['application'])
            return HttpResponseRedirect(app.get_absolute_url())
        return super(ApprovalStatusChange, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        
        self.object = form.save(commit=False)
        app = self.get_object()
        status = self.kwargs['status']
        self.object.status = ApprovalModel.APPROVAL_STATE_CHOICES.__getattr__(status)
        self.object.save()

        action = Action(
            content_object=app, category=Action.ACTION_CATEGORY_CHOICES.change,
            user=self.request.user.id, action='Approval Change')
        action.save()
        if status == 'surrendered':
             emailcontext = {'approval_id': app.id, 'app': app}
             emailGroup('Approval surrendered AP-'+str(app.id) , emailcontext, 'approval_surrendered.html', None, None, None, 'Statdev Processor')


        return super(ApprovalStatusChange, self).form_valid(form)

class ApprovalActions(DetailView):
    model = ApprovalModel
    template_name = 'approvals/approvals_actions.html'

    def get(self, request, *args, **kwargs):
        context_processor = template_context(self.request)
        admin_staff = context_processor['admin_staff']
        if admin_staff == True:
           donothing =""
        else:
           messages.error(self.request, 'Forbidden from viewing this page.')
           return HttpResponseRedirect("/")
        return super(ApprovalActions, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApprovalActions, self).get_context_data(**kwargs)
        app = self.get_object()
        # TODO: define a GenericRelation field on the Application model.
        context['actions'] = Action.objects.filter(
            content_type=ContentType.objects.get_for_model(app), object_id=app.pk).order_by('-timestamp')
        return context

class ApprovalCommsCreate(CreateView):
    model = CommunicationApproval
    form_class = apps_forms.CommunicationCreateForm
    template_name = 'applications/application_comms_create.html'

    def get_context_data(self, **kwargs):
        context = super(ApprovalCommsCreate, self).get_context_data(**kwargs)
        context['page_heading'] = 'Create new communication'
        return context

    def get_initial(self):
        initial = {}
        initial['application'] = self.kwargs['pk']
        return initial

    def get_form_kwargs(self):
        kwargs = super(ApprovalCommsCreate, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        if request.POST.get('cancel'):
            return HttpResponseRedirect(reverse('home'))
        return super(ApprovalCommsCreate, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        """Override form_valid to set the assignee as the object creator.
        """
        self.object = form.save(commit=False)
        app_id = self.kwargs['pk']

        approval = ApprovalModel.objects.get(id=app_id)
        self.object.approval = approval
        self.object.save()

        if self.request.FILES.get('records'):
            if Attachment_Extension_Check('multi', self.request.FILES.getlist('records'), None) is False:
                raise ValidationError('Documents attached contains and unallowed attachment extension.')

            for f in self.request.FILES.getlist('records'):
                doc = Record()
                doc.upload = f
                doc.save()
                self.object.records.add(doc)
        self.object.save()
        # If this is not an Emergency Works set the applicant as current user
        #print app_id
        success_url = reverse('approvals_comms', args=(app_id,))
        return HttpResponseRedirect(success_url)

class ApprovalComms(DetailView):
    model = ApprovalModel 
    template_name = 'approvals/approval_comms.html'

    def get_context_data(self, **kwargs):
        context = super(ApprovalComms, self).get_context_data(**kwargs)
        app = self.get_object()

        # TODO: define a GenericRelation field on the Application model.
        context['communications'] = CommunicationApproval.objects.filter(approval_id=app.pk).order_by('-created')
        return context

#class ViewPDF():
def getPDF(request,approval_id):
  can_view = False
  app = ApprovalModel.objects.get(id=approval_id)

  if request.user.is_staff:
      can_view = True
  elif request.user.is_superuser:
      can_view = True
  elif app.applicant == request.user:
      can_view = True
  elif Delegate.objects.filter(email_user=request.user.id,organisation=app.organisation).exists(): 
      can_view = True



  if can_view is True:
      #app = ApprovalModel.objects.get(id=approval_id)
      BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
      filename = BASE_DIR+'/pdfs/approvals/'+str(app.id)+'-approval.pdf'

      if app.status == 7 or os.path.isfile(filename) is False:
      #if os.path.isfile(filename) is False:
#      if app.id:
          pdftool = PDFtool()
          if app.app_type == 1:
               pdftool.generate_permit(app)
          elif app.app_type == 2:
              pdftool.generate_licence(app)
          elif app.app_type == 3:
              pdftool.generate_part5(app)
          elif app.app_type == 4:
              pdftool.generate_emergency_works(app)
          elif app.app_type == 6:
              pdftool.generate_section_84(app)

      if os.path.isfile(filename) is True:
          pdf_file = open(filename, 'rb')
          pdf_data = pdf_file.read()
          pdf_file.close()
          return HttpResponse(pdf_data, content_type='application/pdf')
  else:
     messages.error(request, 'Forbidden from viewing this page.')
     return HttpResponseRedirect("/")
   
    
 
