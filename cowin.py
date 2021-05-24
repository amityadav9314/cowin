import hashlib
import json
import traceback

import time
from datetime import datetime
from types import SimpleNamespace

import requests


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


def check_dose1_and_get_centers():
    available_centers = []
    today = datetime.today().strftime("%d-%m-%Y")
    try:
        resp = get_cowin_response_by_district(district_id="651", date=today)
        # resp = get_cowin_response_by_pincode(pincode="201009", date=today)
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
    # pretty = Formatter()
    formatted_response = None
    do_loop = True
    while do_loop:
        print("\nChecking slots after %s seconds" % wait_duration)
        available_centers = check_dose1_and_get_centers()
        if len(available_centers) > 0:
            print("\tSending message on telegram")
            md5_hash_old = generate_hash(formatted_response)
            formatted_response = get_formatted_response(available_centers)
            md5_hash_new = generate_hash(formatted_response)
            if md5_hash_old != md5_hash_new:
                telegram_msg(formatted_response)
            else:
                print("\tNot telegraming as msg is same as old")
        else:
            print("\tSlots not available")

        print("\tSleeping for %s seconds" % wait_duration)
        # do_loop = False
        time.sleep(wait_duration)


def telegram_msg(msg):
    registered_users = [] # List of chat ids
    for user in registered_users:
        url = "https://api.telegram.org/bot{token}/sendMessage?text=%s&parse_mode=markdown&chat_id=%s"
        requests.get(url % (msg, user))


def generate_hash(msg):
    if not msg:
        return ""
    hash_object = hashlib.md5(msg.encode())
    md5_hash = hash_object.hexdigest()
    return md5_hash


if __name__ == "__main__":
    run(10)

