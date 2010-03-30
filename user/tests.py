from django.test import TestCase
from django.contrib.auth.models import User


class UserTest(TestCase):
    # local urls won't work, coz templates refer to repository_index
    #urls = 'user.urls'
    url = {
        'index': '/user/',
        'view_user': '/user/view/2/',
        'view_admin': '/user/view/1/',
        'update_user': '/user/update/2/',
        'update_admin': '/user/update/1/',
    }
    updated_user = {
        'firstname': 'foo',
        'lastname': 'bar',
        'email': 'update@mldata.org',
        'password1': 'baz',
        'password2': 'baz',
    }


    def setUp(self):
        admin = User.objects.create_user('admin', 'admin@mldata.org', 'admin')
        admin.is_superuser = True
        admin.save()
        user = User.objects.create_user('user', 'user@mldata.org', 'user')
        user.save()


    def test_index_anon(self):
        r = self.client.get(self.url['index'])
        self.assertEqual(r.status_code, 403)


    def test_index_user(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.get(self.url['index'])
        self.assertEqual(r.status_code, 403)


    def test_index_admin(self):
        if not self.client.login(username='admin', password='admin'):
            raise Exception('Login unsuccessful')
        r = self.client.get(self.url['index'])
        self.assertEqual(r.context['section'], 'accounts')
        self.assertTemplateUsed(r, 'user/user_list.html')


    def test_view_anon(self):
        r = self.client.get(self.url['view_user'])
        self.assertEqual(r.status_code, 403)


    def test_view_user(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.get(self.url['view_user'])
        self.assertEqual(r.context['section'], 'accounts')
        self.assertTemplateUsed(r, 'user/user_detail.html')


    def test_view_admin(self):
        if not self.client.login(username='admin', password='admin'):
            raise Exception('Login unsuccessful')
        r = self.client.get(self.url['view_user'])
        self.assertEqual(r.context['section'], 'accounts')
        self.assertTemplateUsed(r, 'user/user_detail.html')


    def test_view_other(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.get(self.url['view_admin'])
        self.assertEqual(r.status_code, 403)


    def test_update_anon(self):
        r = self.client.post(self.url['update_user'], self.updated_user)
        self.assertEqual(r.status_code, 403)


    def test_update_user(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.post(self.url['update_user'], self.updated_user)
        self.assertEqual(r.context['section'], 'accounts')
        self.assertTemplateUsed(r, 'user/user_change_done.html')
        user = User.objects.get(pk=2)
        self.assertEqual(user.first_name, self.updated_user['firstname'])


    def test_update_admin(self):
        if not self.client.login(username='admin', password='admin'):
            raise Exception('Login unsuccessful')
        r = self.client.post(self.url['update_user'], self.updated_user)
        self.assertEqual(r.context['section'], 'accounts')
        self.assertTemplateUsed(r, 'user/user_change_done.html')
        user = User.objects.get(pk=2)
        self.assertEqual(user.first_name, self.updated_user['firstname'])


    def test_update_other(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.post(self.url['update_admin'], self.updated_user)
        self.assertEqual(r.status_code, 403)


