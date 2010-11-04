"""
URL patterns for Repository
"""

from django.conf.urls.defaults import *
import repository.views as views
import repository.views.base
import repository.views.data
import repository.views.task
import repository.views.solution
import repository.views.challenge
import repository.views.ajax
import repository.views.publication
import repository.forms as forms

urlpatterns = patterns('',
    # index
    url(r'^$', views.base.main_index, name='repository_index'),

    # search
    (r'^search/$', views.base.search),

    # tags
    (r'^tags/data/(?P<tag>[A-Za-z0-9-_.]+)/$', views.data.tags_view),
    (r'^tags/task/(?P<tag>[A-Za-z0-9-_.]+)/$', views.task.tags_view),
    (r'^tags/solution/(?P<tag>[A-Za-z0-9-_.]+)/$', views.solution.tags_view),
    (r'^tags/challenge/(?P<tag>[A-Za-z0-9-_.]+)/$', views.challenge.tags_view),

    # data, tasks, solutions, challenges
    (r'^data/', include('mldata.repository.data_urls')),
    (r'^task/', include('mldata.repository.task_urls')),
    (r'^solution/', include('mldata.repository.solution_urls')),
    (r'^challenge/', include('mldata.repository.challenge_urls')),

    # publications
    (r'^publication/edit/$', views.publication.edit),
    (r'^publication/get/(?P<id>\d+)/$', views.publication.get),

    # upload progress AJAX
    (r'^upload_progress/$', views.ajax.upload_progress),
)
