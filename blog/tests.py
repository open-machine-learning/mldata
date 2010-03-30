import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from blog.models import Post


class BlogTest(TestCase):
    # local urls won't work, coz templates refer to repository_index
    #urls = 'user.urls'
    url = {
        'index': '/blog/',
        'new': '/blog/new/',
    }
    entry = {
        'headline':'headline',
        'summary':'summary',
        'body':'body',
    }
    date = {
        'year': '2010',
        'month': '03',
        'day': '30',
    }


    def setUp(self):
        user = User.objects.create_user('user', 'user@mldata.org', 'user')
        user.save()

        post = Post()
        post.pub_date = datetime.datetime(
            int(self.date['year']),
            int(self.date['month']),
            int(self.date['day'])
        )
        post.headline = 'h'
        post.summary = 's'
        post.body = 'b'
        post.author_id = user.id
        post.save()


    def test_index(self):
        r = self.client.get(self.url['index'])
        self.assertEqual(r.context['section'], 'blog')
        self.assertTemplateUsed(r, 'blog/post_archive.html')


    def test_new_anon(self):
        r = self.client.get(self.url['new'])
        self.assertEqual(r.status_code, 302)
        for item in r.items():
            if item[0] == 'Location':
                self.assertEqual(
                    item[1].split('?')[-1], 'next=' + self.url['new'])


    def test_new_user(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.get(self.url['new'])
        self.assertEqual(r.context['section'], 'blog')
        self.assertTemplateUsed(r, 'blog/new.html')


    def test_post_anon(self):
        r = self.client.post(self.url['new'], self.entry)
        self.assertEqual(r.status_code, 302)
        for item in r.items():
            if item[0] == 'Location':
                self.assertEqual(
                    item[1].split('?')[-1], 'next=' + self.url['new'])


    def test_post_user(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.post(self.url['new'], self.entry, follow=True)
        self.assertEqual(r.context['section'], 'blog')
        self.assertTemplateUsed(r, 'blog/post_detail.html')


    def test_view_detail(self):
        url = self.url['index'] +\
            self.date['year'] + '/' +\
            self.date['month'] + '/' +\
            self.date['day'] + '/' +\
            'h/'
        r = self.client.get(url)
        self.assertEqual(r.context['section'], 'blog')
        self.assertTemplateUsed(r, 'blog/post_detail.html')


    def test_view_year(self):
        url = self.url['index'] + self.date['year'] + '/'
        r = self.client.get(url)
        self.assertEqual(r.context['section'], 'blog')
        self.assertTemplateUsed(r, 'blog/post_archive_year.html')


    def test_view_month(self):
        url = self.url['index'] +\
            self.date['year'] + '/' +\
            self.date['month'] + '/'
        r = self.client.get(url)
        self.assertEqual(r.context['section'], 'blog')
        self.assertTemplateUsed(r, 'blog/post_archive_month.html')


    def test_view_day(self):
        url = self.url['index'] +\
            self.date['year'] + '/' +\
            self.date['month'] + '/' +\
            self.date['day'] + '/'
        r = self.client.get(url)
        self.assertEqual(r.context['section'], 'blog')
        self.assertTemplateUsed(r, 'blog/post_archive_day.html')
