from django.db import models


from django.db import models

class Movie(models.Model):

    GENRE_CHOICES = [
    ('Action', 'Action'),
    ('Comedy', 'Comedy'),
    ('Romance', 'Romance'),
    ('Rom-Com', 'Rom-Com'),
    ('Love Story', 'Love Story'),
    ('Horror', 'Horror'),
    ('Sci-Fi', 'Sci-Fi'),
    ('Drama', 'Drama'),
    ('Thriller', 'Thriller'),
    ('Adventure', 'Adventure'),
]

    LANGUAGE_CHOICES = [
        ('English', 'English'),
        ('Tamil', 'Tamil'),
        ('Malayalam', 'Malayalam'),
        ('Hindi', 'Hindi'),
        ('Telugu', 'Telugu'),
    ]

    movie_name = models.CharField(max_length=100)

    movie_description = models.TextField()

    movie_image = models.ImageField(upload_to='movies/')

    rating = models.FloatField()

    cast = models.CharField(max_length=200)

    trailer_url = models.URLField(blank=True, null=True)

    genre = models.CharField(
        max_length=50,
        choices=GENRE_CHOICES,
        default='Action',
        db_index=True
    )

    language = models.CharField(
        max_length=50,
        choices=LANGUAGE_CHOICES,
        default='English',
        db_index=True
    )

    def __str__(self):
        return self.movie_name


class Theater(models.Model):

    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE
    )

    name = models.CharField(max_length=100)

    time = models.DateTimeField()

    def __str__(self):
        return f"{self.name} - {self.movie.movie_name}"


class Seat(models.Model):

    theater = models.ForeignKey(
        Theater,
        on_delete=models.CASCADE
    )

    seat_number = models.CharField(max_length=10)

    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return self.seat_number
    
from django.contrib.auth.models import User


class Booking(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)

    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)

    booked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Booking by {self.user.username}'