from django.contrib import admin

from .models import Movie, Theater, Seat, Booking


admin.site.register(Movie)

admin.site.register(Theater)

admin.site.register(Seat)

admin.site.register(Booking)