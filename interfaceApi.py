from data import basic_success, jsonResponse, db, basic_failure, basic_error
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from bson.objectid import ObjectId
from external.sheet import get_scheduler_sheet
import calendar

monthDict = dict((v, k) for k,v in enumerate(calendar.month_name))
lasttouch_dict = (db.form.find_one({"operation": "channel"}, {"regex": True}))['regex']

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

        result = db.queries.insert_one(data)

        url = 'http://45.55.72.208/wadi/query?id='+str(result.inserted_id)
        row = ['Once', 'external', date, hour, minute, english, arabic, url]

        if 'debug' in data and data['debug'] is True:
            db.queries.remove({"_id": result.inserted_id})
            return jsonResponse({'success': True, 'data_received': data, 'row created': row})
        else:
            wrk_sheet = get_scheduler_sheet()
            size = len(wrk_sheet.get_all_values())
            wrk_sheet.insert_row(row, size+1)
            return jsonResponse({'success': True})

    except Exception, e:
        return basic_error(e)

def query(request):
    """
    Get the pipeline and options for the wadi system
    """
    id = request.GET['id']
    obj = db.queries.find_one({"_id": ObjectId(id)})
    if obj:
        options = obj['target_config']
        # Customisation ----------------- #
        if 'customer' not in options:
            options['mode'] = 'all'
        else:
            cust = options.pop('customer')
            if len(cust) == 2:
                options['mode'] = 'all'
            else:
                options['mode'] = cust[0]

        if 'purchase_month' in options:
            options['purchase_month'] = [monthDict[a] for a in options['purchase_month']]

        if 'channel' in options:
            options['channel'] = map(lambda k: lasttouch_dict[k], options['channel'])
        # ------------------------------- #
        pipeline = [k for k, v in options.items() if k != 'mode']
        pipeline.append('customer')

        return jsonResponse({"pipeline": pipeline, "options": options})
    else:
        raise Http404

def get_form_data(request):
    """
    Get the form
    """
    data = db.form.find({}, {"_id": False, "regex": False})
    return jsonResponse(data)

def status_updates(request):
    """
    Api endpoint which will be used by the wadi tool to submit status updates
    :param request:
    :return:
    """
    if request.method == 'GET':
        pass
    elif request.method == 'POST':
        pass
