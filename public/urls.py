from django.urls import re_path
from public import views

urlpatterns = [
                  re_path(r'^public/applications/(?P<action>\w+)/$', views.PublicApplicationsList.as_view(), name='public_application_list'),
                  re_path(r'^public/application/(?P<pk>\d+)/(?P<action>\w+)/$', views.PublicApplicationFeedback.as_view(), name='public_application'),
              ]

