from data import jsonResponse, db, basic_error, basic_failure, basic_success
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from external.sheet import append_to_sheet
from bson.json_util import ObjectId

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
    final = []
    for job in lst:
        if str(job["ref_job"]) in master_cache:
            job.update(master_cache[str(job["ref_job"])])
        else:
            master = db.jobs.find_one({"_id": job["ref_job"]},
                                      {"_id": False, "job": True, "name": True, "description": True})
            if not master:
                continue
            else:
                umaster = {'name': master.get('name', 'Untitled'), 'description': master.get('description', '')}
                if 't_id' in master.get('job', {}):
                    umaster['t_id'] = master['job']['t_id']
                if 'customer_count' in master.get('job', {}).get('report', {}):
                    umaster['count'] = master['job']['report']['customer_count']

                master_cache[str(job["ref_job"])] = umaster
                job.update(umaster)
        final.append(job)

    return jsonResponse({"success": True, "data": final})


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
                append_to_sheet(row)
            return basic_success
    except Exception, e:
        return basic_error(e)

