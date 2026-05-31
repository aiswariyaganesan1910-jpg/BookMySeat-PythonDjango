from django.core.management.base import BaseCommand

from django.utils import timezone

from datetime import timedelta

from movies.models import Seat


class Command(BaseCommand):

    help = 'Release expired reserved seats'


    def handle(self, *args, **kwargs):

        expired_time = timezone.now() - timedelta(minutes=2)

        expired_seats = Seat.objects.filter(

            is_reserved=True,

            is_booked=False,

            reserved_at__lt=expired_time

        )

        released_count = expired_seats.update(

            is_reserved=False,

            reserved_at=None

        )

        self.stdout.write(

            self.style.SUCCESS(

                f'{released_count} expired seats released.'

            )

        )