from datetime import datetime

from django.views.decorators.csrf import csrf_exempt
import json

from data import basic_error, db, jsonResponse, basic_success


def _correct_list(lst):
    return map(
        lambda k: [k['phone'].strip().replace('+','').replace('-',''), k['language'], k['country']],
        lst
    )

def count_external_data(request):
    try:
        base_counts = db.external_data.aggregate([
            {"$group": {"_id": "$segment_number", "count": {"$sum": 1}}}
        ])
        final = {}
        unsegmented = 0
        for doc in base_counts:
            if doc['_id'] is None:
                unsegmented = doc['count']
            else:
                final[doc['_id']] = doc['count']
        return jsonResponse({"success": True, "data": {
            'segmented': final,
            'unsegmented': unsegmented
        }})
    except Exception, e:
        return basic_error(e)


def _external_data_get(options):
    pipeline = [
        {"$project": {"_id": 0, "phone": 1, "language": 1, "country": 1, "segment_number": 1}}
    ]
    base_match = {}
    # ---------- segment number -------------------
    seg_str = options.get('seg_num', options.get('segment', ''))
    if seg_str:
        try:
            seg_nums = [int(s) for s in seg_str.split(',')]
        except:
            seg_nums = [1]
        base_match['segment_number'] = {"$in": seg_nums}
    # ---------------------------------------------

    # ---------- country --------------------------
    country = options.get('country', '').lower()
    if country and country != 'both':
        if country == 'uae':
            country = 'UAE'
        else:
            country = 'KSA'

        base_match['country'] = country
    # ---------------------------------------------

    if base_match:
        pipeline.append({"$match": base_match})
    pipeline.append({"$unwind": "$language" })

    language = [x.strip() for x in options.get('language', 'English,Arabic').split(',')]
    if len(language) == 1 and language[0].lower() != 'both':
        lflag = False
        if 'eng' in language[0].lower():
            lan = 'English'
        else:
            lan = 'Arabic'
        pipeline.append({"$match": {"language": lan}})
    else:
        lflag = True

    base_result = db.external_data.aggregate(pipeline)
    if not lflag:
        return jsonResponse({"success": True, "data": _correct_list(list(base_result)), "lflag": lflag})
    else:
        collision_set = {}
        for customer in base_result:
            ph = customer['phone']
            if ph not in collision_set or customer['language'] == 'Arabic':
                collision_set[ph] = customer
        return jsonResponse({"success": True, "data": _correct_list(collision_set.values()), "lflag": lflag})


def _external_data_post(options):
    def _create_job(segment):
        return {
            "english": segment['english'],
            "arabic": segment['arabic'],
            "date": segment['date'],
            "language": segment['language'],
            "country": segment['country'],
            "status": [{
                "status": "Pending",
                "time": datetime.now()
            }]
        }

    # IMPORTANT, the Language or Country cannot have commas in it
    def _create_sheet_row (seg_data):
        seg_num = seg_data.get('segment_number')
        if not seg_num:
            return None
        else:
            segment = seg_data['jobs'][-1]
            job_num = len(seg_data['jobs']) - 1

            dt = datetime.fromtimestamp(segment['date'] / 1000)
            oid = str(seg_data['_id'])
            oid += "_%i_esegment" % job_num
            opts = "seg_num=%i&language=%s&country=%s" % (job_num, segment['language'], segment['country'])
            return [
                'Once', 'segment', dt.strftime("%m/%d/%Y"), '',
                dt.hour, dt.minute, segment['english'], segment['arabic'],
                oid + ',' + opts
            ]

    job_col = db.segment_external
    segments = options.get('segments', [])
    if len(segments) == 0:
        return jsonResponse({"success": False, "reason": "No segments given"})

    if options.get('is_new', False):
        try:
            orig_seg = seg_num = max(db.external_data.distinct("segment_number"))
        except:
            orig_seg = seg_num = 0
        insertions = []
        # Step 1, create Jobs in segment_external
        for segment in segments:
            seg_num += 1
            insertions.append({
                "segment_number": seg_num,
                "jobs": [_create_job(segment)]
            })
        job_col.insert_many(insertions)

        # Step 2, segment external database members
        unsegmented_count = db.external_data.count({"segment_number": {"$exists": False}})
        total_segs = len(segments)
        user_per_seg = unsegmented_count // total_segs
        for i in range(total_segs):
            orig_seg += 1
            for j in range(user_per_seg):
                db.external_data.update_one({"segment_number": {"$exists": False}},
                                            {"$set": {"segment_number": orig_seg}})

        db.external_data.update_one({"segment_number": {"$exists": False}},
                                    {"$set": {"segment_number": orig_seg}})
        sheet_rows = [ _create_sheet_row(insertion) for insertion in insertions]
    else:
        for segment in segments:
            job = _create_job(segment)
            job_col.update_one({"segment_number": segment['segment_number']}, {"$push": {"jobs": job}})
        all_jobs = job_col.find({"segment_number": {"$in": [s['segment_number'] for s in segments]}})
        sheet_rows = [ _create_sheet_row(seg_data) for seg_data in all_jobs]

    # Last step, add stuff to sheet todo
    return jsonResponse({"success": True, "rows": sheet_rows})

@csrf_exempt
def external_data(request):
    """
    GET: Returns the external customers list as a [list of [phone, language]]
         parameters:
            seg_num: int,   >> Segment number, if not present, returns the entire list
            language: String, >> English,Arabic comma separated, if not, then both with arabic being preferred
            country: String, >> KSA or UAE
    """
    try:
        if request.method == "GET":
            return _external_data_get(request.GET)
        elif request.method == "POST":
            return _external_data_post(json.loads(request.body))
        else:
            return basic_error("Unimplemented Method")
    except Exception, e:
        raise
        return basic_error(e)
