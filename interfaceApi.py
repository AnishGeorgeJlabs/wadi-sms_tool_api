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
def form_post(request):
    """ Form submission api """
    try:
        data = json.loads(request.body)
        # Do processing here

        campaign = data['campaign_config']
        repeat = campaign.get('repeat', 'Once')
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
        data['name'] = data.get('name', 'Untitled')             # Add name and description
        data['description'] = data.get('description', '')
        data['job'] = {'status': 'Pending'}                     # Add the job subdocument, will be used later

        debug = data.pop('debug', False)

        result = db.jobs.insert_one(data)           # >> Insertion here

        # url = 'http://45.55.72.208/wadi/query?id=' + str(result.inserted_id)
        row = [repeat, 'external', date, hour, minute, english, arabic, str(result.inserted_id)]

        if debug:
            # db.jobs.remove({"_id": result.inserted_id})
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

def get_sample_form_data(request):
    """ Just for testing """
    data = db.form.find({"operation": {"$in": ["item_status", "payment_method", "repeat_buyer"]}}, {"_id": False, "regex": False})
    return jsonResponse(data)


def get_jobs(request):
    jobs = db.jobs.aggregate([
        {"$match": {"job": {"$exists": True}}},
        {"$sort": {"timestamp": -1}},
        {"$project": {
            "name": 1, "description": 1,
            "_id": 0,
            "id": "$_id.$oid",
            "status": "$job.status",
            "file": "$job.file_link",
            "t_id": "$job.t_id",
            "count": "$job.report.customer_count"
        }}
    ])
    return jsonResponse({"success": True, "data": list(jobs)})
