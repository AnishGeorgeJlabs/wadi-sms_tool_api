from django.views.decorators.csrf import csrf_exempt
from data import basic_error, basic_success, db, jsonResponse
import requests
import json

def _correct_list(lst):
    return map(
        lambda k: [k['phone'].strip().replace('+','').replace('-',''), k['language'], k['country']],
        lst
    )

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
            pipeline = [
                {"$project": {"_id": 0, "phone": 1, "language": 1, "country": 1, "segment_number": 1}}
            ]
            base_match = {}
            # ---------- segment number -------------------
            seg_str = request.GET.get('seg_num', '')
            if seg_str:
                try:
                    seg_nums = [int(s) for s in seg_str.split(',')]
                except:
                    seg_nums = [1]
                base_match['segment_number'] = {"$in": seg_nums}
            # ---------------------------------------------

            # ---------- country --------------------------
            country = request.GET.get('country', '').lower()
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

            language = [x.strip() for x in request.GET.get('language', 'English,Arabic').split(',')]
            if len(language) == 1 and language[0].lower() != 'both':
                lflag = True
                if 'eng' in language[0].lower():
                    lan = 'English'
                else:
                    lan = 'Arabic'
                pipeline.append({"$match": {"language": lan}})
            else:
                lflag = False

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

        elif request.method == "POST":
            return basic_error("Unimplemented Method")
            pass
        else:
            return basic_error("Unimplemented Method")
    except Exception, e:
        raise
        return basic_error(e)
