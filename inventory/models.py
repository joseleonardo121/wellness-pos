from django.db import models
from django.contrib.auth.models import User

# Create your models here.
from django.db import models
from io import BytesIO
import barcode
from barcode.writer import ImageWriter
from django.core.files.base import ContentFile

import uuid

from django.db import models

class Proveedor(models.Model):
    # id se crea automáticamente en Django
    persona_deposito = models.CharField(max_length=100, help_text="Persona a nombre de quien se hace el depósito")
    nombre_empresa = models.CharField(max_length=150, help_text="Nombre del proveedor o empresa")
    rubro = models.CharField(max_length=150, help_text="Qué es lo que vende el proveedor")
    celular = models.CharField(max_length=15, help_text="Número de contacto del proveedor")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_empresa} - {self.rubro}"


def generar_numero_venta():
    """Genera un número único para cada venta"""
    return f"V-{uuid.uuid4().hex[:8].upper()}"

class Productos(models.Model):
    Codigo = models.CharField(primary_key=True, max_length=100, unique=True, editable=False)  # autogenerado
    Talla = models.CharField(max_length=50, null=False)
    Marca = models.CharField(max_length=100, null=False)
    Modelo = models.CharField(max_length=100, null=False)
    Diseno = models.CharField(max_length=100, null=False)
    Color = models.CharField(max_length=50, null=False)
    Costo = models.DecimalField(max_digits=10, decimal_places=2, default=18)
    Precio = models.DecimalField(max_digits=10, decimal_places=2)

    # Stock por ubicación
    S1 = models.IntegerField(default=0)  # Tienda 1
    S2 = models.IntegerField(default=0)  # Tienda 2
    S3 = models.IntegerField(default=0)  # Tienda 3
    Almacen = models.IntegerField(default=0)  # Almacén central

    # Imagen del código de barras
    codigo_barras = models.ImageField(upload_to="barcodes/", blank=True, null=True)

    class Meta:
        verbose_name_plural = "Productos"

    @property
    def CANT_TOTAL(self):
        return (self.S1 or 0) + (self.S2 or 0) + (self.S3 or 0) + (self.Almacen or 0)

    @property
    def estado_stock(self):
        total = self.CANT_TOTAL
        if total == 1:
            return "🚨 Urgente"
        elif total == 2:
            return "⚠️ Sugerido"
        elif 3 <= total <= 5:
            return "👍 Está bien"
        else:
            return "✅ Excelente"




    def __str__(self):
        return f"{self.Codigo} | {self.Marca} | {self.Modelo} | {self.Color} | {self.Talla}"

    # ================== Cálculos ==================

    def total(self):
        """Cantidad total disponible en todas las ubicaciones"""
        return self.S1 + self.S2 + self.S3 + self.Almacen

    def inversion(self):
        """Inversión total considerando el costo * stock"""
        return self.Costo * self.total()

    def inversion_t1(self):
        return self.Costo * self.S1

    def inversion_t2(self):
        return self.Costo * self.S2

    def inversion_t3(self):
        return self.Costo * self.S3

    def inversion_almacen(self):
        return self.Costo * self.Almacen

    def ganancia(self):
        """Ingresos esperados si se venden todas las unidades al precio establecido"""
        return self.Precio * self.total()

    # ================== Código de barras ==================

    def generar_codigo(self):
        """Genera un código único basado en ID o combinación de atributos"""
        # Ejemplo: Marca + Modelo + Color + Talla → acortado
        base = f"{self.Marca[:3]}{self.Modelo[:3]}{self.Color[:2]}{self.Talla}".upper()
        return base.replace(" ", "")

    def generar_codigo_barras(self):
        """Genera la imagen del código de barras y la guarda en el campo"""
        EAN = barcode.get_barcode_class("code128")
        ean = EAN(self.Codigo, writer=ImageWriter())
        buffer = BytesIO()
        ean.write(buffer)
        filename = f"{self.Codigo}.png"
        self.codigo_barras.save(filename, ContentFile(buffer.getvalue()), save=False)

    def save(self, *args, **kwargs):
        # Generar código si no existe
        if not self.Codigo:
            self.Codigo = self.generar_codigo()

        # Generar código de barras antes de guardar
        self.generar_codigo_barras()

        super().save(*args, **kwargs)




from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.conf import settings

class Ventas(models.Model):
    numero = models.CharField(max_length=20, unique=True, default=generar_numero_venta)
    METODOS_PAGO = [
        ("efectivo", "Efectivo"),
        ("yape", "Yape"),
        ("visa", "Visa"),
        ("mixto", "Mixto"),
    ]
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("completada", "Completada"),
        ("anulada", "Anulada"),
    ]

    fecha = models.DateTimeField(default=timezone.now)
    sucursal = models.CharField(max_length=2, choices=[("S1","Sucursal 1"),("S2","Sucursal 2"),("S3","Sucursal 3"),("A","Almacén")])
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vendedor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")  # <- nuevo

    def __str__(self):
        return f"Venta {self.numero} - {self.sucursal} - {self.estado} - {self.fecha.strftime('%d/%m/%Y')} - {self.vendedor}"


class DetalleVentas(models.Model):
    venta = models.ForeignKey(Ventas, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Productos, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)



class PagoVenta(models.Model):
    venta = models.ForeignKey(Ventas, on_delete=models.CASCADE, related_name="pagos")
    metodo = models.CharField(max_length=20, choices=Ventas.METODOS_PAGO)
    monto = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.metodo} - {self.monto}"
    

class Traspaso(models.Model):
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("entregado", "Entregado"),
        ("cancelado", "Cancelado"),
    ]

    producto = models.ForeignKey(Productos, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    sucursal_origen = models.CharField(max_length=2, choices=[("S1","Sucursal 1"),("S2","Sucursal 2"),("S3","Sucursal 3"),("A","Almacén")])
    sucursal_destino = models.CharField(max_length=2, choices=[("S1","Sucursal 1"),("S2","Sucursal 2"),("S3","Sucursal 3"),("A","Almacén")])
    solicitado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="traspasos_solicitados")
    entregado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="traspasos_entregados")
    fecha_solicitud = models.DateTimeField(default=timezone.now)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="pendiente")

    def __str__(self):
        return f"{self.producto} | {self.sucursal_origen} → {self.sucursal_destino} | {self.cantidad}"

class ReporteMensual(models.Model):
    mes = models.IntegerField()
    anio = models.IntegerField()

    ventas_s1 = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ventas_s2 = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ventas_s3 = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ventas_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    ganancia_s1 = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ganancia_s2 = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ganancia_s3 = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ganancia_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("mes", "anio")  # evita duplicados
        ordering = ["-anio", "-mes"]

    def __str__(self):
        return f"Reporte {self.mes}/{self.anio}"

class CompraProveedor(models.Model):
    proveedor = models.ForeignKey('Proveedor', on_delete=models.CASCADE)
    fecha = models.DateField()
    producto = models.CharField(max_length=200)  # opcional, si quieres detalle
    cantidad = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def costo_total(self):
        return self.cantidad * self.costo_unitario

    def __str__(self):
        return f"{self.proveedor.nombre_empresa} - {self.fecha}"
    
from django.db import models

class Compra(models.Model):
    proveedor = models.ForeignKey('Proveedor', on_delete=models.CASCADE, related_name='compras')
    descripcion = models.TextField(help_text="Detalle de los productos comprados")
    fecha = models.DateField(auto_now_add=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monto total de la compra")

    def __str__(self):
        return f"Compra a {self.proveedor.nombre_empresa} - {self.fecha} - S/. {self.monto}"

from django.db import models

class Cliente(models.Model):
    # El ID se crea automáticamente en Django como primary key
    nombres = models.CharField(max_length=150)
    celular = models.CharField(max_length=20)
    fecha_registro = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombres} - {self.celular}"



def generar_numero_cambio():
    ultimo = NotaCambio.objects.all().order_by("id").last()
    if not ultimo:
        return "NC0001"
    numero = int(ultimo.numero.replace("NC", "")) + 1
    return f"NC{numero:04d}"


class NotaCambio(models.Model):
    numero = models.CharField(max_length=20, unique=True, default=generar_numero_cambio)
    venta_origen = models.ForeignKey("Ventas", on_delete=models.CASCADE, related_name="notas_cambio")
    fecha = models.DateTimeField(default=timezone.now)
    vendedor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sucursal = models.CharField(
        max_length=2,
        choices=[("S1", "Sucursal 1"), ("S2", "Sucursal 2"), ("S3", "Sucursal 3"), ("A", "Almacén")]
    )
    diferencia = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # monto adicional a pagar o devolver

    def __str__(self):
        return f"Nota de Cambio {self.numero} - {self.venta_origen.numero}"

class DetalleNotaCambio(models.Model):
    nota_cambio = models.ForeignKey(NotaCambio, on_delete=models.CASCADE, related_name="detalles")
    producto_devuelto = models.ForeignKey(
        "Productos",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cambios_devueltos"
    )
    producto_entregado = models.ForeignKey(
        "Productos",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cambios_entregados"
    )
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Cambio: {self.cantidad} x {self.producto_devuelto} → {self.producto_entregado}"