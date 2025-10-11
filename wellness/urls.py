from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings              # 👈 importar settings
from django.conf.urls.static import static  
urlpatterns = [
    path("admin/", admin.site.urls),
    path("select2/", include("django_select2.urls")),
    path("inventory/", include("inventory.urls")),  # ← ahora sí tendrán prefijo /inventory/
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)