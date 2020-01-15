import requests
import json
import re
import config
import helpers

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    for record in event['Records']:
        callback_url = record['messageAttributes']['callback_url']['stringValue']
        forum_id = record['messageAttributes']['forum_id']['stringValue']
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        
        page_no = 1
        
        data = {'c': forum_id, 'p': page_no, 'moduleName': 'forum/ForumViewCategoryModule'}
        haystack = helpers.fetch(data, wikidot_site)
        try:
            threads = re.findall('(?:\n\t\t\t\t\t\t\t\t\t\t\t\t<a href="\/forum\/t-)([^\/]*)', haystack)
            if wikidot_site == 'fondationscp':  # SCP-FR
                pages = re.findall('(?:<span class="pager-no">page 1 de )(\d*)', haystack) # This technically returns 2 indistinguishable objects because Wikidot.
            elif wikidot_site == 'scp-wiki-de':  # SCP-DE
                pages = re.findall('(?:<span class="pager-no">Seite 1 von )(\d*)', haystack) # This technically returns 2 indistinguishable objects because Wikidot.
            elif wikidot_site == 'scp-pl':  # SCP-PL
                pages = re.findall('(?:<span class="pager-no">strona 1 z )(\d*)', haystack) # This technically returns 2 indistinguishable objects because Wikidot.
            elif wikidot_site == 'scp-pt-br':  # SCP-PT
                pages = re.findall('(?:<span class="pager-no">página 1 do )(\d*)', haystack) # This technically returns 2 indistinguishable objects because Wikidot.
            elif wikidot_site == 'fondazionescp':  # SCP-IT
                pages = re.findall('(?:<span class="pager-no">pagina 1 di )(\d*)', haystack) # This technically returns 2 indistinguishable objects because Wikidot.
            elif wikidot_site == 'scpko':  # SCP-KO
                pages = re.findall('(?:<span class="pager-no">페이지: 1 / )(\d*)', haystack) # This technically returns 2 indistinguishable objects because Wikidot.
            else:  # SCP-EN and English-speaking wikis (Some -INT sites didn't have this translated, like -RU, -UA, -CN...)
                pages = re.findall('(?:<span class="pager-no">page 1 of )(\d*)', haystack) # This technically returns 2 indistinguishable objects because Wikidot.
            logger.info(str(pages))
        except:  # This only really fails on a deleted page.
            # TODO Make scuttle handle this.
            return False
        payload = {"wd_forum_id": forum_id, "threads": threads}
        output = json.dumps(payload)
        
        #  Send everything to SCUTTLE
        headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
        r = requests.put(callback_url + '/2stacks/forum/threads', data=output, headers=headers)
        
        if not pages: # The Pythonic™ way of checking if a list is empty.
            return { 'job': 'complete' }
        
        else:
            for page_no in range(int(pages[0])):
                page_no += 1
                data = {'c': forum_id, 'p': page_no, 'moduleName': 'forum/ForumViewCategoryModule'}
                haystack = helpers.fetch(data, wikidot_site)
                try:
                    threads = re.findall('(?:\n\t\t\t\t\t\t\t\t\t\t\t\t<a href="\/forum\/t-)([^\/]*)', haystack)
                    
                except:  # This only really fails on a deleted page.
                    # TODO Make scuttle handle this.
                    return False
                payload = {"wd_forum_id": forum_id, "threads": threads}
                output = json.dumps(payload)
                
                #  Send everything to SCUTTLE
                headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
                r = requests.put(callback_url + '/2stacks/forum/threads', data=output, headers=headers)


    return {
        'job': 'complete'
    }
