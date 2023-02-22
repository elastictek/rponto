from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.authentication import JWTAuthentication

def jwt_required(func):
    print("%%%%xxxxxxxxxxxxxxxxzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx%%%")
    def wrapper(request, *args, **kwargs):
        try:
            print("%%%%xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx%%%")
            print(request)
            JWTAuthentication().authenticate(request)
            print("%%%%validddddddddddddddddddddddddddddddddddddddddddddd%%%")
        except InvalidToken:
            return Response({'error': 'Invalid token'}, status=401)
        return func(request, *args, **kwargs)
    return wrapper