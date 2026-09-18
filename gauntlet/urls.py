from django.urls import include, path
from rest_framework.routers import DefaultRouter
from gauntlet.views import GauntletViewSet

router = DefaultRouter()
router.register(r'runs', GauntletViewSet, basename='gauntlet-run')

urlpatterns = [
    path('', include(router.urls)),
]
