from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from .models import Movie, Theater, Seat, Booking


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

    theaters = Theater.objects.filter(
        movie=movie
    )

    return render(

        request,
        'movies/theater_list.html',

        {
            'movie': movie,
            'theaters': theaters
        }

    )


def book_seats(request, theater_id):

    theater = Theater.objects.get(id=theater_id)

    seats = Seat.objects.filter(theater=theater)

    if request.method == "POST":

        selected_seats = request.POST.getlist('seats')

        for seat_id in selected_seats:

            seat = Seat.objects.get(id=seat_id)

            Booking.objects.create(

                user=request.user,

                movie=theater.movie,
                
                theater=theater,

                seat=seat

            )

        return redirect('profile')

    return render(

        request,

        'movies/seat_selection.html',

        {

            'theater': theater,

            'seats': seats

        }

    )