import base64
import uuid

from django.core.files.base import ContentFile
from django.db import IntegrityError
from rest_framework.exceptions import APIException

from rest_framework.serializers import (
    Serializer, UUIDField, ModelSerializer,
    SerializerMethodField, ImageField
)
from rest_framework_simplejwt.tokens import AccessToken

from api.models import Link, Task, Volunteer, Unit, Comment


class Base64ImageField(ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format_, img_str = data.split(';base64,')
            name, ext = str(uuid.uuid4().urn[9:]), format_.split('/')[-1]
            data = ContentFile(base64.b64decode(img_str), name=name + '.' + ext)
        return super(Base64ImageField, self).to_internal_value(data)


class UnitSerializer(ModelSerializer):

    class Meta:
        model = Unit
        fields = (
            "title",
            "description"
        )


class VolunteerReadSerializer(ModelSerializer):
    unit = UnitSerializer(source="link.unit", read_only=True)
    score = SerializerMethodField()

    def get_score(self, obj):
        return obj.score

    class Meta:
        model = Volunteer
        fields = (
            "unit",
            "first_name",
            "last_name",
            "email",
            "avatar",
            "score"
        )


class VolunteerSerializer(ModelSerializer):

    code = UUIDField(required=True, write_only=True)
    avatar = Base64ImageField(required=False)

    def create(self, validated_data):
        code = self.validated_data.pop("code")
        link = Link.objects.filter(code=code).first()
        if not link or not link.is_open:
            raise APIException({"code": "Not found or locked"}, 404)
        try:
            volunteer = Volunteer(**self.validated_data, link=link)
            volunteer.save()
        except IntegrityError as e:
            raise APIException({"detail": str(e)}, 400)
        return volunteer

    @property
    def data(self):
        volunteer_serializer = VolunteerReadSerializer(
            instance=self.instance, context=self.context
        )
        return volunteer_serializer.data

    class Meta:
        model = Volunteer
        fields = (
            "first_name",
            "last_name",
            "email",
            "avatar",
            "code"
        )


class TaskSerializer(ModelSerializer):

    photo = SerializerMethodField()

    def get_photo(self, obj):
        comment = obj.comments.filter(photo__isnull=False).first()
        if comment:
            request = self.context["request"]
            return request.build_absolute_uri(comment.photo.url)
        return None

    class Meta:
        model = Task
        read_only_fields = ('photo',)
        fields = (
            "id",
            "title",
            "description",
            "score",
            "date_start",
            "date_end",
            "is_open",
            "photo"
        )


class CommentReadSerializer(ModelSerializer):

    volunteer = VolunteerReadSerializer(read_only=True)
    task = TaskSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ("text", "photo", "volunteer", "task")


class CommentSerializer(ModelSerializer):

    photo = Base64ImageField(required=False, write_only=True)

    def __init__(self, *args, **kwargs):
        self.task = kwargs.pop("task") if kwargs.get("task") else None
        self.volunteer = kwargs.pop("volunteer") if kwargs.get("volunteer") else None
        super().__init__(*args, **kwargs)

    @property
    def data(self):
        comment_serializer = CommentReadSerializer(
            instance=self.instance, context=self.context
        )
        print(self.context)
        return comment_serializer.data

    def create(self, validated_data):
        try:
            obj = Comment(**self.validated_data)
            obj.task, obj.volunteer = self.task, self.volunteer
            obj.save()
        except IntegrityError as e:
            raise APIException({"detail": str(e)}, 400)
        return obj

    class Meta:
        model = Comment
        fields = ("text", "photo",)


class VolunteerLoginSerializer(Serializer):

    code = UUIDField(required=True)

    def validate(self, attrs):
        link = Link.objects.filter(code=attrs.get('code')).first()
        if not link or not hasattr(link, 'volunteer'):
            raise APIException({"message": "Code is invalid"}, 400)

        token = AccessToken.for_user(link.volunteer)
        return {"access": str(token)}
