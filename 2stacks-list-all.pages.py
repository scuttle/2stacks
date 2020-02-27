import config
import json
import requests
from xmlrpc.client import ServerProxy
# import logging
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    for record in event['Records']:
        callback_url = record['messageAttributes']['callback_url']['stringValue']
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        # logger.info("Pinging Wikidot for info on " + wikidot_site)
        s = ServerProxy('https://' + config.wikidot_username + ':' + config.wikidot_api_key + '@www.wikidot.com/xml-rpc-api.php')
        headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
        pageslist = s.pages.select({'site': wikidot_site})
        # logger.info("Got " + str(len(pageslist)) + " pages back, sending to SCUTTLE...")
        j = json.dumps(pageslist)
        r = requests.put(callback_url + '/2stacks/pages/manifest', data=j, headers=headers)
        # logger.info("SCUTTLE sez: " + r.text)
    return {
        'job': 'complete'
    }