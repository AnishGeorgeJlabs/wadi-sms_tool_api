from data import jsonResponse, db, basic_error, basic_failure, basic_success
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
        if data.get('segmented', False):
            row = ['No Send', 'external', '_', '', '1', '1', '_', '_']
            data.pop('campaign_config', {})
        else:
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

            row = [repeat, 'external', start_date, end_date, hour, minute, english, arabic]


        data['name'] = data.get('name', 'Untitled')             # Add name and description
        data['description'] = data.get('description', '')
        data['job'] = {'status': 'Pending'}                     # Add the job subdocument, will be used later
        debug = data.pop('debug', False)

        data['timestamp'] = datetime.now()
        result = db.jobs.insert_one(data)           # >> Insertion here
        row.append(str(result.inserted_id))

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
            "name": 1, "description": 1, "timestamp": 1, "segmented": 1,
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

def get_segment_jobs(request):
    master_cache = {}           # A cache of master jobs data

    lst = db.segment_jobs.aggregate([
        {"$group": {
            "_id": {
                "ref_job": "$ref_job",
                "timestamp": "$timestamp"
            },
            "segments": {
                "$push": {
                    "status": "$job.status",
                    "english": "$text.english",
                    "arabic": "$text.arabic",
                    "date": "$date",
                    "num": "$segment_number"
                }
            }
        }},
        {"$project": {
            "_id": 0, "segments": 1,
            "ref_job": "$_id.ref_job",
            "timestamp": "$_id.timestamp"
        }},
        {"$sort": {"timestamp": -1}}
    ])
    debug_message = ""
    final = []
    for job in lst:
        if str(job["ref_job"]) in master_cache:
            debug_message += "master cache, "
            job.update(master_cache[str(job["ref_job"])])
        else:
            master = db.jobs.find_one({"_id": job["ref_job"]},
                                      {"_id": False, "job": True})
            if not master:
                lst.pop(job)
                debug_message += "Removing job: "+json.dumps(job)
            else:
                debug_message += "Got master for job"
                umaster = {'name': master.get('name', 'Untitled'), 'description': master.get('description', '')}
                if 't_id' in master.get('job', {}):
                    umaster['t_id'] = master['job']['t_id']
                if 'customer_count' in master.get('job', {}).get('report', {}):
                    umaster['count'] = master['job']['report']['customer_count']

                master_cache[str(job["ref_job"])] = umaster
                job.update(umaster)
                final.append(job)

    return jsonResponse({"success": True, "result": final, "data": lst, "debug": debug_message, "original": orig_lst})

def _append_to_sheet(row):
    wrk_sheet = get_scheduler_sheet()
    size = len(wrk_sheet.get_all_values())
    wrk_sheet.insert_row(row, size + 1)

@csrf_exempt
def post_segment_form(request):
    try:
        data = json.loads(request.body)
        total = data['total']
        segments = data['segments']
        ref_job = data['ref_job']
        t_id = data['t_id']
        if db.jobs.count({"_id": ObjectId(ref_job)}) == 0:
            return basic_failure

        # Step 1: Setup limits
        slen = len(segments)
        sub_size = int(total) // slen

        limits = [
            [sub_size*i, sub_size*(i+1)] for i in range(0, slen)
        ]
        limits[-1][1] = total

        # Step 2, create db jobs for each segment
        result = []
        sheet_rows = []
        timestamp = datetime.now()
        for i, segment in enumerate(segments):
            date = segment['date']
            res = db.segment_jobs.insert_one({
                "ref_job": ObjectId(ref_job),
                "timestamp": timestamp,
                "segment_number": i+1,
                "limits": {
                    "lower": limits[i][0],
                    "upper": limits[i][1]
                },
                "text": {
                    "english": segment['english'],
                    "arabic": segment['arabic']
                },
                "date": date,
                "job": {
                    "status": "pending"
                }
            })
            oid_col = str(res.inserted_id) + ("_segment,%i,%i,%i" % (t_id, limits[i][0], limits[i][1]))     # Added _segment
            result.append(oid_col)

            # Creating the row
            date = datetime.fromtimestamp(date / 1000)
            start_date = date.strftime("%m/%d/%Y")
            hour = date.hour
            minute = date.minute

            row = ['Once', 'segment', start_date, '', hour, minute, segment['english'], segment['arabic'], oid_col]
            sheet_rows.append(row)

        if data.get('debug', False):
            return jsonResponse({"success": True, "result": sheet_rows})
        else:
            for row in sheet_rows:
                _append_to_sheet(row)
            return basic_success
    except Exception, e:
        return basic_error(e)



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

        search.update({"job": {"$exists": True}})
        job = db.jobs.find_one(search, {"job": True})

        worksheet = get_scheduler_sheet()

        if not job:
            return jsonResponse({"success": False, "error": "Cannot find job"})
        elif 'sheet_row' in job['job']: # We know the exact row number
            worksheet.update_acell("J"+str(job['job']['sheet_row']), "Cancel")
        else:
            full = worksheet.get_all_records()
            if t_id == 0:
                t_id = job['job'].get('t_id', 0)

            if t_id == 0:
                return jsonResponse({"success": False, "error": "Need t_id"})

            t_id = str(t_id)
            for record in full:
                if t_id == str(record['ID']):
                    row = full.index(record) + 2
                    worksheet.update_acell("J"+str(row), "Cancel")
                    break
        db.jobs.update_one({"_id": job['_id']}, {"$set": {"job.status": "Cancel"}})
        return basic_success

    except Exception, e:
        return basic_error(e)
