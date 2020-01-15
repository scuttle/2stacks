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
        logger.info(wikidot_site)
        logger.info(wd_page_id)

        data = {'page_id': wd_page_id, 'moduleName': 'history/PageRevisionListModule', 'perpage': 99999}
        haystack = helpers.fetch(data, wikidot_site)
        if haystack is None: # Page was deleted before the task fired.
            return False
        revision_ids = re.findall('(?:<tr id="revision-row-)(\d*)', haystack)
        revision_numbers = re.findall('(?:<td>)(\d*)(?:.<\/td>)', haystack)
        usernames = re.findall('(?:alt=")([^"]*)', haystack)
        user_ids = re.findall('((?:userInfo\()([^\)]*)(?:\); return false;"  )|(?:data-id=")(\d*)|(?:UserInfo\(\\\')([\d\|\.]*)(?:\\\'\); return false;\" ><))', haystack)
        timestamps = re.findall('(?:<span class="odate time_)([^ ]*)', haystack)
        # The revision type can be empty! Old tag actions didn't have an associated revision type
        # The unicode points in here if we need them later, are Thai (0E00-037F)
        revision_type = re.findall('((?:<span class="spantip" title="(?:[\D \/])*">)(\w)(?:<\/span>)|(?:<td>)(?:\\n\\t\\t\\t\\t\\t \\t\\t\\t \\t\\t\\t \\t\\t\\t \\t  \\n\\t\\t \\t  \\n\\t\\t \\t \\n\\t\\t<)(\/)(?:td>))', haystack)
        comments = re.findall('(?:<td style="font-size: 90%">)([^<]*)', haystack)
        # logger.info(wd_page_id)
        # logger.info(len(revision_ids))
        # logger.info(len(revision_numbers))
        # logger.info(len(usernames))
        # logger.info(len(user_ids))
        # logger.info(len(timestamps))
        # logger.info(len(revision_type))
        # logger.info(len(comments))
        
        # Clean up the match object we made for user_ids.
        for idx, user in enumerate(user_ids):
            user_ids[idx] = user[1:] # Remove the non-matching object
        for idx, user in enumerate(user_ids):
            user_ids[idx] = ''.join(user) # Flatten the tuple to one string object.
            
        # Clean up the match object we made for revision_type.
        for idx, revision in enumerate(revision_type):
            revision_type[idx] = revision[1:] # Remove the non-matching object
        for idx, revision in enumerate(revision_type):
            revision_type[idx] = ''.join(revision) # Flatten the tuple to one string object.
        
        innerpayload = {}
        logger.info(str(len(revision_ids)) + " revisions.")
        logger.info(str(len(revision_type)) + " revision type rows.")
        for row in range(len(revision_type)):
            logger.info(revision_type[row])
        for row in range(len(revision_ids)):
            # logger.info("Processing revision " + revision_numbers[row])
            # We need to handle some edge cases for deleted and anonymous users.
            if len(usernames[row]) == 0:
                #This can be either a deleted or anonymous account
                if "." in user_ids[row]:
                    #Anonymous account
                    usernames[row] = "Anonymous User (" + str(user_ids[row]) + ")"
                    user_ids[row] = 0
                else:
                    #Deleted Account
                    usernames[row] = "Deleted Account (" + str(user_ids[row]) + ")"
            if revision_type[row] == "/":
                revision_type[row] = "A"
            innerpayload[row] = (
                {'revision_id': revision_ids[row], 'username': usernames[row], 'user_id': user_ids[row],
                 'timestamp': timestamps[row], 'revision_type': revision_type[row], 'revision_number': revision_numbers[row],
                 'comments': comments[row]})
        payload = {"wd_page_id": wd_page_id, "revisions": innerpayload}
        output = json.dumps(payload)

        #  Send everything to SCUTTLE
        headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
        r = requests.put(callback_url + '/2stacks/page/revisions', data=output, headers=headers)
        if r.status_code == 500:
            logger.info('500:')
            logger.info(r.text)

    return {
        'job': 'complete'
    }
