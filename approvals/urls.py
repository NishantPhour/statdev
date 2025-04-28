from django.urls import re_path
from approvals import views

urlpatterns = [
                  re_path(r'^approvals/$', views.ApprovalList.as_view(), name='approval_list'),
                  re_path(r'^approvals/(?P<pk>\d+)/$', views.ApprovalDetails.as_view(), name='approval_detail'),
                  re_path(r'^approvals/(?P<pk>\d+)/change/(?P<status>\w+)/$', views.ApprovalStatusChange.as_view(), name='approval_status_change'),
                  re_path(r'^approvals/(?P<pk>\d+)/actions/$', views.ApprovalActions.as_view(), name='approval_actions'),
                  re_path(r'^approvals/(?P<pk>\d+)/comms-create/$', views.ApprovalCommsCreate.as_view(), name='approvals_comms_create'),
                  re_path(r'^approvals/(?P<pk>\d+)/comms/$', views.ApprovalComms.as_view(), name='approvals_comms'),
                  re_path(r'^approvals/viewpdf-(?P<approval_id>\d+).pdf$', views.getPDF, name='approvals_view_pdf'),
              ]
