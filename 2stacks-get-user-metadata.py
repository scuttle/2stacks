import json
import boto3
from botocore.exceptions import ClientError
import logging
import helpers
import requests
import re
import config
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    for record in event['Records']:
        callback_url = record['messageAttributes']['callback_url']['stringValue']
        user_id = record['messageAttributes']['user_id']['stringValue']
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        
        # Get the basic info from wikidot.
        data = {"user_id": user_id, 'moduleName': 'users/UserInfoWinModule'}
        response = helpers.fetch(data, wikidot_site)
        
        # Believe it or not, the next two patterns look for two different things. Thanks Wikidot.
        # logger.info(response)
        if wikidot_site == 'scp-ru':  #SCP-RU
            wd_registration_timestamp = re.search('(?:Wikidot.com с:)(?:\D*)(\d*)', response).group(1)
        elif wikidot_site == 'lafundacionscp' or wikidot_site == 'scp-pt-br':  # SCP-ES & -PT
            wd_registration_timestamp = re.search('(?:desde:)(?:\D*)(\d*)', response).group(1)
        elif wikidot_site == 'fondationscp':  # SCP-FR
            wd_registration_timestamp = re.search('(?:depuis:)(?:\D*)(\d*)', response).group(1)
        elif wikidot_site == 'scp-wiki-de':  # SCP-DE
            wd_registration_timestamp = re.search('(?:seit:)(?:\D*)(\d*)', response).group(1)
        elif wikidot_site == 'scp-pl':  # SCP-PL
            wd_registration_timestamp = re.search('(?:Wikidot.com od:)(?:\D*)(\d*)', response).group(1)
        elif wikidot_site == 'fondazionescp':  # SCP-IT
            wd_registration_timestamp = re.search('(?:Wikidot dal:)(?:\D*)(\d*)', response).group(1)
        elif wikidot_site == 'scp-wiki-cn':  # SCP-CN
            wd_registration_timestamp = re.search('(?:使用者始于：)(?:\D*)(\d*)', response).group(1)
        elif wikidot_site == 'scpko':  # SCP-KO
            wd_registration_timestamp = re.search('(?:Wikidot.com 사용자 시작:)(?:\D*)(\d*)', response).group(1)
        else: # SCP-EN and English-speaking wikis, and a few translated sites (-UA, -CS, )
            wd_registration_timestamp = re.search('(?:since:)(?:\D*)(\d*)', response).group(1)            
            
        try:
            if wikidot_site == 'scp-ru':  # SCP-RU
                wiki_membership_timestamp = re.search('(?:сайта: с)(?:\D*)(\d*)', response).group(1)
            elif wikidot_site == 'lafundacionscp' or wikidot_site == 'scp-pt-br':  # SCP-ES & -PT
                wiki_membership_timestamp = re.search('(?:: desde)(?:\D*)(\d*)', response).group(1)
            elif wikidot_site == 'fondationscp':  # SCP-FR
                wiki_membership_timestamp = re.search('(?:: depuis :)(?:\D*)(\d*)', response).group(1)
            elif wikidot_site == 'scp-wiki-de':  # SCP-DE
                wiki_membership_timestamp = re.search('(?:Site: seit)(?:\D*)(\d*)', response).group(1)
            elif wikidot_site == 'scp-ukrainian':  # SCP-UA
                wiki_membership_timestamp = re.search('(?:сайту: з)(?:\D*)(\d*)', response).group(1)
            elif wikidot_site == 'scp-cs':  # SCP-CS
                wiki_membership_timestamp = re.search('(?:Stránky: od)(?:\D*)(\d*)', response).group(1)
            elif wikidot_site == 'scp-th':  # SCP-TH
                wiki_membership_timestamp = re.search('(?:เป็นสมาชิกตั้งแต่)(?:\D*)(\d*)', response).group(1)
            elif wikidot_site == 'scp-pl':  # SCP-PL
                wiki_membership_timestamp = re.search('(?:projektu: od)(?:\D*)(\d*)', response).group(1)
            elif wikidot_site == 'fondazionescp':  # SCP-IT
                wiki_membership_timestamp = re.search('(?:sito: dal)(?:\D*)(\d*)', response).group(1)
            elif wikidot_site == 'scp-wiki-cn':  # SCP-CN
                wiki_membership_timestamp = re.search('(?:本站成员：始于)(?:\D*)(\d*)', response).group(1)
            elif wikidot_site == 'scpko':  # SCP-KO
                wiki_membership_timestamp = re.search('(?:이 사이트의 회원 시작 시간:)(?:\D*)(\d*)', response).group(1)
            else:  # SCP-EN and English-speaking wikis.
                wiki_membership_timestamp = re.search('(?:: since)(?:\D*)(\d*)', response).group(1)
        except AttributeError:
            # Altogether possible this user is no longer a member. We'll send a boolean false.
            wiki_membership_timestamp = False
            
        username = re.search('(?:<h1>)(.*)(?:<\/h1>)', response).group(1)
        
        # Download the user's avatar as a file object.
        r_avatar = requests.get('http://www.wikidot.com/avatar.php?userid=' + user_id)
        avatar = r_avatar.content  # Bytes-like object here.
    
        # Upload the avatar to s3
        s3 = boto3.client('s3')
        upload = s3.put_object(Bucket="scuttle-s3", Body=avatar, Key="avatars/wikidot/" + str(user_id))
        # Give SCUTTLE back the data requested and a link to the file.
        payload = {"wd_user_id": user_id, "username": username, 
        "wd_user_since": wd_registration_timestamp, 
        "avatar_path": "https://cdn.scpfoundation.wiki/avatars/wikidot/" + user_id, 
        "wiki_member_since": wiki_membership_timestamp}
    
        #  Send everything to SCUTTLE
        headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
        j = json.dumps(payload)
        r = requests.put(callback_url + '/2stacks/user/metadata', data=j, headers=headers)

    
    return {
        'job': 'complete'
    }
