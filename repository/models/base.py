"""
Model classes for app Repository
"""

from datetime import datetime as dt
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext as _
import ml2h5.data
import ml2h5.fileformat
import ml2h5.task
import random
from tagging.models import Tag
from tagging.models import TaggedItem
from tagging.utils import calculate_cloud
from utils import slugify

import repository

class Slug(models.Model):
    """Slug - URL-compatible item name.

    @cvar text: URL-compatible item name
    @type text: string / models.CharField
    """
    text = models.CharField(max_length=32, unique=True)

    class Meta:
       app_label = 'repository'

    def __unicode__(self):
        return unicode(self.text)


class License(models.Model):
    """License to be used by Data items.

    @cvar name: name of the license
    @type name: string / models.CharField
    @cvar url: url of the license
    @type url: string / models.CharField
    """
    name = models.CharField(max_length=255, unique=True)
    url = models.CharField(max_length=255)

    class Meta:
       app_label = 'repository'

    def __unicode__(self):
        return unicode(self.name)


class FixedLicense(models.Model):
    """License to be used by Task or Method items.

    For some reason, it didn't work when just inheriting, so
    the code needs to be duplicated.

    @cvar name: name of the license
    @type name: string / models.CharField
    @cvar url: url of the license
    @type url: string / models.CharField
    """
    name = models.CharField(max_length=255, unique=True)
    url = models.CharField(max_length=255)

    class Meta:
       app_label = 'repository'

    def __unicode__(self):
        return unicode(self.name)


class Publication(models.Model):
    title = models.CharField(max_length=80)
#    slug = models.SlugField(unique=True)
    content = models.TextField()
#    firstauthor = models.CharField(max_length=256)
#    bibtype = models.CharField(max_length=256)
#    authors = models.CharField(max_length=2048)
#    year = models.IntegerField()
#    bibitem = models.TextField()
#    category = models.ForeignKey(Category)
#    abstract = models.TextField()
#    month = models.CharField(max_length=20, blank=True, null=True)
#    journal = models.CharField(max_length=256, blank=True, null=True)
#    number = models.CharField(max_length=256, blank=True, null=True)
#    institution = models.CharField(max_length=256, blank=True, null=True)
#    subcategory = models.ForeignKey('self', blank=True, null=True)
#    editor = models.CharField(max_length=2048, blank=True, null=True)
#    publisher = models.CharField(max_length=256, blank=True, null=True)
#    booktitle = models.CharField(max_length=256, blank=True, null=True)
#    pages = models.CharField(max_length=256, blank=True, null=True)
#    pdf = models.CharField(max_length=256, blank=True, null=True)
#    ps = models.CharField(max_length=256, blank=True, null=True)
#    url = models.CharField(max_length=256, blank=True, null=True)
#    note = models.CharField(max_length=256, blank=True, null=True)
#    pubtype = models.CharField(max_length=256, blank=True, null=True)
#    school = models.CharField(max_length=256, blank=True, null=True)
#    dataset = models.CharField(max_length=256, blank=True, null=True)
#    address = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        ordering = ('title', )
        app_label = 'repository'

    def __unicode__(self):
        return self.title



class Repository(models.Model):
    """Base class for Repository items: Data, Task, Method

    @cvar pub_date: publication date (item creation date)
    @type pub_date: models.DateTimeField
    @cvar version: version number to flip between different incarnations of the item
    @type version: integer / models.IntegerField
    @cvar name: item's name
    @type name: string / models.CharField
    @cvar slug: item's slug
    @type slug: string / Slug
    @cvar summary: item's summary
    @type summary: string / models.CharField
    @cvar description: item's description
    @type description: string / models.TextField
    @cvar urls: URLs linking to more information about item
    @type urls: string / models.CharField
    @cvar publications: publications where item is mentioned or used
    @type publications: models.ManyToManyField
    @cvar is_public: if item is public
    @type is_public: boolean / models.BooleanField
    @cvar is_deleted: if item is deleted
    @type is_deleted: boolean / models.BooleanField
    @cvar is_current: if item is the current one
    @type is_current: boolean / models.BooleanField
    @cvar user: user who created the item
    @type user: Django User
    @cvar rating_avg: item's average overal rating
    @type rating_avg: float / models.FloatField
    @cvar rating_avg_interest: item's average interesting rating
    @type rating_avg_interest: float / models.FloatField
    @cvar rating_avg_doc: item's average documentation rating
    @type rating_avg_doc: float / models.FloatField
    @cvar rating_votes: item's total number of rating votes
    @type rating_votes: integer / models.IntegerField
    """
    pub_date = models.DateTimeField()
    version = models.IntegerField(default=1)
    name = models.CharField(max_length=32)
    slug = models.ForeignKey(Slug)
    summary = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    urls = models.CharField(max_length=255, blank=True)
    publications = models.ManyToManyField(Publication, blank=True)
    is_public = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False, editable=True)
    is_current = models.BooleanField(default=False, editable=True)
    #user = models.ForeignKey(User, related_name='%(app_label)s_%(class)s_related')
    user = models.ForeignKey(User, related_name='repository_user')
    rating_avg = models.FloatField(editable=False, default=-1)
    rating_avg_interest = models.FloatField(editable=False, default=-1)
    rating_avg_doc = models.FloatField(editable=False, default=-1)
    rating_votes = models.IntegerField(editable=False, default=0)
    downloads = models.IntegerField(editable=False, default=0)
    hits = models.IntegerField(editable=False, default=0)

    class Meta:
        """Inner meta class to specify options.

        @cvar ordering: default ordering of items in queries
        @type ordering: list
        @cvar get_latest_by: latestness will be determined by this field
        @type get_latest_by: string
        """
        ordering = ('-pub_date', )
        get_latest_by = 'pub_date'
        app_label = 'repository'
        #abstract = True

    def check_is_approved(self):
        """Checks whether this object is approved.
        
        True by default. Overwritten in Data because
        of the extra review step."""
        return True

    def update_current_hits(self):
        """Update the hits count on the given object.
        """
        current = Repository.objects.get(slug=self.slug, is_current=True)
        current.hits += 1
        current.save(silent_update=True)
        return current

    def has_h5(self):
        """Checks whether has h5 and updates the object if this is the case.

        No-Op by default, overwritten for Data. If overwritten, sets the has_h5
        attribute, or the conversion-failed attribute.
        """
        return False

    def get_extract(self):
        """Get an h5 based extract for this data set.

        No-op by default, overwritten in Task and Data.
        """
        return None

    def get_public_qs(self, user=None, queryset=None):
        """Returns the public most current object or private one owned
        by the user
        """
        if user and user.id:
            qs = (Q(user=user) | Q(is_public=True)) & Q(is_current=True)
        else:
            qs = Q(is_public=True) & Q(is_current=True)

        if queryset:
            qs = qs & queryset

        qs = qs & Q(is_deleted=False)

        return qs

    def get_tags(self):
        return self.tags.split()

    def has_tags(self):
        return self.tags

    @classmethod
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
            qs_result = (Q(method__user=user) | Q(method__is_public=True)) & Q(method__is_current=True)
        else:
            qs = Q(is_public=True) & Q(is_current=True);
            qs_result = Q(method__is_public=True) & Q(method__is_current=True);

        # slices return max number of elements if num > max
        recent_data = repository.models.Data.objects.filter(qs).order_by('-pub_date')
        recent_data = recent_data.filter(is_approved=True)
        recent_tasks = repository.models.Task.objects.filter(qs).order_by('-pub_date')
        recent_challenges = repository.models.Challenge.objects.filter(qs).order_by('-pub_date')
        recent_results = repository.models.Result.objects.filter(qs_result).order_by('-pub_date')

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
            l=list(zip(len(results)*['Method'],results))
            recent.extend(l)

        recent.sort(key=lambda r: r[1].pub_date, reverse=True)
        return recent[:num]

    @classmethod
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
                                                  repository.models.Data.objects.filter(qs & Q(is_approved=True)), counts=True)
            tags.extend(Tag.objects.usage_for_queryset(
                        repository.models.Task.objects.filter(qs), counts=True))
            tags.extend(Tag.objects.usage_for_queryset(
                        repository.models.Method.objects.filter(qs), counts=True))

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

    @classmethod
    def get_current_tagged_items(cls, user, tag):
        """Get current items with specific tag.

        @param user: user to get current items for
        @type user: auth.models.user
        @param tag: tag to get tagged items for
        @type tag: tagging.Tag
        @return: current tagged items
        @rtype: list of Data, Task or Method
        """
        # without if-construct sqlite3 barfs on AnonymousUser
        qs = cls().get_public_qs()

        tagged = TaggedItem.objects.filter(tag=tag)
        current = cls.objects.filter(qs).order_by('name')
        items = []
        for c in current:
            for t in tagged:
                if t.object_id == c.id:
                    items.append(c)
                    break
        return items

    @classmethod
    def get_object(cls, slug_or_id, version=None):
        """Retrieves an item by slug or id

            @param slug_or_id: item's slug or id for lookup
            @type slug_or_id: string or integer
            @param version: specific version of the item to retrieve
            @type version: integer
            @return: found object or None
            @rtype: Repository
            """
        if not slug_or_id:
            return None

        if version:
            obj = cls.objects.filter(slug__text=slug_or_id, is_deleted=False, version=version)
        else:
            obj = cls.objects.filter(slug__text=slug_or_id, is_deleted=False, is_current=True)

        if obj: # by slug
            obj = obj[0]
        else: # by id
            try:
                id=int(slug_or_id)
            except ValueError:
                return None
            try:
                obj = cls.objects.get(pk=slug_or_id)
            except cls.DoesNotExist:
                return None
            if not obj or obj.is_deleted:
                return None

        return obj

    @classmethod
    def set_current(klass, cur):
        """Set the latest version of the item identified by given obj to be the current one.

            @param cur: item to set
            @type object: repository object
            @return: the current item or None
            @rtype: repository.Data/Task/Method
            """

        # handle deleted case first
        if cur.is_deleted:
            # we did not delete the current version of the object but an older one
            # so just return current version of the object which must exist
            if not cur.is_current:
                obj=klass.objects.get(slug=cur.slug, is_current=True)
                return obj

            # else we are deleting the most current version
            cur.is_current=False
            cur.save(silent_update=True)

            new_cur = klass.objects.filter(slug=cur.slug,
                    is_deleted=False).order_by('-version')
            if new_cur.count():
                prev = cur
                cur=new_cur[0]
                cur.is_current=True
                cur.save(silent_update=True)
            else:
                return None
        else:
            prev = klass.objects.get(slug=cur.slug, is_current=True)

        rklass = eval('repository.models.' + klass.__name__ + 'Rating')
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

        # this should be atomic:
        prev.is_current = False
        prev.save(silent_update=True)
        cur.is_current = True
        cur.save(silent_update=True)

        return cur

    def get_initial_submission(self):
        return Repository.objects.get(slug__text=self.slug.text, version=1)

    def __init__(self, * args, ** kwargs):
        super(Repository, self).__init__(*args, ** kwargs)

    def __unicode__(self):
        return unicode(self.name)

    def save(self, **kwargs):
        """Save item.

        Creates a slug if necessary.
        """
        if not self.slug_id:
            self.slug = self.make_slug()

        if not kwargs.has_key('silent_update') or not kwargs.pop('silent_update'):
            self.pub_date = dt.now()

        super(Repository, self).save()


    def delete(self):
        """Delete item.

        Delete the corresponding slug.
        """
        try:
            Slug.objects.get(pk=self.slug.id).delete()
        except Slug.DoesNotExist:
            pass


    def make_slug(self):
        """Make a slug generated for the item's name.

        @return: a slug
        @rtype: Slug
        @raise AttributeError: if item's name is not set
        """
        if not self.name:
            raise AttributeError, 'Attribute name is not set!'
        slug = Slug(text=slugify(self.name))
        slug.save()
        return slug


    def get_next_version(self):
        """Get next available version for this item.

        @return: next available version
        @rtype: integer
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'
        objects = self.__class__.objects.filter(
                                                slug=self.slug_id, is_deleted=False
                                                ).order_by('-version')
        return objects[0].version + 1


    def get_absolute_url(self):
        """Get absolute URL for this item, using its id.

        @return: an absolute URL
        @rtype: string
        """
        view = 'repository.views.' + self.__class__.__name__.lower() + '_view'
        return reverse(view, args=[self.id])


    def is_owner(self, user):
        """Is given user owner of this

        @param user: user to check for
        @type user: Django User
        @return: if user owns this
        @rtype: boolean
        """
        if user.is_staff or user.is_superuser or user == self.user:
            return True
        return False

    def can_activate(self, user):
        """Can given user activate this.

        @param user: user to check for
        @type user: Django User
        @return: if user can activate this
        @rtype: boolean
        """
        if not self.is_owner(user):
            return False
        if self.dependent_entries_exist():
            return False
        if not self.is_public:
            return True
        if not self.is_current:
            return True

        return False

    def can_edit(self, user):
        """Can given user edit this item.

        @param user: user to check for
        @type user: Django User
        @return: if user can activate this
        @rtype: boolean
        """
        if self.dependent_entries_exist():
            return False
        return self.can_view(user)

    def can_fork(self, user):
        """Can given user fork this item.

        @param user: user to check for
        @type user: Django User
        @return: if user can activate this
        @rtype: boolean
        """
        return self.can_view(user)

    def can_delete(self, user):
        """Can given user delete this item.

        @param user: user to check for
        @type user: Django User
        @return: if user can activate this
        @rtype: boolean
        """
        ret = self.is_owner(user)
        if not ret:
            return False
        # don't delete if this is last item and something depends on it
        #if self.__class__.objects.filter(slug=self.slug).count() == 1:
        if self.dependent_entries_exist():
            return False
        return True


    def can_view(self, user):
        """Can given user view this.

        @param user: user to check for
        @type user: Django User
        @return: if user can view this
        @rtype: boolean
        """
        if self.is_public or self.is_owner(user):
            return True
        return False


    def can_download(self, user):
        """Can given user download this.

        @param user: user to check for
        @type user: Django User
        @return: if user can download this
        @rtype: boolean
        """
        return self.can_view(user)


    def increase_downloads(self):
        """Increase hit counter for current version of given item."""
        obj = self.__class__.objects.get(slug=self.slug, is_current=True)
        obj.downloads += 1
        obj.save(silent_update=True)


    def get_completeness(self):
        """Determine item's completeness.

        @return: completeness of item as a percentage
        @rtype: integer
        """
        attrs = self.get_completeness_properties()

        attrs_len = len(attrs)
        attrs_complete = 0
        for attr in attrs:
            if eval('self.' + attr):
                attrs_complete += 1
        return int((attrs_complete * 100) / attrs_len)

    completeness = property(get_completeness)

    def get_completeness_properties(self):
        return []

    def get_versions(self, user):
        """Retrieve all versions of this item viewable by user

        @param user: user to get versions for
        @type user: auth.model.User
        @return: viewable versions of this item
        @rtype: list of Repository
        """
        qs = Q(slug__text=self.slug.text) & Q(is_deleted=False)
        items = self.__class__.objects.filter(qs).order_by('version')
        return [i for i in items if i.can_view(user)]

    def create_slug(self):
        """Create the slug entry for this object.

        Throws IntegrityError in case the slug already exists.
        """
        self.slug = self.make_slug();

    def attach_file(self, file_object):
        """
        Attach the given file to the object.

        file_object is suitable for the kind of object you get from
        request.FILES, i.e. it implements the methods read(), size(), name().
        """
        raise NotImplementedError("attach_file not implemented for Repository objects.")

class Rating(models.Model):
    """Rating for a Repository item

    Each user can rate a Repository item only once, but she might change
    her rating later on.
    It acts as a base class for more specific Rating classes.

    @cvar user: rating user
    @type user: Django User
    @cvar interest: how interesting the item is
    @type interest: integer / models.IntegerField
    @cvar doc: how well the item is documented
    @type doc: integer / models.IntegerField
    """
    user = models.ForeignKey(User, related_name='rating_user')
    interest = models.IntegerField(default=0)
    doc = models.IntegerField(default=0)

    class Meta:
        app_label = 'repository'

    def update(self, interest, doc):
        """Update rating for an item.

        @param interest: interesting value
        @type interest: integer
        @param doc: documentation value
        @type doc: integer
        """
        self.interest = interest
        self.doc = doc
        self.save()

        repo = self.repository
        ratings = self.__class__.objects.filter(repository=repo)
        l = float(len(ratings))
        i = d = 0
        for r in ratings:
            i += r.interest
            d += r.doc

        num_scores = 2.0
        repo.rating_avg = float(i + d) / (num_scores * l)
        repo.rating_avg_interest = float(i) / l
        repo.rating_avg_doc = float(d) / l
        repo.rating_votes = l
        repo.save()

    def __unicode__(self):
        try:
            return unicode("%s %s %s" % (self.user.username, _('on'), self.repository.name))
        except AttributeError:
            return unicode("%s %s %s" % (self.user.username, _('on'), self.id))







