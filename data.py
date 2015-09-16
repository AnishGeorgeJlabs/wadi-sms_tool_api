import pymongo
from django.http import HttpResponse
from bson.json_util import dumps

# Utility methods
def jsonResponse(obj):
    return HttpResponse(dumps(obj), content_type='application/json')


basic_success = jsonResponse({"success": True})
basic_failure = jsonResponse({"success": False})

def failed_reason(r):
    return jsonResponse({"success": False, "reason": r})

def basic_error(e):
    return jsonResponse({
        "success": False,
        "error": str(e)
    })

unimplemented_error = failed_reason("Method not implemented")

# Data base
dbclient = pymongo.MongoClient("45.55.232.5:27017")
dbclient.wadi.authenticate('wadiAdmin', 'secureWadiOp', mechanism='MONGODB-CR')
db = dbclient.wadi

cl_blocked = db.blocked
