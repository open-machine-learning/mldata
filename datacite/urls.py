"""
URLconf for datacite app. The only view is the xml file
with matadata related to given dataset. View gets the DOI
and recovers item's slug and version from it.
"""

from django.conf.urls.defaults import *
from django.contrib.auth import views as auth_views
from datacite.views import metadata_xml, datacite_post

urlpatterns = patterns('',
                       url(r'request-doi/(?P<slug>[A-Za-z0-9-_]+)/$',
                           datacite_post,
                           {},
                           name='datacite_post'),
                       url(r'^(?P<doi>.+)/$',
                           metadata_xml,
                           {},
                           name='metadata_xml'),
                       )
