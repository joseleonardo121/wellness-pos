from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Sum, F, DecimalField, ExpressionWrapper

from .models import Productos
from .forms import ProductoForm
from django.utils import timezone

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
import io
import barcode
from barcode.writer import ImageWriter
from PIL import Image
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import formset_factory
from django.contrib import messages
from django.db import transaction
from .forms import VentaForm, DetalleVentaForm, PagoForm
from .models import Ventas, DetalleVentas,Productos,CompraProveedor
import json
from django.shortcuts import render, redirect
from django.utils import timezone
from .models import Ventas, DetalleVentas, PagoVenta, Productos

from decimal import Decimal

from django.http import JsonResponse
from .models import Productos


from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from .models import Productos

from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Count
from django.utils.timezone import now

from .models import Productos, Ventas, DetalleVentas

from django.utils.timezone import now
import calendar

from .models import Productos, Ventas, DetalleVentas,ReporteMensual

from calendar import month_name


def generar_reporte_mensual(request):
    hoy = now()
    mes = hoy.month
    anio = hoy.year

    # ---------------------------
    # Ventas por sucursal
    # ---------------------------
    ventas_s1 = Ventas.objects.filter(sucursal="S1", fecha__month=mes, fecha__year=anio).aggregate(total=Sum("total"))["total"] or 0
    ventas_s2 = Ventas.objects.filter(sucursal="S2", fecha__month=mes, fecha__year=anio).aggregate(total=Sum("total"))["total"] or 0
    ventas_s3 = Ventas.objects.filter(sucursal="S3", fecha__month=mes, fecha__year=anio).aggregate(total=Sum("total"))["total"] or 0
    ventas_total = ventas_s1 + ventas_s2 + ventas_s3

    # ---------------------------
    # Ganancias reales (precio - costo) * cantidad
    # ---------------------------
    def calcular_ganancia(sucursal):
        return (
            DetalleVentas.objects.filter(venta__sucursal=sucursal, venta__fecha__month=mes, venta__fecha__year=anio)
            .aggregate(
                total=Sum(
                    ExpressionWrapper(
                        (F("producto__Precio") - F("producto__Costo")) * F("cantidad"),
                        output_field=DecimalField(max_digits=15, decimal_places=2),
                    )
                )
            )["total"]
            or 0
        )

    ganancia_s1 = calcular_ganancia("S1")
    ganancia_s2 = calcular_ganancia("S2")
    ganancia_s3 = calcular_ganancia("S3")
    ganancia_total = ganancia_s1 + ganancia_s2 + ganancia_s3

    # ---------------------------
    # Guardar o actualizar en la base de datos
    # ---------------------------
    reporte, creado = ReporteMensual.objects.update_or_create(
        mes=mes,
        anio=anio,
        defaults={
            "ventas_s1": ventas_s1,
            "ventas_s2": ventas_s2,
            "ventas_s3": ventas_s3,
            "ventas_total": ventas_total,
            "ganancia_s1": ganancia_s1,
            "ganancia_s2": ganancia_s2,
            "ganancia_s3": ganancia_s3,
            "ganancia_total": ganancia_total,
        },
    )

    return redirect("reportes_historicos")


# ---------------------------
# Vista para mostrar los reportes históricos
# ---------------------------
def reportes_historicos(request):
    # Capturar parámetros de búsqueda
    anio = request.GET.get("anio")
    mes = request.GET.get("mes")

    reportes = ReporteMensual.objects.all().order_by("-anio", "-mes")

    if anio:
        reportes = reportes.filter(anio=anio)
    if mes:
        reportes = reportes.filter(mes=mes)

    return render(request, "reportes_historicos.html", {
        "reportes": reportes,
        "anio_filtro": anio,
        "mes_filtro": mes,
    })

def exportar_reportes_pdf(request):
    hoy = now()

    # ---------------------------
    # Inversiones
    # ---------------------------
    inversion_total = Productos.objects.aggregate(
        total=Sum(F("Costo") * (F("S1") + F("S2") + F("S3") + F("Almacen")))
    )["total"] or 0

    inversion_s1 = Productos.objects.aggregate(total=Sum(F("Costo") * F("S1")))["total"] or 0
    inversion_s2 = Productos.objects.aggregate(total=Sum(F("Costo") * F("S2")))["total"] or 0
    inversion_s3 = Productos.objects.aggregate(total=Sum(F("Costo") * F("S3")))["total"] or 0
    inversion_almacen = Productos.objects.aggregate(total=Sum(F("Costo") * F("Almacen")))["total"] or 0

    # ---------------------------
    # Ventas
    # ---------------------------
    ventas_s1 = Ventas.objects.filter(sucursal="S1", fecha__month=hoy.month, fecha__year=hoy.year).aggregate(total=Sum("total"))["total"] or 0
    ventas_s2 = Ventas.objects.filter(sucursal="S2", fecha__month=hoy.month, fecha__year=hoy.year).aggregate(total=Sum("total"))["total"] or 0
    ventas_s3 = Ventas.objects.filter(sucursal="S3", fecha__month=hoy.month, fecha__year=hoy.year).aggregate(total=Sum("total"))["total"] or 0

    # ---------------------------
    # Ganancias
    # ---------------------------
    def calcular_ganancia(sucursal):
        return (
            DetalleVentas.objects.filter(venta__sucursal=sucursal, venta__fecha__month=hoy.month, venta__fecha__year=hoy.year)
            .aggregate(
                total=Sum(
                    ExpressionWrapper(
                        (F("producto__Precio") - F("producto__Costo")) * F("cantidad"),
                        output_field=DecimalField(max_digits=15, decimal_places=2),
                    )
                )
            )["total"]
            or 0
        )

    ganancia_s1 = calcular_ganancia("S1")
    ganancia_s2 = calcular_ganancia("S2")
    ganancia_s3 = calcular_ganancia("S3")
    ganancia_total = ganancia_s1 + ganancia_s2 + ganancia_s3

    # ---------------------------
    # Crear PDF
    # ---------------------------
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="reporte.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("📊 Reporte de Inventario y Ventas", styles["Title"]))
    elementos.append(Spacer(1, 12))

    # Tabla de inversiones
    data_inversiones = [
        ["Ubicación", "Inversión (S/.)"],
        ["Total", f"{inversion_total:.2f}"],
        ["Sucursal 1", f"{inversion_s1:.2f}"],
        ["Sucursal 2", f"{inversion_s2:.2f}"],
        ["Sucursal 3", f"{inversion_s3:.2f}"],
        ["Almacén", f"{inversion_almacen:.2f}"],
    ]
    tabla_inversiones = Table(data_inversiones, hAlign="LEFT")
    tabla_inversiones.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightblue), ("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    elementos.append(Paragraph("💰 Inversiones Generales", styles["Heading2"]))
    elementos.append(tabla_inversiones)
    elementos.append(Spacer(1, 12))

    # Tabla de ventas
    data_ventas = [
        ["Sucursal", "Ventas (S/.)", "Ganancia (S/.)"],
        ["Sucursal 1", f"{ventas_s1:.2f}", f"{ganancia_s1:.2f}"],
        ["Sucursal 2", f"{ventas_s2:.2f}", f"{ganancia_s2:.2f}"],
        ["Sucursal 3", f"{ventas_s3:.2f}", f"{ganancia_s3:.2f}"],
        ["TOTAL", f"{(ventas_s1+ventas_s2+ventas_s3):.2f}", f"{ganancia_total:.2f}"],
    ]
    tabla_ventas = Table(data_ventas, hAlign="LEFT")
    tabla_ventas.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgreen), ("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    elementos.append(Paragraph("🛒 Ventas y Ganancias del Mes", styles["Heading2"]))
    elementos.append(tabla_ventas)

    doc.build(elementos)
    return response


@login_required
def buscar_producto(request):
    """
    Busca un producto por Código exacto o Diseño parcial.
    Devuelve JSON con 'success' y 'producto' si se encuentra,
    o 'success': False y 'error' si no.
    """
    codigo = request.GET.get("codigo", "").strip()
    if not codigo:
        return JsonResponse({"success": False, "error": "Ingrese un código para buscar."})

    producto = Productos.objects.filter(
        Q(Codigo__iexact=codigo) | Q(Diseno__icontains=codigo)
    ).first()

    if producto:
        data = {
            "codigo": producto.Codigo,
            "marca": producto.Marca,
            "modelo": producto.Modelo,
            "diseno": producto.Diseno,
            "color": producto.Color,
            "talla": producto.Talla,
            "precio": float(producto.Precio),
        }
        return JsonResponse({"success": True, "producto": data})
    else:
        return JsonResponse({"success": False, "error": "Producto no encontrado."})
    

def api_producto(request):
    """
    GET /inventory/api/producto/?codigo=...
    Devuelve JSON con las claves que usa el front.
    """
    codigo = request.GET.get("codigo", "").strip()
    if not codigo:
        return JsonResponse({"error": "Falta parámetro 'codigo'."}, status=400)

    producto = Productos.objects.filter(
        Q(Codigo__iexact=codigo) | Q(Diseno__icontains=codigo)
    ).first()

    if not producto:
        return JsonResponse({"error": "Producto no encontrado"}, status=404)

    data = {
        "Codigo": producto.Codigo,
        "Marca": producto.Marca,
        "Modelo": producto.Modelo,
        "Diseno": producto.Diseno,
        "Color": producto.Color,
        "Talla": producto.Talla,
        "Precio": float(producto.Precio),
        "stock_total": producto.total(),   # usa el método total()
        "S1": producto.S1,
        "S2": producto.S2,
        "S3": producto.S3,
        "Almacen": producto.Almacen,
    }
    return JsonResponse(data)

DetalleFormSet = formset_factory(DetalleVentaForm, extra=5, min_num=1, validate_min=True)
PagoFormSet = formset_factory(PagoForm, extra=3, min_num=1, validate_min=True)

def crear_venta(request):
    """
    Recibe POST JSON desde crear_venta.html
    Body: { metodo_pago, sucursal, productos: [{Codigo, cantidad, precio_unitario, subtotal}, ...] }
    """
    if request.method == "GET":
        return render(request, "inventory/crear_venta.html")

    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    metodo_pago = data.get("metodo_pago")
    sucursal = data.get("sucursal")
    productos = data.get("productos", [])

    if not productos:
        return JsonResponse({"error": "No se recibieron productos"}, status=400)

    # validar estructura de productos
    for p in productos:
        if not all(k in p for k in ("Codigo", "cantidad", "precio_unitario", "subtotal")):
            return JsonResponse({"error": "Formato de producto inválido"}, status=400)

    total_calculado = sum(p["subtotal"] for p in productos)

    try:
        with transaction.atomic():
            venta = Ventas.objects.create(
                fecha=timezone.now(),
                metodo_pago=metodo_pago,
                sucursal=sucursal,
                total=total_calculado,
                vendedor=request.user if request.user.is_authenticated else None,
                estado="pendiente"
            )

            # validar stocks primero (no descontar parcialmente)
            for p in productos:
                producto = Productos.objects.select_for_update().get(Codigo=p["Codigo"])
                qty = int(p["cantidad"])
                if sucursal == "S1" and producto.S1 < qty:
                    raise ValueError(f"Stock insuficiente en S1 para {producto.Codigo}")
                if sucursal == "S2" and producto.S2 < qty:
                    raise ValueError(f"Stock insuficiente en S2 para {producto.Codigo}")
                if sucursal == "S3" and producto.S3 < qty:
                    raise ValueError(f"Stock insuficiente en S3 para {producto.Codigo}")
                if sucursal == "A" and producto.Almacen < qty:
                    raise ValueError(f"Stock insuficiente en Almacén para {producto.Codigo}")

            # si pasaron las validaciones, descontar stock y crear detalles
            for p in productos:
                producto = Productos.objects.select_for_update().get(Codigo=p["Codigo"])
                qty = int(p["cantidad"])

                if sucursal == "S1":
                    producto.S1 -= qty
                elif sucursal == "S2":
                    producto.S2 -= qty
                elif sucursal == "S3":
                    producto.S3 -= qty
                elif sucursal == "A":
                    producto.Almacen -= qty

                producto.save()

                DetalleVentas.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=qty,
                    precio_unitario=p["precio_unitario"],
                    subtotal=p["subtotal"]
                )

            # finalmente marcar completada
            venta.estado = "completada"
            venta.save()

    except Productos.DoesNotExist:
        return JsonResponse({"error": "Algún producto no existe"}, status=404)
    except ValueError as ve:
        return JsonResponse({"error": str(ve)}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Error interno: {str(e)}"}, status=500)

    return JsonResponse({"success": True, "venta_id": venta.id})

from django.db.models import Q
from datetime import datetime
from django.utils.timezone import localdate

def historial_ventas(request):
    fecha_str = request.GET.get("fecha")
    numero_str = request.GET.get("numero")  # 🔹 Capturamos el número de boleta
    ventas = Ventas.objects.filter(estado="completada").select_related("vendedor").prefetch_related("detalles__producto")

    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            ventas = ventas.filter(fecha__date=fecha)
        except ValueError:
            pass

    if numero_str:
        ventas = ventas.filter(numero__icontains=numero_str)  # 🔹 Filtrado por número de boleta (parcial o completo)

    if not fecha_str and not numero_str:
        # si no hay filtros, mostrar solo del día actual
        ventas = ventas.filter(fecha__date=localdate())

    resumen_sucursales = ventas.values("sucursal").annotate(total_sucursal=Sum("total")).order_by("sucursal")
    total_general = ventas.aggregate(total=Sum("total"))["total"] or 0

    context = {
        "ventas": ventas.order_by("-fecha"),
        "fecha_filtro": fecha_str,
        "numero_filtro": numero_str,
        "resumen_sucursales": resumen_sucursales,
        "total_general": total_general,
    }

    if request.user.is_staff or request.user.is_superuser:
        resumen_diario = (
            Ventas.objects.filter(estado="completada")
            .values("fecha__date", "sucursal")
            .annotate(total_dia=Sum("total"))
            .order_by("-fecha__date")
        )
        resumen_mensual = (
            Ventas.objects.filter(estado="completada")
            .extra(select={"fecha_mes": "strftime('%%Y-%%m', fecha)"})
            .values("fecha_mes", "sucursal")
            .annotate(total_mes=Sum("total"))
            .order_by("-fecha_mes")
        )
        resumen_anual = (
            Ventas.objects.filter(estado="completada")
            .extra(select={"fecha_anio": "strftime('%%Y', fecha)"})
            .values("fecha_anio", "sucursal")
            .annotate(total_anio=Sum("total"))
            .order_by("-fecha_anio")
        )
        context.update({
            "resumen_diario": resumen_diario,
            "resumen_mensual": resumen_mensual,
            "resumen_anual": resumen_anual,
        })
    else:
        hoy = localdate()
        total_hoy = (
            Ventas.objects.filter(
                vendedor=request.user,
                fecha__date=hoy,
                estado="completada"
            ).aggregate(total_dia=Sum("total"))["total_dia"] or 0
        )
        context["total_hoy"] = total_hoy
        context["fecha_hoy"] = hoy

    return render(request, "historial_ventas.html", context)

def detalle_venta(request, pk):
    venta = get_object_or_404(Ventas, pk=pk)
    detalles = venta.detalles.select_related("producto").all()
    pagos = venta.pagos.all()
    return render(request, "inventory/detalle_venta.html", {
        "venta": venta,
        "detalles": detalles,
        "pagos": pagos,
    })

def lista_ventas(request):
    ventas = Ventas.objects.all().order_by("-fecha")
    return render(request, "inventory/lista_ventas.html", {"ventas": ventas})




def home(request):
    if request.user.is_authenticated:
        return redirect("lista_productos")  # usuario logueado → productos
    else:
        return redirect("login")  # usuario NO logueado → login

@login_required
def crear_producto(request):
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("lista_productos")
    else:
        form = ProductoForm()

    return render(request, "inventory/crear_producto.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("lista_productos")
    else:
        form = AuthenticationForm()
    return render(request, "inventory/login.html", {"form": form})

@login_required
def logout_view(request):
    logout(request)
    return redirect("login")

from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from .models import Productos
from .forms import ProductoForm

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from .models import Productos


from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from .models import Productos


@login_required
def lista_productos(request):
    query = request.GET.get("q", "").strip()

    # 🧭 Filtros manuales
    marca_filtro = request.GET.get("marca", "")
    modelo_filtro = request.GET.get("modelo", "")
    diseno_filtro = request.GET.get("diseno", "")
    color_filtro = request.GET.get("color", "")
    talla_filtro = request.GET.get("talla", "")

    productos = Productos.objects.all()

    # 🔍 Filtro del buscador general
    if query:
        productos = productos.filter(
            Q(Marca__icontains=query) |
            Q(Modelo__icontains=query) |
            Q(Diseno__icontains=query) |
            Q(Color__icontains=query) |
            Q(Talla__icontains=query) |
            Q(Codigo__icontains=query)
        )

    # 🧩 Filtros manuales adicionales
    if marca_filtro:
        productos = productos.filter(Marca__iexact=marca_filtro)
    if modelo_filtro:
        productos = productos.filter(Modelo__iexact=modelo_filtro)
    if diseno_filtro:
        productos = productos.filter(Diseno__iexact=diseno_filtro)
    if color_filtro:
        productos = productos.filter(Color__iexact=color_filtro)
    if talla_filtro:
        productos = productos.filter(Talla__iexact=talla_filtro)

    # 📦 Obtener valores únicos para los selects
    marcas = Productos.objects.values_list("Marca", flat=True).distinct().order_by("Marca")
    modelos = Productos.objects.values_list("Modelo", flat=True).distinct().order_by("Modelo")
    disenos = Productos.objects.values_list("Diseno", flat=True).distinct().order_by("Diseno")
    colores = Productos.objects.values_list("Color", flat=True).distinct().order_by("Color")
    tallas = Productos.objects.values_list("Talla", flat=True).distinct().order_by("Talla")

    context = {
        "productos": productos,
        "query": query,
        "marca_filtro": marca_filtro,
        "modelo_filtro": modelo_filtro,
        "diseno_filtro": diseno_filtro,
        "color_filtro": color_filtro,
        "talla_filtro": talla_filtro,
        "marcas": marcas,
        "modelos": modelos,
        "disenos": disenos,
        "colores": colores,
        "tallas": tallas,
    }

    return render(request, "inventory/lista_productos.html", context)

@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(Productos, pk=pk)
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect("lista_productos")
    else:
        form = ProductoForm(instance=producto)
    return render(request, "inventory/crear_producto.html", {"form": form})

@login_required
def eliminar_producto(request, pk):
    producto = get_object_or_404(Productos, pk=pk)
    if request.method == "POST":
        producto.delete()
        return redirect("lista_productos")
    return render(request, "inventory/eliminar_producto.html", {"producto": producto})

from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from .models import Productos, Ventas, DetalleVentas
from django.utils.timezone import now

from django.shortcuts import render
from django.utils.timezone import now
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Count
from .models import Productos, Ventas, DetalleVentas


def reportes(request):
    hoy = now()

    # ---------------------------
    # Inversiones por ubicación
    # ---------------------------
    inversion_total = Productos.objects.aggregate(
        total=Sum(F("Costo") * (F("S1") + F("S2") + F("S3") + F("Almacen")))
    )["total"] or 0

    inversion_s1 = Productos.objects.aggregate(
        total=Sum(F("Costo") * F("S1"))
    )["total"] or 0

    inversion_s2 = Productos.objects.aggregate(
        total=Sum(F("Costo") * F("S2"))
    )["total"] or 0

    inversion_s3 = Productos.objects.aggregate(
        total=Sum(F("Costo") * F("S3"))
    )["total"] or 0

    inversion_almacen = Productos.objects.aggregate(
        total=Sum(F("Costo") * F("Almacen"))
    )["total"] or 0

    # ---------------------------
    # Ventas del mes (totales y productos vendidos)
    # ---------------------------
    ventas_s1 = Ventas.objects.filter(sucursal="S1", fecha__month=hoy.month, fecha__year=hoy.year).aggregate(total=Sum("total"))["total"] or 0
    ventas_s2 = Ventas.objects.filter(sucursal="S2", fecha__month=hoy.month, fecha__year=hoy.year).aggregate(total=Sum("total"))["total"] or 0
    ventas_s3 = Ventas.objects.filter(sucursal="S3", fecha__month=hoy.month, fecha__year=hoy.year).aggregate(total=Sum("total"))["total"] or 0

    productos_vendidos_s1 = DetalleVentas.objects.filter(venta__sucursal="S1", venta__fecha__month=hoy.month, venta__fecha__year=hoy.year).aggregate(total=Sum("cantidad"))["total"] or 0
    productos_vendidos_s2 = DetalleVentas.objects.filter(venta__sucursal="S2", venta__fecha__month=hoy.month, venta__fecha__year=hoy.year).aggregate(total=Sum("cantidad"))["total"] or 0
    productos_vendidos_s3 = DetalleVentas.objects.filter(venta__sucursal="S3", venta__fecha__month=hoy.month, venta__fecha__year=hoy.year).aggregate(total=Sum("cantidad"))["total"] or 0

    # ---------------------------
    # Ganancias reales (precio - costo) * cantidad
    # ---------------------------
    def calcular_ganancia(sucursal):
        return (
            DetalleVentas.objects.filter(venta__sucursal=sucursal, venta__fecha__month=hoy.month, venta__fecha__year=hoy.year)
            .aggregate(
                total=Sum(
                    ExpressionWrapper(
                        (F("producto__Precio") - F("producto__Costo")) * F("cantidad"),
                        output_field=DecimalField(max_digits=15, decimal_places=2),
                    )
                )
            )["total"]
            or 0
        )

    ganancia_s1 = calcular_ganancia("S1")
    ganancia_s2 = calcular_ganancia("S2")
    ganancia_s3 = calcular_ganancia("S3")
    ganancia_total = ganancia_s1 + ganancia_s2 + ganancia_s3

    # ---------------------------
    # Boletas por mes
    # ---------------------------
    boletas_por_mes = (
        Ventas.objects.extra(select={"mes": "strftime('%%Y-%%m', fecha)"})
        .values("mes")
        .annotate(cantidad_boletas=Count("id"))
        .order_by("mes")
    )

    # ---------------------------
    # Boletas del mes por sucursal
    # ---------------------------
    boletas_s1 = Ventas.objects.filter(sucursal="S1", fecha__month=hoy.month, fecha__year=hoy.year).count()
    boletas_s2 = Ventas.objects.filter(sucursal="S2", fecha__month=hoy.month, fecha__year=hoy.year).count()
    boletas_s3 = Ventas.objects.filter(sucursal="S3", fecha__month=hoy.month, fecha__year=hoy.year).count()
    boletas_almacen = Ventas.objects.filter(sucursal="A", fecha__month=hoy.month, fecha__year=hoy.year).count()
    boletas_total = boletas_s1 + boletas_s2 + boletas_s3 + boletas_almacen

        # Al final de la función reportes antes de return render(...)
    request.context_inversion = {
        "s1": inversion_s1,
        "s2": inversion_s2,
        "s3": inversion_s3,
        "almacen": inversion_almacen,
        "total": inversion_total,
    }

    request.context_ventas = {
        "s1": ventas_s1,
        "s2": ventas_s2,
        "s3": ventas_s3,
        "total": ventas_s1 + ventas_s2 + ventas_s3,
        "prod_s1": productos_vendidos_s1,
        "prod_s2": productos_vendidos_s2,
        "prod_s3": productos_vendidos_s3,
        "prod_total": productos_vendidos_s1 + productos_vendidos_s2 + productos_vendidos_s3,
        "gan_s1": ganancia_s1,
        "gan_s2": ganancia_s2,
        "gan_s3": ganancia_s3,
        "gan_total": ganancia_total,
    }

    request.context_boletas = {
        "s1": boletas_s1,
        "s2": boletas_s2,
        "s3": boletas_s3,
        "almacen": boletas_almacen,
        "total": boletas_total,
    }


    return render(request, "reportes.html", {
        "now": hoy,
        "inversion_total": inversion_total,
        "inversion_s1": inversion_s1,
        "inversion_s2": inversion_s2,
        "inversion_s3": inversion_s3,
        "inversion_almacen": inversion_almacen,

        "ventas_s1": ventas_s1,
        "ventas_s2": ventas_s2,
        "ventas_s3": ventas_s3,

        "productos_vendidos_s1": productos_vendidos_s1,
        "productos_vendidos_s2": productos_vendidos_s2,
        "productos_vendidos_s3": productos_vendidos_s3,

        "ganancia_s1": ganancia_s1,
        "ganancia_s2": ganancia_s2,
        "ganancia_s3": ganancia_s3,
        "ganancia_total": ganancia_total,

        "boletas_por_mes": boletas_por_mes,

        "boletas_s1": boletas_s1,
        "boletas_s2": boletas_s2,
        "boletas_s3": boletas_s3,
        "boletas_almacen": boletas_almacen,
        "boletas_total": boletas_total,
    })

from django.shortcuts import render, redirect
from .models import Productos, Traspaso
from django.contrib.auth.decorators import login_required
from django.utils import timezone

@login_required
def crear_traspaso(request):
    if request.method == "POST":
        codigo_producto = request.POST.get("producto_id")  # este viene del <select>
        cantidad = int(request.POST.get("cantidad"))
        sucursal_origen = request.POST.get("sucursal_origen")
        sucursal_destino = request.POST.get("sucursal_destino")

        # Buscar producto por Código
        producto = get_object_or_404(Productos, Codigo=codigo_producto)

        # Crear el traspaso
        traspaso = Traspaso.objects.create(
            producto=producto,
            cantidad=cantidad,
            sucursal_origen=sucursal_origen,
            sucursal_destino=sucursal_destino,
            solicitado_por=request.user
        )

        # 🔹 Si la petición viene de AJAX, devolvemos JSON
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "traspaso_id": traspaso.id,
                "producto": {
                    "Codigo": producto.Codigo,
                    "Marca": producto.Marca,
                    "Modelo": producto.Modelo,
                    "Diseno": producto.Diseno,
                    "Color": producto.Color,
                    "Talla": producto.Talla
                },
                "cantidad": cantidad,
                "sucursal_origen": sucursal_origen,
                "sucursal_destino": sucursal_destino
            })

        # Si es formulario normal
        messages.success(request, "✅ Traspaso creado correctamente (pendiente de aprobación).")
        return redirect("lista_traspasos")

    productos = Productos.objects.all()
    return render(request, "inventory/nuevo_traspaso.html", {"productos": productos})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Traspaso, Productos

@login_required
def lista_traspasos(request):
    traspasos = Traspaso.objects.all().order_by("-fecha_solicitud")
    return render(request, "inventory/lista_traspasos.html", {"traspasos": traspasos})


@login_required
def aprobar_traspaso(request, traspaso_id):
    traspaso = get_object_or_404(Traspaso, id=traspaso_id)

    # 🔹 Mapeo sucursal → campo en el modelo
    sucursal_field_map = {
        "S1": "S1",
        "S2": "S2",
        "S3": "S3",
        "A": "Almacen",
    }

    campo_origen = sucursal_field_map[traspaso.sucursal_origen]
    campo_destino = sucursal_field_map[traspaso.sucursal_destino]

    producto = traspaso.producto
    cantidad = traspaso.cantidad

    # Verificar stock en origen
    if getattr(producto, campo_origen) < cantidad:
        messages.error(request, f"❌ Stock insuficiente en {traspaso.sucursal_origen}.")
        return redirect("lista_traspasos")

    # 🔹 Descontar de origen y sumar en destino
    setattr(producto, campo_origen, getattr(producto, campo_origen) - cantidad)
    setattr(producto, campo_destino, getattr(producto, campo_destino) + cantidad)

    producto.save()

    # Cambiar estado del traspaso
    traspaso.estado = "entregado"   # <-- Usa el mismo formato definido en el modelo
    traspaso.entregado_por = request.user
    traspaso.fecha_entrega = timezone.now()
    traspaso.save()

    messages.success(request, f"✅ Traspaso #{traspaso.id} aprobado con éxito.")
    return redirect("lista_traspasos")

def rechazar_traspaso(request, traspaso_id):
    traspaso = get_object_or_404(Traspaso, id=traspaso_id)

    if traspaso.estado != "pendiente":
        messages.warning(request, "Este traspaso ya fue procesado.")
        return redirect("lista_traspasos")

    traspaso.estado = "rechazado"
    traspaso.entregado_por = request.user
    traspaso.fecha_entrega = timezone.now()
    traspaso.save()

    messages.info(request, "El traspaso fue rechazado.")
    return redirect("lista_traspasos")


from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Productos

@login_required
@csrf_exempt
def productos_a_bajar(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            codigo = data.get("codigo")
            sucursal_destino = data.get("sucursal")
            cantidad = int(data.get("cantidad", 1))

            producto = Productos.objects.get(Codigo=codigo)

            if producto.Almacen < cantidad:
                return JsonResponse({"error": "Stock insuficiente en Almacén"})

            # Mapeo de sucursal al campo del modelo
            sucursal_field_map = {"S1": "S1", "S2": "S2", "S3": "S3", "A": "Almacen"}
            campo_destino = sucursal_field_map[sucursal_destino]

            # Restar del almacén y sumar a la sucursal
            producto.Almacen -= cantidad
            setattr(producto, campo_destino, getattr(producto, campo_destino) + cantidad)
            producto.save()

            return JsonResponse({"success": True})
        except Productos.DoesNotExist:
            return JsonResponse({"error": "Producto no encontrado"})
        except Exception as e:
            return JsonResponse({"error": str(e)})

    # GET → generar la lista de productos a bajar
    productos = Productos.objects.all()
    lista_bajar = []

    for producto in productos:
        if producto.S1 < 1 and producto.Almacen > 0:
            lista_bajar.append({
                "Codigo": producto.Codigo,
                "Marca": producto.Marca,
                "Modelo": producto.Modelo,
                "Diseno": producto.Diseno,
                "Talla": producto.Talla,
                "Color": producto.Color,
                "Sucursal": "S1",
                "Stock_Sucursal": producto.S1,
                "Stock_Almacen": producto.Almacen,
            })
        if producto.S2 < 1 and producto.Almacen > 0:
            lista_bajar.append({
                "Codigo": producto.Codigo,
                "Marca": producto.Marca,
                "Modelo": producto.Modelo,
                "Diseno": producto.Diseno,
                "Talla": producto.Talla,
                "Color": producto.Color,
                "Sucursal": "S2",
                "Stock_Sucursal": producto.S2,
                "Stock_Almacen": producto.Almacen,
            })

    return render(request, "inventory/productos_a_bajar.html", {"productos": lista_bajar})

from django.shortcuts import render
from .models import Productos

@login_required
def productos_a_pedir(request):
    productos = Productos.objects.all()

    urgentes = [p for p in productos if  p.CANT_TOTAL == 0 ]
    sugeridos = [p for p in productos if p.CANT_TOTAL == 2 or p.CANT_TOTAL == 1 ]
    normales = [p for p in productos if 3 <= p.CANT_TOTAL <= 5]
    excelentes = [p for p in productos if p.CANT_TOTAL > 5]

    context = {
        "urgentes": urgentes,
        "sugeridos": sugeridos,
        "normales": normales,
        "excelentes": excelentes,
    }
    return render(request, "inventory/productos_a_pedir.html", context)


from django.shortcuts import render, redirect, get_object_or_404
from .models import Proveedor
from .forms import ProveedorForm

# 📋 Listar proveedores
def listar_proveedores(request):
    proveedores = Proveedor.objects.all().order_by('-fecha_registro')
    return render(request, 'proveedores/listar.html', {'proveedores': proveedores})

# ➕ Crear proveedor
def crear_proveedor(request):
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_proveedores')
    else:
        form = ProveedorForm()
    return render(request, 'proveedores/form.html', {'form': form, 'accion': 'Crear'})

# ✏️ Editar proveedor
def editar_proveedor(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            return redirect('listar_proveedores')
    else:
        form = ProveedorForm(instance=proveedor)
    return render(request, 'proveedores/form.html', {'form': form, 'accion': 'Editar'})

# 🗑️ Eliminar proveedor
def eliminar_proveedor(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    proveedor.delete()
    return redirect('listar_proveedores')





from django.shortcuts import render
from django.db.models import Sum, F, FloatField
from .models import Proveedor, Compra
from datetime import datetime

def reporte_inversion_mensual(request):
    # Tomar el mes y año de los filtros o usar mes actual
    mes = int(request.GET.get('mes', datetime.now().month))
    anio = int(request.GET.get('anio', datetime.now().year))

    # Filtrar compras del mes y año seleccionado
    compras_mes = Compra.objects.filter(fecha__year=anio, fecha__month=mes)

    # Agrupar por proveedor
    inversion_proveedores = []

    proveedores = Proveedor.objects.all()
    for proveedor in proveedores:
        compras_proveedor = compras_mes.filter(proveedor=proveedor)
        if compras_proveedor.exists():
            # Calcular total invertido
            total_invertido = compras_proveedor.aggregate(
                total=Sum('monto')
            )['total']

            # Lista de compras (solo descripción y monto)
            compras_detalle = []
            for compra in compras_proveedor:
                compras_detalle.append({
                    'descripcion': compra.descripcion,
                    'monto': compra.monto
                })

            inversion_proveedores.append({
                'proveedor__nombre_empresa': proveedor.nombre_empresa,
                'total_invertido': total_invertido,
                'compras': compras_detalle
            })

    context = {
        'mes': mes,
        'anio': anio,
        'inversion_proveedores': inversion_proveedores
    }
    return render(request, 'reporte_inversion.html', context)
from django.shortcuts import render, redirect, get_object_or_404
from .models import Compra, Proveedor
from .forms import CompraForm
from django.contrib import messages

def listar_compras(request):
    compras = Compra.objects.all().order_by('-fecha')
    return render(request, 'compras/listar_compras.html', {'compras': compras})

def crear_compra(request):
    if request.method == 'POST':
        form = CompraForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Compra registrada correctamente.")
            return redirect('listar_compras')
    else:
        form = CompraForm()
    return render(request, 'compras/crear_compra.html', {'form': form})

def editar_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    if request.method == 'POST':
        form = CompraForm(request.POST, instance=compra)
        if form.is_valid():
            form.save()
            messages.success(request, "Compra actualizada correctamente.")
            return redirect('listar_compras')
    else:
        form = CompraForm(instance=compra)
    return render(request, 'compras/crear_compra.html', {'form': form})

def eliminar_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    compra.delete()
    messages.success(request, "Compra eliminada correctamente.")
    return redirect('listar_compras')


from django.shortcuts import render, redirect, get_object_or_404
from .models import Cliente
from .forms import ClienteForm
from django.db.models import Q

# Listar clientes con búsqueda
def listar_clientes(request):
    query = request.GET.get('q', '')
    if query:
        clientes = Cliente.objects.filter(
            Q(nombres__icontains=query) | Q(celular__icontains=query)
        ).order_by('-fecha_registro')
    else:
        clientes = Cliente.objects.all().order_by('-fecha_registro')
    return render(request, 'clientes/listar_clientes.html', {'clientes': clientes, 'query': query})

# Crear cliente
def crear_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_clientes')
    else:
        form = ClienteForm()
    return render(request, 'clientes/crear_cliente.html', {'form': form})

# Editar cliente
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('listar_clientes')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'clientes/editar_cliente.html', {'form': form, 'cliente': cliente})

# Eliminar cliente
def eliminar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        return redirect('listar_clientes')
    return render(request, 'clientes/eliminar_cliente.html', {'cliente': cliente})


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Ventas, NotaCambio
from .forms import NotaCambioForm, DetalleNotaCambioFormSet

from django.db import transaction
from django.contrib import messages

from django.db import transaction

from django.db import transaction

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

@login_required
def crear_nota_cambio(request, venta_id):
    venta = get_object_or_404(Ventas, id=venta_id)

    SUCURSAL_FIELD_MAP = {
        "S1": "S1",
        "S2": "S2",
        "S3": "S3",
        "A": "Almacen",
    }

    if request.method == "POST":
        form = NotaCambioForm(request.POST)
        formset = DetalleNotaCambioFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    nota = form.save(commit=False)
                    nota.venta_origen = venta
                    nota.vendedor = request.user
                    nota.save()

                    sucursal_field = SUCURSAL_FIELD_MAP.get(nota.sucursal)
                    diferencia_total = 0
                    cambios_realizados = False

                    for detalle_form in formset:
                        if not detalle_form.cleaned_data:
                            continue

                        detalle = detalle_form.save(commit=False)
                        detalle.nota_cambio = nota

                        codigo_dev = request.POST.get(f"{detalle_form.prefix}-codigo_devuelto", "").strip()
                        codigo_ent = request.POST.get(f"{detalle_form.prefix}-codigo_entregado", "").strip()

                        if codigo_dev:
                            detalle.producto_devuelto = Productos.objects.filter(Codigo__iexact=codigo_dev).first()
                        if codigo_ent:
                            detalle.producto_entregado = Productos.objects.filter(Codigo__iexact=codigo_ent).first()

                        if not detalle.producto_devuelto or not detalle.producto_entregado:
                            continue

                        producto_ent = detalle.producto_entregado
                        producto_dev = detalle.producto_devuelto

                        # --- Validar stock ---
                        stock_actual = getattr(producto_ent, sucursal_field)
                        if stock_actual < detalle.cantidad:
                            raise ValueError(
                                f"No se puede realizar el cambio: stock insuficiente para {producto_ent.Diseno} ({producto_ent.Color})."
                            )

                        # --- Actualizar stock ---
                        setattr(producto_dev, sucursal_field, getattr(producto_dev, sucursal_field) + detalle.cantidad)
                        setattr(producto_ent, sucursal_field, getattr(producto_ent, sucursal_field) - detalle.cantidad)
                        producto_dev.save()
                        producto_ent.save()

                        diferencia_total += (producto_ent.Precio - producto_dev.Precio) * detalle.cantidad
                        detalle.save()
                        cambios_realizados = True

                    nota.diferencia = diferencia_total
                    nota.save()

                    if not cambios_realizados:
                        return JsonResponse({
                            "status": "warning",
                            "message": "❌ No se realizó ningún cambio válido."
                        })

                    return JsonResponse({
                        "status": "success",
                        "message": "✅ Nota de cambio registrada y stock actualizado correctamente."
                    })

            except ValueError as e:
                return JsonResponse({
                    "status": "error",
                    "message": f"❌ No se realizó el cambio: {str(e)}"
                })

            except Exception as e:
                return JsonResponse({
                    "status": "error",
                    "message": f"⚠️ Error inesperado: {str(e)}"
                })
        else:
            return JsonResponse({
                "status": "error",
                "message": "❌ Verifica los datos del formulario."
            })

    else:
        form = NotaCambioForm()
        formset = DetalleNotaCambioFormSet()

    return render(request, "nota_cambio_form.html", {
        "venta": venta,
        "form": form,
        "formset": formset,
    })


@login_required
def lista_notas_cambio(request):
    notas = NotaCambio.objects.all().select_related("venta_origen", "vendedor")
    return render(request, "notas_cambio/notas_cambio_list.html", {"notas": notas})

@login_required
def detalle_nota_cambio(request, pk):
    nota = get_object_or_404(NotaCambio, pk=pk)
    detalles = nota.detalles.all().select_related("producto_devuelto", "producto_entregado")
    return render(request, "notas_cambio/nota_cambio_detalle.html", {
        "nota": nota,
        "detalles": detalles,
    })


@login_required
def imprimir_venta(request, venta_id):
    venta = get_object_or_404(Ventas, pk=venta_id)
    detalles = venta.detalles.all().select_related("producto")
    pagos = venta.pagos.all()
    return render(request, "venta_imprimir.html", {
        "venta": venta,
        "detalles": detalles,
        "pagos": pagos,
    })

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Ventas, DetalleVentas

def anular_venta(request, venta_id):
    venta = get_object_or_404(Ventas, id=venta_id)

    if venta.estado == "anulada":
        messages.warning(request, "⚠️ Esta venta ya está anulada.")
        return redirect("historial_ventas")  # Ajusta al nombre real de tu vista

    # Cambiar el estado
    venta.estado = "anulada"
    venta.save()

    # Opcional: Devolver stock a inventario
    detalles = DetalleVentas.objects.filter(venta=venta)
    for detalle in detalles:
        producto = detalle.producto
        if venta.sucursal == "S1":
            producto.S1 += detalle.cantidad
        elif venta.sucursal == "S2":
            producto.S2 += detalle.cantidad
        elif venta.sucursal == "S3":
            producto.S3 += detalle.cantidad
        elif venta.sucursal == "A":
            producto.A += detalle.cantidad
        producto.save()

    messages.success(request, "❌ Venta anulada correctamente. El stock fue restaurado.")
    return redirect("historial_ventas")


def imprimir_codigo_barras(request, codigo):
    producto = get_object_or_404(Productos, Codigo=codigo)
    return render(request, 'imprimir_codigo.html', {'producto': producto})

from django.shortcuts import render, get_object_or_404
from .models import Productos

def imprimir_codigo(request, producto_id):
    producto = get_object_or_404(Productos, id=producto_id)
    return render(request, 'inventario/imprimir_codigo.html', {'producto': producto})
