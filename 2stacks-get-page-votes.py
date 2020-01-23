import requests
import random
import string
import json
import re
import config
import helpers
import boto3
import os

#temp
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    for record in event['Records']:
        callback_url = record['messageAttributes']['callback_url']['stringValue']
        wd_page_id = record['messageAttributes']['page_id']['stringValue']
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        
        logger.info(wd_page_id)
        data = {'pageId': wd_page_id, 'moduleName': 'pagerate/WhoRatedPageModule'}
        try:
            haystack = helpers.fetch(data, wikidot_site)
        except:  # It gone.
            return { 'job': 'article_deleted' }
        votes = re.findall('(?:#777\">\n)(?:\s*)([12345+-])', haystack)
        user_ids = re.findall('(?:u=)([^\)]*)', haystack)
        usernames = re.findall('(?:alt=\")([^\"]*)', haystack)
        
        logger.info(str(len(votes)) + " votes found")
        
        if len(votes) > 0:
        
            innerpayload = {}
            for row in range(len(user_ids)):
                innerpayload[row] = (
                    {'user_id': user_ids[row], 'username': usernames[row], 'vote': votes[row]})
            payload = {"wd_page_id": wd_page_id, "votes": innerpayload}
            output = json.dumps(payload)
            
            #  Send everything to SCUTTLE
            headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
            r = requests.put(callback_url + '/2stacks/page/votes', data=output, headers=headers)
            if r.status_code == 500:
                logger.info('500:')
                logger.info(r.text)

    return {
        'job': 'complete'
    }
