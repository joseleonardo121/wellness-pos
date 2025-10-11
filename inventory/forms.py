from django import forms
from .models import Productos, Ventas, DetalleVentas, PagoVenta,Proveedor,Compra

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['persona_deposito', 'nombre_empresa', 'rubro', 'celular']
        widgets = {
            'persona_deposito': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-control'}),
            'rubro': forms.TextInput(attrs={'class': 'form-control'}),
            'celular': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Productos
        fields = "__all__"


class VentaForm(forms.ModelForm):
    class Meta:
        model = Ventas
        fields = ["sucursal", "metodo_pago", "total"]


class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = DetalleVentas
        fields = ["producto", "cantidad", "precio_unitario", "subtotal"]


class PagoForm(forms.ModelForm):
    class Meta:
        model = PagoVenta
        fields = ["metodo", "monto"]
        
from django import forms
from django_select2.forms import ModelSelect2Widget
from .models import Traspaso, Productos

class TraspasoForm(forms.ModelForm):
    class Meta:
        model = Traspaso
        fields = ["producto", "cantidad", "sucursal_origen", "sucursal_destino"]

        widgets = {
            "producto": ModelSelect2Widget(
                model=Productos,
                search_fields=["Codigo__icontains", "Marca__icontains", "Diseno__icontains", "Color__icontains"],
                attrs={"data-placeholder": "Buscar producto...", "style": "width: 100%"},
            ),
        }

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['proveedor', 'descripcion', 'monto']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
        }


from .models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombres', 'celular']
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'celular': forms.TextInput(attrs={'class': 'form-control'}),
        }

        
from django import forms
from django.forms import inlineformset_factory
from .models import NotaCambio, DetalleNotaCambio

class NotaCambioForm(forms.ModelForm):
    class Meta:
        model = NotaCambio
        fields = ["sucursal", "diferencia"]

class DetalleNotaCambioForm(forms.ModelForm):
    codigo_devuelto = forms.CharField(
        label="Código devuelto",
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm",
            "placeholder": "Escanea o escribe el código del producto devuelto"
        })
    )
    codigo_entregado = forms.CharField(
        label="Código entregado",
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm",
            "placeholder": "Escanea o escribe el código del producto entregado"
        })
    )

    class Meta:
        model = DetalleNotaCambio
        fields = ["producto_devuelto", "producto_entregado", "cantidad", "codigo_devuelto", "codigo_entregado"]
        widgets = {
            "producto_devuelto": forms.HiddenInput(),
            "producto_entregado": forms.HiddenInput(),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }

    def clean(self):
        cleaned = super().clean()
        from .models import Productos

        codigo_devuelto = cleaned.get("codigo_devuelto")
        codigo_entregado = cleaned.get("codigo_entregado")

        # Buscar producto devuelto por código exacto
        if codigo_devuelto:
            producto = Productos.objects.filter(Codigo__iexact=codigo_devuelto.strip()).first()
            if producto:
                cleaned["producto_devuelto"] = producto
            else:
                self.add_error("codigo_devuelto", "Producto devuelto no encontrado.")

        # Buscar producto entregado por código exacto
        if codigo_entregado:
            producto = Productos.objects.filter(Codigo__iexact=codigo_entregado.strip()).first()
            if producto:
                cleaned["producto_entregado"] = producto
            else:
                self.add_error("codigo_entregado", "Producto entregado no encontrado.")

        return cleaned


# Formset: permitirá manejar varios detalles en una sola nota
DetalleNotaCambioFormSet = inlineformset_factory(
    NotaCambio,
    DetalleNotaCambio,
    form=DetalleNotaCambioForm,
    extra=1,  # mínimo un producto
    can_delete=True
)
