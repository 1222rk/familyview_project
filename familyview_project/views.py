# familyview_project/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from collections import Counter

# Import your models
from familyview_project.models import Movie, WatchlistItem, DiaryEntry, ChildAccount


def home(request):
    """Landing page."""
    return render(request, 'familyview_project/home.html')


def register_parent(request):
    """Register a new parent account."""
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        # Create a new parent user
        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, 'Parent account created. Please log in.')
        return redirect('login_user')
    return render(request, 'familyview_project/register_parent.html')


def login_user(request):
    """Log in an existing user."""
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('movie_list')
        else:
            messages.error(request, 'Invalid credentials.')
    return render(request, 'familyview_project/login.html')


def logout_user(request):
    """Log out the current user."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


def movie_list(request):
    query = request.GET.get('q', '')
    selected_genre = request.GET.get('genre', '')
    age_rating = request.GET.get('age_rating', '')

    movies = Movie.objects.all()

    # Get all distinct genres from the Movie table
    genres = Movie.objects.values_list('genre', flat=True).distinct()

    if query:
        movies = movies.filter(title__icontains=query)
    if selected_genre:
        movies = movies.filter(genre__iexact=selected_genre)
    if age_rating:
        movies = movies.filter(age_rating=age_rating)

    # Optional: Apply child filtering if necessary
    if request.user.is_authenticated and hasattr(request.user, 'child_profile'):
        max_rating = request.user.child_profile.max_age_rating
        if max_rating == "U":
            movies = movies.filter(age_rating__in=["U"])
        elif max_rating == "PG":
            movies = movies.filter(age_rating__in=["U", "PG"])
        elif max_rating == "12":
            movies = movies.filter(age_rating__in=["U", "PG", "12"])

    context = {
        'movies': movies,
        'genres': genres,  # Pass the dynamic list of genres
    }
    return render(request, 'familyview_project/movie_list.html', context)



@login_required
def add_to_watchlist(request, movie_id):
    """Add a movie to the user's watchlist."""
    movie = get_object_or_404(Movie, id=movie_id)
    if not WatchlistItem.objects.filter(user=request.user, movie=movie).exists():
        WatchlistItem.objects.create(user=request.user, movie=movie)
        messages.success(request, f'{movie.title} added to your watchlist.')
    else:
        messages.info(request, f'{movie.title} is already in your watchlist.')
    return redirect('movie_list')


@login_required
def watchlist(request):
    """Display the logged-in user's watchlist."""
    items = WatchlistItem.objects.filter(user=request.user)
    return render(request, 'familyview_project/watchlist.html', {'items': items})


@login_required
def create_child(request):
    """Allow a parent to create a child account."""
    if request.method == 'POST':
        child_username = request.POST['child_username']
        child_password = request.POST['child_password']
        max_rating = request.POST['max_age_rating']
        child_user = User.objects.create_user(username=child_username, password=child_password)
        # Create a child profile for the new user
        ChildAccount.objects.create(user=child_user, max_age_rating=max_rating)
        messages.success(request, f'Child account {child_username} created.')
        return redirect('movie_list')
    return render(request, 'familyview_project/create_child.html')


@login_required
def edit_child(request, child_id):
    """Allow a parent to update a child's max age rating."""
    child_user = get_object_or_404(User, id=child_id)
    if not hasattr(child_user, 'child_profile'):
        messages.error(request, "This is not a child account.")
        return redirect('movie_list')
    if request.method == 'POST':
        max_rating = request.POST['max_age_rating']
        child_user.child_profile.max_age_rating = max_rating
        child_user.child_profile.save()
        messages.success(request, f'Child account {child_user.username} updated.')
        return redirect('movie_list')
    return render(request, 'familyview_project/edit_child.html', {
        'child_user': child_user,
        'current_rating': child_user.child_profile.max_age_rating
    })


@login_required
def recommendations(request):
    """Provide movie recommendations based on the user's watchlist."""
    items = WatchlistItem.objects.filter(user=request.user)
    if not items.exists():
        messages.info(request, "Add more movies to your watchlist to get recommendations!")
        return render(request, 'familyview_project/recommendations.html', {'movies': None})

    genres = [item.movie.genre for item in items]
    genre_counts = Counter(genres)
    # Choose the top 2 genres from the watchlist
    top_genres = [genre for genre, count in genre_counts.most_common(2)]
    watchlist_ids = [item.movie.id for item in items]
    recommended = Movie.objects.filter(genre__in=top_genres).exclude(id__in=watchlist_ids)

    # If the user is a child, further restrict by max_age_rating
    if hasattr(request.user, 'child_profile'):
        max_rating = request.user.child_profile.max_age_rating
        if max_rating == "U":
            recommended = recommended.filter(age_rating__in=["U"])
        elif max_rating == "PG":
            recommended = recommended.filter(age_rating__in=["U", "PG"])
        elif max_rating == "12":
            recommended = recommended.filter(age_rating__in=["U", "PG", "12"])

    if not recommended.exists():
        messages.warning(request, "No recommendations found based on your watchlist.")
        return render(request, 'familyview_project/recommendations.html', {'movies': None})

    return render(request, 'familyview_project/recommendations.html', {'movies': recommended})


@login_required
def diary(request):
    """Allow the user to log watched movies and view diary entries."""
    if request.method == 'POST':
        movie_id = request.POST['movie_id']
        watched_on = request.POST['watched_on']
        thumbs_up = request.POST.get('thumbs_up') == 'on'
        movie = get_object_or_404(Movie, id=movie_id)
        DiaryEntry.objects.create(
            user=request.user,
            movie=movie,
            watched_on=watched_on,
            thumbs_up=thumbs_up
        )
        messages.success(request, 'Diary entry added.')
        return redirect('diary')

    entries = DiaryEntry.objects.filter(user=request.user)
    all_movies = Movie.objects.all()
    return render(request, 'familyview_project/diary.html', {'entries': entries, 'movies': all_movies})
