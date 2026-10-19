from django import forms

from products.models import Product
from suppliers.models import Supplier
from warehouses.models import Warehouse

SELECT = {"class": "select w-full max-w-md"}


class ProductChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, product):
        return f"{product.sku} — {product.name}"


class PurchaseOrderForm(forms.Form):
    supplier = forms.ModelChoiceField(
        Supplier.objects.all(), empty_label="Select a supplier", widget=forms.Select(attrs=SELECT)
    )
    warehouse = forms.ModelChoiceField(
        Warehouse.objects.all(), empty_label="Deliver to", widget=forms.Select(attrs=SELECT)
    )
    expected_at = forms.DateField(
        required=False,
        label="Expected",
        widget=forms.DateInput(attrs={"type": "date", "class": "input w-full max-w-md"}),
    )


class LineForm(forms.Form):
    product = ProductChoiceField(
        Product.objects.all(),
        required=False,
        empty_label="Select a product",
        widget=forms.Select(attrs={"class": "select select-sm w-full"}),
    )
    quantity_ordered = forms.IntegerField(
        min_value=1, required=False, widget=forms.NumberInput(attrs={"class": "input input-sm w-full"})
    )
    unit_cost = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "input input-sm w-full", "step": "0.01"}),
    )

    def clean(self):
        data = super().clean()
        filled = [data.get("product"), data.get("quantity_ordered"), data.get("unit_cost")]
        if any(v is not None for v in filled) and any(v is None for v in filled):
            raise forms.ValidationError("Pick a product, a quantity and a unit cost.")
        return data


class BaseLineFormSet(forms.BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        products = [f.cleaned_data["product"] for f in self.forms if f.cleaned_data.get("product")]
        if not products:
            raise forms.ValidationError("Add at least one item.")
        if len(products) != len(set(products)):
            raise forms.ValidationError("Each product can appear only once.")

    def lines(self):
        return [
            (f.cleaned_data["product"], f.cleaned_data["quantity_ordered"], f.cleaned_data["unit_cost"])
            for f in self.forms
            if f.cleaned_data.get("product")
        ]


LineFormSet = forms.formset_factory(LineForm, formset=BaseLineFormSet, extra=6)
