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
from gettext import gettext as _

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
    """License to be used by Task or Solution items.

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
    """Base class for Repository items: Data, Task, Solution

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

    #
    # New stuff by Mikio here
    #

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

    def get_related_data(self):
        """Returns the data set related to this data set.

        No-op by default. Overwritten in Task and Data.
        """
        return None

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

    #
    # Old stuff by Sebastian below
    #

    @classmethod
    def get_current_tagged_items(cls, user, tag):
        """Get current items with specific tag.

        @param user: user to get current items for
        @type user: auth.models.user
        @param tag: tag to get tagged items for
        @type tag: tagging.Tag
        @return: current tagged items
        @rtype: list of Data, Task or Solution
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
    def set_current(cls, obj):
        repository.util.set_current(cls, obj)


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

        silent_update =  kwargs.has_key('silent_update')
        if silent_update:
            kwargs.pop('silent_update')
        else:
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
        if not self.is_public:
            return True
        if not self.is_current:
            return True

        return False


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
        siblings = self.__class__.objects.filter(slug=self.slug)
        if len(siblings) == 1:
            if repository.util.dependent_entries_exist(self):
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


    def can_edit(self, user):
        """Can given user edit this.

        @param user: user to check for
        @type user: Django User
        @return: if user can edit this
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

    def filter_related(self, user):
        """Filter Task/Solution related to a superior Data/Task to contain only
        current and permitted Task/Solution.

        This might be part of a manager class, because it works on table-level
        for the related items. But then it works on row-level for the item
        which is looked at...

        @param user: User to filter for
        @type user: models.User
        @return: filtered items
        @rtype: list of repository.Task or repository.Solution
        """
        qs = self.qs_for_related()

        if not qs:
            return None

        current = qs.filter(is_current=True)
        ret = []
        for c in current:
            if c.can_view(user):
                ret.append(c)

        return ret

    def qs_for_related(self):
        return None

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







