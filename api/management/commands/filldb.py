import uuid
from math import ceil
from random import randint, choice

from django.conf import settings

from typing import List

import pytz
from django.core.management.base import BaseCommand, CommandError

from django.db.models import Model
from faker import Faker

from api.models import VUser, Unit, Link, Volunteer, Task, Rating, Comment


def custom_save(size, dir_):
    filename = f"{dir_}/{uuid.uuid4()}.png"
    with open(settings.MEDIA_ROOT / filename, "wb") as file:
        file.write(FAKER.image(size, image_format="png"))
    return filename


def remove_objects(model: Model):
    def outer(func):
        def inner(*args, **kwargs):
            queryset = model.objects.all()
            try:
                if model == VUser:
                    queryset = queryset.filter(is_superuser=False)
                queryset.delete()
                print(f"Start filling {model.__name__}")
                result = func(*args, **kwargs)
                print(f"Success!\n")
                return result
            except Exception as e:
                queryset.delete()
                raise e
                raise CommandError(e)
        return inner
    return outer


FAKER = Faker()


class Command(BaseCommand):
    help = "Full fill the db with random data"

    @remove_objects(model=VUser)
    def add_admins(self, amount: int = 5):
        admins = [
            VUser(
                is_staff=True, is_superuser=False,
                is_active=True, first_name=FAKER.first_name(),
                last_name=FAKER.last_name(), email=FAKER.email(),
                tariff=VUser.TARIFFS[randint(0, 2)][0],
                username=FAKER.user_name()
            )
            for _ in range(amount)
        ]
        [a.set_password("admin") for a in admins]
        return VUser.objects.bulk_create(admins)

    @remove_objects(model=Unit)
    def add_units(self, admins: List[VUser], amount: int = 3):
        units = [
            Unit(
                creator=admin, title=FAKER.company(),
                description=FAKER.text(),
            )
            for admin in admins for _ in range(amount)
        ]
        return Unit.objects.bulk_create(units)

    @remove_objects(model=Link)
    def add_links(self, units: List[Unit], amount: int = 5):
        links = [Link(unit=unit)for unit in units for _ in range(amount)]
        return Link.objects.bulk_create(links)

    @remove_objects(model=Volunteer)
    def add_volunteers(self, links: List[Link]):
        volunteers = [
            Volunteer(
                first_name=FAKER.first_name(),
                last_name=FAKER.last_name(), email=FAKER.email(),
                link=link, avatar=custom_save((250, 250), "volunteer")
            )
            for link in links
        ]
        return Volunteer.objects.bulk_create(volunteers)

    @remove_objects(model=Task)
    def add_tasks(self, units: List[Unit], amount: int = 15):
        tasks = [
            Task(
                title=FAKER.text(max_nb_chars=100),
                description=FAKER.paragraph(), unit=unit,
                score=randint(100, 1000), date_start=FAKER.date_time(tzinfo=pytz.UTC),
                date_end=FAKER.date_time(tzinfo=pytz.UTC), is_open=randint(0, 1)
            )
            for unit in units for _ in range(amount)
        ]
        return Task.objects.bulk_create(tasks)

    @remove_objects(model=Rating)
    def add_ratings(self, volunteers: List[Volunteer], max_amount: int = 5):
        ratings, tasks = [], dict()
        for vol in volunteers:
            if not (current_tasks := tasks.get(vol.link.unit_id)):
                current_tasks = tasks[vol.link.unit_id] = vol.link.unit.tasks.all()
            current_tasks = list(current_tasks).copy()
            for x in range(amount := randint(0, max_amount)):
                task = current_tasks.pop(randint(0, amount - x - 1))
                ratings.append(Rating(task=task, volunteer=vol))
        return Rating.objects.bulk_create(ratings)

    @remove_objects(model=Comment)
    def add_comments(self, volunteers: List[Volunteer], tasks: List[Task],
                     max_task_comments: int = 3, max_vol_comments: int = None):
        if not max_vol_comments or max_vol_comments * len(volunteers) < max_task_comments * len(tasks):
            max_vol_comments = ceil(max_task_comments * len(tasks) / len(volunteers))
        comments, vol_comments = [], dict()
        for task in tasks:
            for _ in range(randint(0, max_task_comments)):
                while True:
                    volunteer = choice(volunteers)
                    if vol_comments.get(volunteer.id, 0) >= max_vol_comments:
                        volunteers.remove(volunteer)
                        continue
                    break
                comments.append(
                    Comment(
                        task=task, volunteer=volunteer,
                        text=FAKER.text(), photo=custom_save((450, 150), "comment")
                    )
                )
                vol_comments[volunteer.id] = vol_comments.get(volunteer.id, 0) + 1

        return Comment.objects.bulk_create(comments)

    def handle(self, *args, **options):
        admins = self.add_admins(7)
        units = self.add_units(admins, 4)
        tasks = self.add_tasks(units, 25)
        links = self.add_links(units, 10)
        volunteers = self.add_volunteers(links)
        self.add_ratings(volunteers, 15)
        self.add_comments(volunteers, tasks, 5)

