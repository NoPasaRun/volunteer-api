import os
from datetime import timedelta, datetime
from uuid import uuid4

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Sum
from django.utils.deconstruct import deconstructible


@deconstructible
class UploadToPathAndRename(object):
    def __init__(self, path):
        self.sub_path = path

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1]
        name = instance.pk if instance.pk else uuid4().hex
        return os.path.join(self.sub_path, '{}.{}'.format(name, ext))


class VUser(AbstractUser):
    TARIFFS = (
        ("free", "Бесплатный"),
        ("advanced", "Расширенный"),
        ("special", "Специальный")
    )
    tariff = models.CharField(max_length=100, choices=TARIFFS, default="free", verbose_name="Тарифф")

    @property
    def advanced(self):
        return self.tariff == "advanced"

    def __str__(self):
        return str(self.username)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class Unit(models.Model):
    creator = models.ForeignKey(VUser, on_delete=models.CASCADE,
                                related_name='units', verbose_name="Создатель")
    title = models.CharField(max_length=100, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"

    def __str__(self):
        return str(self.title)


class Link(models.Model):
    code = models.UUIDField(unique=True, default=uuid4, verbose_name="Код")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='links', verbose_name="Группа")

    @property
    def owner(self):
        return self.unit.creator

    def __str__(self):
        return f"{self.code} - {self.unit}"

    class Meta:
        verbose_name = "Ссылка"
        verbose_name_plural = "Ссылки"

    def is_open(self):
        return hasattr(self, 'volunteer')


class Task(models.Model):
    title = models.CharField(max_length=100, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='tasks', verbose_name="Группа")
    score = models.PositiveIntegerField(default=0, verbose_name="Баллы")
    date_start = models.DateTimeField(verbose_name="Дата начала")
    date_end = models.DateTimeField(verbose_name="Дата завершения")
    is_open = models.BooleanField(default=True, verbose_name="Доступна")

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"

    @property
    def owner(self):
        return self.unit.creator

    @property
    def is_archived(self):
        return (self.date_end + timedelta(days=2)).timestamp() < datetime.now().timestamp()


class Volunteer(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    last_name = models.CharField(max_length=100, verbose_name="Фамилия")
    email = models.EmailField(unique=True, verbose_name="Почта")
    link = models.OneToOneField(Link, on_delete=models.CASCADE,
                                related_name='volunteer', verbose_name="Ссылка")
    avatar = models.ImageField(upload_to=UploadToPathAndRename("volunteer"),
                               null=True, blank=True, verbose_name="Аватар")

    @property
    def fullname(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def owner(self):
        return self.link.unit.creator

    def __str__(self):
        return f"Волонтер {self.fullname}"

    class Meta:
        verbose_name = "Волонтер"
        verbose_name_plural = "Волонтеры"

    @property
    def score(self):
        value = self.ratings.filter(task__is_open=False).aggregate(
            Sum("task__score")
        ).get("task__score__sum", 0)
        return 0 if not value else value


class Rating(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='ratings', verbose_name="Задача")
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE,
                                  related_name='ratings', verbose_name="Волонтер")

    def __str__(self):
        return f"{self.volunteer} на {self.task}"

    @property
    def owner(self):
        return self.task.unit.creator

    class Meta:
        unique_together = ('task', 'volunteer')
        verbose_name = "Рейтинг"
        verbose_name_plural = "Рейтинги"


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments', verbose_name="Задача")
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE,
                                  related_name='comments', verbose_name="Волонтер")
    text = models.TextField(verbose_name="Текст")
    photo = models.ImageField(upload_to=UploadToPathAndRename("comment"),
                              null=True, blank=True, verbose_name="Фото")

    def __str__(self):
        return f"От {self.volunteer}: {self.text[:20] + ('...' if len(self.text) > 20 else '')}"

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
