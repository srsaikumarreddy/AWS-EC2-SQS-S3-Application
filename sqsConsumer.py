import os
import boto3
from PIL import Image
from io import BytesIO
import base64
import subprocess
from datetime import datetime

def process_message(message,input_bucket,output_bucket):

    print(f"message id: {message['MessageId']}")
    
    image_name="default"
    uid="default"

    if message['MessageAttributes'] is not None:
        image_name = message['MessageAttributes']['ImageName']['StringValue']
        uid = message['MessageAttributes']['UID']['StringValue']
        print("Image Name: ",image_name)
        print("UID: ",uid)

    #Face Recognition
    im = Image.open(BytesIO(base64.b64decode(message['Body'])))
    im.save(image_name)

    output = subprocess.run(["python3", "face_recognition.py", image_name], capture_output=True)
    label = output.stdout.decode("utf-8").rstrip("\n")
    name = label if label else 'default'

    print(name)

    #S3 Input
    try:
        file_name = str(image_name)
        input_obj = input_bucket.Object(file_name)
        with open(str(image_name), 'rb') as data:
            input_obj.upload_fileobj(data)
    except Exception as e:
        print(f"File upload to S3 Input Bucket : Fail ::: {repr(e)}")

    print("File upload to S3 Input Bucket : Success")

    #S3 Output
    file_name = str(image_name).split(".")[0]
    output_obj = output_bucket.Object(file_name)
    output_bucket_response = output_obj.put(Body=name)

    if output_bucket_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print("File upload to S3 Output Bucket : Success")
    else:
        print("File upload to S3 Output Bucket : Fail")


    os.system("rm " + str(image_name))

    result = {
        'ImageName' : image_name,
        'Name' : name,
        'UID': uid
    }

    return result

def send_message(sqs,result,output_queue_url):

    sqs.send_message(
        QueueUrl=output_queue_url,
        DelaySeconds=10,
        MessageAttributes={
            'ImageName': {
                    'StringValue': result['ImageName'],
                    'DataType': 'String'
                },
                'UID': {
                    'StringValue': result['UID'],
                    'DataType': 'String'
                }
        },
        MessageBody=(result['Name'])
    )

    print("Msg sent to Output Queue")

if __name__ == "__main__":

    AWS_REGION='us-east-1'
    AWS_ACCESS_KEY="AKIA3DVXYSAZCAPOFO4E"
    AWS_SECRET_ACCESS_KEY="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"

    INPUT_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/763815825458/InputQueue"
    OUTPUT_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/763815825458/OutputQueue"

    INPUT_BUCKET="ccprojgrp38input"
    OUTPUT_BUCKET="ccprojgrp38output"

    MESSAGE_ATTRIBUTES=['ImageName','UID']

    sqs = boto3.client("sqs",region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

    s3 = boto3.resource("s3",region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    input_bucket = s3.Bucket(INPUT_BUCKET)
    output_bucket = s3.Bucket(OUTPUT_BUCKET)

    while True:

        response = sqs.receive_message(
            QueueUrl=INPUT_QUEUE_URL,
            AttributeNames=MESSAGE_ATTRIBUTES,
            MaxNumberOfMessages=10,
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=30
        )
        if 'Messages' in response:
            print("Messages received at : ", datetime.now()) #.strftime("%H:%M:%S")
            for message in response['Messages']:
                try:
                    print("============================")
                    result=process_message(message,input_bucket,output_bucket)
                except Exception as e:
                    print(f"Exception while processing message: {repr(e)}")
                    continue

                try:
                    send_message(sqs,result,OUTPUT_QUEUE_URL)
                    print("============================")
                except Exception as e:
                    print(f"Exception while sending message: {repr(e)}")
                    continue
                
                try:
                    receipt_handle = message['ReceiptHandle']
                    sqs.delete_message(
                        QueueUrl=INPUT_QUEUE_URL,
                        ReceiptHandle=receipt_handle
                    )
                except Exception as e:
                    print(f"Exception while deleting message: {repr(e)}")
                    continue
