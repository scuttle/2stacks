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
# used to check arguments for performing various jobs
from sys import argv

if "-wikidot" in argv:
    # used to talk to Wikidot
    from xmlrpclib import ServerProxy

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
            # Rename content to payload to avoid a PHP keyword error in SCUTTLE.
            page["payload"] = page["content"]
            page["content"] = ""
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

if "-scrape=revisions" in argv:
# else:
    # Used as the primary scraper.
    from selenium import webdriver
    # Used to interact with Wikidot.
    from selenium.webdriver.common.keys import Keys
    # Used for regular expression matching
    import re
    # Used to check the existence of more revisions by the presence of an element.
    from selenium.common.exceptions import NoSuchElementException
    # Used to perform various waiting functions needed to reliably get data.
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    # SCUTTLE will send us a list of pages and all correctly scraped revisions.
    r_scrape_headers = {"Authorization": "Bearer " + config.scuttle_token}
    r_scrapes = requests.get(config.scuttle_endpoint + '/scrape/revisions/manifest', headers=r_scrape_headers)
    scrape_json = r_scrapes.json()

    driver = webdriver.Chrome()
    for page in list(scrape_json.keys()):
        print "Processing " + str(page)
        driver.get("http://" + config.wikidot_site + ".wikidot.com/" + page)

        # On a single page, there's quite a few things we want:
        # * Revision history (who did what, when, and what was it?)
        # * Rating breakdown (who voted and how?)
        # * Discussion on the article (who said what, when, and what was it?)
        # * Attached files and metadata.

        # We will skip processing a page if all of the below criteria are met:
        # SCUTTLE reports all revisions have been scraped and that's matched by a len() comparison.
        # The rating has not changed.
        # The number of comments has not changed.
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="page-info"]')))

        pageInfo = driver.find_element_by_xpath('//*[@id="page-info"]')
        match = re.match('(page revision: )(\d+)(,)', pageInfo.text)
        totalrevisions = int(match.group(2))+1
        print "Page shows " + str(totalrevisions) + " total revisions."
        try:
            json_revision_count = len(scrape_json[page]["revisions"][0])
        except IndexError:
            json_revision_count = 0
        print "SCUTTLE reports " + str(json_revision_count) + " stored revisions"
        if totalrevisions == json_revision_count:
            print "Skipping this page."
            sleep(0.25)
            continue

        revisions_python = {}

        # Click on history button.
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="history-button"]')))
        driver.find_element_by_xpath('//*[@id="history-button"]').click()

        def process_page():
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="revision-list"]/table/tbody')))
            tblPageHistory = driver.find_element_by_xpath('//*[@id="revision-list"]/table/tbody')
            rows = tblPageHistory.find_elements_by_tag_name('tr')
            for row in rows:
                # Skip the header.
                if row.text == u'rev.   flags actions by date comments':
                    continue
                thisrev = {}
                revid = row.find_element_by_xpath('./td[1]').text
                thisrev["wd_revision_id"] = int(revid.rstrip("."))
                # Make sure this revisions is not already stored.
                try:
                    if thisrev["wd_revision_id"] in scrape_json[page]["revisions"][0]:
                        print "Revision " + str(thisrev["wd_revision_id"]) + " already stored in SCUTTLE, skipping."
                        continue
                except IndexError:
                    # No revisions stored in SCUTTLE with that key, NBD.
                    pass
                # Get the revision type:
                # S is a source content change and we'll want to upload the revision source.
                # F is a file add/remove/rename.
                # T is a title change (friendly name).
                # R is a rename/move (slug).
                # A is a tag add or remove.
                # M is a metadata change.
                # N is a new page.
                thisrev["type"] = row.find_element_by_xpath('./td[3]').text
                # Get the friendly name of the user.
                thisrev["updated_by"] = row.find_element_by_xpath('./td[5]').text
                # Find the wikidot User ID that's in the onClick
                try:
                    rgxUserID = row.find_element_by_xpath('./td[5]/span/a').get_attribute('onclick')
                    match = re.match('(WIKIDOT.page.listeners.userInfo\()(\d+)(\))', rgxUserID)
                    thisrev["wd_user_id"] = int(match.group(2))
                except NoSuchElementException:
                    # Account deleted
                    thisrev["wd_user_id"] = 0
                # Get the timestamp for the revision.
                timestamp = row.find_element_by_xpath('./td[6]/span').get_attribute('class')
                # Note we use re.search here instead of re.match.
                match = re.search('time_(\d+)', timestamp)
                thisrev["timestamp"] = match.group(1)
                thisrev["comment"] = row.find_element_by_xpath('./td[7]').text
                # Now, if we have a source content change, get the revision source.
                if thisrev["type"] == "S":
                    row.find_element_by_xpath('./td[4]/a[2]').click()
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//div[@class="page-source"]')))
                    thisrev["payload"] = driver.find_element_by_xpath('//div[@class="page-source"]').text
                thisrev["page_id"] = scrape_json[page]["id"]
                headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
                payload = json.dumps(thisrev)
                r = requests.put(config.scuttle_endpoint + '/scrape/revisions', data=payload, headers=headers)
                print "Stored revision " + str(thisrev["wd_revision_id"])
                sleep(0.25)
            # This try-catch block is meant to check for the existence of BOTH the pager element AND the next button.
            # The existence of both means we have not finished with the revision history. If they're both there,
            # click the 'next' button and return true for the while loop this function is run from, indicating there's
            # more to process. If they're not both there, we either have one page of revisions or we're on the last
            # page. In either event, we do not need to do any more work once we're out of this current loop, so return
            # false.
            try:
                print "Looking for pager and next button."
                pager = driver.find_element_by_xpath('//div[@class="pager"]')
                btnNext = pager.find_element_by_partial_link_text('next')
            except NoSuchElementException:
                print "Couldn't find, page shows " + str(totalrevisions) + " revisions."
                return False
            else:
                print "Found, clicking the next button."
                btnNext.click()
                sleep(0.5)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="revision-list"]/table/tbody')))
                return True
        # If we only have one page of revisions, process it, otherwise go into a while loop and depend on the return
        # value to determine whether there's more revisions to process.
        if totalrevisions <= 20:
            process_page()
        else:  # We have to process pages.
            while True:
                print "Processing this set of revisions."
                result = process_page()
                if result is False:
                    print "No more pages, leaving."
                    break
