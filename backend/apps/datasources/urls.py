from django.urls import path

from . import views

urlpatterns = [
    path("", views.DataSourceListCreateView.as_view()),
    path("<int:pk>/", views.DataSourceDetailView.as_view()),
]
