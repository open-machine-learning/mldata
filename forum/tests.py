from django.test import TestCase
from django.contrib.auth.models import User
from forum.models import *


class ForumTest(TestCase):
    # local urls won't work, coz templates refer to repository_index
    #urls = 'user.urls'
    url = {
        'index': '/forum/',
        'thread': '/forum/thread/',
    }
    entry_post = {
        'body': 'body',
    }
    entry_thread = {
        'title': 'title',
        'body': 'body',
    }
    forum_title = 'forum'
    thread_title = 'thread'


    def setUp(self):
        user = User.objects.create_user('user', 'user@mldata.org', 'user')
        user.save()

        forum = Forum()
        forum.title = self.forum_title
        forum.slug = self.forum_title
        forum.parent = None
        forum.save()

        thread = Thread()
        thread.forum = forum
        thread.title = self.thread_title
        thread.save()


    def test_index(self):
        r = self.client.get(self.url['index'])
        self.assertEqual(r.context['section'], 'forum')
        self.assertTemplateUsed(r, 'forum/forum_list.html')


    def test_view_forum(self):
        r = self.client.get(self.url['index'] + self.forum_title + '/')
        self.assertEqual(r.context['section'], 'forum')
        self.assertTemplateUsed(r, 'forum/thread_list.html')


    def test_view_thread(self):
        r = self.client.get(self.url['thread'] + '1/')
        self.assertEqual(r.context['section'], 'forum')
        self.assertTemplateUsed(r, 'forum/thread.html')


    def test_newthread_anon(self):
        r = self.client.post(self.url['index'] + self.forum_title + '/new/',
            self.entry_thread, follow=True)
        self.assertTemplateUsed(r, 'authopenid/signin.html')


    def test_newthread_user(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.post(self.url['index'] + self.forum_title + '/new/',
            self.entry_post, follow=True)
        self.assertEqual(r.context['section'], 'forum')
        self.assertTemplateUsed(r, 'forum/thread_new.html')


    def test_reply_anon(self):
        r = self.client.post(self.url['thread'] + '1/reply/',
            self.entry_post, follow=True)
        self.assertTemplateUsed(r, 'authopenid/signin.html')


    def test_reply_user(self):
        if not self.client.login(username='user', password='user'):
            raise Exception('Login unsuccessful')
        r = self.client.post(self.url['thread'] + '1/reply/', self.entry_post, follow=True)
        self.assertEqual(r.context['section'], 'forum')
        self.assertTemplateUsed(r, 'forum/thread.html')



