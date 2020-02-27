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
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        
        domain = wikidot_site + '.wikidot.com' # TODO support non-wd domains like sandbox.
        data = {'hidden': "true", 'moduleName': 'forum/ForumStartModule'}
        token = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))
        data.update({'wikidot_token7': token})
        cookies = requests.cookies.RequestsCookieJar()
        cookies.set('wikidot_token7', str(token), domain=domain, path='/')
        p = requests.post('http://' + domain + '/ajax-module-connector.php', data=data, cookies=cookies)
        response = json.loads(p.text)
        haystack = response['body']
        
        # What we should have back is HTML laying out the front page of forums.
        
        category_ids = re.findall('(?:<a href="\/forum\/c-)(\d*)', haystack)
        category_names = re.findall('(?:<div class="title"><[^>]*>)([^<]*)', haystack)
        category_descriptions = re.findall('(?:<\/a><\/div><div class="description">)([^<]*)', haystack)
        category_threads = re.findall('(?:td class="threads">)(\d*)', haystack)
        category_posts = re.findall('(?:td class="posts">)(\d*)', haystack)
        # category_last_posted = re.findall('(?:time_)(\d*)', haystack)
        # category_last_post = re.findall('(?:#post-)(\d*)(?:">Jump!)', haystack)
        # category_last_poster_id = re.findall('(?:userInfo\()(\d*)(?:\); return false;"  )', haystack)
        # category_last_poster_username = re.findall('(?:alt=")([^"]*)', haystack)
        # category_last_thread = re.findall('(?:\/forum\/t-)(\d*)(?:#)', haystack)
        
        innerpayload = {}
        for row in range(len(category_ids)):
            innerpayload[row] = ({
                'category_id': category_ids[row], 'category_name': category_names[row],
                'category_description': category_descriptions[row], 'category_threads': category_threads[row],
                'category_posts': category_posts[row]
                #, 'category_last_posted': category_last_posted[row],
                #'category_last_post': category_last_post[row], 'category_last_poster_id': category_last_poster_id[row],
                #'category_last_poster_username': category_last_poster_username[row], 'category_last_thread': category_last_thread[row]
            })
        payload = {"wd_wiki": wikidot_site, "forums": innerpayload}
        output = json.dumps(payload)
        
        #  Send everything to SCUTTLE
        headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
        r = requests.put(callback_url + '/2stacks/forum/metadata', data=output, headers=headers)
        # if r.status_code == 500:
        #     logger.info('500:')
        #     logger.info(r.text)