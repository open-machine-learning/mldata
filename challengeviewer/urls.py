"""
URLconf for datacite app. The only view is the xml file
with matadata related to given dataset. View gets the DOI
and recovers item's slug and version from it.
"""

from django.conf.urls.defaults import *
from django.contrib.auth import views as auth_views
from challengeviewer.views import *

urlpatterns = patterns('',
                       url(r'^(?P<slug>[A-Za-z0-9-_]+)/$',
                           challengeviewer_index,
                           {},
                           name='challengeviewer_index'),
                       url(r'^(?P<slug>[A-Za-z0-9-_]+)/results/$',
                           challengeviewer_results,
                           {},
                           name='challengeviewer_results'),
                       url(r'^(?P<slug>[A-Za-z0-9-_]+)/submit/$',
                           challengeviewer_submit,
                           {},
                           name='challengeviewer_submit'),
                       url(r'^(?P<slug>[A-Za-z0-9-_]+)/login/$',
                           challengeviewer_login,
                           {},
                           name='challengeviewer_login'),
                       url(r'^(?P<slug>[A-Za-z0-9-_]+)/logout/$',
                           challengeviewer_logout,
                           {},
                           name='challengeviewer_logout'),
                       url(r'^(?P<slug>[A-Za-z0-9-_]+)/task/(?P<task_slug>[A-Za-z0-9-_]+)/$',
                           challengeviewer_task,
                           {},
                           name='challengeviewer_task'),
                       )
