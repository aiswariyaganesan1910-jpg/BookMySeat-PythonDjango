from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

from movies.models import Movie, Booking


def home(request):

    movies = Movie.objects.all()

    return render(

        request,

        'home.html',

        {

            'movies': movies

        }

    )


def register_view(request):

    if request.method == 'POST':

        form = UserCreationForm(request.POST)

        if form.is_valid():

            form.save()

            return redirect('login')

    else:

        form = UserCreationForm()

    return render(

        request,

        'users/register.html',

        {

            'form': form

        }

    )


@login_required
def profile_view(request):

    bookings = Booking.objects.filter(
        user=request.user
    )

    return render(

        request,

        'users/profile.html',

        {

            'bookings': bookings

        }

    )