from django.db.models import Count, Q, Avg, Func, FloatField
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from rest_framework.response import Response

from api.models import Volunteer, Unit
from api.serializers import VolunteerLoginSerializer


class Round(Func):
    function = 'ROUND'
    arity = 2
    output_field = FloatField()


def volunteer_chart(request):
    labels = []
    data = []

    queryset = Volunteer.objects.values('first_name', "last_name").annotate(
        task_count=Count('ratings__task', filter=Q(ratings__task__is_open=False))
    ).order_by('-task_count')[:5]
    for entry in queryset:
        labels.append(entry['first_name'] + " " + entry['last_name'])
        data.append(entry['task_count'])

    return JsonResponse(data={
        'labels': labels,
        'data': data + [0],
    })


def average_participant_count(request):
    data = Unit.objects.annotate(
        participant_count=Count("links__volunteer")
    ).aggregate(
        avg_participant_count=Round(Avg('participant_count'), 4)
    )
    return JsonResponse(data=data)


def task_chart(request):
    labels = []
    data = []

    queryset = Unit.objects.values("title").annotate(
        open_task_count=Count('tasks', filter=Q(tasks__is_open=True))
    ).annotate(closed_task_count=Count('tasks', filter=Q(tasks__is_open=False)))

    for entry in queryset:
        labels.append(entry['title'] + " запланировано")
        data.append(entry['open_task_count'])
        labels.append(entry['title'] + " завершено")
        data.append(entry['closed_task_count'])

    return JsonResponse(data={
        'labels': labels,
        'data': data + ["0"],
    })


def spa(request, *args, **kwargs):
    data = {"access": request.COOKIES.get('token')}
    data["block"] = "lk" if data["access"] else request.GET.get("block", "login")
    return HttpResponse(render(request, "spa.html", context=data))


def token(request, code, *args, **kwargs):
    serializer = VolunteerLoginSerializer(data={"code": code})
    if serializer.is_valid():
        access = serializer.validated_data["access"]
        response = HttpResponseRedirect("/spa/")
        response.set_cookie('token', access)
        return response
    return Response(serializer.errors, status=400)


def logout(request):
    response = HttpResponseRedirect("/spa/")
    response.delete_cookie('token')
    return response

