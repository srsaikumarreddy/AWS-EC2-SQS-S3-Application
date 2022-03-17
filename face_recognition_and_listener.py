# importing libraries
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
from torchvision import datasets
from torch.utils.data import DataLoader
from PIL import Image
import csv
import os
import sys
import boto3
from io import BytesIO
import base64
import subprocess
from datetime import datetime

mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20) # initializing mtcnn for face detection
resnet = InceptionResnetV1(pretrained='vggface2').eval() # initializing resnet for face img to embeding conversion

#test_image = sys.argv[1]
#dataset=datasets.ImageFolder('../data/test_images/') # photos folder path 
#dir_path = os.getcwd()
#dataset=datasets.ImageFolder(dir_path +'/face_images_100_1/') # photos folder path 
#idx_to_class = {i:c for c,i in dataset.class_to_idx.items()} # accessing names of peoples from folder names
#print(idx_to_class)

def collate_fn(x):
    return x[0]

#loader = DataLoader(dataset, collate_fn=collate_fn)

#face_list = [] # list of cropped faces from photos folder
#name_list = [] # list of names corrospoing to cropped photos
#embedding_list = [] # list of embeding matrix after conversion from cropped faces to embedding matrix using resnet
#
#for img, idx in loader:
#    face, prob = mtcnn(img, return_prob=True) 
#    if face is not None and prob>0.90: # if face detected and porbability > 90%
#        emb = resnet(face.unsqueeze(0)) # passing cropped face into resnet model to get embedding matrix
#        embedding_list.append(emb.detach()) # resulten embedding matrix is stored in a list
#        name_list.append(idx_to_class[idx]) # names are stored in a list
#
#
#data = [embedding_list, name_list]
#torch.save(data, 'data.pt') # saving data.pt file

def face_match(img_path, data_path): # img_path= location of photo, data_path= location of data.pt 
    # getting embedding matrix of the given img
    img = Image.open(img_path)
    face, prob = mtcnn(img, return_prob=True) # returns cropped face and probability
    emb = resnet(face.unsqueeze(0)).detach() # detech is to make required gradient false
    
    saved_data = torch.load('data.pt') # loading data.pt file
    embedding_list = saved_data[0] # getting embedding data
    name_list = saved_data[1] # getting list of names
    dist_list = [] # list of matched distances, minimum distance is used to identify the person
    
    for idx, emb_db in enumerate(embedding_list):
        dist = torch.dist(emb, emb_db).item()
        dist_list.append(dist)
        
    idx_min = dist_list.index(min(dist_list))
    return (name_list[idx_min], min(dist_list))


#result = face_match('../data/test_images/angelina_jolie/1.jpg', 'data.pt')
#result = face_match(test_image, 'data.pt')

#print('Face matched with: ',result[0], 'With distance: ',result[1])
#print(result[0])


def process_message(message,input_bucket,output_bucket):

    print(f"message id: {message['MessageId']}")
    
    image_name="default"
    uid="default"

    if message['MessageAttributes'] is not None:
        image_name = message['MessageAttributes']['ImageName']['StringValue']
        uid = message['MessageAttributes']['UID']['StringValue']
        print("Image Name: ",image_name)
        print("UID: ",uid)

    #Save Image
    im2 = base64.b64decode(message['Body'])
    with open(image_name,"wb") as f:
        f.write(im2)

    if not os.path.exists(image_name):
        im = Image.open(BytesIO(base64.b64decode(message['Body'])))
        im.save(image_name)

    
    #Face Recognition

    #output = subprocess.run(["python3", "face_recognition.py", image_name], capture_output=True)
    #label = output.stdout.decode("utf-8").rstrip("\n")
    #name = label if label else 'default'

    output = str(face_match(image_name, 'data.pt')[0])
    name = output if output else 'default'

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
        'ImageName' : image_name,   # test_00.jpg
        'Name' : name,              # Paul
        'UID': uid                  # UID_001
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
