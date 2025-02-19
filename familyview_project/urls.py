# familyview_project/urls.py

from django.contrib import admin
from django.urls import path
from familyview_project import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Landing page
    path('', views.home, name='home'),

    # Parent registration
    path('register_parent/', views.register_parent, name='register_parent'),

    # Login & Logout
    path('login/', views.login_user, name='login_user'),
    path('logout/', views.logout_user, name='logout_user'),

    # Movie list & watchlist
    path('movie_list/', views.movie_list, name='movie_list'),
    path('watchlist/', views.watchlist, name='watchlist'),
    path('add_to_watchlist/<int:movie_id>/', views.add_to_watchlist, name='add_to_watchlist'),

    # Child account creation & editing
    path('create_child/', views.create_child, name='create_child'),
    path('edit_child/<int:child_id>/', views.edit_child, name='edit_child'),

    # Recommendations & diary
    path('recommendations/', views.recommendations, name='recommendations'),
    path('diary/', views.diary, name='diary'),

    # Removal links
    path('remove_from_watchlist/<int:movie_id>/', views.remove_from_watchlist, name='remove_from_watchlist'),
    path('remove_diary_entry/<int:entry_id>/', views.remove_diary_entry, name='remove_diary_entry'),


    # Basic admin pages
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('edit_user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('remove_user/<int:user_id>/', views.remove_user, name='remove_user'),

]