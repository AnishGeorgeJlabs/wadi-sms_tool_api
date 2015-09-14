import json

from django.views.decorators.csrf import csrf_exempt
from bson.json_util import ObjectId

from data import jsonResponse, db, basic_error, basic_success
from external.sheet import get_scheduler_sheet


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
        elif 'sheet_row' in job['job']:  # We know the exact row number
            worksheet.update_acell("J" + str(job['job']['sheet_row']), "Cancel")
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
                    worksheet.update_acell("J" + str(row), "Cancel")
                    break
        db.jobs.update_one({"_id": job['_id']}, {"$set": {"job.status": "Cancel"}})
        return basic_success

    except Exception, e:
        return basic_error(e)


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

    final = []
    for job in jobs:
        if isinstance(job['status'], list):
            job['status'] = job['status'][-1]['status']
        final.append(job)
    return jsonResponse({"success": True, "data": final})
