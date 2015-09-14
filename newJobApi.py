import json
from datetime import datetime

from django.views.decorators.csrf import csrf_exempt

from data import jsonResponse, db, basic_error
from external.sheet import append_to_sheet


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

        data['name'] = data.get('name', 'Untitled')  # Add name and description
        data['description'] = data.get('description', '')
        data['job'] = {'status': [{'status': 'Pending', 'time': datetime.now()}]}  # Add the job subdocument, will be used later
        debug = data.pop('debug', False)

        data['timestamp'] = datetime.now()
        result = db.jobs.insert_one(data)  # >> Insertion here
        row.append(str(result.inserted_id))

        if debug:
            # db.jobs.remove({"_id": result.inserted_id})
            return jsonResponse({'success': True, 'data_received': data, 'row created': row})
        else:
            append_to_sheet(row)
            return jsonResponse({'success': True})

    except Exception, e:
        return basic_error(e)


def get_form_data(request):
    """
    Get the form
    """
    data = db.form.find({"enabled": True}, {"_id": False, "regex": False, "enabled": False})
    return jsonResponse(data)


def get_sample_form_data(request):
    """ Just for testing """
    data = db.form.find({"operation": {"$in": ["item_status", "payment_method", "repeat_buyer"]}},
                        {"_id": False, "regex": False})
    return jsonResponse(data)


@csrf_exempt
def schedule_testing_send(request):
    """ Create a testing campaign which schedules sms to be sent to the selected user in the other sheet """
    try:
        data = json.loads(request.body)
        english = data.get('english', '_')
        arabic = data.get('arabic', '_')
        row = ['Immediately', 'testing', '_', '', '_', '_', english, arabic]
        append_to_sheet(row)
        return jsonResponse({"success": True})

    except Exception, e:
        return basic_error(e)
