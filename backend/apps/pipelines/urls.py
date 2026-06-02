from django.urls import path

from . import views

urlpatterns = [
    path("", views.PipelineListCreateView.as_view()),
    path("<int:pk>/", views.PipelineDetailView.as_view()),
    path("<int:pk>/run", views.run_pipeline),
]
