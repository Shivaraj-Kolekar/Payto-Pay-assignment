from django.db import connection
from django.http import JsonResponse


def db_version(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
    return JsonResponse({"version": version})
