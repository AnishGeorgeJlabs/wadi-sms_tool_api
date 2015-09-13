import calendar
import json

from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
from bson.objectid import ObjectId
from datetime import datetime

from data import db, jsonResponse, basic_failure

monthDict = dict((v, k) for k, v in enumerate(calendar.month_name))
lasttouch_dict = (db.form.find_one({"operation": "channel"}, {"regex": True}))['regex']


def get_pipeline(request):
    """
    Get the pipeline and options for the wadi system
    Refer docs/jobs_format.json

    Currently supports both the new and the old api. Future releases will deprecate the old
    pipeline method
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
            if isinstance(cust, list):
                if len(cust) == 2:
                    options['mode'] = 'all'
                else:
                    options['mode'] = cust[0].lower()
            else:
                if cust.lower() in ['both', 'all']:
                    options['mode'] = 'all'
                else:
                    options['mode'] = cust.lower()

        if 'language' in options and options['language'].lower() in ['both', 'all']:
            options.pop('language')

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
            # complete.pop('customer', '')
            for k, v in complete.items():
                if k in options:
                    pipeline[v['co_type']].append(k)
            pipeline['required'].append('customer')

        else:
            pipeline = [k for k, v in options.items() if k != 'mode']
            pipeline.append('customer')

        return jsonResponse({"pipeline": pipeline, "options": options})
    else:
        raise Http404


@csrf_exempt
def job_update(request):
    """
    API endpoint for sms tool to update job status and all of that
    Refer docs/status_update_format.json
    """

    if request.method == 'GET':
        query_dict = request.GET
    else:
        query_dict = json.loads(request.body)

    update = {}
    p_update = {}

    for key in ['t_id', 'file_link']:
        if key in query_dict:
            update['job.' + key] = query_dict[key]
    if 'status' in query_dict:
        p_update['job.status'] = {
            'status': query_dict['status'],
            'time': datetime.now()
        }

    for key in ['customer_count', 'sms_sent', 'sms_failed', 'errors']:
        if key in query_dict:
            update['job.report.' + key] = query_dict[key]

    if 'id' not in query_dict or not update or not p_update:
        return basic_failure
    else:
        oid = query_dict['id']
        if oid.endswith('_segment'):
            oid = oid.replace('_segment', '')
            collection = db.segment_jobs
        else:
            collection = db.jobs

        final_update = {}
        if update:
            final_update["$set"] = update
        if p_update:
            final_update["$push"] = p_update

        collection.update_one({"_id": ObjectId(oid)}, final_update)
        return jsonResponse({"success": True})
