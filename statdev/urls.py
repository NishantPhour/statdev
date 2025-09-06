from django.urls import include, path, re_path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import login, logout
# from ledger.accounts.views import logout 
from ledger_api_client.urls import urlpatterns as ledger_patterns

urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    # re_path(r'^login/$', login, name='login', kwargs={'template_name': 'login.html'}),
    # re_path(r'^logout/$', logout, name='logout' ),
    re_path(r'^', include('applications.urls')),
    re_path(r'^', include('approvals.urls')),
    re_path(r'^', include('public.urls')),
    path('', include('social_django.urls', namespace='social')),
    # url(r'^ledger/', include('ledger.accounts.urls', namespace='accounts')),
    # url(r'^ledger/', include('social_django.urls', namespace='social')),
    #url(r'^', include('approvals.urls'))
] + ledger_patterns

if settings.ENABLE_DJANGO_LOGIN:
    urlpatterns.append(
        re_path(r"^ssologin/", auth_views.LoginView.as_view(), name="ssologin")
    )

if settings.DEBUG:
    from django.views.static import serve
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
