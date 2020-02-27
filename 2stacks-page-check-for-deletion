import json
import config
import helpers

def lambda_handler(event, context):
    for record in event['Records']:
        callback_url = record['messageAttributes']['callback_url']['stringValue']
        wd_page_id = record['messageAttributes']['page_id']['stringValue']
        wikidot_site = record['messageAttributes']['wikidot_site']['stringValue']
        
        data = {'page_id': wd_page_id, 'moduleName': 'pagerate/PageRateWidgetModule'}
        try:
            haystack = helpers.fetch(data, wikidot_site)
        except JSONDecodeError:  
            # We get a 500 error back on an actually 
            # deleted page which is exposed here as a JSON Decode error as we're 
            # looking for the body of the message, which isn't passed to us.
            
            # This is actually the only place we need to act because moved pages 
            # are handled by SCUTTLE firing a get_page_metadata job on what it 
            # sees as a 'new page.'

            headers = {"Authorization": "Bearer " + config.scuttle_token, "Content-Type": "application/json"}
            r = requests.delete(callback_url + '/2stacks/page/delete/' + str(wd_page_id), headers=headers)
            
            return { 'job': 'article_deleted' }
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
