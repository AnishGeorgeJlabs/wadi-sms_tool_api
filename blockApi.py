from data import basic_success, jsonResponse, db, basic_failure, basic_error
from django.http import Http404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
import csv


def _block_email(email):
    if email is not None and db.blocked_email.count({"email": email}) == 0:
        db.blocked_email.insert_one({
            "email": email,
            "timestamp": datetime.now()
        })
        return True
    return False


def _block_phone(phone, language):
    if language is None or language == '':
        lan_list = ['English', 'Arabic']
    elif isinstance(language, list):
        lan_list = language
    else:
        lan_list = language.split(',')

    flist = map(
        lambda l: 'English' if 'eng' in l.lower() else 'Arabic',
        lan_list
    )

    if db.blocked_phone.count({"phone": phone}) == 0:
        db.blocked_phone.insert_one({
            "phone": phone,
            "language": flist,
            "timestamp": datetime.now()
        })
        return True
    else:
        db.blocked_phone.update_one(
            {
                "phone": phone
            },
            {
                "$addToSet": {
                    "language": {"$each": flist}
                },
                "$set": {
                    "timestamp": datetime.now()
                }
            })
        return True


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
        main_data = request.GET
    else:
        main_data = json.loads(request.body)

    if 'data' in main_data:
        main_data = main_data['data']
    else:
        main_data = [main_data]

    res = []
    for data in main_data:
        d = {}
        # ----- Email ------ #
        if 'email' in data:
            d['email entry'] = _block_email(data['email'])

        # ----- Phone ------ #
        if 'phone' in data:
            d['phone entry'] = _block_phone(data['phone'], data.get('language'))

        res.append(d)

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


def _block_using_csv(cvlist, email_index=0, phone_index=1, lan_index=2):
    email_blocked = 0
    phone_blocked = 0

    for row in cvlist:
        if row[email_index] != '' and \
                _block_email(row[email_index]):
            email_blocked += 1

        if row[phone_index] != '' and \
                _block_phone(row[phone_index], row[lan_index]):
            phone_blocked += 1

    return email_blocked, phone_blocked


@csrf_exempt
def block_list_csv(request):
    if request.method == 'POST' and 'file' in request.FILES:
        reader = csv.reader(request.Files['file'])
        ecount, pcount = _block_using_csv(list(reader)[1:])
        return jsonResponse({"success": True, "emails blocked": ecount, "phones blocked": pcount})
    else:
        return jsonResponse({"success": False, "error": "No file"})

@csrf_exempt
def dummy_block_list_csv(request):
    if request.method == 'POST' and 'file' in request.FILES:
        reader = csv.reader(request.Files['file'])
        return jsonResponse({"success": True, "data": list(reader)[1:]})
    else:
        return jsonResponse({"success": False, "error": "No file"})
