from django.contrib import admin

from .models import (
    Movie,
    Theater,
    Seat,
    Booking,
    ProcessedWebhook
)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):

    list_display = (

        'user',
        'movie',
        'theater',
        'seat',
        'payment_status',
        'payment_id',
        'booked_at'

    )

    search_fields = (

        'user__username',
        'movie__movie_name',
        'payment_id'

    )

    list_filter = (

        'payment_status',
        'movie',
        'theater'

    )


admin.site.register(Movie)
admin.site.register(Theater)
admin.site.register(Seat)
admin.site.register(ProcessedWebhook)