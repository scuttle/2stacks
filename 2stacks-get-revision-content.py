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
        logger.info(record['messageAttributes'])
        callback_url = record['messageAttributes']['callback_url']['stringValue']
        wd_revision_id = record['messageAttributes']['revision_id']['stringValue']
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        wd_url = record['messageAttributes']['wikidot_url']['stringValue']
        
        logger.info(wd_revision_id)
        logger.info(wikidot_site)
        
        data = {'revision_id': wd_revision_id, 'moduleName': 'history/PageSourceModule'}
        haystack = helpers.fetch(data, wd_url)
        if haystack is None:
            return { 'revision': 'deleted ' }
        else:
            logger.info('haystack:')
            logger.info(haystack)
            content = re.search('(?:<div class="page-source">)(.*)(?:<\/div>$)', haystack, re.DOTALL).group(1)
            payload = {"wd_revision_id": str(wd_revision_id), "content": content}
            output = json.dumps(payload)
            logger.info("got output")
            #  Send everything to SCUTTLE
            headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
            r = requests.put(callback_url + '/2stacks/revision/content', data=output, headers=headers)
            if r.status_code is not 200:
                raise ValueError('SCUTTLE isn\'t well. Returned ' + str(r.status_code))
    return {
        'job': 'complete'
    }
