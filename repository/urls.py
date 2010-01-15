"""
URL patterns for Repository
"""

from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
import repository.views as views

urlpatterns = patterns('',
    url(r'^$', views.index, name='repository_index'),
    (r'^tags/$', views.tags_index),
    (r'^tags/(?P<tag>[A-Za-z0-9-_]+)/$', views.tags_view),
    (r'^data/$', views.data_index),
    (r'^data/my/$', views.data_my),
    (r'^data/new/$', views.data_new),
    (r'^data/new/review/(?P<id>\d+)/$', views.data_new_review),
    (r'^data/view/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.data_view),
    (r'^data/edit/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.data_edit),
    (r'^data/delete/(?P<id>\d+)/$', views.data_delete),
    (r'^data/activate/(?P<id>\d+)/$', views.data_activate),
    (r'^data/download/(?P<id>\d+)/$', views.data_download),
    (r'^data/rate/(?P<id>\d+)/$', views.data_rate),
    (r'^task/$', views.task_index),
    (r'^task/my/$', views.task_my),
    (r'^task/new$', views.task_new),
    (r'^task/view/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.task_view),
    (r'^task/edit/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.task_edit),
    (r'^task/delete/(?P<id>\d+)/$', views.task_delete),
    (r'^task/activate/(?P<id>\d+)/$', views.task_activate),
    (r'^task/rate/(?P<id>\d+)/$', views.task_rate),
    (r'^splits/download/(?P<id>\d+)/$', views.splits_download),
    (r'^solution/$', views.solution_index),
    (r'^solution/my/$', views.solution_my),
    (r'^solution/new$', views.solution_new),
    (r'^solution/view/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.solution_view),
    (r'^solution/edit/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.solution_edit),
    (r'^solution/delete/(?P<id>\d+)/$', views.solution_delete),
    (r'^solution/activate/(?P<id>\d+)/$', views.solution_activate),
    (r'^solution/rate/(?P<id>\d+)/$', views.solution_rate),
    (r'^score/download/(?P<id>\d+)/$', views.score_download),
)
