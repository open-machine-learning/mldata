import os.path

from django.db.models import Q

from repository.models import Data
from repository.models import Task
from repository.models import Solution

from tagging.models import Tag
from tagging.utils import calculate_cloud
import random

def get_recent(cls, user):
    """Get recently changed items.

        @param user: user to get recent items for
        @type user: auth.models.user
        @return: list of recently changed items
        @rtype: list of Repository
        """
    num = 3

    # without if-construct sqlite3 barfs on AnonymousUser
    if user.id:
        qs = (Q(user=user) | Q(is_public=True)) & Q(is_current=True)
    else:
        qs = Q(is_public=True) & Q(is_current=True);

    # slices return max number of elements if num > max
    recent_data = Data.objects.filter(qs).order_by('-pub_date')
    recent_tasks = Task.objects.filter(qs).order_by('-pub_date')
    recent = []
    if len(recent_data) > 0:
        recent.extend(recent_data[0:num])
    if len(recent_tasks) > 0:
        recent.extend(recent_tasks[0:num])
    return sorted(recent, key=lambda r: r.pub_date, reverse=True)

def get_tag_cloud(cls, user):
    """Get current tags available to user.

        @param user: user to get current items for
        @type user: auth.models.user
        @return: current tags available to user
        @rtype: list of tagging.Tag
        """
    # without if-construct sqlite3 barfs on AnonymousUser
    if user.id:
        qs = (Q(user=user) | Q(is_public=True)) & Q(is_current=True)
    else:
        qs = Q(is_public=True) & Q(is_current=True)

    if cls:
        qs = cls.get_query(qs)
        tags = Tag.objects.usage_for_queryset(cls.objects.filter(qs), counts=True)
    else:
        tags = Tag.objects.usage_for_queryset(
                                              Data.objects.filter(qs & Q(is_approved=True)), counts=True)
        tags.extend(Tag.objects.usage_for_queryset(
                    Task.objects.filter(qs), counts=True))
        tags.extend(Tag.objects.usage_for_queryset(
                    Solution.objects.filter(qs), counts=True))

    current = {}
    for t in tags:
        if not t.name in current:
            current[t.name] = t
        else:
            current[t.name].count += t.count

    tags = current.values()
    if tags:
        cloud = calculate_cloud(tags, steps=2)
        random.shuffle(cloud)
    else:
        cloud = None
    return cloud

def set_current(klass, slug):
    """Set the latest version of the item identified by given slug to be the current one.

        @param slug: slug of item to set
        @type slug: repository.Slug
        @return: the current item or None
        @rtype: repository.Data/Task/Solution
        """
    cur = klass.objects.filter(slug=slug).\
        filter(is_deleted=False).order_by('-version')
    if not cur:
        return None
    else:
        cur = cur[0]

    prev = klass.objects.get(slug=slug, is_current=True)
    if not prev: return

    rklass = eval(klass.__name__ + 'Rating')
    try:
        rating = rklass.objects.get(user=cur.user, repository=prev)
        rating.repository = cur
        rating.save()
    except rklass.DoesNotExist:
        pass
    cur.rating_avg = prev.rating_avg
    cur.rating_avg_interest = prev.rating_avg_interest
    cur.rating_avg_doc = prev.rating_avg_doc
    cur.rating_votes = prev.rating_votes
    cur.hits = prev.hits
    cur.downloads = prev.downloads

    Comment.objects.filter(object_pk=prev.pk).update(object_pk=cur.pk)

    prev.is_current = False
    cur.is_current = True

    # this should be atomic:
    prev.save()
    cur.save()

    return cur


def search(klass, objects, searchterm):
    """Search for searchterm in objects queryset.

        @param objects: queryset to search in
        @type objects: Queryset
        @param searchterm: term to search for
        @type searchterm: string
        @return: found objects and if search failed
        @rtype: tuple of querset and boolean
        """
    # only match name and summary for now
    #Q(version__icontains=q) | Q(description__icontains=q)
    found = objects.filter(Q(name__icontains=searchterm) | Q(summary__icontains=searchterm))

    if klass == Repository: # only approved Data items are allowed
        for f in found:
            if hasattr(f, 'data') and not f.data.is_approved:
                found = found.exclude(id=f.id)

    if found.count() < 1:
        return objects, True
    else:
        return found, False

def dependent_entries_exist(obj):
    """Check whether there exists an object which depends on obj.

    For Data objects, checks whether there exists a Task object,
    for Task objects, checks whether there exists a Data object.
    """
    if obj.__class__ == Data:
        dependencies = Task.objects.filter(data=obj)
        if len(dependencies) > 0:
            return True
    elif obj.__class__ == Task:
        dependencies = Solution.objects.filter(task=obj)
        if len(dependencies) > 0:
            return True
