# familyview_project/views.py

import re
import random
from datetime import datetime, date
from collections import Counter

from django.shortcuts            import render, redirect, get_object_or_404
from django.contrib              import messages
from django.contrib.auth        import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator       import Paginator

from .models import (
    Movie,
    WatchlistItem,
    DiaryEntry,
    ChildAccount,
    AdminRequest
)
from .forms import AdminRequestForm


def is_strong_password(password):
    """
    Returns True if password is at least 8 characters long
    and contains at least one numeric digit.
    """
    return len(password) >= 8 and bool(re.search(r"\d", password))


def home(request):
    """Landing page. Redirect authenticated users to movie list."""
    if request.user.is_authenticated:
        return redirect('movie_list')
    return render(request, 'familyview_project/home.html')


def register_parent(request):
    """Allow a new parent to sign up, enforcing our password policy."""
    if request.method == 'POST':
        username = request.POST.get('username', '')
        email    = request.POST.get('email', '')
        password = request.POST.get('password', '')

        # 1. Check username uniqueness
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken, please choose a different one.")
            return redirect('register_parent')

        # 2. Enforce password policy
        if not is_strong_password(password):
            messages.error(
                request,
                "Password must be at least 8 characters long and include at least one number."
            )
            return redirect('register_parent')

        # 3. Create the user
        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, 'Parent account created successfully! Please log in.')
        return redirect('login_user')

    return render(request, 'familyview_project/register_parent.html')


def login_user(request):
    """Authenticate and log in an existing user."""
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )
        if user:
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('movie_list')
        messages.error(request, 'Invalid credentials.')
    return render(request, 'familyview_project/login.html')


def logout_user(request):
    """Log out the current user."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


def movie_list(request):
    """Display the movie list with search, filter, sort, pagination."""
    query = request.GET.get('q', '')
    selected_genre = request.GET.get('genre', '')
    age_rating = request.GET.get('age_rating', '')
    sort_option = request.GET.get('sort', '')

    # Retrieve and filter
    movies = Movie.objects.all()
    if query:
        movies = movies.filter(title__icontains=query)
    if selected_genre:
        movies = movies.filter(genre__iexact=selected_genre)
    if age_rating:
        movies = movies.filter(age_rating=age_rating)

    # Child age restriction
    if request.user.is_authenticated and hasattr(request.user, 'child_profile'):
        max_rating = request.user.child_profile.max_age_rating
        allowed = (
            ["U"] if max_rating == "U" else
            ["U", "PG"] if max_rating == "PG" else
            ["U", "PG", "12"]
        )
        movies = movies.filter(age_rating__in=allowed)

    # Sorting
    if sort_option == 'alphabetical':
        movies = movies.order_by('title')
    elif sort_option == 'release':
        movies = movies.order_by('release_date')

    # Genres list
    genres = sorted(Movie.objects.values_list('genre', flat=True).distinct())

    # Paginate: 4 per page for a 2×2 grid
    paginator = Paginator(movies, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'familyview_project/movie_list.html', {
        'movies': page_obj,
        'genres': genres,
        'query': query,
        'selected_genre': selected_genre,
        'selected_age': age_rating,
        'sort': sort_option,
        'page_obj': page_obj,
    })


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
    """
    Allow a parent to create a child account.
    Links the child to the current user as parent.
    """
    if hasattr(request.user, 'child_profile'):
        messages.error(request, "Child accounts cannot create another child account.")
        return redirect('movie_list')

    if request.method == 'POST':
        child_username = request.POST['child_username']
        child_password = request.POST['child_password']
        max_rating = request.POST['max_age_rating']

        if not is_strong_password(child_password):
            messages.error(request,
                           "Child password must be at least 8 characters long and include at least one number.")
            return redirect('create_child')

        child_user = User.objects.create_user(username=child_username, password=child_password)
        ChildAccount.objects.create(
            user=child_user,
            parent=request.user,
            max_age_rating=max_rating
        )
        messages.success(request, f'Child account {child_username} created.')
        return redirect('movie_list')

    return render(request, 'familyview_project/create_child.html')


@login_required
def edit_child(request, child_id):
    """
    Allow a parent to edit their child's max age rating.
    Only the parent who created the child may edit.
    """
    profile = get_object_or_404(ChildAccount, id=child_id, parent=request.user)

    if request.method == 'POST':
        new_rating = request.POST.get('max_age_rating')
        if new_rating in ["U", "PG", "12"]:
            profile.max_age_rating = new_rating
            profile.save()
            messages.success(request, f"{profile.user.username}'s age rating updated to {new_rating}.")
        else:
            messages.error(request, "Invalid rating selected.")
        return redirect('movie_list')

    return render(request, 'familyview_project/edit_child.html', {
        'child_profile': profile
    })


@login_required
def recommendations(request):
    """
    Provide movie recommendations based on watchlist + diary.
    Supports shuffle via '?shuffle=1'.
    """
    watchlist_items = WatchlistItem.objects.filter(user=request.user)
    diary_likes      = DiaryEntry.objects.filter(user=request.user, thumbs_up=True)

    if not watchlist_items.exists() and not diary_likes.exists():
        messages.info(request, "Add movies to your watchlist or diary to get recommendations!")
        return render(request, 'familyview_project/recommendations.html', {'recommendations': None})

    # Determine top genres
    genres = [w.movie.genre for w in watchlist_items] + [d.movie.genre for d in diary_likes]
    top_two = [g for g, _ in Counter(genres).most_common(2)]

    # Exclude seen
    exclude_ids = [w.movie.id for w in watchlist_items]
    qs = Movie.objects.filter(genre__in=top_two).exclude(id__in=exclude_ids)

    # Child filtering
    if hasattr(request.user, 'child_profile'):
        max_r = request.user.child_profile.max_age_rating
        allowed = (
            ["U"] if max_r == "U" else
            ["U", "PG"] if max_r == "PG" else
            ["U", "PG", "12"]
        )
        qs = qs.filter(age_rating__in=allowed)

    if not qs.exists():
        messages.warning(request, "No recommendations found based on your preferences.")
        return render(request, 'familyview_project/recommendations.html', {'recommendations': None})

    # Build recommendation list
    recommendations = []
    for movie in qs[:10]:
        reasons = []
        wi = watchlist_items.filter(movie__genre=movie.genre).first()
        if wi:
            reasons.append(f"you added {wi.movie.title} to your watchlist")
        dl = diary_likes.filter(movie__genre=movie.genre).first()
        if dl:
            reasons.append(f"you liked {dl.movie.title} in your diary")
        reason_text = "Because " + " and ".join(reasons) if reasons else ""
        recommendations.append({'movie': movie, 'reason': reason_text})

    # Shuffle if requested
    if request.GET.get('shuffle') == '1':
        random.shuffle(recommendations)

    return render(request, 'familyview_project/recommendations.html', {
        'recommendations': recommendations
    })


@login_required
def diary(request):
    """Log and view diary entries."""
    all_movies = Movie.objects.all()
    if hasattr(request.user, 'child_profile'):
        max_r = request.user.child_profile.max_age_rating
        allowed = (
            ["U"] if max_r == "U" else
            ["U", "PG"] if max_r == "PG" else
            ["U", "PG", "12"]
        )
        all_movies = all_movies.filter(age_rating__in=allowed)

    if request.method == 'POST':
        movie_id = request.POST['movie_id']
        watched_str = request.POST['watched_on']
        try:
            watched_on = datetime.strptime(watched_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format. Use YYYY-MM-DD.")
            return redirect('diary')

        if watched_on > date.today():
            messages.error(request, "You cannot log a future date.")
            return redirect('diary')

        movie = get_object_or_404(Movie, id=movie_id)
        if hasattr(request.user, 'child_profile') and movie.age_rating not in allowed:
            messages.error(request, "This movie is not allowed for your age.")
            return redirect('diary')

        thumbs_up = request.POST.get('thumbs_up') == 'on'
        DiaryEntry.objects.create(
            user=request.user,
            movie=movie,
            watched_on=watched_on,
            thumbs_up=thumbs_up
        )
        messages.success(request, 'Diary entry added.')
        return redirect('diary')

    entries = DiaryEntry.objects.filter(user=request.user)
    return render(request, 'familyview_project/diary.html', {
        'entries': entries,
        'movies': all_movies
    })


@login_required
def remove_from_watchlist(request, movie_id):
    """Remove a movie from the user's watchlist."""
    item = WatchlistItem.objects.filter(user=request.user, movie__id=movie_id).first()
    if item:
        item.delete()
        messages.success(request, f'{item.movie.title} removed from your watchlist.')
    else:
        messages.info(request, 'That movie was not in your watchlist.')
    return redirect('watchlist')


@login_required
def remove_diary_entry(request, entry_id):
    """Remove a diary entry."""
    entry = get_object_or_404(DiaryEntry, id=entry_id, user=request.user)
    entry.delete()
    messages.success(request, 'Diary entry removed.')
    return redirect('diary')


@login_required
def admin_dashboard(request):
    """List all users for superuser editing/removal."""
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to view this page.")
        return redirect('home')

    users = User.objects.all().order_by('username')
    return render(request, 'familyview_project/admin_dashboard.html', {'users': users})


@login_required
def edit_user(request, user_id):
    """Allow superusers to edit a user's email."""
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to view this page.")
        return redirect('home')

    user_to_edit = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user_to_edit.email = request.POST.get('email', '')
        user_to_edit.save()
        messages.success(request, "User updated successfully.")
        return redirect('admin_dashboard')

    return render(request, 'familyview_project/edit_user.html', {'user_to_edit': user_to_edit})


@login_required
def remove_user(request, user_id):
    """Allow superusers to remove a user (not themselves)."""
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('home')

    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        messages.error(request, "You cannot remove your own account.")
        return redirect('admin_dashboard')

    target.delete()
    messages.success(request, "User removed successfully.")
    return redirect('admin_dashboard')


@login_required
def submit_request(request):
    """Let any user submit an admin request."""
    if request.method == 'POST':
        form = AdminRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.user = request.user
            req.save()
            messages.success(request, "Your request has been submitted to the admins.")
            return redirect('movie_list')
    else:
        form = AdminRequestForm()

    return render(request, 'familyview_project/submit_request.html', {'form': form})
