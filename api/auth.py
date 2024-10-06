from rest_framework_simplejwt.authentication import JWTAuthentication

from api.models import Volunteer


class JWTVolunteerAuthentication(JWTAuthentication):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_model = Volunteer
