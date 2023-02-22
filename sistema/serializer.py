from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework import serializers

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    remember = serializers.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs['context']['request']
        super().__init__(*args, **kwargs)

    def validate(self, attrs):
        print("validateeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
        data = super().validate(attrs)
        if attrs.get('remember'):
            self.request.session.set_expiry(86400)  # set session expiry to 24 hours
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        print("tooottttttttttttttttttttttttttttttttttttt")
        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer