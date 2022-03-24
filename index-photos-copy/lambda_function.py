import json
import urllib.parse
import boto3
import datetime
from requests_aws4auth import AWS4Auth
import requests

print('Loading function')

s3 = boto3.client('s3')
TYPE = {'image/jpeg', 'image/png'}

def lambda_handler(event, context):
    # print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    # print("bucket is " + bucket + ", key is " + key)
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        # print(response)
        # print("CONTENT TYPE: " + response['ContentType'])
        
        # labels = getRekLabel(bucket, key)
        # label = response['Metadata']['customlabels'] # type: string, need to convert to 
        # print("labels are" + labels)
        # return response['ContentType']
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e
        
    # print(response['ContentType'])
    if response['ContentType'] not in TYPE:
        print('Uploaded file format not supported by lambda')
        return 
    # test case
    # key = 'sight.jpg'
    # bucket = 'coms6998hw2-b2'
    # key = 'sight3.jpg'
    # bucket = 'coms6998hw2-b2'
    # labels=['Landscape', 'Nature', 'Outdoors', 'Scenery', 'Aerial View']
    # labels=[['cat','fat'],['cat','fat'],['cat','fat'],['cat','fat'],['dog','dat'],['dog','dat'],['fish','pig'],['fish','pig'],['fish','pig'],
    # ['rat','dog'],['rat','dog']]
    # get labels from rekognition
    
    labels = getRekLabel(bucket,key)
    print(labels)
    
    photo_path = {  
        "objectKey": key,
        "bucket": bucket,
        "createdTimestamp": datetime.datetime.now().strftime("%y-%m-%d %H:%M:%S"),
        "labels": labels
    }
        
    # print(photo_path)
    response = dump_to_es(photo_path)
    print(response)
    
    return
    
def getRekLabel(bucket, key, MAX_LABEL=5): # solved ------------------
    # detect the top k labels of input figure
    # param list:
    
    # bucket: (String) bucket name of the stored figure
    # key: (String) key name of the figure
    # MAX_LABEL: (int) user defined maximum confidence scores labels to return, which
    # should be greater than 0
    
    rekognition = boto3.client('rekognition')
    response = rekognition.detect_labels(
        Image = {
            'S3Object' : {
                'Bucket' : bucket,
                'Name' : key
            }
        },
        MaxLabels=MAX_LABEL
    )
    
    # store detected labels
    labels = []
    for res in response['Labels']:
        labels.append(res['Name'])
    
    # get S3 metadata using headObject() method
    headObject = s3.head_object(Bucket=bucket, Key=key)

    # get metadata from head object
    metaData = headObject['Metadata']
    if len(metaData) != 0:
        custom_labels = metaData['customlabels'].split(',')
        labels.extend(custom_labels)
        
    # convert labels to lower case
    for i in range(len(labels)):
        labels[i] = labels[i].lower()
        
    return labels


def dump_to_es(path): 
    # dump the json format of the input figure to elastic search domain
    # param list:
    
    # path: json format of the input figure, with the format as:
    #     {"objectKey": ,
    #      "bucket": ,
    #      "createdTimestamp": ,
    #      "labels": 
    #     }
    
    endpoint = 'https://search-photos-gcpis6vjw5ug7kqim6bfijfera.us-east-1.es.amazonaws.com/photos/photo'
    headers = { "Content-Type": "application/json"}
    response = requests.post(endpoint, auth=("photo", "Photo123!"), json=path, headers=headers)
    
    return response 