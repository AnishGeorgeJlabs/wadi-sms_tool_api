from data import db, jsonResponse
from django.http import Http404
import calendar
from datetime import datetime
from bson.objectid import ObjectId

monthDict = dict((v, k) for k,v in enumerate(calendar.month_name))
lasttouch_dict = (db.form.find_one({"operation": "channel"}, {"regex": True}))['regex']

def get_pipeline(request):
    """
    Get the pipeline and options for the wadi system
    """
    id = request.GET['id']
    obj = db.jobs.find_one({"_id": ObjectId(id)})
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
