from django.contrib import messages

from razorpay.errors import SignatureVerificationError

from django.http import JsonResponse
from django.db.models.functions import ExtractHour
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Count, Sum
import razorpay

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db import models
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
from .models import (
    Movie,
    Theater,
    Seat,
    Booking,
    ProcessedWebhook
)
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

    print("EMAIL FUNCTION CALLED")
    print(user.email)

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

        try:
            email.send()
            print("EMAIL SENT SUCCESSFULLY")

        except Exception as e:
            print("EMAIL SEND FAILED:", repr(e))

    except Exception as e:
        print("BOOKING EMAIL FUNCTION ERROR:", repr(e))

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

    paginator = Paginator(movies, 6)

    page_number = request.GET.get('page')

    movies = paginator.get_page(page_number)

    genre_counts = Movie.objects.values(
        'genre'
    ).annotate(
        total=Count('genre')
    )

    language_counts = Movie.objects.values(
        'language'
    ).annotate(
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

    if total_amount <= 0:

      messages.error(
        request,
        "Please select at least one seat."
    )

      return redirect(
        'book_seats',
        theater_id=theater_id
    )

    payment = client.order.create({

    "amount": total_amount * 100,

    "currency": "INR",

    "payment_capture": "1"

})


   
    



    TEST_MODE = True

    if TEST_MODE:

        payment_id = f"PAY{random.randint(100000,999999)}"

        for seat_id in selected_seats:

            seat = Seat.objects.get(id=seat_id)

            if not seat.is_booked:

                Booking.objects.create(

                    user=request.user,

                    movie=theater.movie,

                    theater=theater,

                    seat=seat,

                    payment_id=payment_id,

                    payment_status="Success"

                )

                seat.is_booked = True

                seat.save()

        seat_numbers = seat_objects.values_list(

            'seat_number',

            flat=True

        )
        try:
         send_booking_email(
            request.user,
            theater.movie,
            theater,
            ", ".join(seat_numbers)
    )
        except Exception as e:
           print("EMAIL ERROR:", e)


        return redirect(

            f"/movies/payment-success/?payment_id={payment_id}"

        )

    if request.method == "POST":
        

        razorpay_payment_id = request.POST.get(

            'razorpay_payment_id'

        )

        razorpay_order_id = request.POST.get(

            'razorpay_order_id'

        )

        razorpay_signature = request.POST.get(

            'razorpay_signature'

        )

        params_dict = {

            'razorpay_order_id': razorpay_order_id,

            'razorpay_payment_id': razorpay_payment_id,

            'razorpay_signature': razorpay_signature

        }

        try:

            client.utility.verify_payment_signature(

                params_dict

            )

        except SignatureVerificationError:

            return render(

                request,

                'movies/payment_failed.html',

                {

                    'error': 'Payment signature verification failed.'

                }

            )

        payment_status = request.POST.get(
            'payment_status'
        )

        payment_id = f"PAY{random.randint(100000,999999)}"

        if Booking.objects.filter(

            payment_id=payment_id

        ).exists():

            return render(

                request,

                'movies/payment_failed.html',

                {

                    'error': 'Duplicate payment detected.'

                }

            )

        if payment_status != "Success":

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

        seat_numbers = seat_objects.values_list(

            'seat_number',

            flat=True

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
                    seat.is_reserved = True

                    seat.reserved_at = timezone.now()

                    seat.save()

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
@staff_member_required
def admin_dashboard(request):
   

    

    dashboard_data = cache.get('dashboard_data')

    if dashboard_data:

        return render(

            request,

            'movies/admin_dashboard.html',

            dashboard_data

        )

    total_movies = Movie.objects.count()

    total_bookings = Booking.objects.count()

    total_users = User.objects.count()

    total_revenue = total_bookings * 200

    popular_movies = Movie.objects.annotate(

        booking_count=Count('booking')

    ).order_by('-booking_count')[:5]

    today = timezone.now()

    daily_revenue = Booking.objects.filter(

        booked_at__date=today.date()

    ).count() * 200

    weekly_revenue = Booking.objects.filter(

        booked_at__gte=today - timedelta(days=7)

    ).count() * 200

    monthly_revenue = Booking.objects.filter(

        booked_at__gte=today - timedelta(days=30)

    ).count() * 200

    busiest_theaters = Theater.objects.annotate(

        booked_seats=Count(

            'seat',

            filter=models.Q(seat__is_booked=True)

        ),

        total_seats=Count('seat')

    ).order_by('-booked_seats')[:5]

    peak_booking_hours = Booking.objects.annotate(

        hour=ExtractHour('booked_at')

    ).values(

        'hour'

    ).annotate(

        total_bookings=Count('id')

    ).order_by('-total_bookings')[:5]

    cancelled_bookings = Booking.objects.filter(

        payment_status='Failed'

    ).count()

    total_booking_count = Booking.objects.count()

    cancellation_rate = 0

    if total_booking_count > 0:

        cancellation_rate = round(

            (cancelled_bookings / total_booking_count) * 100,

            2

        )

    dashboard_data = {

        'total_movies': total_movies,

        'total_bookings': total_bookings,

        'total_users': total_users,

        'total_revenue': total_revenue,

        'popular_movies': popular_movies,

        'daily_revenue': daily_revenue,

        'weekly_revenue': weekly_revenue,

        'monthly_revenue': monthly_revenue,

        'busiest_theaters': busiest_theaters,

        'peak_booking_hours': peak_booking_hours,

        'cancelled_bookings': cancelled_bookings,

        'cancellation_rate': cancellation_rate,

    }

    cache.set(

        'dashboard_data',

        dashboard_data,

        60

    )

    return render(

        request,

        'movies/admin_dashboard.html',

        dashboard_data

    )
@staff_member_required
def analytics_api(request):

    data = {

        'total_movies': Movie.objects.count(),

        'total_bookings': Booking.objects.count(),

        'total_users': User.objects.count(),

    }

    return JsonResponse(data)
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def payment_webhook(request):

    if request.method == "POST":

        event_id = request.headers.get(
            'X-Razorpay-Event-Id'
        )

        if event_id:

            if ProcessedWebhook.objects.filter(
                event_id=event_id
            ).exists():

                return JsonResponse(

                    {

                        'status': 'duplicate webhook ignored'

                    }

                )

            ProcessedWebhook.objects.create(

                event_id=event_id

            )

        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        received_signature = request.headers.get(
            'X-Razorpay-Signature'
        )

        body = request.body.decode('utf-8')

        try:

            client.utility.verify_webhook_signature(

                body,

                received_signature,

                webhook_secret

            )

        except SignatureVerificationError:

            return JsonResponse(

                {

                    'status': 'invalid signature'

                },

                status=400

            )

        return JsonResponse(

            {

                'status': 'webhook verified'

            }

        )

    return JsonResponse(

        {

            'status': 'invalid request'

        },

        status=400

    )