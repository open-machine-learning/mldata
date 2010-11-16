import os.path

from django.db.models import Q
from django.contrib.comments.models import Comment

from repository.models import Repository
from repository.models import Data, DataRating
from repository.models import Task, TaskRating
from repository.models import Solution, SolutionRating
from repository.models import Challenge, ChallengeRating, Result

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
    num = 5

    # without if-construct sqlite3 barfs on AnonymousUser
    if user.id:
        qs = (Q(user=user) | Q(is_public=True)) & Q(is_current=True)
        qs_result = (Q(solution__user=user) | Q(solution__is_public=True)) & Q(solution__is_current=True)
    else:
        qs = Q(is_public=True) & Q(is_current=True);
        qs_result = Q(solution__is_public=True) & Q(solution__is_current=True);

    # slices return max number of elements if num > max
    recent_data = Data.objects.filter(qs).order_by('-pub_date')
    recent_tasks = Task.objects.filter(qs).order_by('-pub_date')
    recent_challenges = Challenge.objects.filter(qs).order_by('-pub_date')
    recent_results = Result.objects.filter(qs_result).order_by('-pub_date')

    recent = []
    if recent_data.count() > 0:
        data=recent_data[:num]
        l=list(zip(len(data)*['Data'],data))
        recent.extend(l)
    if recent_tasks.count() > 0:
        tasks=recent_tasks[:num]
        l=list(zip(len(tasks)*['Task'],tasks))
        recent.extend(l)
    if recent_challenges.count() > 0:
        challenges=recent_challenges[:num]
        l=list(zip(len(challenges)*['Challenge'],challenges))
        recent.extend(l)
    if recent_results.count() > 0:
        results=recent_results[:num]
        l=list(zip(len(results)*['Solution'],results))
        recent.extend(l)

    recent.sort(key=lambda r: r[1].pub_date, reverse=True)
    return recent[:num]

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
        random.seed(hash(cls)+len(tags))
        random.shuffle(cloud)
    else:
        cloud = None
    return cloud

def set_current(klass, cur):
    """Set the latest version of the item identified by given obj to be the current one.

        @param cur: item to set
        @type object: repository object
        @return: the current item or None
        @rtype: repository.Data/Task/Solution
        """
    if cur.is_deleted:
        return None

    prev = klass.objects.get(slug=cur.slug, is_current=True)
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
    prev.save(silent_update=True)
    cur.save()

    return cur


def dependent_entries_exist(obj):
    """Check whether there exists an object which depends on obj.

    For Data objects, checks whether there exists a Task object,
    for Task objects, checks whether there exists a Data object.
    """
    if obj.__class__ == Data:
        if Task.objects.filter(data=obj).count() > 0:
            return True
    elif obj.__class__ == Task:
        if Challenge.objects.filter(task=obj).count() > 0:
            return True

        if Result.objects.filter(task=obj).count() > 0:
            return True
    elif obj.__class__ == Solution:
        if Result.objects.filter(solution=obj).count() > 0:
            return True
