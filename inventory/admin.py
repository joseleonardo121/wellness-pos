from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Productos,Decimal


@admin.register(Productos)
class ProductosAdmin(admin.ModelAdmin):
    # columnas que se muestran en la tabla
    list_display = (
        "Codigo",
        "Marca",
        "Modelo",
        "Diseno",
        "Color",
        "Talla",
        "Costo",
        "Precio",
        "S1",
        "S2",
        "S3",
        "Almacen",
        "total",       # método definido en tu modelo
        "inversion",   # método definido en tu modelo
    )

    # campos por los que se puede buscar
    search_fields = ("Codigo", "Marca", "Modelo", "Diseno", "Color", "Talla")

    # filtros en la barra lateral
    list_filter = ("Marca", "Color", "Talla")

    # orden por defecto
    ordering = ("Marca", "Modelo", "Color", "Talla")

    # campos de solo lectura
    readonly_fields = ("Codigo", "codigo_barras")

    # mostrar la imagen del código de barras en el panel de detalle
    def codigo_barras_preview(self, obj):
        if obj.codigo_barras:
            return f'<img src="{obj.codigo_barras.url}" width="200"/>'
        return "No disponible"
    codigo_barras_preview.allow_tags = True
    codigo_barras_preview.short_description = "Código de Barras"

    # organizar los campos en secciones
    fieldsets = (
        ("Información del producto", {
            "fields": ("Codigo", "Marca", "Modelo", "Diseno", "Color", "Talla", "Costo", "Precio")
        }),
        ("Inventario", {
            "fields": ("S1", "S2", "S3", "Almacen")
        }),
        ("Código de barras", {
            "fields": ("codigo_barras",),
        }),
    )
