from data import db, jsonResponse
from django.http import Http404
import calendar
from datetime import datetime
import json
from bson.objectid import ObjectId

monthDict = dict((v, k) for k,v in enumerate(calendar.month_name))
lasttouch_dict = (db.form.find_one({"operation": "channel"}, {"regex": True}))['regex']

def get_pipeline(request):
    """
    Get the pipeline and options for the wadi system
    Refer docs/jobs_format.json
    """
    id = request.GET['id']
    obj = db.jobs.find_one({"_id": ObjectId(id)})
    if obj:
        options = obj['target_config']
        if not options or not isinstance(options[options.keys()[0]], dict):
            new_api = False
        else:
            new_api = True
            complete = options.copy()
            options = dict(map(
                lambda kv: (kv[0], kv[1]['value']),
                options.items()
            ))

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

        if new_api:
            pipeline = {
                'required': [],
                'additional': []
            }
            complete.pop('customer', '')
            for k, v in complete.items():
                pipeline[v['co_type']].append(k)
            pipeline['additional'].append('customer')

        else:
            pipeline = [k for k, v in options.items() if k != 'mode']
            pipeline.append('customer')

        return jsonResponse({"pipeline": pipeline, "options": options})
    else:
        raise Http404

def job_update(request):
    """
    API endpoint for sms tool to update job status and all of that
    Refer docs/status_update_format.json
    """

    if request.method == 'GET':
        query_dict = request.GET
    else:
        query_dict = json.loads(request.body)

    if 'id' in query_dict:
        search = {"_id": ObjectId(query_dict['id'])}
    else:
        return jsonResponse({"success": False})

    update = {}

    for key in ['status', 't_id', 'file_link']:
        if key in query_dict:
            update['job.'+key] = query_dict[key]

    for key in ['customer_count', 'sms_sent', 'sms_failed', 'errors']:
        if key in query_dict:
            update['job.report.'+key] = query_dict[key]

    if not update:
        return jsonResponse({"success": False})
    else:
        db.jobs.update_one(search, {"$set": update})
        return jsonResponse({"success": True})

