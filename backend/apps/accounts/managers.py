"""Custom user manager keyed on phone number (the primary login identifier).

Iranian auto-parts shops and buyers log in with their mobile number, so phone
replaces username. Email is optional.
"""

from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError("شماره موبایل الزامی است.")
        # Normalize email if one was supplied.
        email = extra_fields.pop("email", "")
        if email:
            email = self.normalize_email(email)
        user = self.model(phone=phone, email=email, **extra_fields)
        user.set_password(password)  # hashes with Argon2 (see PASSWORD_HASHERS)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        """Regular self-service registration (customer by default)."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        """The site owner: full access to everything via Django admin."""
        from .models import User  # local import to avoid circular reference

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_approved", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(phone, password, **extra_fields)
