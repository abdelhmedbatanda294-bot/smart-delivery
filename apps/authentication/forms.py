from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms

from apps.authentication.models import User
from apps.delivery.models import CustomerProfile, DriverProfile

UserModel = get_user_model()


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


class CustomerRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)
    company_name = forms.CharField(max_length=120, required=False)

    class Meta:
        model = UserModel
        fields = ("username", "first_name", "last_name", "email", "phone", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CUSTOMER
        user.phone = self.cleaned_data.get("phone", "")
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
            profile, _ = CustomerProfile.objects.get_or_create(user=user)
            profile.company_name = self.cleaned_data.get("company_name", "")
            profile.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserModel
        fields = ("first_name", "last_name", "email", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


class StaffUserCreateForm(UserCreationForm):
    role = forms.ChoiceField(choices=User.Role.choices)
    phone = forms.CharField(max_length=30, required=False)
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    vehicle_type = forms.CharField(max_length=80, required=False)
    vehicle_plate = forms.CharField(max_length=30, required=False)

    class Meta:
        model = UserModel
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role == User.Role.ADMIN:
            raise forms.ValidationError("Create administrators from Django admin only.")
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.phone = self.cleaned_data.get("phone", "")
        if commit:
            user.save()
            if user.role == User.Role.DRIVER:
                profile, _ = DriverProfile.objects.get_or_create(user=user)
                profile.vehicle_type = self.cleaned_data.get("vehicle_type", "")
                profile.vehicle_plate = self.cleaned_data.get("vehicle_plate", "")
                profile.save()
        return user
