from data import jsonResponse, db, basic_error
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from external.sheet import get_scheduler_sheet
from bson.json_util import ObjectId


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

        start_date = datetime.fromtimestamp(campaign['start_date'] / 1000).strftime("%m/%d/%Y")
        if 'end_date' in campaign:
            end_date = datetime.fromtimestamp(campaign['end_date'] / 1000).strftime("%m/%d/%Y")
        else:
            end_date = ''

        time = datetime.fromtimestamp(campaign['time'] / 1000)
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
        row = [repeat, 'external', start_date, end_date, hour, minute, english, arabic, str(result.inserted_id)]

        if debug:
            # db.jobs.remove({"_id": result.inserted_id})
            return jsonResponse({'success': True, 'data_received': data, 'row created': row})
        else:
            _append_to_sheet(row)
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
            "name": 1, "description": 1, "timestamp": 1,
            "start_date": "$campaign_config.start_date",
            "end_date": "$campaign_config.end_date",
            "time": "$campaign_config.time",
            "repeat": "$campaign_config.repeat",
            "status": "$job.status",
            "file": "$job.file_link",
            "t_id": "$job.t_id",
            "count": "$job.report.customer_count"
        }}
    ])
    return jsonResponse({"success": True, "data": list(jobs)})

def _append_to_sheet(row):
    wrk_sheet = get_scheduler_sheet()
    size = len(wrk_sheet.get_all_values())
    wrk_sheet.insert_row(row, size + 1)

@csrf_exempt
def schedule_testing_send(request):
    try:
        data = json.loads(request.body)
        english = data.get('english', '_')
        arabic = data.get('arabic', '_')
        row = ['Immediately', 'testing', '_', '', '_', '_', english, arabic]
        _append_to_sheet(row)
        return jsonResponse({"success": True})

    except Exception, e:
        return basic_error(e)

@csrf_exempt
def cancel_job(request):
    """
    Cancel the given job
    json body: { id: Object id, t_id: tool id }
    """
    try:
        data = json.loads(request.body)
        oid = data.get('id', data.get('oid', data.get('_id')))
        t_id = int(data.get('t_id', 0))
        if oid is not None:
            search = {"_id": ObjectId(oid)}
        elif t_id != 0:
            search = {"job.t_id": t_id}
        else:
            return jsonResponse({"success": False, "error": "Cannot find job, please give either an id or a t_id"})

        search.update({"job.sheet_row": {"$exists": True}})
        job = db.jobs.find_one(search, {"job.sheet_row": True, "_id": False})

        worksheet = get_scheduler_sheet()

        if job: # We know the exact row number
            worksheet.update_acell("J"+str(job['job']['sheet_row']), "Cancel")
        else:
            full = worksheet.get_all_records()
            if t_id == 0:
                return jsonResponse({"success": False, "error": "Need the t_id in this case"})
            t_id = str(t_id)
            for record in full:
                if t_id == record['ID']:
                    row = full.index(record) + 2
                    worksheet.update_aceel("J"+str(row), "Cancel")
                    break
        return jsonResponse({"success": True})

    except Exception, e:
        return basic_error(e)