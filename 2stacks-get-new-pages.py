import json
import config
import helpers
import json
import requests
import re


def lambda_handler(event, context):
    for record in event['Records']:
        # We receive a payload from SCUTTLE with a wiki and the most recent slug we have for it.
        callback_url = record['messageAttributes']['callback_url']['stringValue']
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        wd_url = record['messageAttributes']['wikidot_url']['stringValue']
        slug = record['messageAttributes']['page_slug']['stringValue']
        
        # Get the 20 most recent pages.
        data = {'order': 'dateCreatedDesc', 'moduleName': 'list/WikiPagesModule', 'limit':20, 'preview':True}
        haystack = helpers.fetch(data, wd_url)
        
        # Get the slugs back.
        slugs = re.findall('(?:<a href="\/)([^"]*)', haystack)
        
        # If the most recent page slug matches the one scuttle sent us, it already knows about it, terminate.
        if slugs[0] == slug:
            return { 'job': 'complete' }
        else:
            # Otherwise, let's get a stub together for scuttle.