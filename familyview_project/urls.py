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
]
