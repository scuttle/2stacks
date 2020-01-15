import json
import re
import boto3
import os
import config
import helpers
import requests
import urllib
from time import sleep
from xmlrpc.client import ServerProxy

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    for record in event['Records']:
        callback_url = record['messageAttributes']['callback_url']['stringValue']
        slug = record['messageAttributes']['page_slug']['stringValue']
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        #  Hit Wikidot's API
        s = ServerProxy('https://' + config.wikidot_username + ':' + config.wikidot_api_key + '@www.wikidot.com/xml-rpc-api.php')
        try:
            files = s.files.select({'site': wikidot_site, 'page': slug})
        except:  # Page is gone.
            payload = {'slug': slug, 'has_files': False}
            #  Send the news to SCUTTLE
            headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
            j = json.dumps(payload)
            r = requests.put(callback_url + '/2stacks/page/files', data=j, headers=headers)
            return {
                'job': 'complete'
            }
        # Returns a list, either with filenames or empty.
        if len(files) == 0:
            payload = {'slug': slug, 'has_files': False}
            #  Send the good news to SCUTTLE
            headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
            j = json.dumps(payload)
            r = requests.put(callback_url + '/2stacks/page/files', data=j, headers=headers)
        else:
            # Dang, we have to work.
            #  Be Nice
            sleep(0.25)
            
            #  Hit Wikidot's Frontend. We need the page_id so we don't clash two files, from different milestones, in one S3 namespace.
            wdpage = requests.get('http://' + wikidot_site + ".wikidot.com/" + slug)
            
            try:
                wd_page_id = re.search("(?:WIKIREQUEST.info.pageId = )([^;]*)", wdpage.text).group(1)
            except IndexError: # The page we got from Wikidot doesn't have a page ID.
            # This can happen if they're returning a 5XX error, or the page has been deleted.
            # TODO: Look at wdpage for a 200 status to better determine why it's crapping out.
                for i in range(5):
                    sleep(1) # Give wikidot a chance.
                    try:
                        wd_page_id = re.search("(?:WIKIREQUEST.info.pageId = )([^;]*)", wdpage.text).group(1)
                    except IndexError:
                        continue
                    else:
                        pass
            for idx, file in enumerate(files):
                logger.info(idx)
                sanitizedfilename = urllib.parse.quote(file, safe='')
                info = s.files.get_meta({"site": wikidot_site, "page": slug, "files": [file]})
                # logger.info(info[file]['download_url'])
                filedict = list(info.values())[0]
                thefile = requests.get(filedict['download_url'])
                filebytes = thefile.content # Bytes object.
            
                
                # Push it to S3 in a sensible manner.
                s3 = boto3.client('s3')
                upload = s3.put_object(Bucket="scuttle-s3", Body=filebytes, Key="files/page/" + str(wd_page_id) + "/" + sanitizedfilename)
                # Give SCUTTLE back the data requested and a link to the file.
                payload = {"slug": slug, "has_files": True, "wd_page_id": wd_page_id, 
                "filename": filedict['filename'], "size": filedict['size'], 
                "path": "https://cdn.scpfoundation.wiki/files/page/" + str(wd_page_id) + "/" + sanitizedfilename, 
                "metadata": {"wd_username": filedict['uploaded_by'], 
                'created_at': filedict['uploaded_at'], 'mime_type': filedict['mime_type'],
                'mime_description': filedict['mime_description'],
                'original_url': filedict['download_url']}}
                
                #  Send everything to SCUTTLE
                headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
                j = json.dumps(payload)
                r = requests.put(callback_url + '/2stacks/page/files', data=j, headers=headers)
                if r.status_code == 500:
                    logger.info('500:')
                    logger.info(r.text)
                #  Be Nice
                sleep(0.25)
    
    return {
        'job': 'complete'
    }