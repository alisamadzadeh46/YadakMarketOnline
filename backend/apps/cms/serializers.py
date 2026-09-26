from rest_framework import serializers

from .models import Slide


class SlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slide
        fields = (
            "id",
            "badge",
            "title",
            "highlight",
            "text",
            "image",
            "button_text",
            "button_link",
            "order",
            "is_active",
        )
