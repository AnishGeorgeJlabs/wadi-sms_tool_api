import json

from django.views.decorators.csrf import csrf_exempt

from data import jsonResponse, db, basic_error


@csrf_exempt
def login(request):
    """
    Simple login protocol
    method: POST
    post data: { username: string, password: <md5 hash> String }
    """
    try:
        data = json.loads(request.body)
        if db.credentials.count({"username": data['username'], "password": data['password']}) > 0:
            return jsonResponse({"success": True})
        else:
            return jsonResponse({"success": False})
    except Exception, e:
        return basic_error(e)


@csrf_exempt
def change_pass(request):
    """
    Simple change password protocol
    """
    try:
        data = json.loads(request.body)
        res = db.credentials.update_one({"username": data['username'], "password": data['old_pass']},
                                        {"$set": {"password": data['new_pass']}})
        return jsonResponse({"success": bool(res.modified_count)})
    except Exception, e:
        return basic_error(e)