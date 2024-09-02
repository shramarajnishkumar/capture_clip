from django.urls import path
from .views import Home, Login, SignUp, VerifyEmail, Logout, CaptureClipView, Journal

urlpatterns = [
    path("", Home.as_view(), name="home"),
    path("login", Login.as_view(), name="login"),
    path("signup", SignUp.as_view(), name="signup"),
    path("logout", Logout.as_view(), name="logout"),
    path("email-verify", VerifyEmail.as_view(), name="email-verify"),
    path("home", Home.as_view(), name="home"),
    path("capture_clip", CaptureClipView.as_view(), name="capture_clip"),
    path("journal", Journal.as_view(), name="journal"),
]