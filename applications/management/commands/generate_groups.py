from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
import logging
from ledger_api_client.managed_models import SystemUser, SystemUserAddress, SystemGroup

logger = logging.getLogger('statdev')


class Command(BaseCommand):
    help = 'Checks and (if required) creates required groups.'

    def handle(self, *args, **options):
        groups = ['Statdev Processor', 'Statdev Assessor', 'Statdev Approver', 'Statdev Referee', 'Statdev Executive', 'Statdev Director', 'Statdev Emergency']
        for group in groups:
            if not SystemGroup.objects.filter(name=group).exists():
                new_group = SystemGroup.objects.create(name=group)
                self.stdout.write('Group created: {}'.format(group))
                logger.info('Group created: {}'.format(group))

        return
