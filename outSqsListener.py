import boto3
from datetime import datetime

def process_message(message):

    print(f"Message Body : {message['Body']}")
    print(f"Message ID : {message['MessageId']}")
    
    image_name="default"
    uid="default"
    label=''.join(filter(str.isalnum, str(message['Body'])))

    if message['MessageAttributes'] is not None:
        image_name = message['MessageAttributes']['ImageName']['StringValue']
        uid = message['MessageAttributes']['UID']['StringValue']
        print(f"Image Name : {image_name}")
        print(f"UID : {uid}")
 
    with open("requests_files/" + uid + ".txt", "w") as file:
        file.write(label)

if __name__ == "__main__":

    AWS_REGION='us-east-1'
    AWS_ACCESS_KEY="AKIA3DVXYSAZCAPOFO4E"
    AWS_SECRET_ACCESS_KEY="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"

    OUTPUT_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/763815825458/OutputQueue"

    MESSAGE_ATTRIBUTES=['ImageName','UID']

    sqs = boto3.client("sqs",region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

    while True:
        response = sqs.receive_message(
            QueueUrl=OUTPUT_QUEUE_URL,
            AttributeNames=MESSAGE_ATTRIBUTES,
            MaxNumberOfMessages=10,
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=30
        )
        if 'Messages' in response:
            for message in response['Messages']:
                try:
                    print("============================")
                    print("Message received at : ",datetime.now())#.strftime("%H:%M:%S")
                    process_message(message)
                    print("============================")
                except Exception as e:
                    print(f"Exception while processing message: {repr(e)}")
                    continue
                
                try:
                    receipt_handle = message['ReceiptHandle']
                    sqs.delete_message(
                        QueueUrl=OUTPUT_QUEUE_URL,
                        ReceiptHandle=receipt_handle
                    )
                except Exception as e:
                    print(f"Exception while deleting message: {repr(e)}")
                    continue