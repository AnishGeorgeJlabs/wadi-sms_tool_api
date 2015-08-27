from data import cl_blocked, basic_success, jsonResponse, db
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def test(request):
    if request.method == "GET":
        extra = {
            "method": "GET",
            "requestData": request.GET
        }
    else:
        extra = {
            "method": "POST",
            "requestData": request.body
        }
    return jsonResponse({
        "success": True,
        "Message": "Test api, ECHO",
        "extra": extra
    })

@csrf_exempt
def get_conf(request, namespace, key):
    """ Get configuration values for the various wadi tools
    :param request:
    :param namespace:
    :param key:
    :return:
    """
    if request.method == 'GET':
        res = db.configuration.find_one({"namespace": namespace})

        if not res:
            return jsonResponse({"success": False, "error": "Wrong namespace: "+namespace})

        if len(key) == 0:
            return jsonResponse({"success": True, "namespace": namespace, "keys": res['conf'].keys()})
        if key not in res['conf']:
            return jsonResponse({"success": False, "error": "Wrong key: "+key})
        else:
            return jsonResponse({"success": True, "value": res['conf'][key]})
    else:   # Updation not support just yet
        raise Http404
