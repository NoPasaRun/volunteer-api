import base64
from io import BytesIO

import qrcode
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Count

from api.models import (
    VUser, Volunteer, Rating, Comment, Task, Link, Unit
)


def allow_all_to_superuser(cls):
    def outer(func):
        def inner(self, request, *args, **kwargs):
            if not request.user.is_superuser:
                return func(self, request, *args, **kwargs)
            return getattr(super(cls, self), func.__name__)(request, *args, **kwargs)
        return inner
    return outer


def modify_request_methods(methods):
    def wrapper(cls):
        for func_name in filter(lambda n: n in methods, dir(cls)):
            func = allow_all_to_superuser(cls)(getattr(cls, func_name))
            setattr(cls, func_name, func)
        return cls
    return wrapper


class UnitFilter(admin.SimpleListFilter):

    title = "Группа"
    parameter_name = 'unit'

    def lookups(self, request, model_admin):
        self.model_admin = model_admin
        if not request.user.is_superuser:
            return tuple((unit.id, unit.title) for unit in Unit.objects.filter(creator=request.user))
        return tuple((unit.id, unit.title) for unit in Unit.objects.all())

    def queryset(self, request, queryset):
        parameter_name = self.parameter_name
        if hasattr(self.model_admin, 'parameter_name'):
            parameter_name = self.model_admin.parameter_name
        if self.value():
            return queryset.filter(**{parameter_name: self.value()})
        return queryset


@admin.register(VUser)
class VUserAdmin(admin.ModelAdmin):
    list_display = ("id", 'username', "is_staff", "is_superuser")
    search_fields = ('username',)
    list_filter = ('is_staff', 'is_superuser')
    list_display_links = ("id", 'username',)

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return self.readonly_fields + ("password",)
        return self.readonly_fields

    def save_model(self, request, obj: VUser, form, change):
        if not change:
            obj.set_password(form.cleaned_data['password'])
        super().save_model(request, obj, form, change)


@admin.register(Volunteer)
@modify_request_methods(methods=["has_change_permission", "save_model", "get_queryset"])
class VolunteerAdmin(admin.ModelAdmin):

    list_display = ("id", 'fullname', "email", "link", "unit")
    search_fields = ('fullname', 'email',)
    list_display_links = ("id", 'fullname',)
    list_filter = (UnitFilter,)
    parameter_name = "link__unit"

    change_form_template = "admin/api/volunteer/change_form.html"

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        link = Link.objects.filter(volunteer__id=object_id).first()
        if link is not None:
            img = qrcode.make(request.build_absolute_uri(f"/token/{link.code}/"))
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = "data: image/png;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")
            extra_context["qrcode"] = img_str
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return obj.owner == request.user
        return super().has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if form.cleaned_data["link"].owner != request.user:
            raise PermissionDenied("This link does not belong to you")
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['link'].queryset = Link.objects.filter(unit__creator=request.user, volunteer__isnull=True)
        return form

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_queryset(self, request):
        return Volunteer.objects.filter(link__unit__creator=request.user)

    def unit(self, obj):
        return obj.link.unit

    unit.short_description = "Группа"


@admin.register(Link)
@modify_request_methods(methods=["has_change_permission", "save_model", "get_queryset", "get_form"])
class LinkAdmin(admin.ModelAdmin):
    list_display = ("id", 'code', 'unit', "is_free")
    search_fields = ('code',)
    list_display_links = ("id", 'code',)

    def is_free(self, obj):
        return not hasattr(obj, "volunteer")

    is_free.boolean = True
    is_free.short_description = "Доступна"

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return obj.unit.creator == request.user
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_queryset(self, request):
        return Link.objects.filter(unit__creator=request.user)

    def save_model(self, request, obj, form, change):
        if form.cleaned_data["unit"] not in request.user.units.all():
            raise PermissionDenied("This unit does not belong to you")
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['unit'].queryset = Unit.objects.filter(creator=request.user)
        return form


@admin.register(Rating)
@modify_request_methods(methods=["has_change_permission", "get_form"])
class RatingAdmin(admin.ModelAdmin):
    list_display = ("id", 'task', 'volunteer', "score")
    search_fields = ('task', 'volunteer',)
    list_display_links = ("id", 'task', 'volunteer',)

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return all([request.user == o for o in [obj.task.owner, obj.volunteer.owner]])
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def score(self, obj: Rating):
        return obj.task.score if not obj.task.is_open else 0

    def save_model(self, request, obj, form, change):
        if obj.task.unit != obj.volunteer.link.unit:
            raise PermissionDenied("Task unit and volunteer unit must be the same")
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['task'].queryset = Task.objects.filter(unit__creator=request.user)
        form.base_fields['volunteer'].queryset = Volunteer.objects.filter(link__unit__creator=request.user)
        return form


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", 'task', 'volunteer', 'text')
    list_display_links = ("id", 'task', 'volunteer')
    search_fields = ('task', 'volunteer')


@admin.register(Task)
@modify_request_methods(methods=["has_change_permission", "save_model", "get_form"])
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", 'title', 'unit', 'score', 'date_start', 'date_end', 'is_open')
    list_display_links = ("id", 'title')
    search_fields = ('title',)
    list_filter = (UnitFilter, 'date_start', 'date_end')
    exclude = ("creator",)
    parameter_name = "unit"

    change_form_template = 'admin/api/task/change_form.html'
    change_list_template = 'admin/api/task/change_list.html'

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        volunteers = Volunteer.objects.filter(ratings__task_id=object_id)
        for volunteer in volunteers:
            setattr(volunteer, "task_comments", list(volunteer.comments.filter(task_id=object_id)))
        extra_context["volunteers"] = volunteers
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return obj.owner == request.user
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if form.cleaned_data["unit"].creator != request.user:
            raise PermissionDenied("This task does not belong to you")
        if form.cleaned_data["unit"].tasks.count() >= 20:
            raise PermissionDenied("You can't make more than 20 tasks attached to one group")
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['unit'].queryset = Unit.objects.annotate(task_count=Count('tasks')).filter(
            creator=request.user, task_count__lt=20
        )
        return form


@admin.register(Unit)
@modify_request_methods(methods=["get_queryset", "has_change_permission"])
class UnitAdmin(admin.ModelAdmin):
    list_display = ("id", 'title', 'description', "participant_amount")
    list_display_links = ("id", 'title')
    search_fields = ('title',)
    exclude = ("creator",)

    def get_queryset(self, request):
        return Unit.objects.filter(creator=request.user)

    def has_add_permission(self, request):
        return request.user.units.count() < 2 or request.user.advanced

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return obj.creator == request.user
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        obj.creator = request.user
        super().save_model(request, obj, form, change)

    def participant_amount(self, obj):
        return Volunteer.objects.filter(link__unit=obj).count()

    participant_amount.short_description = "Кол-во участников"
