from __future__ import unicode_literals
from django.contrib.auth.models import Group
import os
import json
__all__ = (
        "Flow"
)

"""

Workflow.py utilise a .json file per each form flow linked to the app_type category on the application.   The json config contains a list of routes (also maybe called steps).
All routes start at route id 1 (step 1) within each route it contains a list of sub configs ,  title, hidden, actions, assigntoaccess, groupaccess, collapse, fields.

1. When each form is loaded it will load the route config for the step the form is at.  The application contains a routeid to keep track of which routes the application is at.

2. The hidden and collapse can be linked to the template which allows you to hide and collapse different boxes on the form depending on the step the form is at. Requires the template to have if statements and {{ }} variables added to the css collapse class.

3. groupaccess is a list of permissions applied to different actions with in the template.  These rights are applied depending on the groups linked to there user groups.  If a person is linked to many groups eg. Assessor and Proccessor and only one group has a rule set to True than by default it will set the overall access to True for that rule for that person.  groupaccess contains the group name in django and a list of permission rules which are set to "True" or "False"

4. assigntoaccess is a list of permissions applied when the application is assigned to a person and only when that person is accessing the form. example would be when assigning back to form creator.

5. action is a list of routes the application can progress on to.  Actions can contain multiple actions each consisting of the action title, route,state and required.   Action is used to push the form onto the step in the workflow.  Where as form components allow changes to the form with out progressing the form onto the next person.

    a) title = title of action which appears as the title under actions on the form
    b) route = this is route number of the route which will be applied when clicking the action which will update the application routeid to.
    c) routegroup = we have many action groups with in statdev and this is use to link the type of action being clicked when the button is clicked so the correct route is updated on the application
    d) required =  this is a list of fields on the Application model that are required to be completed before the action can continue onto the next step.

6. formcomponent = only has one component at the moment which is the Update Application commponent which allows the ahref link to have different titles between each step.  eg attached signed document.  There are other components but are not configurable and are linked into permissions.

7. fields = is linked to form componenet "Update Application" this allows input fields to be hidden on each step only showing fields not listed.

8. required = under the main level and not under action --> required <-- different.   The requirement under the main level links to the formcomponent "Update Application" allows you to set fields to required to be completed so when the form update button is clicked and the field is not completed will cause and error asking for the fields to be completed.

"""

class Flow():
    def get(self,flow):
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(BASE_DIR+'/applications/flowconf/workflow.'+flow+'.json') as json_data_file:
            json_obj = json.load(json_data_file)
            self.json_obj = json_obj

    def getAllRouteConf(self,flow,routeid):
        json_obj = self.json_obj
        if routeid:
           if json_obj[str(routeid)]:
              return json_obj[str(routeid)]
        return None

    def setAccessDefaults(self,context):
        # Form Actions
        if "may_update" not in context:
            context["may_update"] = "False"
        if "may_lodge" not in context:
            context["may_lodge"] = "False"
        if "may_refer" not in context:
            context["may_refer"] = "False"
        if "may_assign_customer" not in context:
            context["may_assign_customer"] = "False"
        if "may_assign_processor" not in context:
            context["may_assign_processor"] = "False"
        if "may_assign_assessor" not in context:
            context["may_assign_assessor"] = "False"
        if "may_request_compliance" not in context:
            context["may_request_compliance"] = "False"
        if "may_assign" not in context:
            context["may_assign"] = "False"
        if "may_create_condition" not in context:
            context["may_create_condition"] = "False"
        if "may_submit_approval" not in context:
            context["may_submit_approval"] = "False"
       	if "may_issue" not in context:
            context["may_issue"] = "False"
        if "may_generate_pdf" not in context:
            context["may_generate_pdf"] = "False"
        if "may_assign_director" not in context:
            context["may_assign_director"] = "False"
        if "may_assign_exec" not in context:
            context["may_assign_exec"] = "False"
        if "may_send_for_referral" not in context:
            context["may_send_for_referral" ] = "False"
        if "may_update_publication_newspaper" not in context:
            context["may_update_publication_newspaper" ] = "False"
        if "may_update_publication_website" not in context:
            context["may_update_publication_website" ] = "False"
        if "may_publish_website" not in context:
            context["may_publish_website" ] = "False"
        if "may_update_publication_feedback_review" not in context:
            context["may_update_publication_feedback_review"] = "False"
        if "may_update_publication_feedback_draft" not in context:
            context["may_update_publication_feedback_draft"] = "False"
        if "may_publish_feedback_draft" not in context:
            context["may_publish_feedback_draft"] = "False"
        if "may_update_publication_feedback_final" not in context:
            context["may_update_publication_feedback_final"] = "False"
        if "may_publish_feedback_final" not in context:
            context["may_publish_feedback_final"] = "False"
        if "may_recall_resend" not in context:
            context["may_recall_resend"] = "False"
        if "may_assign_emergency" not in context:
            context["may_assign_emergency"] = "False"
        if "may_assign_to_creator" not in context:
            context["may_assign_to_creator"] = "False"
        if "may_referral_delete" not in context:
            context["may_referral_delete"] = "False"
        if "may_referral_resend" not in context:
            context["may_referral_resend"] = "False"
        if "may_update_condition" not in context:
            context["may_update_condition"] = "False"
        if "may_accept_condition" not in context:
            context["may_accept_condition"] = "False"
        if "may_update_publication_feedback_final" not in context:
            context["may_update_publication_feedback_final"] = "False"
        if "may_view_action_log" not in context:
            context["may_view_action_log"] = "False"
        if "may_view_comm_log" not in context:
            context["may_view_comm_log"] = "False"
        if "may_publish_publication_feedback_draft" not in context:
            context["may_publish_publication_feedback_draft"] = "False"
        if "may_publish_publication_feedback_final" not in context:
            context["may_publish_publication_feedback_final"] = "False"
        if "may_publish_publication_feedback_determination" not in context:
            context["may_publish_publication_feedback_determination"] = "False"
        if "may_update_publication_feedback_determination" not in context:
            context["may_update_publication_feedback_determination"] = "False"
        if "may_change_application_applicant" not in context:
            context["may_change_application_applicant"] = "False"
        if "may_update_vessels_list" not in context:
            context["may_update_vessels_list"] = "False"
        if "allow_admin_side_menu" not in context:
            context["allow_admin_side_menu"] = "False"
        if "hide_form_buttons" not in context:
            context['show_form_buttons'] = "False"
        if "may_assessor_advise" not in context:
            context['may_assessor_advise'] = "False"
        if "may_assign_to_person" not in context:
            context['may_assign_to_person'] = "False"
        if "may_payment" not in context:
            context['may_payment'] = "False"
        if "allow_access_attachments" not in context:
            context['allow_access_attachments'] = "False"       
        if "may_assign_to_officer" not in context:
            context['may_assign_to_officer'] = "False"

        # Form Components
        if "form_component_update" not in context:
            context["form_component_update_title"] = "Update Application"
        if "application_assignee_id" not in context:
            context['application_assignee_id'] = None
        if "application_submitter_id" not in context:
            context['application_submitter_id'] = None
        if "application_owner" not in context:
            context['application_owner'] = None

        return context

    def getAccessRights(self,request,context,route,flow):
        context = self.setAccessDefaults(context)
        context = self.getAllGroupAccess(request,context,route)
        if context['application_assignee_id'] is None:
              context['application_assignee_id'] = -100000
        if context['application_submitter_id'] is None:
              context['application_submitter_id'] = -100000
        if context['application_assignee_id'] == request.user.id:
            context = self.getAssignToAccess(context,route)
        if context['application_submitter_id'] == request.user.id:
            context = self.getSubmitterAccess(context,route)
        if context['application_owner'] is True:
            context = self.getOwnerAccess(context,route)
        return context

    def getAssignToAccess(self,context,route):
        json_obj = self.json_obj
        if json_obj[str(route)]:
           if "assigntoaccess" in json_obj[str(route)]:
                 assigntoaccess = json_obj[str(route)]['assigntoaccess']
                 for at in assigntoaccess:
                     if at in context:
                        if context[at]:
                           if context[at] in 'True':
                              donothing = ''
                           else:
                              context[at] = assigntoaccess[at]
                        else:
                           context[at] = assigntoaccess[at]
        return context

    def getSubmitterAccess(self,context,route):
        json_obj = self.json_obj
        if json_obj[str(route)]:
           if "submitteraccess" in json_obj[str(route)]:
                 assigntoaccess = json_obj[str(route)]['submitteraccess']
                 for at in assigntoaccess:
                     if at in context:
                        if context[at]:
                           if context[at] in 'True':
                              donothing = ''
                           else:
                              context[at] = assigntoaccess[at]
                        else:
                           context[at] = assigntoaccess[at]
        return context

    def getOwnerAccess(self,context,route):
        json_obj = self.json_obj
        if json_obj[str(route)]:
           if "owneraccess" in json_obj[str(route)]:
                 assigntoaccess = json_obj[str(route)]['owneraccess']
                 for at in assigntoaccess:
                     if at in context:
                        if context[at]:
                           if context[at] in 'True':
                              donothing = ''
                           else:
                              context[at] = assigntoaccess[at]
                        else:
                           context[at] = assigntoaccess[at]
        return context


    def getGroupAccess(self,context,route,group):
        json_obj = self.json_obj
        if json_obj[str(route)]:
           if "groupaccess" in json_obj[str(route)]:
              if group in json_obj[str(route)]['groupaccess']:
                 groupaccess = json_obj[str(route)]['groupaccess'][group]
                 for ga in groupaccess:
                     if ga in context:
                        if context[ga]:
                           if context[ga] in 'True':
                              donothing = ''
                           else:
                              context[ga] = groupaccess[ga]
                        else:
                           context[ga] = groupaccess[ga]
        return context

    def getAllGroupAccess(self,request,context,route):
        emergency = None
        processor = None
        assessor = None
        approver = None
        referee = None
        director = None
        executive = None

        if Group.objects.filter(name='Statdev Processor').exists():
            processor = Group.objects.get(name='Statdev Processor')
        if Group.objects.filter(name='Statdev Assessor').exists():
            assessor = Group.objects.get(name='Statdev Assessor')
        if Group.objects.filter(name='Statdev Approver').exists():
            approver = Group.objects.get(name='Statdev Approver')
        if Group.objects.filter(name='Statdev Referee').exists():
            referee = Group.objects.get(name='Statdev Referee')
        if Group.objects.filter(name='Statdev Director').exists():
            director = Group.objects.get(name='Statdev Director')
        if Group.objects.filter(name='Statdev Executive').exists():
            executive = Group.objects.get(name='Statdev Executive')
        if Group.objects.filter(name='Statdev Emergency').exists():
            emergency = Group.objects.get(name='Statdev Emergency')

        if processor in request.user.groups().all():
            context = self.getGroupAccess(context,route,'Statdev Processor')
        if assessor in request.user.groups().all():
            context = self.getGroupAccess(context,route,'Statdev Assessor')
        if approver in request.user.groups().all():
            context = self.getGroupAccess(context,route,'Statdev Approver')
        if referee in request.user.groups().all():
            context = self.getGroupAccess(context,route,'Statdev Referee')
        if director in request.user.groups().all():
            context = self.getGroupAccess(context,route,'Statdev Director')
        if executive in request.user.groups().all():
            context = self.getGroupAccess(context,route,'Statdev Executive')
        if emergency in request.user.groups().all():
            context = self.getGroupAccess(context,route,'Statdev Emergency')

        return context

    def getCollapse(self,context,route,flow):
        context['collapse'] = {}
        json_obj = self.json_obj
        if "collapse" in json_obj[str(route)]:
           collapse = json_obj[str(route)]['collapse']
           for c in collapse:
               if collapse[c] in "False":
                  context['collapse'][c] = "in"
        return context

    def getHiddenAreas(self,context,route,flow, request):
        context['hidden'] = {}
        json_obj = self.json_obj
        if json_obj[str(route)]:
           if json_obj[str(route)]['hidden']:
              context["hidden"] = json_obj[str(route)]['hidden']
        if "hide_form_buttons" not in context["hidden"]:
               context["hidden"]["hide_form_buttons"] = "False"
        return context

    def getFields(self,context,route,flow):
        context['fields'] = {}
        json_obj = self.json_obj
        if json_obj[str(route)]:
           if "fields" in json_obj[str(route)]:
              context["fields"] = json_obj[str(route)]['fields']
        return context

    def getRequired(self,context,route,flow):
        context['required'] = {}
        json_obj = self.json_obj
        if json_obj[str(route)]:
            if "required" in json_obj[str(route)]:
               context["required"] = json_obj[str(route)]['required']
            else: 
               context["required"] = json_obj[str(route)]['required'] = []

        return context

    def getDisabled(self,context,route,flow):
        context['disabled'] = {}
        json_obj = self.json_obj
        if json_obj[str(route)]:
            if "disabled" in json_obj[str(route)]:
               context["disabled"] = json_obj[str(route)]['disabled']
            else:
               context["disabled"] = json_obj[str(route)]['disabled'] = []
        return context["disabled"]
 

    def getFormComponent(self,route,flow):
        json_obj = self.json_obj
        if json_obj[str(route)]:
            if "formcomponent" in json_obj[str(route)]:
                if "update" not in json_obj[str(route)]['formcomponent']:
                    json_obj[str(route)] = {'formcomponent': {"update": {"title":  "Update Application"}}}
            else:
                donothing = ""
                json_obj[str(route)] = {'formcomponent': {"update": {"title":  "Update Application"}}}

            return json_obj[str(route)]['formcomponent']


    def getNextRoute(self,action,route,flow):
        json_obj = self.json_obj
        if json_obj[str(route)]:
           if json_obj[str(route)]['actions']:
              for a in json_obj[str(route)]['actions']:
                  if a["routegroup"]:
                     if a["routegroup"] == action:
                        return a["route"]

    def getNextRouteObj(self,action,route,flow):
        json_obj = self.json_obj
        if json_obj[str(route)]:
            if json_obj[str(route)]['actions']:
               for a in json_obj[str(route)]['actions']:
                   if a["routegroup"]:
                       if a["routegroup"] == action:
                           if "required" not in a:
                              a["required"]= []
                           return a
        return None
    def getNextRouteObjViaId(self,actionid,route,flow):
        json_obj = self.json_obj
        if json_obj[str(route)]:
            if json_obj[str(route)]['actions']:
               a = json_obj[str(route)]['actions'][actionid]
               if "required" not in a:
                  a["required"]= []
               return a

        return None
    def getAllRouteActions(self,route,flow):
        json_obj = self.json_obj
        if json_obj[str(route)]:
            if json_obj[str(route)]['actions']:
               i =0
               while i < len(json_obj[str(route)]['actions']):
                     json_obj[str(route)]['actions'][i]['actionid'] = i
                     i += 1 
               #for a in json_obj[str(route)]['actions']:
               #     print (a)
               return json_obj[str(route)]['actions']

    def getAllConditionBasedRouteActions(self,route):
        json_obj = self.json_obj
        if json_obj[str(route)]:
            if 'condition-based-actions' in json_obj[str(route)]:
                if json_obj[str(route)]['condition-based-actions']:
                    return json_obj[str(route)]['condition-based-actions']


    def checkAssignedAction(self,action,context):
        assign_action = False
        if action == "admin":
           if context["may_assign_processor"] == "True":
                assign_action = True
        elif action == "assess":
            if context["may_assign_assessor"] == "True":
                assign_action = True
        elif action == "referral":
            if context["may_refer"] == "True":
                assign_action = True
        elif action == "manager":
            if context["may_submit_approval"] == "True":
                assign_action = True
        elif action == "director":
            if context["may_assign_director"] == "True":
                assign_action = True
        elif action == "exec":
            if context["may_assign_exec"] == "True":
                assign_action = True
        elif action == "creator":
            if context["may_assign_to_creator"] == "True":
                assign_action = True
        return assign_action

    def groupList(self):

        DefaultGroups = {'grouplink': {}, 'group': {}}
        DefaultGroups['grouplink']['admin'] = 'Statdev Processor'
        DefaultGroups['grouplink']['assess'] = 'Statdev Assessor'
        DefaultGroups['grouplink']['manager'] = 'Statdev Approver'
        DefaultGroups['grouplink']['director'] = 'Statdev Director'
        DefaultGroups['grouplink']['exec'] = 'Statdev Executive'
        DefaultGroups['grouplink']['referral'] = 'Statdev Referee'
        DefaultGroups['grouplink']['emergency'] = 'Statdev Emergency'

        # create reverse mapping groups
        for g in DefaultGroups['grouplink']:
            val = DefaultGroups['grouplink'][g]
            DefaultGroups['group'][val] = g
        return DefaultGroups
    def FriendlyGroupList(self):
        DefaultGroups = {'grouplink': {}, 'group': {}}
        DefaultGroups['grouplink']['admin'] = 'Admin Officer'
        DefaultGroups['grouplink']['assess'] = 'Assessor'
        DefaultGroups['grouplink']['manager'] = 'Manager'
        DefaultGroups['grouplink']['director'] = 'Director'
        DefaultGroups['grouplink']['exec'] = 'Executive'
        DefaultGroups['grouplink']['referral'] = 'Referee'
        DefaultGroups['grouplink']['emergency'] = 'Emergency'
        return DefaultGroups

    def getWorkFlowTypeFromApp(self,app):
        workflowtype = ''
        if app.app_type == app.APP_TYPE_CHOICES.part5:
            workflowtype = 'part5'
        elif app.app_type == app.APP_TYPE_CHOICES.emergency:
            workflowtype = 'emergency'
        elif app.app_type == app.APP_TYPE_CHOICES.permit:
            workflowtype = 'permit'
        elif app.app_type == app.APP_TYPE_CHOICES.licence:
            workflowtype = 'licence'
        elif app.app_type == app.APP_TYPE_CHOICES.part5cr:
            workflowtype = 'part5cr'
        elif app.app_type == app.APP_TYPE_CHOICES.part5amend:
            workflowtype = 'part5amend'
        elif app.app_type == app.APP_TYPE_CHOICES.permitamend:
            workflowtype = 'permitamend'
        elif app.app_type == app.APP_TYPE_CHOICES.licenceamend:
            workflowtype = 'licenceamend'
        elif app.app_type == app.APP_TYPE_CHOICES.permitrenew:
            workflowtype = 'permitrenew'
        elif app.app_type == app.APP_TYPE_CHOICES.licencerenew:
            workflowtype = 'licencerenew'
        elif app.app_type == app.APP_TYPE_CHOICES.test:
            workflowtype = 'test'
        else:
            print ("No Work Flow Group in workflow.py function getWorkFlowTypeFromApp")
            workflowtype = '' 
        return workflowtype


    def getWorkflowOptions(self):
        json_obj = self.json_obj
        if "options" in json_obj:
            return json_obj["options"]
        return None
