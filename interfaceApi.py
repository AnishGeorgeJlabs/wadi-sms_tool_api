from data import jsonResponse, db, basic_error
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from external.sheet import get_scheduler_sheet


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
def formPost(request):
    """
    Form submission api
    """
    try:
        data = json.loads(request.body)
        # Do processing here

        campaign = data['campaign_config']
        date = campaign['date']
        time = datetime.strptime(campaign['time'], "%H:%M")
        hour = time.hour
        minute = time.minute
        english = campaign['text']['english']
        arabic = campaign['text']['arabic']
        if len(english.strip()) == 0:
            english = '_'
        if len(arabic.strip()) == 0:
            arabic = '_'
        data['timestamp'] = datetime.now()

        result = db.jobs.insert_one(data)

        url = 'http://45.55.72.208/wadi/query?id=' + str(result.inserted_id)
        row = ['Once', 'external', date, hour, minute, english, arabic, url]

        if 'debug' in data and data['debug'] is True:
            db.jobs.remove({"_id": result.inserted_id})
            return jsonResponse({'success': True, 'data_received': data, 'row created': row})
        else:
            wrk_sheet = get_scheduler_sheet()
            size = len(wrk_sheet.get_all_values())
            wrk_sheet.insert_row(row, size + 1)
            return jsonResponse({'success': True})

    except Exception, e:
        return basic_error(e)


def get_form_data(request):
    """
    Get the form
    """
    data = db.form.find({}, {"_id": False, "regex": False})
    return jsonResponse(data)
