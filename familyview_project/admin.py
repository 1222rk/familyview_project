# familyview_project/admin.py

from django.contrib import admin
from .models import Movie, WatchlistItem, DiaryEntry, AdminRequest, ChildAccount

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display    = ('title', 'genre', 'age_rating', 'release_date')
    list_filter     = ('age_rating', 'genre')
    search_fields   = ('title', 'genre')
    ordering        = ('title',)

@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display  = ('user', 'movie')
    search_fields = ('user__username', 'movie__title')

@admin.register(DiaryEntry)
class DiaryEntryAdmin(admin.ModelAdmin):
    list_display  = ('user', 'movie', 'watched_on', 'thumbs_up')
    list_filter   = ('thumbs_up',)
    search_fields = ('user__username', 'movie__title')

@admin.register(AdminRequest)
class AdminRequestAdmin(admin.ModelAdmin):
    list_display    = ('user', 'request_type', 'created_at')
    readonly_fields = ('user', 'created_at')
    list_filter     = ('request_type', 'created_at')
    search_fields   = ('user__username', 'details')

@admin.register(ChildAccount)
class ChildAccountAdmin(admin.ModelAdmin):
    list_display  = ('user', 'max_age_rating')
    list_filter   = ('max_age_rating',)
    search_fields = ('user__username',)
