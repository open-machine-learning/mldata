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
    url(r'^search/$', views.base.search, name='repository_search'),

    # tags
    url(r'^tags/data/(?P<tag>[A-Za-z0-9-_.]+)/$', views.data.tags_view, name='data_tags_view'),
    url(r'^tags/task/(?P<tag>[A-Za-z0-9-_.]+)/$', views.task.tags_view, name='task_tags_view'),
    url(r'^tags/solution/(?P<tag>[A-Za-z0-9-_.]+)/$', views.solution.tags_view, name='solution_tags_view'),
    url(r'^tags/challenge/(?P<tag>[A-Za-z0-9-_.]+)/$', views.challenge.tags_view, name='challenge_tags_view'),

    # data, tasks, solutions, challenges
    (r'^data/', include('mldata.repository.data_urls')),
    (r'^task/', include('mldata.repository.task_urls')),
    (r'^solution/', include('mldata.repository.solution_urls')),
    (r'^challenge/', include('mldata.repository.challenge_urls')),

    # publications
    url(r'^publication/edit/$', views.publication.edit, name='publication_edit'),
    url(r'^publication/get/(?P<id>\d+)/$', views.publication.get, name='publication_get'),

    # upload progress AJAX
    (r'^upload_progress/$', views.ajax.upload_progress),
)
