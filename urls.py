from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^about/', include('about.urls')),
    (r'^blog/', include('blog.urls')),
    (r'^forum/', include('forum.urls')),
    (r'^repository/', include('repository.urls')),

    # somewhat util
    #(r'^accounts/', include('registration.urls')),
    (r'^accounts/', include('django_authopenid.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^user/', include('user.urls')),

    # redirect the root to hello
    ('^$', 'django.views.generic.simple.redirect_to', {'url':'/about/'}),
)

if settings.DEBUG and not settings.PRODUCTION:
	urlpatterns += patterns('',(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'media'}),)
