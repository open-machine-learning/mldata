"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
import os

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files import File
from datetime import datetime as dt

from settings import *

from repository.models import *
from preferences.models import *

from repository.models.task import *
from repository.models.data import *
from repository.models.method import *

class RepositoryTest(TestCase):
    def remove_if_exists(self, path):
        try:
            os.remove(path)
        except OSError, e:
            # No file to be removed
            pass

    url = {
        'index': '/repository/',
        'index_data': '/repository/data/',
        'index_task': '/repository/task/',
        'index_method': '/repository/method/',
        'index_tags': '/repository/tags/',
        'view_tags_foobar': '/repository/tags/data/foobar/',
        'index_data_my': '/repository/data/my/',
        'index_task_my': '/repository/task/my/',
        'index_method_my': '/repository/method/my/',
        'new_data': '/repository/data/new/',
        'new_task': '/repository/task/new/',
        'new_method': '/repository/method/new/',
        'new_data_review': '/repository/data/new/review/test/',
        'new_data_view': '/repository/data/view/test/',

        'new_data_review_generic': '/repository/data/new/review/%s/',
        'new_data_view_generic': '/repository/data/view/%s/',
        }
    minimal_data = {
        'license': '1',
        'name': 'test',
        'summary': 'summary',
        'tags': 'test, data',
        'file': open('fixtures/breastcancer-small.txt', 'r'),
    }
    data_file_name = os.path.join(MEDIA_ROOT, 'data', 'test.h5')
    data_file_name_src = os.path.join(MEDIA_ROOT, 'data', 'breastcancer.txt')
    review_data_approve = {
        'format': 'libsvm',
        'seperator': ' ',
        'convert': '1',
        'approve': '1',
    }
    review_data_revert = {
        'format': 'arff',
        'revert': '1',
    }

    #
    # Some helper functions
    #
    def do_login(self):
        if not self.client.login(username='user', password='pass'):
            raise Exception('Login unsuccessful')

    def do_get(self, url, follow=False):
        return self.client.get(self.url[url], follow=follow)

    def do_post(self, url, params, follow=False):
        return self.client.post(self.url[url], params, follow=follow)

    #
    # Tests
    #

    def setUp(self):
        user = User.objects.create_user('user', 'user@mldata.org', 'pass')
        user.save()
        license = License(name='foobar', url='http://foobar.com')
        license.save()
        license = FixedLicense(name='foobar', url='http://foobar.com')
        license.save()
        data = Data(name='foobar',
            pub_date=dt.now(), version=1, user_id=1, license_id=1,
            is_current=True, is_public=True, is_approved=True,
            tags='foobar')
        data.save()
        p = Preferences(name='default', max_data_size=1024*1024*64)
        p.save()


class CorrectnessTest(RepositoryTest):
    def test_index(self):
        r = self.do_get('index')
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/index.html')


    def test_index_data(self):
        r = self.do_get('index_data')
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/item_index.html')


    def test_index_task(self):
        r = self.do_get('index_task')
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/item_index.html')


#    def test_index_method(self):
#        r = self.client.get(self.url['index_method'])
#        self.assertEqual(r.context['section'], 'repository')
#        self.assertTemplateUsed(r, 'repository/item_index.html')


    def test_index_data_my(self):
        r = self.do_get('index_data_my')
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/item_index.html')


    def test_index_task_my(self):
        r = self.do_get('index_task_my')
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/item_index.html')


#    def test_index_method_my(self):
#        r = self.client.get(self.url['index_method_my'])
#        self.assertEqual(r.context['section'], 'repository')
#        self.assertTemplateUsed(r, 'repository/item_index.html')


    def test_new_data_anon(self):
        r = self.do_get('new_data', follow=True)
        self.assertTemplateUsed(r, 'authopenid/signin.html')


    def test_new_task_anon(self):
        r = self.do_get('new_task', follow=True)
        self.assertTemplateUsed(r, 'authopenid/signin.html')


#    def test_new_method_anon(self):
#        r = self.client.get(self.url['new_method'], follow=True)
#        self.assertTemplateUsed(r, 'authopenid/signin.html')

    def test_new_data_user(self):
        self.do_login()
        r = self.do_get('new_data', follow=True)
        self.assertTemplateUsed(r, 'data/item_new.html')



    def test_new_data_user_approve(self):
        """Post a new data set and approve"""
        self.remove_if_exists(self.data_file_name)

        self.do_login()
        r = self.do_post('new_data', self.minimal_data, follow=True)

        self.minimal_data['file'].seek(0)
        self.assertTemplateUsed(r, 'data/data_new_review.html')
        r = self.do_post('new_data_review', self.review_data_approve, follow=True)

        self.assertTemplateUsed(r, 'data/item_view.html')
        self.assertTrue(os.access(self.data_file_name_src, os.R_OK), 'Cannot read ' + self.data_file_name_src)
        self.assertTrue(os.access(self.data_file_name, os.R_OK), 'Cannot read ' + self.data_file_name + '.\nProbably conversion error')


    def test_new_data_user_revert(self):
        self.do_login()
        r = self.do_post('new_data', self.minimal_data, follow=True)
        self.minimal_data['file'].seek(0)
        self.assertTemplateUsed(r, 'data/data_new_review.html')
        r = self.do_post('new_data_review', self.review_data_revert, follow=True)
        self.assertTemplateUsed(r, 'data/item_new.html')


    def test_new_task_user(self):
        self.do_login()
        r = self.do_get('new_task', follow=True)
        self.assertTemplateUsed(r, 'task/item_new.html')


#    def test_new_method_user(self):
#        if not self.client.login(username='user', password='user'):
#            raise Exception('Login unsuccessful')
#        r = self.client.get(self.url['new_method'], follow=True)
#        self.assertTemplateUsed(r, 'repository/item_new.html')


    def test_view_tags_foobar(self):
        r = self.do_get('view_tags_foobar')
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/item_index.html')

    def test_create_data_set(self):
        d = Data(name = 'test_data_set',
            user=User.objects.get(username='user'),
            license=License.objects.get(name='foobar'))

        d.create_slug()
        d.attach_file(File(open('fixtures/breastcancer.txt', 'r')))
        d.save()
        self.assertEqual(1, len(Data.objects.filter(name='test_data_set')))

    def test_tags_with_comma(self):
        d = Data(name = 'test_data_set_tags',
            user=User.objects.get(username='user'),
            license=License.objects.get(name='foobar'),
            tags="test, test2")

        d.create_slug()
        d.attach_file(File(open('fixtures/breastcancer.txt', 'r')))
        d.save()

        datasets = Data.objects.filter(name='test_data_set_tags')
        self.assertEqual(1, len(datasets))

        # if tags were added properly then TagField
        # returnes them without comma. Functionality tested in tagging app
        self.assertEqual("test test2", datasets[0].tags)

    def test_task_results(self):
        #login user
        self.do_login()

        # create collaborative-filtering dataset by hand
        file = open('fixtures/ratings.csv', 'w')
        file.write("1,1,5\n3,1,2\n1,3,3\n3,4,5\n2,1,5\n2,3,5\n2,4,2\n3,3,4\n1,2,2\n")
        file.close()

        # convert file to hdf5
        from ml2h5.converter import Converter
        Converter("fixtures/ratings.csv","fixtures/ratings.h5").run()

        # create a dataset by adding Data entity (not via www which was tested bedore)
        d = Data(name = 'test_data_set_recommends',
            user=User.objects.get(username='user'),
            license=License.objects.get(name='foobar'),
            tags="")
        d.create_slug()
        d.attach_file(File(open('fixtures/ratings.h5', 'r')))

        # following fields are required for creating task
        d.num_instances = 9
        d.num_attributes = 3
        d.is_approved = True
        d.is_current = True
        d.is_public = True
        d.save()

        # create task via www (since we want to indicate variables, and train/test set
        r = self.do_post('new_task', {
                 'name': 'test_task_recommends',
                 'data': d.id,
                 'input_variables': '0:2',
                 'output_variables': '2:3',
                 'train_idx': '0:6',
                 'test_idx': '6:9',
                 'input': ' ',
                 'output': ' ',
                 'type': 'Regression',
                 'performance_measure': 'Root Mean Squared Error'
            }, follow=True)
        t = Task.objects.get(slug__text='test_task_recommends')

        # create dummy method
        m = Method(name = 'Collaborative-filtering',
                 user=User.objects.get(username='user'),
                 license=FixedLicense.objects.get(name='foobar'),
                 )
        m.save()

        # write some results for task
        file = open('fixtures/res.txt', 'w')
        file.write("1\n1\n3\n")
        file.close()

        # create results entity
        r = Result(task = t, method = m, output_file=File(open('fixtures/res.txt','r')))
        r.save()

        # store predictions
        score,msg,success = r.predict()

        # check if whole path succeeded
        self.assertGreater(score,-1,msg)


class PerformenceTest(RepositoryTest):
    def add_data(self, suffix=''):
        self.do_login()
        data = self.minimal_data.copy()

        data['name'] = data['name'] + suffix
        self.remove_if_exists(os.path.join(MEDIA_ROOT, 'data', data['name'] + ".h5"))
        r = self.client.post(self.url['new_data'],
                             data,
                             follow=True)

        self.minimal_data['file'].seek(0)
        self.assertTemplateUsed(r, 'data/data_new_review.html')
        r = self.client.post(self.url['new_data_review_generic'] % data['name'],
                             self.review_data_approve,
                             follow=True)
        self.assertTemplateUsed(r, 'data/item_view.html')

    def test_view_data_queries(self):
        from django.conf import settings
        from django.db import connection

        self.remove_if_exists(self.data_file_name)
        settings.DEBUG = True
        self.add_data()
        connection.queries = []
        r = self.do_post('new_data_view', {}, follow=True)
        self.assertLess(len(connection.queries), 5, "More than 5 queries executed during simple data view")
        settings.DEBUG = False

    def test_view_many_datasets(self):
        from django.conf import settings
        from django.db import connection

        for i in xrange(1, 10):
            self.add_data(i.__str__())

        import time
        start = time.time()
        settings.DEBUG = True
        connection.queries = []
        r = self.do_post('new_data_view', {}, follow=True)
        self.assertLess(len(connection.queries), 5, "More than 5 queries executed during simple data view")
        settings.DEBUG = False
        self.assertLess(time.time() - start, 1000, "Slow response ( > 1 sek)")
