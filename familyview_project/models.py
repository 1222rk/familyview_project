# familyview_project/models.py

from django.db import models
from django.contrib.auth.models import User

class ChildAccount(models.Model):
    """
    A child account linked to a standard Django User.
    It has a max_age_rating that restricts accessible movies.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="child_profile")
    max_age_rating = models.CharField(
        max_length=5,
        choices=[("U", "U"), ("PG", "PG"), ("12", "12")],
        default="U"
    )

    def __str__(self):
        return f"Child: {self.user.username} (Max Age: {self.max_age_rating})"

class Movie(models.Model):
    """
    Movie model stores all films with genre and age rating.
    """
    title = models.CharField(max_length=255)
    genre = models.CharField(max_length=50)
    age_rating = models.CharField(
        max_length=5,
        choices=[("U", "U"), ("PG", "PG"), ("12", "12")]
    )

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
