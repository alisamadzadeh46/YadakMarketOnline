"""Serializers for registration, profile, KYC and addresses."""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Address, KYCDocument, ShopkeeperProfile, User


class UserSerializer(serializers.ModelSerializer):
    """Read-only representation of the authenticated user."""

    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "email",
            "full_name",
            "role",
            "role_display",
            "is_approved",
            "phone_verified",
            "date_joined",
        )
        read_only_fields = ("role", "is_approved", "phone_verified", "date_joined")


class RegisterSerializer(serializers.ModelSerializer):
    """Self-service registration.

    The client may request the SHOPKEEPER role, but the account stays
    unapproved until the owner confirms it; customers are usable immediately.
    """

    password = serializers.CharField(write_only=True, validators=[validate_password])
    requested_role = serializers.ChoiceField(
        choices=[User.Role.CUSTOMER, User.Role.SHOPKEEPER],
        default=User.Role.CUSTOMER,
        write_only=True,
    )

    class Meta:
        model = User
        fields = ("phone", "full_name", "email", "password", "requested_role")

    def create(self, validated_data):
        requested_role = validated_data.pop("requested_role")
        password = validated_data.pop("password")
        user = User(role=requested_role, **validated_data)
        # Shopkeepers require manual approval; customers are auto-approved
        # inside User.save().
        user.is_approved = requested_role == User.Role.CUSTOMER
        user.set_password(password)
        user.save()
        return user


class KYCDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCDocument
        fields = ("id", "doc_type", "file", "created_at")
        read_only_fields = ("created_at",)

    def validate_file(self, value):
        # A FileField accepts anything by default. These are served from our
        # own origin, so an .svg or .html here would be stored XSS.
        from apps.core.uploads import validate_document_upload

        return validate_document_upload(value)

    def to_representation(self, instance):
        """Hand out a signed, expiring URL instead of the raw private path."""
        from apps.core.protected import protected_url

        data = super().to_representation(instance)
        if instance.file:
            data["file"] = protected_url(self.context.get("request"), instance.file.name)
        return data


class ShopkeeperProfileSerializer(serializers.ModelSerializer):
    documents = KYCDocumentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ShopkeeperProfile
        fields = (
            "id",
            "shop_name",
            "owner_national_id",
            "business_license_no",
            "province",
            "city",
            "address",
            "landline",
            "status",
            "status_display",
            "review_note",
            "documents",
        )
        # The applicant cannot approve their own KYC.
        read_only_fields = ("status", "status_display", "review_note")


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            "id",
            "title",
            "receiver_name",
            "receiver_phone",
            "province",
            "city",
            "postal_code",
            "line",
            "lat",
            "lng",
            "is_default",
        )
