import hashlib
import json
import os
import time
import traceback
from datetime import datetime
from enum import Enum
from types import SimpleNamespace

import requests


class SearchType(Enum):
    PINCODE = 1
    DISTRICT = 2


district_id_chat_ids_map = {
    651: [],
}

pincode_chat_ids_map = {
    110077: [],
    110075: [],
}


def get_cowin_response_by_district(district_id, date):
    headers = {
        'User-Agent':
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'
    }
    url = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id=%s&date=%s" % (
        district_id, date)
    r = requests.get(
        url,
        headers=headers
    )

    res = r.text
    parsed_res = json.loads(res, object_hook=lambda d: SimpleNamespace(**d))
    return parsed_res


def get_cowin_response_by_pincode(pincode, date):
    headers = {
        'User-Agent':
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'
    }
    url = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin?pincode=%s&date=%s" % (
        pincode, date)
    r = requests.get(
        url,
        headers=headers
    )

    res = r.text
    parsed_res = json.loads(res, object_hook=lambda d: SimpleNamespace(**d))
    return parsed_res


def check_dose1_and_get_centers(pincode=None, district_id=None):
    available_centers = []

    if not any([pincode, district_id]):
        return available_centers

    if all([pincode, district_id]):
        raise Exception("Only one of pincode or district_id exptected")

    today = datetime.today().strftime("%d-%m-%Y")

    try:
        if pincode:
            resp = get_cowin_response_by_pincode(pincode=pincode, date=today)
        else:
            resp = get_cowin_response_by_district(district_id=district_id, date=today)
    except Exception as e:
        print("Exception occurred")
        print(traceback.format_exc())
        resp = None

    if not resp:
        return available_centers

    for center in resp.centers:
        date_list = []
        center_name = center.address + " -> " + center.name
        center_dict = {}
        for session in center.sessions:
            if session.available_capacity_dose1 > 1 and session.min_age_limit == 18:
                msg = "%s, Slots: *%s*, Age: %s" % (
                    session.date, session.available_capacity_dose1, session.min_age_limit)
                date_list.append(msg)
        if len(date_list) > 0:
            center_dict[center_name] = date_list
            available_centers.append(center_dict)

    return available_centers


def get_formatted_response(available_centers):
    resp = ""
    for center in available_centers:
        for k in center:
            val = center[k]
            center_resp = "%s" % k
            center_resp += "\n"
            for date in val:
                center_resp += "\t"
                center_resp += date
                center_resp += "\n"
            resp += center_resp
        resp += "\n"
    return resp


def run(wait_duration=60):
    do_loop = True
    pincode_formatted_response = None
    district_formatted_response = None
    while do_loop:
        # TODO Make the below calls parallel
        try:
            pincode_formatted_response = hit_api_and_telegram_slots(
                SearchType.PINCODE, pincode_chat_ids_map,
                pincode_formatted_response, wait_duration
            )
            district_formatted_response = hit_api_and_telegram_slots(
                SearchType.DISTRICT, district_id_chat_ids_map,
                district_formatted_response, wait_duration
            )
        except Exception as e:
            error = None
            if hasattr(e, 'message'):
                error = e.message
            msg = "Code kahin fata h, dekh use jaldi se. %s" % error
            users = []
            telegram_msg(msg, users)
        print("Sleeping for %s seconds" % wait_duration)
        print("=" * 100)
        # do_loop = False
        time.sleep(wait_duration)


def hit_api_and_telegram_slots(search_type, chat_map, formatted_response, wait_duration):
    for k in chat_map:
        code = k
        registered_users = chat_map[k]
        print("\nChecking slots for %s: %s after %s seconds" % (search_type, code, wait_duration))
        if search_type == SearchType.PINCODE:
            available_centers = check_dose1_and_get_centers(pincode=str(code))
        else:
            available_centers = check_dose1_and_get_centers(district_id=str(code))
        if len(available_centers) > 0:
            print("\tSending message on telegram")
            md5_hash_old = generate_hash(formatted_response)
            formatted_response = get_formatted_response(available_centers)
            md5_hash_new = generate_hash(formatted_response)
            if md5_hash_old != md5_hash_new:
                telegram_msg(formatted_response, registered_users)
            else:
                print("\tNot telegraming as msg is same as old")
        else:
            print("\tSlots not available")
    return formatted_response


def telegram_msg(msg, registered_users):
    token = os.environ["telegram_bot_token"]
    for user in registered_users:
        url = "https://api.telegram.org/bot%s/sendMessage?text=%s&parse_mode=markdown&chat_id=%s" % (token, msg, user)
        requests.get(url)


def generate_hash(msg):
    if not msg:
        return ""
    hash_object = hashlib.md5(msg.encode())
    md5_hash = hash_object.hexdigest()
    return md5_hash


if __name__ == "__main__":
    run(30)

