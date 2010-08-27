"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from datetime import datetime

from repository.models import *
from preferences.models import *


class RepositoryTest(TestCase):
    url = {
        'index': '/repository/',
        'index_data': '/repository/data/',
        'index_task': '/repository/task/',
        'index_solution': '/repository/solution/',
        'index_tags': '/repository/tags/',
        'view_tags_foobar': '/repository/tags/data/foobar/',
        'index_data_my': '/repository/data/my/',
        'index_task_my': '/repository/task/my/',
        'index_solution_my': '/repository/solution/my/',
        'new_data': '/repository/data/new/',
        'new_task': '/repository/task/new/',
        'new_solution': '/repository/solution/new/',
        'new_data_review': '/repository/data/new/review/test/',
    }
    minimal_data = {
        'license': '1',
        'name': 'test',
        'summary': 'summary',
        'tags': 'test, data',
        'file': open('fixtures/breastcancer.txt', 'r'),
    }
    data_file_name = os.path.join(MEDIA_ROOT, 'data', 'test.libsvm.h5')
    review_data_approve = {
        'format': 'arff',
        'seperator': ' ',
        'convert': '0',
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
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')

    def do_get(self, url, follow=False):
        return self.client.get(self.url[url], follow=follow)

    def do_post(self, url, params, follow=False):
        return self.client.post(self.url[url], params, follow=follow)
        
    #
    # Tests
    #

    def setUp(self):
        user = User.objects.create_user('user', 'user@mldata.org', 'user')
        user.save()
        license = License(name='foobar', url='http://foobar.com')
        license.save()
        data = Data(name='foobar',
            pub_date=datetime.now(), version=1, user_id=1, license_id=1,
            is_current=True, is_public=True, is_approved=True,
            tags='foobar')
        data.save()
        p = Preferences(name='default', max_data_size=1024*1024*64)
        p.save()


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


#    def test_index_solution(self):
#        r = self.client.get(self.url['index_solution'])
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


#    def test_index_solution_my(self):
#        r = self.client.get(self.url['index_solution_my'])
#        self.assertEqual(r.context['section'], 'repository')
#        self.assertTemplateUsed(r, 'repository/item_index.html')


    def test_new_data_anon(self):
        r = self.do_get('new_data', follow=True)
        self.assertTemplateUsed(r, 'authopenid/signin.html')


    def test_new_task_anon(self):
        r = self.do_get('new_task', follow=True)
        self.assertTemplateUsed(r, 'authopenid/signin.html')


#    def test_new_solution_anon(self):
#        r = self.client.get(self.url['new_solution'], follow=True)
#        self.assertTemplateUsed(r, 'authopenid/signin.html')

    def test_new_data_user(self):
        self.do_login()
        r = self.do_get('new_data', follow=True)
        self.assertTemplateUsed(r, 'repository/item_new.html')



    def test_new_data_user_approve(self):
        """Post a new data set and approve"""

        os.remove(self.data_file_name)

        self.do_login()
        r = self.do_post('new_data', self.minimal_data, follow=True)
        self.minimal_data['file'].seek(0)
        self.assertTemplateUsed(r, 'repository/data_new_review.html')
        r = self.do_post('new_data_review', self.review_data_approve, follow=True)
        self.assertTemplateUsed(r, 'repository/item_view.html')

        self.assertTrue(os.access(self.data_file_name, os.R_OK), 'Cannot read ' + self.data_file_name + '.')


    def test_new_data_user_revert(self):
        self.do_login()
        r = self.do_post('new_data', self.minimal_data, follow=True)
        self.minimal_data['file'].seek(0)
        self.assertTemplateUsed(r, 'repository/data_new_review.html')
        r = self.do_post('new_data_review', self.review_data_revert, follow=True)
        self.assertTemplateUsed(r, 'repository/item_new.html')


    def test_new_task_user(self):
        self.do_login()
        r = self.do_get('new_task', follow=True)
        self.assertTemplateUsed(r, 'repository/item_new.html')


#    def test_new_solution_user(self):
#        if not self.client.login(username='user', password='user'):
#            raise Exception('Login unsuccessful')
#        r = self.client.get(self.url['new_solution'], follow=True)
#        self.assertTemplateUsed(r, 'repository/item_new.html')


    def test_view_tags_foobar(self):
        r = self.do_get('view_tags_foobar')
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/tags_view.html')
        