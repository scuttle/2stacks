# -*- coding: utf-8 -*-
# 2STACKS - Backup Tools for The SCP Wiki.
# Licensed as Yeezyware - If you can do it better than me, then you do it.
# Rename config.py.example to config.py and enter the needed info.
import config
# used to decode the JSON returned from Wikidot
import json
# used to obey Wikidot's limits.
from time import sleep
# used to make the put request to SCUTTLE
import requests
# used to talk to Wikidot
from xmlrpclib import ServerProxy
# used to check arguments for performing various jobs
from sys import argv

if "-wikidot" in argv:

    # We'll access SCUTTLE's API of all extant pages and the number of revisions at the last crawl.
    r_revisions_headers = {"Authorization": "Bearer " + config.scuttle_token}
    r_revisions = requests.get(config.scuttle_endpoint + '/revisions', headers=r_revisions_headers)
    revision_json = r_revisions.json()

    # See: http://developer.wikidot.com/doc:api
    s = ServerProxy('https://' + config.wikidot_username + ':' + config.wikidot_api_key + '@www.wikidot.com/xml-rpc-api.php')

    # Retrieve a list of all pages.
    pageslist = s.pages.select({'site': config.wikidot_site})
    print "Found " + str(len(pageslist)) + " pages."
    # Wikidot's limit is 240 requests a minute, sleep(0.25) will keep us under that.
    sleep(0.25)

    # Getting metadata can only be done with sets of 10 pages at a time. Given that we have OVER 9000 (!) pages to process,
    # let's do everything we can to make it go quickly. This function splits a big list into small lists.
    def chunks(l, n):
        # We're taking the length of the first argument (the big list), and using the desired length for the second arg.
        for i in range(0, len(l), n):
            # And returning an index range of the appropriate number of items.
            yield l[i:i+n]

    # This list will hold all metadata about all pages. We'll iterate over it later with the SCUTTLE endpoint.
    pages = []

    pages_chunked = chunks(pageslist, 10)

    # This is just a fancy way of doing ceil() without importing math, and much faster.
    chunkcount = -(-len(pageslist) // 10)

    for idx, pageset in enumerate(pages_chunked):
        # Get a chunk of metadata.
        metachunk = s.pages.get_meta({'site': config.wikidot_site, 'pages': pageset})
        # Add the chunk to the list.
        pages.append(metachunk)
        print str(idx+1) + "/" + str(chunkcount) + " chunks processed."
        # Sleep and repeat if more chunks exist.
        sleep(0.25)

    # Now we've got a tales dict that's in chunks of 10 nested dicts, we need to pull them all up to the same level.
    p = []
    for chunk in pages:
        for page in chunk:
            p.append(chunk[page])

    # For every page in the wiki...
    for idx, item in enumerate(p):
        # If the page name was in the SCUTTLE package of names...
        # AND the revision count is the same on SCUTTLE and Wikidot...
        if item["fullname"] in revision_json and revision_json[item["fullname"]] == item["revisions"]:
            # Skip it.
            print "Skipped " + str(idx) + " of " + str(len(p)) + ", " + item["fullname"]
            continue
        # Otherwise, send it to SCUTTLE for processing.
        else:
            # Get the actual page content and full metadata set.
            page = s.pages.get_one({"site": config.wikidot_site, "page": item["fullname"]})
            # Obey the speed limit.
            sleep(0.25)
            # Dump the resultant JSON to a string so we can send it on its way.
            pagestr = json.dumps(page)
            # Build the headers and let the SCUTTLE API know to expect a JSON file.
            headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
            # Put the file. This is controlled currently by API/PageController@wdstore.
            r = requests.put(config.scuttle_endpoint + '/wikidot', data=pagestr, headers=headers)
            sleep(1)
            print "Put " + str(idx) + " of " + str(len(p)) + ", " + item["fullname"]
            try:
                print "Revision " + str(item["revisions"]) + " on wikidot vs. " + str(revision_json[item["fullname"]]) + " on SCUTTLE."
            except KeyError:  # New post.
                print "New article."

