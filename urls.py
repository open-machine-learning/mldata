from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    (r'^about/', include('about.urls')),

    # Using registration
    (r'^accounts/', include('registration.urls')),
    (r'^forum/', include('forum.urls')),
#    (r'^community/', include('community.urls')),
    (r'^user/', include('user.urls')),

    # Enable comments
    (r'^comments/', include('django.contrib.comments.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),

    # redirect the root to hello
    ('^$', 'django.views.generic.simple.redirect_to', {'url':'/about/'}),
)

if settings.DEBUG and not settings.PRODUCTION:
	urlpatterns += patterns('',(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'media'}),)
