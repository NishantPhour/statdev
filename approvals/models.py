from __future__ import unicode_literals
from six import python_2_unicode_compatible
from applications.models import Application, Record
from django.conf import settings
from django.db import models
from model_utils import Choices
from applications.models import Application, Organisation

@python_2_unicode_compatible
class Approval(models.Model):
     """This model represents an approvals by a customer to P&W for a single
     permit, licence/permit, part 5, etc.
     """

     APPROVAL_STATE_CHOICES = Choices(
        (1, 'current', ('Current')),
        (2, 'expired', ('Expired')),
        (3, 'cancelled', ('Cancelled')),
        (4, 'surrendered', ('Surrendered')),
        (5, 'suspended', ('Suspended')),
        (6, 'reinstate', ('Reinstate')),
        (7, 'pending', ('Pending')),
        (8, 'not-supported', ('Not Supported'))
     )

     app_type = models.IntegerField(choices=Application.APP_TYPE_CHOICES)
     title = models.CharField(max_length=254)
     applicant = models.IntegerField(blank=True, null=True)
     organisation = models.ForeignKey(Organisation, blank=True, null=True, on_delete=models.PROTECT)
     application = models.ForeignKey(Application, on_delete=models.CASCADE,null=True, blank=True, related_name='application') 
     issue_date = models.DateField(null=True, blank=True, auto_now_add=True)
     start_date = models.DateField(null=True, blank=True)
     expiry_date = models.DateField(null=True, blank=True)
     status = models.IntegerField(choices=APPROVAL_STATE_CHOICES) 
     approval_document = models.ForeignKey(Record, null=True, blank=True, related_name='approval_document', on_delete=models.CASCADE)
     suspend_from_date = models.DateField(null=True, blank=True)
     suspend_to_date = models.DateField(null=True, blank=True)
     ammendment_application  = models.ForeignKey(Application, on_delete=models.CASCADE,null=True, blank=True, related_name='ammendment_application')
     reinstate_date = models.DateField(null=True, blank=True)
     cancellation_date = models.DateField(null=True, blank=True)
     surrender_date = models.DateField(null=True, blank=True)
     details = models.TextField(null=True, blank=True)

     @property
     def approval_url(self):
        print ("APPROVAL URL")
        if self.app_type == 3 or self.app_type == 6:
               if self.approval_document:
                   return ("/private-media/view/"+str(self.approval_document.id)+"-file"+str(self.approval_document.extension)) 
               return None 
        else:
           return str("/approvals/viewpdf-"+str(self.id)+".pdf")

     def __str__(self):
        return 'Approvals {}: {} - {} ({})'.format(
            self.pk, self.get_app_type_display(), self.title, self.get_status_display())

        return self.name


class CommunicationApproval(models.Model):
    """This model represents the communication model
    """
    COMM_TYPE = Choices(
        (0, 'none', ('None')),
        (1, 'phone', ('Phone')),
        (2, 'email', ('Email')),
        (3, 'mail', ('Mail')),
        (4, 'system', ('System'))
    )

    approval = models.ForeignKey(Approval, on_delete=models.PROTECT)
    comms_to = models.CharField(max_length=256, null=True, blank=True)
    comms_from = models.CharField(max_length=256, null=True, blank=True)
    subject = models.CharField(max_length=256, null=True, blank=True)
    comms_type = models.IntegerField(choices=COMM_TYPE, default=COMM_TYPE.none )
    details = models.TextField(blank=True, null=True)
    records = models.ManyToManyField(Record, blank=True, related_name='communication_approvals_docs')
    state = models.IntegerField(blank=True, null=True)  # move to foreign key once APP_STATE_CHOICES becomes a model
    created = models.DateTimeField(auto_now_add=True)

 

