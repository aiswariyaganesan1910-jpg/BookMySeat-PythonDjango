import razorpay
from django.conf import settings
from django.utils import timezone

from datetime import timedelta
from django.db import transaction
from django.core.mail import EmailMultiAlternatives

from django.template.loader import render_to_string

import threading

import logging

import random
from urllib.parse import urlparse, parse_qs
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from .models import Movie, Theater, Seat, Booking
client = razorpay.Client(

    auth=(

        settings.RAZORPAY_KEY_ID,

        settings.RAZORPAY_KEY_SECRET

    )

)

logger = logging.getLogger(__name__)

def get_youtube_embed_url(url):

    try:

        parsed_url = urlparse(url)

        if 'youtube.com' in parsed_url.netloc:

            video_id = parse_qs(
                parsed_url.query
            ).get('v')

            if video_id:

                return f"https://www.youtube.com/embed/{video_id[0]}"

        elif 'youtu.be' in parsed_url.netloc:

            video_id = parsed_url.path.strip('/')

            return f"https://www.youtube.com/embed/{video_id}"

    except:

        return None

def send_booking_email(user, movie, theater, seats):

    try:

        payment_id = f"PAY{random.randint(100000,999999)}"

        html_content = render_to_string(

            'emails/booking_confirmation.html',

            {

                'movie': movie,

                'theater': theater,

                'seats': seats,

                'payment_id': payment_id

            }

        )

        email = EmailMultiAlternatives(

            subject='Booking Confirmation - BookMySeat',

            body='Your booking has been confirmed.',

            from_email=None,

            to=[user.email]

        )

        email.attach_alternative(

            html_content,

            "text/html"

        )

        email.send()

    except Exception as e:

        logger.error(

            f"Email sending failed: {e}"
        )

def movie_list(request):

    movies = Movie.objects.all()

    query = request.GET.get('q')

    genres = request.GET.getlist('genre')

    languages = request.GET.getlist('language')

    sort = request.GET.get('sort')

    if query:

        movies = movies.filter(
            movie_name__icontains=query
        )

    if genres:

        movies = movies.filter(
            genre__in=genres
        )

    if languages:

        movies = movies.filter(
            language__in=languages
        )

    if sort == 'rating':

        movies = movies.order_by('-rating')

    elif sort == 'a-z':

        movies = movies.order_by('movie_name')

    elif sort == 'z-a':

        movies = movies.order_by('-movie_name')

    from django.core.paginator import Paginator

    paginator = Paginator(movies, 6)

    page_number = request.GET.get('page')

    movies = paginator.get_page(page_number)
    genre_counts = Movie.objects.values('genre').annotate(
    total=Count('genre')
    )

    language_counts = Movie.objects.values('language').annotate(
    total=Count('language')
    )

    return render(

        request,

        'movies/movie_list.html',

        {

            'movies': movies,

            'genres': Movie.GENRE_CHOICES,

            'languages': Movie.LANGUAGE_CHOICES,
            
            'genre_counts': genre_counts,

            'language_counts': language_counts,

        }

    )


def theater_list(request, movie_id):

    movie = get_object_or_404(
        Movie,
        id=movie_id
    )
    embed_url = None

    if movie.trailer_url:

       embed_url = get_youtube_embed_url(
        movie.trailer_url
    )

    theaters = Theater.objects.filter(
        movie=movie
    )

    return render(

        request,
        'movies/theater_list.html',

        {
            'movie': movie,
            'theaters': theaters,
            'embed_url': embed_url
        }


    )
def payment_page(request, theater_id):

    theater = Theater.objects.get(id=theater_id)

    selected_seats = request.GET.getlist('seats')

    seat_objects = Seat.objects.filter(
        id__in=selected_seats
    )

    total_amount = len(selected_seats) * 200

    payment = client.order.create({

    "amount": total_amount * 100,

    "currency": "INR",

    "payment_capture": "1"

})

    if request.method == "POST":

        payment_status = request.POST.get(
            'payment_status'
        )

        payment_id = f"PAY{random.randint(100000,999999)}"

        if payment_status == "Failed":

            return render(

                request,

                'movies/payment_failed.html'

            )

        for seat_id in selected_seats:

            seat = Seat.objects.get(id=seat_id)

            Booking.objects.create(

                user=request.user,

                movie=theater.movie,

                theater=theater,

                seat=seat,

                payment_id=payment_id,

                payment_status=payment_status

            )

            seat.is_booked = True

            seat.save()

        return redirect(

            f"/movies/payment-success/?payment_id={payment_id}"

        )

    return render(

        request,

        'movies/payment.html',

        {

            'theater': theater,

            'selected_seats': seat_objects,

            'total_amount': total_amount,
            
            'payment': payment,

            'razorpay_key': settings.RAZORPAY_KEY_ID

        }

    )
def payment_success(request):

    payment_id = request.GET.get('payment_id')

    return render(

        request,

        'movies/payment_success.html',

        {

            'payment_id': payment_id

        }

    )


def book_seats(request, theater_id):

    theater = Theater.objects.get(id=theater_id)

    expired_time = timezone.now() - timedelta(minutes=2)

    expired_seats = Seat.objects.filter(

        is_reserved=True,

        is_booked=False,

        reserved_at__lt=expired_time

    )

    expired_seats.update(

        is_reserved=False,

        reserved_at=None

    )

    seats = Seat.objects.filter(theater=theater)

    if request.method == "POST":

        selected_seats = request.POST.getlist('seats')

        seat_numbers = []

        try:

            with transaction.atomic():

                for seat_id in selected_seats:

                    seat = Seat.objects.select_for_update().get(
                        id=seat_id
                    )

                    if seat.is_booked:

                        return render(

                            request,

                            'movies/seat_selection.html',

                            {

                                'theater': theater,

                                'seats': seats,

                                'error': f"Seat {seat.seat_number} is already booked."

                            }

                        )

                    

                    

                    seat_numbers.append(
                        seat.seat_number
                    )

        except Exception:

            return render(

                request,

                'movies/seat_selection.html',

                {

                    'theater': theater,

                    'seats': seats,

                    'error': "Booking failed. Please try again."

                }

            )

        threading.Thread(

            target=send_booking_email,

            args=(

                request.user,

                theater.movie,

                theater,

                ", ".join(seat_numbers)

            )

        ).start()

        seat_query = "&".join(

            [f"seats={seat}" for seat in selected_seats]

        )

        return redirect(

            f"/movies/payment/{theater.id}/?{seat_query}"

        )

    return render(

        request,

        'movies/seat_selection.html',

        {

            'theater': theater,

            'seats': seats

        }

    )