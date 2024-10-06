from django.db.models import Q

from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics

from rest_framework_simplejwt.views import TokenObtainPairView

from api.models import Link, Task, Rating, Volunteer, Unit, Comment
from api.serializers import TaskSerializer, VolunteerSerializer, CommentSerializer, \
    VolunteerReadSerializer, CommentReadSerializer


class TokenApi(TokenObtainPairView):

    def post(self, request, *args, **kwargs):
        response = super(TokenApi, self).post(request, *args, **kwargs)
        response.set_cookie("token", response.data.get("access"))
        return response


class LinkApiView(APIView):

    permission_classes = (IsAdminUser,)

    def post(self, request, unit_id: int, *args, **kwargs):
        unit = Unit.objects.filter(id=unit_id).first()
        if not unit:
            return Response({"detail": "Unit not found"}, 404)
        if unit.creator != request.user:
            return Response({"detail": "You don't have permission to invite users to this group"}, 403)
        (link := Link(unit=unit)).save()
        return Response({"code": link.code}, 201)


class VolunteerApi(generics.ListAPIView):
    serializer_class = VolunteerSerializer

    def get_queryset(self):
        return sorted(Volunteer.objects.all(), key=lambda v: v.score, reverse=True)


class MyApi(generics.CreateAPIView):

    serializer_class = VolunteerSerializer

    def get_permission_class(self):
        if self.request.method == 'POST':
            return ()
        return (IsAuthenticated(),)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return VolunteerReadSerializer
        return VolunteerSerializer

    def get(self, request):
        data = self.get_serializer(instance=request.user).data
        return Response(data, 200)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)


class TaskApi(generics.ListAPIView):

    serializer_class = TaskSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Task.objects.filter(is_open=False)
        return Task.objects.filter(~Q(ratings__volunteer=self.request.user) & Q(unit=self.request.user.link.unit))


class MyTaskApi(TaskApi):

    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Task.objects.filter(ratings__volunteer=self.request.user, unit=self.request.user.link.unit)


def proceed_task(view):
    def wrapper(self, request, task_id: int, *args, **kwargs):
        task = Task.objects.filter(id=task_id, is_open=True).first()
        if not task:
            return Response({"error": "Task not found or completed"}, status=400)
        return view(self, request, task, *args, **kwargs)
    return wrapper


class ManageTaskApi(APIView):

    permission_classes = (IsAuthenticated,)

    @proceed_task
    def post(self, request, task: Task, *args, **kwargs):
        if task.unit != request.user.link.unit:
            return Response({"detail": "You're not a part of the task's group"}, status=403)
        if not task.is_open:
            return Response({"detail": "You cannot accept task when it is closed"}, status=400)
        unique_data = {"task": task, "volunteer": request.user}
        if Rating.objects.filter(**unique_data).first():
            return Response({"error": "You have already signed to this task"}, status=400)
        Rating(**unique_data).save()
        return Response({"success": True}, 200)

    @proceed_task
    def delete(self, request, task: Task, *args, **kwargs):
        if not task.is_open:
            return Response({"detail": "You cannot deny task when it is closed"}, status=400)
        Rating.objects.filter(task=task).delete()
        return Response({"success": True}, 202)


class CommentApi(generics.CreateAPIView, generics.ListAPIView):

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CommentReadSerializer
        return CommentSerializer

    def get_queryset(self):
        task_id = self.request.parser_context.get('kwargs').get('task_id')
        return Comment.objects.filter(task_id=task_id)

    @proceed_task
    def post(self, request, task: Task, *args, **kwargs):
        serializer = CommentSerializer(
            data=request.data, task=task,
            volunteer=request.user,
            context=self.get_serializer_context()
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)
