from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from mixer.backend.django import mixer
import logging
from ledger_api_client.managed_models import SystemUser, SystemUserAddress, SystemGroup

logger = logging.getLogger('statdev')
User = get_user_model()


class Command(BaseCommand):
    help = 'Create Test users accounts and assign groups'

    def handle(self, *args, **options):
        processor = SystemGroup.objects.get(name='Processor')
        assessor = SystemGroup.objects.get(name='Assessor')
        approver = SystemGroup.objects.get(name='Approver')
        referee = SystemGroup.objects.get(name='Referee')
        emergency = SystemGroup.objects.get(name='Emergency')
        director = SystemGroup.objects.get(name='Director')
        executive = SystemGroup.objects.get(name='Executive')
        referee = SystemGroup.objects.get(name='Referee')

        if not User.objects.filter(email="admin@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="admin@dpaw.wa.gov.au", first_name="Admin", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()
            self.user1.groups.add(processor)

        if not User.objects.filter(email="asessor@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="asessor@dpaw.wa.gov.au", first_name="Assessor", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()
            self.user1.groups.add(assessor)

        if not User.objects.filter(email="manager@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="manager@dpaw.wa.gov.au", first_name="Manager", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()
            self.user1.groups.add(approver)

        if not User.objects.filter(email="director@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="director@dpaw.wa.gov.au", first_name="Director", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()
            self.user1.groups.add(director)

        if not User.objects.filter(email="exec@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="exec@dpaw.wa.gov.au", first_name="Exec", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()
            self.user1.groups.add(executive)

        if not User.objects.filter(email="emergency@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="emergency@dpaw.wa.gov.au", first_name="Emergency", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()
            self.user1.groups.add(emergency)

        if not User.objects.filter(email="referee1@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="referee1@dpaw.wa.gov.au", first_name="Referee", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()
            self.user1.groups.add(referee)

        if not User.objects.filter(email="referee2@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="referee2@dpaw.wa.gov.au", first_name="Referee", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()
            self.user1.groups.add(referee)

        if not User.objects.filter(email="referee3@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="referee3@dpaw.wa.gov.au", first_name="Referee", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()
            self.user1.groups.add(referee)

        if not User.objects.filter(email="referee4@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="referee4@dpaw.wa.gov.au", first_name="Referee", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()
            self.user1.groups.add(referee)

        if not User.objects.filter(email="referee5@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="referee5@dpaw.wa.gov.au", first_name="Referee", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()
            self.user1.groups.add(referee)

        if not User.objects.filter(email="referee6@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="referee6@dpaw.wa.gov.au", first_name="Referee", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()
            self.user1.groups.add(referee)

        if not User.objects.filter(email="customer1@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="customer1@dpaw.wa.gov.au", first_name="Customer", last_name="1", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()

        if not User.objects.filter(email="customer2@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="customer2@dpaw.wa.gov.au", first_name="Customer", last_name="2", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()

        if not User.objects.filter(email="customer3@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="customer3@dpaw.wa.gov.au", first_name="Customer", last_name="3", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()

        if not User.objects.filter(email="customer4@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="customer4@dpaw.wa.gov.au", first_name="Customer", last_name="4", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()

        if not User.objects.filter(email="customer5@dpaw.wa.gov.au").exists():
            self.user1 = mixer.blend(User, email="customer5@dpaw.wa.gov.au", first_name="Customer", last_name="5", is_superuser=False, is_staff=False)
            self.user1.set_password('pass')
            self.user1.save()

        print ("Test Account Creation Completed")

        return
