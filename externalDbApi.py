from django.views.decorators.csrf import csrf_exempt
from data import basic_error, basic_success, db, jsonResponse
import requests
import json

@csrf_exempt
def external_data(request):
    try:
        pass
    except Exception, e:
        return basic_error(e)
