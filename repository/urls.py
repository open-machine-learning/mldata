from django.conf.urls.defaults import *
import repository.views as views

urlpatterns = patterns('',
    (r'^$', views.index),
    (r'^data/$', views.data_index),
    (r'^data/new$', views.data_new),
    (r'^task/$', views.task_index),
    (r'^task/new$', views.task_new),
    (r'^solution/$', views.solution_index),
    (r'^solution/new$', views.solution_new),
)
