
from django import forms

from apps.delivery.models import (
    Address,
    Delivery,
    DeliveryAssignment,
    DriverProfile,
)


class DeliveryCreateForm(forms.ModelForm):

    pickup_label = forms.CharField(
        max_length=80,
        required=False,
        initial="Pickup",
    )

    pickup_street = forms.CharField(max_length=200, required=True)
    pickup_city = forms.CharField(max_length=100, required=True)
    pickup_state = forms.CharField(max_length=100, required=False)
    pickup_postal_code = forms.CharField(max_length=20, required=False)

    dest_label = forms.CharField(
        max_length=80,
        required=False,
        initial="Destination",
    )

    dest_street = forms.CharField(max_length=200, required=True)
    dest_city = forms.CharField(max_length=100, required=True)
    dest_state = forms.CharField(max_length=100, required=False)
    dest_postal_code = forms.CharField(max_length=20, required=False)

    class Meta:
        model = Delivery

        fields = (
            "package_description",
            "weight_kg",
            "expected_delivery_at",
            "notes",
        )

        widgets = {
            "package_description": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Enter package description",
                }
            ),
            "weight_kg": forms.NumberInput(
                attrs={
                    "class": "input",
                    "step": "0.01",
                    "placeholder": "Enter weight",
                }
            ),
            "expected_delivery_at": forms.DateTimeInput(
                attrs={
                    "class": "input",
                    "type": "datetime-local",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "input",
                    "rows": 3,
                    "placeholder": "Additional notes",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "input",
                "style": (
                    "display:block;"
                    "width:100%;"
                    "min-height:44px;"
                    "padding:10px 12px;"
                    "border:1px solid #ccc;"
                    "border-radius:6px;"
                    "background:#ffffff;"
                    "color:#000000;"
                    "box-sizing:border-box;"
                ),
            })

    def save_with_customer(self, user):

        pickup = Address.objects.create(
            label=self.cleaned_data.get("pickup_label") or "Pickup",
            street=self.cleaned_data["pickup_street"],
            city=self.cleaned_data["pickup_city"],
            state=self.cleaned_data.get("pickup_state", ""),
            postal_code=self.cleaned_data.get("pickup_postal_code", ""),
            created_by=user,
        )

        destination = Address.objects.create(
            label=self.cleaned_data.get("dest_label") or "Destination",
            street=self.cleaned_data["dest_street"],
            city=self.cleaned_data["dest_city"],
            state=self.cleaned_data.get("dest_state", ""),
            postal_code=self.cleaned_data.get("dest_postal_code", ""),
            created_by=user,
        )

        delivery = super().save(commit=False)
        delivery.customer = user.customer_profile
        delivery.pickup_address = pickup
        delivery.destination_address = destination
        delivery.save()

        return delivery


class DeliveryUpdateForm(forms.ModelForm):

    pickup_street = forms.CharField(max_length=200)
    pickup_city = forms.CharField(max_length=100)
    pickup_state = forms.CharField(max_length=100, required=False)
    pickup_postal_code = forms.CharField(max_length=20, required=False)

    dest_street = forms.CharField(max_length=200)
    dest_city = forms.CharField(max_length=100)
    dest_state = forms.CharField(max_length=100, required=False)
    dest_postal_code = forms.CharField(max_length=20, required=False)

    class Meta:
        model = Delivery

        fields = (
            "package_description",
            "weight_kg",
            "expected_delivery_at",
            "notes",
        )

        widgets = {
            "package_description": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Enter package description",
                }
            ),
            "weight_kg": forms.NumberInput(
                attrs={
                    "class": "input",
                    "step": "0.01",
                    "placeholder": "Enter weight",
                }
            ),
            "expected_delivery_at": forms.DateTimeInput(
                attrs={
                    "class": "input",
                    "type": "datetime-local",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "input",
                    "rows": 3,
                    "placeholder": "Additional notes",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        delivery = self.instance

        if delivery and delivery.pk:
            self.fields["pickup_street"].initial = delivery.pickup_address.street
            self.fields["pickup_city"].initial = delivery.pickup_address.city
            self.fields["pickup_state"].initial = delivery.pickup_address.state
            self.fields["pickup_postal_code"].initial = delivery.pickup_address.postal_code

            self.fields["dest_street"].initial = delivery.destination_address.street
            self.fields["dest_city"].initial = delivery.destination_address.city
            self.fields["dest_state"].initial = delivery.destination_address.state
            self.fields["dest_postal_code"].initial = delivery.destination_address.postal_code

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "input",
                "style": (
                    "display:block;"
                    "width:100%;"
                    "min-height:44px;"
                    "padding:10px 12px;"
                    "border:1px solid #ccc;"
                    "border-radius:6px;"
                    "background:#ffffff;"
                    "color:#000000;"
                    "box-sizing:border-box;"
                ),
            })

    def save(self, commit=True):

        delivery = super().save(commit=False)

        pickup = delivery.pickup_address
        pickup.street = self.cleaned_data["pickup_street"]
        pickup.city = self.cleaned_data["pickup_city"]
        pickup.state = self.cleaned_data["pickup_state"]
        pickup.postal_code = self.cleaned_data["pickup_postal_code"]
        pickup.save()

        destination = delivery.destination_address
        destination.street = self.cleaned_data["dest_street"]
        destination.city = self.cleaned_data["dest_city"]
        destination.state = self.cleaned_data["dest_state"]
        destination.postal_code = self.cleaned_data["dest_postal_code"]
        destination.save()

        if commit:
            delivery.save()

        return delivery


class DriverAvailabilityForm(forms.ModelForm):

    class Meta:
        model = DriverProfile

        fields = (
            "is_available",
            "is_active",
            "vehicle_type",
            "vehicle_plate",
            "notes",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    "class": "input",
                })


class DeliveryAssignmentForm(forms.ModelForm):

    class Meta:
        model = DeliveryAssignment

        fields = ("driver", "note")

        widgets = {
            "driver": forms.Select(
                attrs={
                    "class": "input",
                }
            ),
            "note": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Assignment note",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["driver"].queryset = (
            DriverProfile.objects
            .filter(
                is_active=True,
                is_available=True,
                user__role="driver",
            )
            .select_related("user")
            .order_by("user__username")
        )


class DeliveryStatusForm(forms.Form):

    status = forms.ChoiceField(
        choices=[
            (Delivery.Status.PICKED_UP, "Picked Up"),
            (Delivery.Status.IN_TRANSIT, "In Transit"),
            (Delivery.Status.DELIVERED, "Delivered"),
        ],
        widget=forms.Select(
            attrs={
                "class": "input",
            }
        ),
    )

    note = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Status update note",
            }
        ),
    )
