import json
import urllib.parse
import boto3
import datetime
import requests
from requests_aws4auth import AWS4Auth
import inflect

s3 = boto3.client('s3')
# Define the client to interact with Lex
client = boto3.client('lex-runtime')

def lambda_handler(event, context):
    print("Lambda function search called.")
    print(event)

    try:
        label_origin = event['queryStringParameters']['q']
    except:
        print('Input query format error!')
        return 
    
    # label_origin = 'cat and butterflies'
    # get labels from frontend
    labels = read_from_lex(label_origin)
    
    print(labels)
    # # test case
    # labels = ['building'] 
    
    photo_path = {}
    photo_path = ES_match(labels)
    
    # delete the object in elastic search with key name
    # delete()
    
    print(photo_path)
    # return result to frontend
    return{
        "isBase64Encoded": 'false',
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Headers': 'Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With,x-api-key',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,PUT,GET',
        },
        'body': json.dumps(photo_path)
    }
    

def read_from_lex(message):
    last_user_message = message
    
    # change this to the message that user submits on 
    # your website using the 'event' variable
    
    # print(f"Message from frontend: {last_user_message}")
    response = client.post_text(botName='PhotoBot',
                                botAlias='photo',
                                userId='photouser',
                                inputText=last_user_message)
    # print(json.dumps(response,indent=2))
    
    labels = []
    
    if 'intentName' not in response:
        return labels
    
    if response['intentName'] == 'SearchIntent':
        for label in  list(response['slots'].values()):
            if label is not None:
                labels.append(label)
    
    result = []
    p = inflect.engine()
    for word in labels:
        if p.singular_noun(word):
            result.append(p.singular_noun(word))
        else:
            result.append(word)
    
    return result

def delete(key='BabyGoat_ROW9287280510_1920x1200.jpg'):
    region = 'us-east-1' 
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    
    # OpenSearch domain endpoint
    host = 'https://search-photos-gcpis6vjw5ug7kqim6bfijfera.us-east-1.es.amazonaws.com/' 
    index = 'photos'
    url = host + index + '/_delete_by_query'

    # Elasticsearch 6.x requires an explicit Content-Type header
    headers = {"Content-Type": "application/json"}
    
    query = {
        "query": {
            "match": {
                "objectKey": key
            }
        }
    }
    
    # Make the signed HTTP request
    r = requests.post(url, auth=awsauth, headers=headers, data=json.dumps(query))
    
    print(r)
    return 
    
def ES_match(labels):
    """
        using elastic search to search 'id' with given record number and message
        message here is the index in elastic search
        
        return type: {'id1': value1, 'id2': value2, ...}
    """
    
    # convert to lower case
    if labels:
        for i in range(len(labels)):
            labels[i] = labels[i].lower()
        
        # remove duplicate search label
        labels = list(set(labels))
    else:
        return []
    
    region = 'us-east-1' 
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    
    # OpenSearch domain endpoint
    host = 'https://search-photos-gcpis6vjw5ug7kqim6bfijfera.us-east-1.es.amazonaws.com/' 
    index = 'photos'
    url = host + index + '/_search'

    # Elasticsearch 6.x requires an explicit Content-Type header
    headers = {"Content-Type": "application/json"}
    
    result = []
    
    for label in labels:
        img_url = dict()
        query = {
            "query": {
                "match": {
                    "labels": label
                }
            }
        }
        # Make the signed HTTP request
        r = requests.get(url, auth=awsauth, headers=headers, data=json.dumps(query))
     
        # get elastic search results and load by json
        
        Idx = json.loads(r.text)
        
        if 'error' in Idx.keys():
            continue
            
        try:
            if Idx['hits']:
                for record in Idx['hits']['hits']:
                    # transfer format 'restaurant_id' to 'id' to fit dynamoDB search
                    img_bucket = record['_source']['bucket']
                    img_key = record['_source']['objectKey']
                    if label not in img_url:
                        img_url[label] = [{'url': 'https://s3.amazonaws.com/' + str(img_bucket) + '/' + str(img_key)}]
                    else:
                        img_url[label].append({'url': 'https://s3.amazonaws.com/' + str(img_bucket) + '/' + str(img_key)})
            else:
                img_url[label] = []
        except:
            img_url[label] = [img_url]
        
        result.append(img_url)
    
    print(json.dumps(result, indent=2))
    return result
