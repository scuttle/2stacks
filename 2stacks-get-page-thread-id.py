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
# import logging
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    for record in event['Records']:
        callback_url = record['messageAttributes']['callback_url']['stringValue']
        wd_page_id = record['messageAttributes']['page_id']['stringValue']
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        
        data = {'pageId': wd_page_id, 'moduleName': 'forum/ForumCommentsListModule'}
        haystack = helpers.fetch(data, wikidot_site)
        # logger.info(haystack)
        try:
            thread_id = re.search('(?:forumThreadId = )(\d*)', haystack).group(1)
        except:  # This only really fails on a deleted page.
            # TODO Make scuttle handle this.
            return False

        payload = {"wd_page_id": wd_page_id, "wd_thread_id": int(thread_id)}
        output = json.dumps(payload)
        
        #  Send everything to SCUTTLE
        headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
        r = requests.put(callback_url + '/2stacks/page/thread', data=output, headers=headers)


    return {
        'job': 'complete'
    }
