from __future__ import unicode_literals
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from six import python_2_unicode_compatible
from model_utils import Choices


@python_2_unicode_compatible
class Action(models.Model):
    """This model represents an action performed to or with another object.
    It uses a generic foreign key to allow any other object to be linked to
    an action.
    """
    ACTION_CATEGORY_CHOICES = Choices(
        (1, 'communicate', ('Communicate')),
        (2, 'assign', ('Assign')),
        (3, 'refer', ('Refer')),
        (4, 'issue', ('Issue')),
        (5, 'decline', ('Decline')),
        (6, 'publish', ('Publish')),
        (7, 'lodge', ('Lodge')),
        (8, 'action', ('Next Step')),
        (9, 'change', ('Change')),
        (10, 'create',('Create')),
        (11, 'cancel',('Cancelled'))
        # TODO: Compliance request
        # TODO: Request/add/remove delegate
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    action = models.CharField(max_length=512)
    timestamp = models.DateTimeField(auto_now_add=True, editable=False)
    user = models.IntegerField(blank=True, null=True)
    category = models.IntegerField(choices=ACTION_CATEGORY_CHOICES, null=True, blank=True)

    def __str__(self):
        return '{}: {}'.format(self.content_object, self.action)
