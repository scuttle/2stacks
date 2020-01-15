import json
import re
import boto3
import os
import config
import helpers
import requests
from time import sleep
from xmlrpc.client import ServerProxy

#temp
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    for record in event['Records']:
        callback_url = record['messageAttributes']['callback_url']['stringValue']
        slug = record['messageAttributes']['page_slug']['stringValue']
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        logger.info('get-page-metadata for ' + slug)
        #  Hit Wikidot's API
        s = ServerProxy('https://' + config.wikidot_username + ':' + config.wikidot_api_key + '@www.wikidot.com/xml-rpc-api.php')
        try:
            wp = s.pages.get_one({'site': wikidot_site, 'page': slug})
        except:
            # Page has been deleted
            return False # Clean this up later.
        
        #  Be Nice
        sleep(0.25)
        
        #  Hit Wikidot's Frontend
        wdpage = requests.get('http://' + wikidot_site + ".wikidot.com/" + slug)
        logger.info(wdpage)
        
        try:
            wd_page_id = re.search("(?:WIKIREQUEST.info.pageId = )([^;]*)", wdpage.text).group(1)
            logger.info(wd_page_id)
        except AttributeError: # The page we got from Wikidot doesn't have a page ID.
        # This can happen if they're returning a 5XX error, or the page has been deleted.
        # TODO: Look at wdpage for a 200 status to better determine why it's crapping out.
            for i in range(5):
                sleep(1) # Give wikidot a chance.
                try:
                    wd_page_id = re.search("(?:WIKIREQUEST.info.pageId = )([^;]*)", wdpage).group(1)
                except AttributeError:
                    continue
                else:
                    pass
            
        
        payload = {"slug": slug, "wd_page_id": wd_page_id, "wikidot_metadata": 
            {"fullname": wp["fullname"], "updated_at": wp["updated_at"], 
            "tags": wp["tags"], "revisions": wp["revisions"], 
            "created_by": wp["created_by"], "commented_by": wp["commented_by"],
            "title_shown": wp["title_shown"], "children": wp["children"],
            "commented_at": wp["commented_at"], "created_at": wp["created_at"],
            "parent_fullname": wp["parent_fullname"], "rating": wp["rating"],
            "updated_by": wp["updated_by"], "title": wp["title"],
            "comments": wp["comments"], "parent_title": wp["parent_title"]
            }, "latest_revision": wp["html"]}
            
        #  Send everything to SCUTTLE
        headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
        j = json.dumps(payload)
        logger.info('Making SCUTTLE request at ' + callback_url)
        r = requests.put(callback_url + '/2stacks/page/metadata', data=j, headers=headers)
        logger.info(r.text)
    return {
        'job': 'complete'
    }
