import requests
import os
import json

def getApicCookie(hostname, username, password, proxies):
    apiLoginUrl = "https://" + hostname + "/api/aaaLogin.json?"
    loginPayload = {"aaaUser":{"attributes": {"name": username, "pwd": password}}}
    r = requests.post(apiLoginUrl, json=loginPayload, proxies=proxies, verify=False)
    result = json.loads(r.text)
    r.close()
    apiCookie = result['imdata'][0]['aaaLogin']['attributes']['token']
    return apiCookie

def apicGetRequest(url, apicCookie, proxies):
    cookie = {"APIC-cookie": apicCookie}
    r = requests.get(url, cookies=cookie, proxies=proxies, verify=False)
    result = json.loads(r.text)
    r.close()
    return result