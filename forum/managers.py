"""
Manager for app Forum
"""

from django.db import models
from django.db.models import Q

class ForumManager(models.Manager):
    """Class for managing forums."""

    def for_groups(self, groups):
        """Get forums for given groups.

        @param groups: groups to get forums for
        @type groups: list of Group
        @return: forums for given group or forums without group
        @rtype: Django queryset
        """
        if groups:
            public = Q(groups__isnull=True)
            user_groups = Q(groups__in=groups)
            return self.filter(public|user_groups).distinct()
        return self.filter(groups__isnull=True)

    def has_access(self, forum, groups):
        """Determine if given groups have access to given forum.

        @param forum: forum to look at
        @type forum: Forum
        @param groups: groups to check for
        @type groups: list of Group
        """
        return forum in self.for_groups(groups)
