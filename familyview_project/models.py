from django.db import models
from django.contrib.auth.models import User

class ChildAccount(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="child_profile"
    )
    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="children",
        null=True,    # temporarily allow blank until you back-fill existing data
        blank=True,
    )
    max_age_rating = models.CharField(
        max_length=5,
        choices=[("U", "U"), ("PG", "PG"), ("12", "12")],
        default="U"
    )

    def __str__(self):
        return f"Child {self.user.username} (Max: {self.max_age_rating})"


class Movie(models.Model):
    """
    Movie model stores all films with genre, age rating, and release date.
    """
    title = models.CharField(max_length=255)
    genre = models.CharField(max_length=50)
    age_rating = models.CharField(
        max_length=5,
        choices=[("U", "U"), ("PG", "PG"), ("12", "12")]
    )
    release_date = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.age_rating}) - {self.genre}"


class WatchlistItem(models.Model):
    """
    Stores movies added to a user's watchlist.
    Links to User (parent or child) and a Movie.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "movie")  # Avoid duplicates

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"


class DiaryEntry(models.Model):
    """
    Stores watched movies with date and rating (thumbs up/down).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    watched_on = models.DateField()
    thumbs_up = models.BooleanField(default=True)

    def __str__(self):
        status = "👍" if self.thumbs_up else "👎"
        return f"{self.user.username} watched {self.movie.title} on {self.watched_on} {status}"


class AdminRequest(models.Model):
    REQUEST_TYPES = [
        ('ADD_MOVIE',  'Add Movie'),
        ('AGE_CHANGE', 'Change Child Age'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    details = models.TextField(help_text="Describe what you'd like us to do.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} – {self.get_request_type_display()} @ {self.created_at:%Y-%m-%d %H:%M}"
