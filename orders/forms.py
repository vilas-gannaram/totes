from django import forms
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce

from customers.models import Customer
from products.models import Product


class ProductChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, product):
        return f"{product.sku} — {product.name} (${product.unit_price}, {product.total_available} in stock)"


def sellable_products():
    return Product.objects.annotate(
        total_available=Coalesce(Sum("inventory__quantity_available"), Value(0))
    ).filter(total_available__gt=0)


class OrderForm(forms.Form):
    customer = forms.ModelChoiceField(
        Customer.objects.all(),
        empty_label="Select a customer",
        widget=forms.Select(attrs={"class": "select w-full max-w-md"}),
    )


class LineForm(forms.Form):
    product = ProductChoiceField(
        sellable_products(),
        required=False,
        empty_label="Select a product",
        widget=forms.Select(attrs={"class": "select select-sm w-full min-w-64"}),
    )
    quantity = forms.IntegerField(
        min_value=1, required=False, widget=forms.NumberInput(attrs={"class": "input input-sm w-full"})
    )

    def clean(self):
        data = super().clean()
        product, quantity = data.get("product"), data.get("quantity")
        if bool(product) != bool(quantity):
            raise forms.ValidationError("Pick a product and a quantity.")
        if product and quantity > product.total_available:
            self.add_error("quantity", f"Only {product.total_available} in stock.")
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
            (f.cleaned_data["product"], f.cleaned_data["quantity"])
            for f in self.forms
            if f.cleaned_data.get("product")
        ]


LineFormSet = forms.formset_factory(LineForm, formset=BaseLineFormSet, extra=6)
