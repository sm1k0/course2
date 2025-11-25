from django.urls import path

from shop import views as shop_views

app_name = 'accounts'

urlpatterns = [
    path('login/', shop_views.login_view, name='login'),
    path('logout/', shop_views.logout_view, name='logout'),
    path('register/', shop_views.register_view, name='register'),
    path('profile/', shop_views.profile_view, name='profile'),
]
