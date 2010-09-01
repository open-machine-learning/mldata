"""
URL patterns for Repository
"""

from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
import repository.views as views
import repository.views.data as data


urlpatterns = patterns('',
    # index
    url(r'^$', views.index, name='repository_index'),

    # search
    (r'^search/$', views.search),

    # tags
    (r'^tags/data/(?P<tag>[A-Za-z0-9-_.]+)/$', views.tags_data_view),
    (r'^tags/task/(?P<tag>[A-Za-z0-9-_.]+)/$', views.tags_task_view),
    (r'^tags/solution/(?P<tag>[A-Za-z0-9-_.]+)/$', views.tags_solution_view),

    # data sets
    url(r'^data/$', views.data.index, name='data_index'),
    (r'^data/my/$', views.data.my),
    (r'^data/new/$', views.data.new),
    (r'^data/new/review/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.new_review),
    (r'^data/view/(?P<id>\d+)/$', views.data.view),

    (r'^view/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.view_slug),
    (r'^view/(?P<slug>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.data.view_slug),

    (r'^data/edit/(?P<id>\d+)/$', views.data.edit),
    (r'^data/delete/(?P<id>\d+)/$', views.data.delete),
    (r'^data/activate/(?P<id>\d+)/$', views.data.activate),
    (r'^data/download/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.download),
    (r'^data/download/xml/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.download_xml),
    (r'^data/download/csv/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.download_csv),
    (r'^data/download/arff/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.download_arff),
    (r'^data/download/libsvm/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.download_libsvm),
    (r'^data/download/matlab/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.download_matlab),
    (r'^data/download/octave/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.download_octave),
    url(r'^data/rate/(?P<id>\d+)/$', views.data.rate, name='repository_data_rate'),

    # tasks
    url(r'^task/$', views.task_index, name='task_index'),
    (r'^task/my/$', views.task_my),
    (r'^task/new/$', views.task_new),
    (r'^task/view/(?P<id>\d+)/$', views.task_view),

    (r'^view/(?P<slug_data>[A-Za-z0-9-_]+)/(?P<slug_task>[A-Za-z0-9-_]+)/$', views.task_view_slug),
    (r'^view/(?P<slug_data>[A-Za-z0-9-_]+)/(?P<slug_task>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.task_view_slug),

    (r'^task/edit/(?P<id>\d+)/$', views.task_edit),
    (r'^task/delete/(?P<id>\d+)/$', views.task_delete),
    (r'^task/activate/(?P<id>\d+)/$', views.task_activate),
    url(r'^task/rate/(?P<id>\d+)/$', views.task_rate, name='repository_task_rate'),
    (r'^task/download/(?P<slug>[A-Za-z0-9-_]+)/$', views.task_download),
    (r'^task/predict/(?P<slug>[A-Za-z0-9-_]+)/$', views.task_predict),

    # solutions
#    url(r'^solution/$', views.solution_index, name='solution_index'),
#    (r'^solution/my/$', views.solution_my),
#    (r'^solution/view/(?P<id>\d+)/$', views.solution_view),
#    (r'^solution/new/$', views.solution_new),
#    (r'^solution/edit/(?P<id>\d+)/$', views.solution_edit),
#    (r'^solution/delete/(?P<id>\d+)/$', views.solution_delete),
#    (r'^solution/activate/(?P<id>\d+)/$', views.solution_activate),
#    url(r'^solution/rate/(?P<id>\d+)/$', views.solution_rate, name='repository_solution_rate'),
#    (r'^score/download/(?P<id>\d+)/$', views.score_download),
#    (r'^view/(?P<slug_data>[A-Za-z0-9-_]+)/(?P<slug_task>[A-Za-z0-9-_]+)/(?P<slug_solution>[A-Za-z0-9-_]+)/$', views.solution_view_slug),
#    (r'^view/(?P<slug_data>[A-Za-z0-9-_]+)/(?P<slug_task>[A-Za-z0-9-_]+)/(?P<slug_solution>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.solution_view_slug),

    # publications
    (r'^publication/edit/$', views.publication_edit),
    (r'^publication/get/(?P<id>\d+)/$', views.publication_get),

    # upload progress AJAX
    (r'^upload_progress/$', views.upload_progress),
)
