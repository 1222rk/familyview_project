from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from collections import Counter
from django.core.paginator import Paginator

# Import your models
from familyview_project.models import Movie, WatchlistItem, DiaryEntry, ChildAccount


def home(request):
    """Landing page. Redirect authenticated users to the movie list."""
    if request.user.is_authenticated:
        return redirect('movie_list')
    return render(request, 'familyview_project/home.html')


def register_parent(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')

        # Check if the username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken, please choose a different one.")
            return redirect('register_parent')

        # Check password length (>= 8 characters)
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('register_parent')

        # Check if password contains at least one digit
        if not any(char.isdigit() for char in password):
            messages.error(request, 'Password must contain at least one number.')
            return redirect('register_parent')

        # If all checks pass, create the user
        user = User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, 'Parent account created successfully! Please log in.')
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
    sort_option = request.GET.get('sort', '')  # Parameter for sorting

    # Retrieve all movies
    movies = Movie.objects.all()

    # Apply search and filter criteria
    if query:
        movies = movies.filter(title__icontains=query)
    if selected_genre:
        movies = movies.filter(genre__iexact=selected_genre)
    if age_rating:
        movies = movies.filter(age_rating=age_rating)

    # If a child is logged in, restrict movies based on the child's max_age_rating
    if request.user.is_authenticated and hasattr(request.user, 'child_profile'):
        max_rating = request.user.child_profile.max_age_rating
        if max_rating == "U":
            movies = movies.filter(age_rating__in=["U"])
        elif max_rating == "PG":
            movies = movies.filter(age_rating__in=["U", "PG"])
        elif max_rating == "12":
            movies = movies.filter(age_rating__in=["U", "PG", "12"])

    # Apply sorting
    if sort_option == 'alphabetical':
        movies = movies.order_by('title')
    elif sort_option == 'release':
        movies = movies.order_by('release_date')

    # Retrieve all distinct genres and sort them alphabetically
    genres = sorted(list(Movie.objects.values_list('genre', flat=True).distinct()))

    # Paginate the movies: 10 per page
    paginator = Paginator(movies, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'movies': page_obj,         # Paginated movies
        'genres': genres,           # Dynamic list of genres
        'query': query,
        'selected_genre': selected_genre,
        'selected_age': age_rating,
        'sort': sort_option,
        'page_obj': page_obj,
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
    """Allow a parent to create a child account.
       Prevent child users from accessing this page.
    """
    # If the current user already has a child_profile, they are a child; block access.
    if hasattr(request.user, 'child_profile'):
        messages.error(request, "Child accounts cannot create another child account.")
        return redirect('movie_list')

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
    """
    Provide movie recommendations based on the user's watchlist and diary likes.
    Limit the final list to a maximum of 10 movies.
    """
    # Retrieve watchlist items and diary entries (thumbs up) for the user
    watchlist_items = WatchlistItem.objects.filter(user=request.user)
    diary_likes = DiaryEntry.objects.filter(user=request.user, thumbs_up=True)

    # If neither exists, show a message
    if not watchlist_items.exists() and not diary_likes.exists():
        messages.info(request, "Add movies to your watchlist or diary to get recommendations!")
        return render(request, 'familyview_project/recommendations.html', {'recommendations': None})

    # Combine genres from watchlist + diary likes
    watchlist_genres = [item.movie.genre for item in watchlist_items]
    diary_genres = [entry.movie.genre for entry in diary_likes]
    combined_genres = watchlist_genres + diary_genres

    # Determine top genres
    genre_counts = Counter(combined_genres)
    top_genres = [genre for genre, count in genre_counts.most_common(2)]

    # Exclude movies already in watchlist
    watchlist_ids = [item.movie.id for item in watchlist_items]
    recommended_qs = Movie.objects.filter(genre__in=top_genres).exclude(id__in=watchlist_ids)

    # Child filtering
    if hasattr(request.user, 'child_profile'):
        max_rating = request.user.child_profile.max_age_rating
        if max_rating == "U":
            recommended_qs = recommended_qs.filter(age_rating__in=["U"])
        elif max_rating == "PG":
            recommended_qs = recommended_qs.filter(age_rating__in=["U", "PG"])
        elif max_rating == "12":
            recommended_qs = recommended_qs.filter(age_rating__in=["U", "PG", "12"])

    # If nothing to recommend
    if not recommended_qs.exists():
        messages.warning(request, "No recommendations found based on your preferences.")
        return render(request, 'familyview_project/recommendations.html', {'recommendations': None})

    # Limit to a maximum of 10 recommended movies
    recommended_qs = recommended_qs[:10]

    # Build the recommendation list
    recommendations = []
    for movie in recommended_qs:
        reasons = []
        # Check watchlist reason
        watchlist_reason_item = watchlist_items.filter(movie__genre=movie.genre).first()
        if watchlist_reason_item:
            reasons.append(f"you added {watchlist_reason_item.movie.title} to your watchlist")
        # Check diary reason
        diary_reason_item = diary_likes.filter(movie__genre=movie.genre).first()
        if diary_reason_item:
            reasons.append(f"you liked {diary_reason_item.movie.title} in your diary")

        reason_text = "Because " + " and ".join(reasons) if reasons else ""
        recommendations.append({
            'movie': movie,
            'reason': reason_text,
        })

    return render(request, 'familyview_project/recommendations.html', {'recommendations': recommendations})


@login_required
def diary(request):
    # For child users, restrict the movies they can choose from
    all_movies = Movie.objects.all()
    if request.user.is_authenticated and hasattr(request.user, 'child_profile'):
        max_rating = request.user.child_profile.max_age_rating
        if max_rating == "U":
            all_movies = all_movies.filter(age_rating="U")
        elif max_rating == "PG":
            all_movies = all_movies.filter(age_rating__in=["U", "PG"])
        elif max_rating == "12":
            all_movies = all_movies.filter(age_rating__in=["U", "PG", "12"])

    if request.method == 'POST':
        movie_id = request.POST['movie_id']
        watched_on_str = request.POST['watched_on']

        # Convert the input string to a date object
        try:
            watched_on_date = datetime.strptime(watched_on_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
            return redirect('diary')

        # Check if the selected date is in the future
        if watched_on_date > date.today():
            messages.error(request, "You cannot log a diary entry for a future date.")
            return redirect('diary')

        movie = get_object_or_404(Movie, id=movie_id)

        # Additional check: if the user is a child, ensure the movie's age rating is allowed
        if hasattr(request.user, 'child_profile'):
            max_rating = request.user.child_profile.max_age_rating
            allowed_ratings = (["U"] if max_rating == "U" else
                               ["U", "PG"] if max_rating == "PG" else
                               ["U", "PG", "12"])
            if movie.age_rating not in allowed_ratings:
                messages.error(request, "This movie is not allowed for your age.")
                return redirect('diary')

        thumbs_up = request.POST.get('thumbs_up') == 'on'
        DiaryEntry.objects.create(
            user=request.user,
            movie=movie,
            watched_on=watched_on_date,
            thumbs_up=thumbs_up
        )
        messages.success(request, 'Diary entry added.')
        return redirect('diary')

    entries = DiaryEntry.objects.filter(user=request.user)
    return render(request, 'familyview_project/diary.html', {'entries': entries, 'movies': all_movies})


@login_required
def remove_from_watchlist(request, movie_id):
    """Remove a movie from the user's watchlist."""
    movie = get_object_or_404(Movie, id=movie_id)
    item = WatchlistItem.objects.filter(user=request.user, movie=movie).first()
    if item:
        item.delete()
        messages.success(request, f'{movie.title} removed from your watchlist.')
    else:
        messages.info(request, f'{movie.title} is not in your watchlist.')
    return redirect('watchlist')


@login_required
def remove_diary_entry(request, entry_id):
    """Remove a diary entry for the logged-in user."""
    entry = get_object_or_404(DiaryEntry, id=entry_id, user=request.user)
    entry.delete()
    messages.success(request, 'Diary entry removed.')
    return redirect('diary')


@login_required
def admin_dashboard(request):
    """
    Temporary admin dashboard that shows a list of all registered users,
    their account type, and options to edit or remove them.
    Only accessible to superusers.
    """
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to view this page.")
        return redirect('home')

    # Retrieve all users
    users = User.objects.all().order_by('username')
    return render(request, 'familyview_project/admin_dashboard.html', {'users': users})


@login_required
def edit_user(request, user_id):
    """
    Allow an admin to update a user's email address.
    Only accessible to superusers.
    """
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to view this page.")
        return redirect('home')

    user_to_edit = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        # For simplicity, we're only editing the email here.
        new_email = request.POST.get('email', '')
        user_to_edit.email = new_email
        user_to_edit.save()
        messages.success(request, "User updated successfully.")
        return redirect('admin_dashboard')

    return render(request, 'familyview_project/edit_user.html', {'user_to_edit': user_to_edit})


@login_required
def remove_user(request, user_id):
    """
    Allow an admin to remove a user.
    Prevent admins from removing their own account.
    Only accessible to superusers.
    """
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('home')

    user_to_remove = get_object_or_404(User, id=user_id)

    if user_to_remove == request.user:
        messages.error(request, "You cannot remove your own account.")
        return redirect('admin_dashboard')

    user_to_remove.delete()
    messages.success(request, "User removed successfully.")
    return redirect('admin_dashboard')