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

    # data sets
    url(r'^data/$', views.data.index, name='data_index'),
    (r'^data/my/$', views.data.my),
    (r'^data/new/$', views.data.new),
    (r'^data/new/review/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.new_review),
    (r'^data/view/(?P<id>\d+)/$', views.data.view),
    (r'^data/viewslug/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.view_slug),
    (r'^data/viewslug/(?P<slug>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.data.view_slug),

    (r'^data/edit/(?P<id>\d+)/$', views.data.edit),
    (r'^data/delete/(?P<id>\d+)/$', views.data.delete),
    (r'^data/activate/(?P<id>\d+)/$', views.data.activate),
    (r'^data/download/([A-Za-z0-9-_]+)/$', views.data.download),
    (r'^data/download/xml/([A-Za-z0-9-_]+)/$', views.data.download_xml),
    (r'^data/download/csv/([A-Za-z0-9-_]+)/$', views.data.download_csv),
    (r'^data/download/arff/([A-Za-z0-9-_]+)/$', views.data.download_arff),
    (r'^data/download/libsvm/([A-Za-z0-9-_]+)/$', views.data.download_libsvm),
    (r'^data/download/matlab/([A-Za-z0-9-_]+)/$', views.data.download_matlab),
    (r'^data/download/octave/([A-Za-z0-9-_]+)/$', views.data.download_octave),
    url(r'^data/rate/(?P<id>\d+)/$', views.data.rate, name='repository_data_rate'),

    # tasks
    url(r'^task/$', views.task.index, name='task_index'),
    (r'^task/my/$', views.task.my),
    (r'^task/new/$', views.task.new),
    (r'^task/view/(?P<id>\d+)/$', views.task.view),
    (r'^task/viewslug/(?P<slug_task>[A-Za-z0-9-_]+)/$', views.task.view_slug),
    (r'^task/viewslug/(?P<slug_task>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.task.view_slug),

    (r'^task/edit/(?P<id>\d+)/$', views.task.edit),
    (r'^task/delete/(?P<id>\d+)/$', views.task.delete),
    (r'^task/activate/(?P<id>\d+)/$', views.task.activate),
    url(r'^task/rate/(?P<id>\d+)/$', views.task.rate, name='repository_task_rate'),
    (r'^task/download/(?P<slug>[A-Za-z0-9-_]+)/$', views.task.download),
    (r'^task/predict/(?P<slug>[A-Za-z0-9-_]+)/$', views.task.predict),
    (r'^task/measures/list/(?P<type>[A-Za-z0-9-_ ]+)/$', views.task.get_measures),
    (r'^task/measures/help/(?P<type>[A-Za-z0-9-_ ]+)/(?P<name>[A-Za-z0-9-_ ]+)/$', views.task.get_measure_help),

    # solutions
    url(r'^solution/$', views.solution.index, name='solution_index'),
    (r'^solution/my/$', views.solution.my),
    (r'^solution/view/(?P<id>\d+)/$', views.solution.view),
    (r'^solution/viewslug/(?P<slug_solution>[A-Za-z0-9-_]+)/$', views.solution.view_slug),
    (r'^solution/viewslug/(?P<slug_solution>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.solution.view_slug),
    (r'^solution/new/$', views.solution.new),
    (r'^solution/edit/(?P<id>\d+)/$', views.solution.edit),
    (r'^solution/delete/(?P<id>\d+)/$', views.solution.delete),
    (r'^solution/activate/(?P<id>\d+)/$', views.solution.activate),
    url(r'^solution/rate/(?P<id>\d+)/$', views.solution.rate, name='repository_solution_rate'),
    (r'^solution/score/download/(?P<id>\d+)/$', views.solution.score_download),

    # challenge
    url(r'^challenge/$', views.challenge.index, name='challenge_index'),
    (r'^challenge/my/$', views.challenge.my),
    (r'^challenge/view/(?P<id>\d+)/$', views.challenge.view),
    (r'^challenge/viewslug/(?P<slug_challenge>[A-Za-z0-9-_]+)/$', views.challenge.view_slug),
    (r'^challenge/viewslug/(?P<slug_challenge>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.challenge.view_slug),
    (r'^challenge/new/$', views.challenge.new),
    (r'^challenge/edit/(?P<id>\d+)/$', views.challenge.edit),
    (r'^challenge/delete/(?P<id>\d+)/$', views.challenge.delete),
    (r'^challenge/activate/(?P<id>\d+)/$', views.challenge.activate),
    url(r'^challenge/rate/(?P<id>\d+)/$', views.challenge.rate, name='repository_challenge_rate'),
    (r'^challenge/score/download/(?P<id>\d+)/$', views.challenge.score_download),
    (r'^challenge/tasks/(?P<id>\d+)/$', views.challenge.get_tasks),

    # publications
    (r'^publication/edit/$', views.publication.edit),
    (r'^publication/get/(?P<id>\d+)/$', views.publication.get),

    # upload progress AJAX
    (r'^upload_progress/$', views.ajax.upload_progress),
)
