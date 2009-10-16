from django.conf.urls.defaults import *
import repository.views as views

urlpatterns = patterns('',
    (r'^$', views.index),
    (r'^data/$', views.data_index),
    (r'^data/new$', views.data_new),
    (r'^data/view/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.data_view),
    (r'^data/edit/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.data_edit),
    (r'^data/delete/(?P<slug_or_id>[A-Za-z0-9-_]+)/$', views.data_delete),
    (r'^data/activate/(?P<id>\d+)/$', views.data_activate),
    (r'^task/$', views.task_index),
    (r'^task/new$', views.task_new),
    (r'^task/view/(\d+)/$', views.task_view),
    (r'^solution/$', views.solution_index),
    (r'^solution/new$', views.solution_new),
    (r'^solution/view/(\d+)/$', views.solution_view),
)
