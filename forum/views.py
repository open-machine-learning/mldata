"""
All forum logic is kept here - displaying lists of forums, threads 
and posts, adding new threads, and adding replies.

@var FORUM_PAGINATION: number of items on one page
@type FORUM_PAGINATION: integer
"""

from datetime import datetime
from django.shortcuts import get_object_or_404, render_to_response
from django.http import Http404, HttpResponseRedirect, HttpResponseServerError, HttpResponseForbidden
from django.template import RequestContext, loader
from django import forms
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.defaultfilters import striptags, wordwrap
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.views.generic import ListView

from forum.models import Forum,Thread,Post,Subscription
from forum.forms import CreateThreadForm, ReplyForm



FORUM_PAGINATION = getattr(settings, 'FORUM_PAGINATION', 10)


class ForumListView(ListView):
    def get_queryset(self):
        return Forum.objects.for_groups(self.request.user.groups.all()).filter(parent__isnull=True)
    def get_context_data(self, **kwargs):
        context = super(ForumListView, self).get_context_data(**kwargs)
        context['section'] = 'forum'
        return context

class ForumView(ListView):
    context_object_name = 'forum'
    template_name = 'forum/thread_list.html',
    paginate_by = FORUM_PAGINATION
    def get_queryset(self):
        try:
            f = Forum.objects.for_groups(self.request.user.groups.all()).select_related().get(slug=self.kwargs['slug'])
        except Forum.DoesNotExist:
            raise Http404
        return f.thread_set.select_related().all()
    def get_context_data(self, **kwargs):
        try:
            f = Forum.objects.for_groups(self.request.user.groups.all()).select_related().get(slug=self.kwargs['slug'])
        except Forum.DoesNotExist:
            raise Http404
        form = CreateThreadForm()
        child_forums = f.child.for_groups(self.request.user.groups.all())
        extra_context = {
            'forum': f,
            'child_forums': child_forums,
            'form': form,
            'login': {
                'reason': _('create a new thread'),
                'next': f.get_absolute_url(),
            },
            'section': 'forum',
        }
        context = super(ForumView, self).get_context_data(**kwargs)
        for key in extra_context:
            context[key] = extra_context[key]
        return context

class ThreadView(ListView):
    context_object_name = 'post',
    template_name = 'forum/thread.html',
    paginate_by = FORUM_PAGINATION
    def get_queryset(self):
        try:
            t = Thread.objects.select_related().get(pk=self.kwargs['thread'])
            if not Forum.objects.has_access(t.forum, self.request.user.groups.all()):
                return HttpResponseForbidden()
        except Thread.DoesNotExist:
            raise Http404
        p = t.post_set.select_related('author').all().order_by('time')
        return p
    
    def get_context_data(self, **kwargs):
        context = super(ThreadView, self).get_context_data(**kwargs)
        try:
            t = Thread.objects.select_related().get(pk=self.kwargs['thread'])
            if not Forum.objects.has_access(t.forum, self.request.user.groups.all()):
                return HttpResponseForbidden()
        except Thread.DoesNotExist:
            raise Http404
        s = None
        if self.request.user.is_authenticated():
            s = t.subscription_set.select_related().filter(author=self.request.user)
        t.views += 1
        t.save()

        if s:
            initial = {'subscribe': True}
        else:
            initial = {'subscribe': False}

        form = ReplyForm(initial=initial)
        extra_context = {
            'forum': t.forum,
            'thread': t,
            'subscription': s,
            'form': form,
            'login': {
                'reason': _('post a reply'),
                'next': t.get_absolute_url(),
            },
            'section': 'forum',
        }
        for key in extra_context:
            context[key] = extra_context[key]
        return context


def reply(request, thread):
    """Post a reply.

    If a thread isn't closed, and the user is logged in, post a reply
    to a thread. Note we don't have "nested" replies at this stage.

    @param thread: thread id to reply to
    @type thread: integer
    @return: a view to post a reply
    @rtype: Django response
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (reverse('user_signin'), request.path))
    t = get_object_or_404(Thread, pk=thread)
    if t.closed:
        return HttpResponseServerError()
    if not Forum.objects.has_access(t.forum, request.user.groups.all()):
        return HttpResponseForbidden()

    if request.method == "POST":
        form = ReplyForm(request.POST)
        if form.is_valid():
            if request.POST.has_key('preview'):
                preview = {'body': form.cleaned_data['body']}
            else:
                body = form.cleaned_data['body']
                p = Post(
                    thread=t, 
                    author=request.user,
                    body=body,
                    time=datetime.now(),
                    )
                p.save()

                sub = Subscription.objects.filter(thread=t, author=request.user)
                if form.cleaned_data.get('subscribe',False):
                    if not sub:
                        s = Subscription(
                            author=request.user,
                            thread=t
                            )
                        s.save()
                else:
                    if sub:
                        sub.delete()

                if t.subscription_set.count() > 0:
                    # Subscriptions are updated now send mail to all the authors subscribed in
                    # this thread.
                    mail_subject = ''
                    try:
                        mail_subject = settings.FORUM_MAIL_PREFIX 
                    except AttributeError:
                        mail_subject = '[Forum]'

                    mail_from = ''
                    try:
                        mail_from = settings.FORUM_MAIL_FROM
                    except AttributeError:
                        mail_from = settings.DEFAULT_FROM_EMAIL

                    mail_tpl = loader.get_template('forum/notify.txt')
                    c = RequestContext({
                        'body': wordwrap(striptags(body), 72),
                        'site' : Site.objects.get_current(),
                        'thread': t,
                        })

                    email = EmailMessage(
                            subject=mail_subject+' '+striptags(t.title),
                            body= mail_tpl.render(c),
                            from_email=mail_from,
                            bcc=[s.author.email for s in t.subscription_set.all()],)
                    email.send(fail_silently=True)

                return HttpResponseRedirect(p.get_absolute_url())
    else:
        preview = False
        form = ReplyForm()

    return render_to_response('forum/reply.html',
        RequestContext(request, {
            'form': form,
            'forum': t.forum,
            'thread': t,
            'preview': preview,
            'section': 'forum',
        }))


def newthread(request, forum):
    """Post a new thread.

    Rudimentary post function - this should probably use 
    newforms, although not sure how that goes when we're updating 
    two models.

    Only allows a user to post if they're logged in.

    @param forum: forum slug to create new thread for.
    @type forum: string
    @return: a view to post a new thread
    @rtype: Django response
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (reverse('user_signin'), request.path))

    f = get_object_or_404(Forum, slug=forum)

    if not Forum.objects.has_access(f, request.user.groups.all()):
        return HttpResponseForbidden()

    preview = False
    if request.method == 'POST':
        form = CreateThreadForm(request.POST)
        if form.is_valid():
            if request.POST.has_key('preview'):
                preview = {
                    'title': form.cleaned_data['title'],
                    'body': form.cleaned_data['body']
                }
            else:
                t = Thread(
                    forum=f,
                    title=form.cleaned_data['title'],
                )
                t.save()

                p = Post(
                    thread=t,
                    author=request.user,
                    body=form.cleaned_data['body'],
                    time=datetime.now(),
                )
                p.save()

                if form.cleaned_data.get('subscribe', False):
                    s = Subscription(
                        author=request.user,
                        thread=t
                        )
                    s.save()
                return HttpResponseRedirect(t.get_absolute_url())
    else:
        form = CreateThreadForm()

    return render_to_response('forum/thread_new.html',
        RequestContext(request, {
            'form': form,
            'forum': f,
            'preview': preview,
            'section': forum,
        }))



def updatesubs(request):
    """Allow users to update their subscriptions all in one shot.

    @return: a view to update user's subscriptions.
    @rtype: Django response
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (reverse('user_signin'), request.path))

    subs = Subscription.objects.select_related().filter(author=request.user)

    if request.POST:
        # remove the subscriptions that haven't been checked.
        post_keys = [k for k in request.POST.keys()]
        for s in subs:
            if not str(s.thread.id) in post_keys:
                s.delete()
        return HttpResponseRedirect(reverse('forum_subscriptions'))

    return render_to_response('forum/updatesubs.html',
        RequestContext(request, {
            'subs': subs,
            'next': request.GET.get('next'),
            'section': 'forum',
        }))
