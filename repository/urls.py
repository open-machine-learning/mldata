from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
import repository.views as views

urlpatterns = patterns('',
    (r'^$', views.index),
    (r'^rate/(?P<type>[A-Za-z0-9-_]+)/(?P<id>\d+)/$', views.rate),
    (r'^data/$', views.data_index),
    (r'^data/my/$', views.data_my),
    (r'^data/new/$', views.data_new),
    (r'^data/view/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.data_view),
    (r'^data/edit/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.data_edit),
    (r'^data/delete/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.data_delete),
    (r'^data/activate/(?P<id>\d+)/$', views.data_activate),
    (r'^data/download/(?P<id>\d+)/$', views.data_download),
    (r'^data/tags/$', views.tags_index),
    (r'^data/tags/(?P<tag>[A-Za-z0-9-_]+)/$', views.tags_view),
    (r'^data/license$', direct_to_template, {'template':'repository/license.html'}),
    (r'^task/$', views.task_index),
    (r'^task/new$', views.task_new),
    (r'^task/view/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.task_view),
    (r'^task/edit/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.task_edit),
    (r'^solution/$', views.solution_index),
    (r'^solution/new$', views.solution_new),
    (r'^solution/view/(\d+)/$', views.solution_view),
)
