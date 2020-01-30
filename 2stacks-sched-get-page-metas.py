import json
import config
import helpers
import requests
from time import sleep
from xmlrpc.client import ServerProxy

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    for record in event['Records']:
        callback_url = record['messageAttributes']['callback_url']['stringValue']
        slugs = record['messageAttributes']['page_slug']['stringValue'].split(',')
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        
        # A typical payload has 100 slugs. We're going to make a pages.get_one request for each slug so we get the most recent revision data as well as the other metadata stuff.
        for slug in slugs:
            
            #  Hit Wikidot's API
            s = ServerProxy('https://' + config.wikidot_username + ':' + config.wikidot_api_key + '@www.wikidot.com/xml-rpc-api.php')
            wp = s.pages.get_one({'site': wikidot_site, 'page': slug})
            logger.info(wp)
            
            #  Be Nice
            sleep(0.25)
            
            # Send all this stuff to SCUTTLE to sort through.
            output = json.dumps(wp)
            # logger.info(output)
            headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
            r = requests.put(callback_url + '/2stacks/scheduled/page/metadata', data=output, headers=headers)
        
        return {
            'job': 'complete'
        }
