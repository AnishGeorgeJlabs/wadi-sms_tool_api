from django.views.decorators.csrf import csrf_exempt
from data import basic_error, basic_success, db, jsonResponse
import requests
import json

@csrf_exempt
def external_data(request):
    """
    GET: Get a list of all the external databases
        :return: {
            success: boolean
            data: [list of {
                    name: <name of db>
                    description: <possibly empty description>
                    oid: <object ID>
                  }]

    JSON POST: Submit a new external database file
        :json body: {
            > file_link: <valid url of direct file download>,
            > name: <unique name for the external db,
            ? description: <optional description for the db
        }
    """
    try:
        if request.method == 'GET':
            res = []
            for d in db.external_data.find():
                d['_id'] = str(d['_id'])
                res.append(d)
            return jsonResponse({"success": True, "data": res})
        elif request.method == 'POST':
            data = json.loads(request.body)
            file_link = data['file_link']
            try:
                r = requests.head(file_link)
                if r.status_code != 200:
                    return jsonResponse({"success": False, "reason": 'File Does not exist'})
            except:
                return jsonResponse({"success": False, "error": "Malformed URL"})

            name = data['name']
            description = data.get('description', '')
            if db.external_data.count({"name": name}) > 0:
                return jsonResponse({"success": False, "reason": 'The given name already exists'})
            else:
                db.external_data.insert_one({
                    "name": name,
                    "description": description,
                    "file_link": file_link
                })
                return basic_success
        else:
            return jsonResponse({"success": False, "error": "Unimplemented Method"})
    except Exception, e:
        return basic_error(e)
