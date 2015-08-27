from data import basic_success, jsonResponse, db, basic_failure, basic_error
from django.http import Http404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime

@csrf_exempt
def block(request):
    """
    GET/POST based method for blocking a phone and/or email
    Parameters: (?: optional, +: required)
        ? email: email address to block
        ? phone: phone number to block
        ? language: a list of one or more languages, separated by comma, to be blocked for given phone.
            Only makes sense when the phone key is given. Supports English, Arabic
        ? pretty (true or false): If set to true, then results in an http response (yet to be styled),
            useful for user links. If set to false or not given, then results in a json response

    tested on Wed, 26 Aug, 10:45 PM
    """
    if request.method == 'GET':
        data = request.GET
    else:
        data = json.loads(request.body)

    res = {}
    # ----- Email ------ #
    if 'email' in data and db.blocked_email.count({"email": data['email']}) == 0:
        resEm = db.blocked_email.insert_one({
            "email": data['email'],
            "timestamp": datetime.now()
        })
        res['email entry'] = str(resEm.inserted_id)

    # ----- Phone ------ #
    if 'phone' in data:
        ph = data['phone']
        if 'language' in data:
            if isinstance(data['language'], list):
                lan_list = data['language']
            else:
                lan_list = data['language'].split(',')
            language = map(
                lambda l: 'English' if 'eng' in l.lower() else 'Arabic',
                lan_list
            )
        else:
            language = ['English', 'Arabic']

        if db.blocked_phone.count({"phone": ph}) == 0:
            resPh = db.blocked_phone.insert_one({
                "phone": ph,
                "language": language,
                "timestamp": datetime.now()
            })
            res['phone entry'] = str(resPh.inserted_id)
        else:
            db.blocked_phone.update_one(
                {
                    "phone": ph
                },
                {
                    "$addToSet": {
                        "language": {"$each": language}
                    },
                    "$set": {
                        "timestamp": datetime.now()
                    }
                })
            res['phone entry'] = 'Updated'
    if 'pretty' in data and data['pretty'] not in [False, 'false']:
        if not res:
            return HttpResponse("There seems to be some problem. You seem to be already unsubscribed")
        else:
            return HttpResponse("You have been successfully unsubscribed")
    else:
        if not res:
            return jsonResponse({"success": False})
        else:
            return jsonResponse({"success": True, "result": res})


def get_blocked(request):
    """
    GET based method for retrieving blocked [phone, language] or email list
    Parameters: (?: optional, +: required)
        + type (email or phone): Get the block list type. If not present, defaults to email.
            Throws error for any other type

    Response:
        1. For type=email:
            success: true,
            data: [list of emails]
        2. For type=phone:
            success: true,
            data: [list of [phone, language]]
    Tested on Wed, 26 Aug, 11:05 PM
    """
    type = request.GET.get('type', 'email')

    if type == 'email':
        return jsonResponse({
            "success": True,
            "data": [
                x['email'] for x in
                db.blocked_email.find({}, {"_id": False, "timestamp": False})
            ]
        })
    elif type == 'phone':
        return jsonResponse({
            "success": True,
            "data": [
                [x['phone'], x['language']] for x in
                db.blocked_phone.aggregate([
                    {"$project": {"_id": False, "phone": True, "language": True}},
                    {"$unwind": "$language"}
                ])
            ]
        })
    else:
        return jsonResponse({
            "success": False,
            "error": "Unknown type"
        })
