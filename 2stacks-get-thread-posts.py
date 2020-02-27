import requests
import random
import string
import json
import re
import config
import helpers
import boto3
import os
from bs4 import BeautifulSoup

#temp
# import logging
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    for record in event['Records']:
        callback_url = record['messageAttributes']['callback_url']['stringValue']
        wd_thread_id = record['messageAttributes']['thread_id']['stringValue']
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        
        data = {'t': wd_thread_id, 'moduleName': 'forum/ForumViewThreadModule'}
        haystack = helpers.fetch(data, wikidot_site)
        
        # Do some stuff with the base thread.
        try:
            soup = BeautifulSoup(haystack, 'html.parser')
        except TypeError: # NoneType, it gone.
            return False # Send this to SCUTTLE.
        titleblock = soup.find("div", {"class": "forum-breadcrumbs"})
        forum = int(re.search('(?:\/forum\/c-)(\d*)', str(titleblock)).group(1))
        title = re.search('(?:» (?!<))(.*)', str(titleblock)).group(1)
        descriptionblock = soup.find("div", {"class": "description-block well"})
        # Get the subtitle, which is a surprising amount of effort.
        if wikidot_site == 'scp-ru':  # SCP-RU
            subtitle = re.findall('(?:<\/div>)(?:\s*<div class="head">Кратко:<\/div>){0,1}([\s\S]*)(?:<\/div>)', str(descriptionblock), re.MULTILINE)
        elif wikidot_site == 'lafundacionscp':  # SCP-ES
            subtitle = re.findall('(?:<\/div>)(?:\s*<div class="head">Resumen:<\/div>){0,1}([\s\S]*)(?:<\/div>)', str(descriptionblock), re.MULTILINE)
        elif wikidot_site == 'fondationscp':  # SCP-FR
            subtitle = re.findall('(?:<\/div>)(?:\s*<div class="head">Résumé:<\/div>){0,1}([\s\S]*)(?:<\/div>)', str(descriptionblock), re.MULTILINE)    
        elif wikidot_site == 'scp-wiki-de':  # SCP-DE
            subtitle = re.findall('(?:<\/div>)(?:\s*<div class="head">Beschreibung:<\/div>){0,1}([\s\S]*)(?:<\/div>)', str(descriptionblock), re.MULTILINE)
        else:  #SCP-EN and English-speaking wikis.
            subtitle = re.findall('(?:<\/div>)(?:\s*<div class="head">Summary:<\/div>){0,1}([\s\S]*)(?:<\/div>)', str(descriptionblock), re.MULTILINE)
        subtitle = ''.join(subtitle)
        subtitle = subtitle.replace('\n','').replace('\t','')  # These are artifacts of scraping HTML and not valid in subtitles.
        if len(subtitle) is 0:
            subtitle = None
        
        # Get the creation timestamp for convenience in sorting later.
        created_timestamp = int(re.search('(?:odate time_)(\d*)', str(descriptionblock)).group(1))
        
        # Get the OP of the thread. This is Wikidot for a per-page discussion thread or a user id otherwise.
        attribution = descriptionblock.find("span", {"class": "printuser"})
        # logger.info(attribution)
        if attribution.string == "Wikidot":
            op_user_id = 0
            op_username = "Wikidot"
        else:
            try:
                op_user_id = int(re.search('(?:userInfo\()(\d*)', str(attribution)).group(1))
                op_username = attribution.text
            except AttributeError:
                try:
                    # Deleted Accounts
                    op_user_id = int(re.search('(?:data-id=\")(\d*)', str(attribution)).group(1))
                    op_username = "Deleted Account (" + str(op_user_id) + ")"
                except AttributeError:
                    try:
                        # Anonymous Accounts
                        op_user_id = 0
                        op_username = "Anonymous User (" + str(re.search('(?:anonymousUserInfo\(\')([\d\.]*)(?:\'\); return false;\"><)', str(attribution)).group(1))
                    except AttributeError:
                        # Guest Accounts
                        op_user_id = 0
                        op_username = str(re.search('(?:</a>)([^<]*)', str(attribution)).group(1))
                
        
        # What we should have back is HTML laying out a page of forum comments.
        # logger.info('haystack returned:')
        # logger.info(haystack)
        
        # First, let's determine if there are multiple pages.
        try:
            maxpages = re.search('(?:<span class="pager-no">page \d* of )(\d*)', haystack).group(1)
            maxpages = int(maxpages)
        except AttributeError: # NoneType means the pager is absent, meaning there's only one page of comments. This is okay.
            maxpages = 1
        # else:  # wtf?
            # logger.info('maxpages returned:')
            # logger.info(maxpages)
            # raise Exception('we hit a weird thing with the maxpages, aborting')
        
        # logger.info('maxpages returned:')
        # logger.info(maxpages)
            
        # Let's handle things the same way for one page or many.
        for page in range(maxpages):
            actualpage = page + 1
            # logger.info('On Page ' + str(actualpage))
            innerpayload = {}
            haystack = get_thread_page(thread=wd_thread_id, page=actualpage, wikidot_site=wikidot_site)  # I'm too lazy to not just increment this range by one to make it work.
            soup = BeautifulSoup(haystack.replace("\\","")[2:], 'html.parser')
            posts = soup.find_all("div", id=re.compile("(fpc-)"))
            # logger.info('posts:')
            # logger.info(len(posts))
            for idx, post in enumerate(posts):
                wd_post_id = int(re.search('(?:<div class="post" id="post-)(\d*)', str(post)).group(1))
                # logger.info("Post " + str(idx) + ", ID " + str(wd_post_id))
                subject = re.search('(?:<div class="title" id="post-title-\d*">\s*)([^\n]*)', str(post)).group(1)
                # On a blank subject this returns as "</div>"
                if subject == "</div>":
                    subject = None
                try:    
                    username = re.search('(?:return false;">)([^<]*)(?:<\/a><\/span>,)', str(post)).group(1)
                    wd_user_id = int(re.search('(?:www\.wikidot\.com\/userkarma.php\?u=)([^\)]*)', str(post)).group(1))
                except AttributeError: #NoneType, deleted user.
                    # logger.info('thread:')
                    # logger.info(wd_thread_id)
                    # logger.info('post:')
                    # logger.info(wd_post_id)
                    try:
                        wd_user_id = int(re.search('(?:data-id=")(\d*)', str(post)).group(1))
                        username = "Deleted Account " + str(wd_user_id)
                    except AttributeError: #NoneType, anonymous user!
                        try:
                            wd_user_id = 0
                            username = "Anonymous User (" + str(re.search('(?:anonymousUserInfo\(\\\')([\d\.]*)', str(post)).group(1)) + ")"
                        except AttributeError: # One last NoneType, GUEST user holy crap.
                            # logger.info(str(post))
                            try:
                                username = re.search('(?:alt=""/></a>)([^>]*)(?:</span>,)', str(post)).group(1)
                                wd_user_id = 0
                            except AttributeError: # This is getting ridiculous. More guest account types.
                                try:
                                    # logger.info(str(post))
                                    username = re.search('(?:&amp;default=http:\/\/www.wikidot.com/common--images/avatars/default/a16.png&amp;size=16"\/><\/a>)([^>]*)(?:<\/span>,)', str(post)).group(1)
                                    wd_user_id = 0
                                except AttributeError:
                                    # Guest with a URL in their name
                                    wd_user_id = 0
                                    tempusername = re.search('(?:rel=\"nofollow\">)([^<]*)(?:<\/a> \(guest\))', str(post)).group(1)
                                    username = tempusername + " (guest"
                post_created_at = int(re.search('(?:<span class="odate time_)([^\s]*)', str(post)).group(1))
                
                content = post.find("div", {"class": "content"})
                body = ''.join(str(item) for item in content.contents)
                body = body[1:-1]  # Wikidot pads the text with a \n on both sides, which the author didn't write.
                try:
                    if post.parent['id'] == 'thread-container-posts':
                        # Top-level response
                        parent = 0
                    else:
                        # 'id' will look like fpc-12345678, take a slice of the string
                        # logger.info('parent:' + post.parent['id'])
                        parent = int(post.parent['id'][4:])
                except KeyError: # We're at the root.
                        parent = 0
                changespresent = post.find("div", {"class": "revisions"})
                if changespresent is not None:
                    # This post was edited, send along a list of revisions and let those get picked up in a different routine.
                    # We're guaranteed at least two entries in here.
                    changes = re.findall('(?:showRevision\(event, )(\d*)', str(changespresent))
                    
                else:
                    changes = False
                    
                    
                innerpayload[idx]={"wd_post_id": wd_post_id, "wd_user_id": wd_user_id, 
                "parent_id": parent, "subject": subject, "username": username, "timestamp": post_created_at,
                "changes": changes, "text": body}
                # logger.info('wd_post_id is a: ') 
                # logger.info(type(wd_post_id))
                # logger.info('wd_user_id is a ')
                # logger.info(type(wd_user_id))
                # logger.info('parent_id is a ')
                # logger.info(type(parent))
                # logger.info('subject is a ')
                # logger.info(type(subject))
                # logger.info('username is a ')
                # logger.info(type(username))
                # logger.info('timestamp is a ')
                # logger.info(type(post_created_at))
                # logger.info('changes is a ')
                # logger.info(type(changes))
                # logger.info('text is a ')
                # logger.info(type(body))
            # While we could wait and send one big payload, that's a risky proposition on threads with lots of posts so let's not.
            # logger.info('out of the loop for a single page')
            
            # Wrap the payload and send it, SCUTTLE can sort out posts it already has.
            outerpayload = {"wd_thread_id": int(wd_thread_id), "wd_forum_id": forum, 
            "wd_user_id": op_user_id, "wd_username": op_username, "title": title,
            "subtitle": subtitle, "created_at": created_timestamp, "posts": innerpayload}
            # logger.info('wd_thread_id is a: ') 
            # logger.info(type(wd_thread_id))
            # logger.info('wd_forum_id is a ')
            # logger.info(type(forum))
            # logger.info('wd_user_id is a ')
            # logger.info(type(wd_user_id))
            # logger.info('wd_username is a ')
            # logger.info(type(op_username))
            # logger.info('title is a ')
            # logger.info(type(title))
            # logger.info('subtitle is a ')
            # logger.info(type(subtitle))
            # logger.info('created_at is a ')
            # logger.info(type(created_timestamp))
            # logger.info('posts is a ')
            # logger.info(type(innerpayload))
            
            #  Send everything to SCUTTLE
            output = json.dumps(outerpayload)
            headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
            r = requests.put(callback_url + '/2stacks/thread/posts', data=output, headers=headers)
            # logger.info('Made a SCUTTLE Request!')
            # logger.info('DATA: ')
            # logger.info(outerpayload)

    return {"job": "complete"}

def get_thread_page(thread: int, page: int, wikidot_site: str):
    data = {'t': thread, 'moduleName': 'forum/ForumViewThreadPostsModule', 'pageNo': page}
    return helpers.fetch(data, wikidot_site)