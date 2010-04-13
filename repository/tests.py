"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from repository.models import License


class RepositoryTest(TestCase):
    url = {
        'index': '/repository/',
        'index_data': '/repository/data/',
        'index_task': '/repository/task/',
        'index_solution': '/repository/solution/',
        'index_tags': '/repository/tags/',
        'view_tags_foobar': '/repository/tags/foobar/',
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
        'file': open('dooby.arff', 'r'),
    }
    review_data_approve = {
        'id_format': 'arff',
        'approve': '1',
    }
    review_data_revert = {
        'id_format': 'arff',
        'revert': '1',
    }


    def setUp(self):
        user = User.objects.create_user('user', 'user@mldata.org', 'user')
        user.save()
        license = License(name='foobar', url='http://foobar.com')
        license.save()


    def test_index(self):
        r = self.client.get(self.url['index'])
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/index.html')


    def test_index_data(self):
        r = self.client.get(self.url['index_data'])
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/item_index.html')


    def test_index_task(self):
        r = self.client.get(self.url['index_task'])
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/item_index.html')


    def test_index_solution(self):
        r = self.client.get(self.url['index_solution'])
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/item_index.html')


    def test_index_data_my(self):
        r = self.client.get(self.url['index_data_my'])
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/item_index.html')


    def test_index_task_my(self):
        r = self.client.get(self.url['index_task_my'])
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/item_index.html')


    def test_index_solution_my(self):
        r = self.client.get(self.url['index_solution_my'])
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/item_index.html')


    def test_new_data_anon(self):
        r = self.client.get(self.url['new_data'], follow=True)
        self.assertTemplateUsed(r, 'authopenid/signin.html')


    def test_new_task_anon(self):
        r = self.client.get(self.url['new_task'], follow=True)
        self.assertTemplateUsed(r, 'authopenid/signin.html')


    def test_new_solution_anon(self):
        r = self.client.get(self.url['new_solution'], follow=True)
        self.assertTemplateUsed(r, 'authopenid/signin.html')


    def test_new_data_user(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.get(self.url['new_data'], follow=True)
        self.assertTemplateUsed(r, 'repository/item_new.html')


    def test_new_data_user_approve(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.post(self.url['new_data'], self.minimal_data,
            follow=True)
        self.minimal_data['file'].seek(0)
        self.assertTemplateUsed(r, 'repository/data_new_review.html')
        r = self.client.post(self.url['new_data_review'],
            self.review_data_approve, follow=True)
        self.assertTemplateUsed(r, 'repository/item_view.html')


    def test_new_data_user_revert(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.post(self.url['new_data'], self.minimal_data,
            follow=True)
        self.minimal_data['file'].seek(0)
        self.assertTemplateUsed(r, 'repository/data_new_review.html')
        r = self.client.post(self.url['new_data_review'],
            self.review_data_revert, follow=True)
        self.assertTemplateUsed(r, 'repository/item_new.html')


    def test_new_task_user(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.get(self.url['new_task'], follow=True)
        self.assertTemplateUsed(r, 'repository/item_new.html')


    def test_new_solution_user(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.get(self.url['new_solution'], follow=True)
        self.assertTemplateUsed(r, 'repository/item_new.html')


    def test_index_tags(self):
        r = self.client.get(self.url['index_tags'])
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/tags_index.html')


    def test_view_tags_foobar(self):
        r = self.client.get(self.url['view_tags_foobar'])
        self.assertEqual(r.context['section'], 'repository')
        self.assertTemplateUsed(r, 'repository/tags_view.html')


