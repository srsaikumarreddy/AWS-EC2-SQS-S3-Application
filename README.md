# AWS-EC2-SQS-S3-Application
AWS Image Recognition as a service

Steps for setup:

Setup AWS Access Key and SSH Key. Download the .pem file

Setup SQS Input and Output Queues

Setup S3 Input and Output Buckets

Update the following values in all the appropriate files:
  AWS_REGION
  AWS_ACCESS_KEY
  AWS_SECRET_ACCESS_KEY
  INPUT_QUEUE_URL
  OUTPUT_QUEUE_URL
  INPUT_QUEUE_NAME
  INPUT_BUCKET
  OUTPUT_BUCKET
 
App-tier setup:
  Create an EC2 instance using given AMI

  Connect to the remote machine using SSH command and install the following:
    python pip3
    python boto3 - pip3 install boto3

  Transfer the following files to the instance:
    face_recognition_and_listener.py

  Setup cron job to run the worker code on start:
    crontab -e
    @reboot python3 -m face_recognition_and_listener
  
  Create new AMI. Make a note of the AMI ID, Security group ID and update the AMI_ID and SECURITY_GROUP_ID values in scaling.py

Web-tier setup:
  Create an EC2 instance
  
  Security group ingress rules

  Connect to the remote machine using SSH command and install the following:
    python pip3
    python Flask - pip3 install flask
    python boto3 - pip3 install boto3

  Transfer the following files to the instance using SCP command:
    app.py
    scaling.py
    outSqsListener.py


Workload Generator setup:

  Download the generator code and the images folder
  
  Test the application using the following command:
    python3 multithread_workload_generator.py --num_request 100 --image_folder face_images_100 --url http://<public-ip-of-web-tier-instance>:5000/

---------
  
Some useful commands:
  
Command that can be used for file transfer:
scp -i /path/my-key-pair.pem /path/my-file.txt ec2-user@my-instance-public-dns-name:path/

The .pem file can be downloaded from AWS UI after generating SSH key pair

Command that can be used to connect to remote machine:
ssh -i /path/my-key-pair.pem my-instance-user-name@my-instance-public-dns-name

Command that can be used to check for running python processes:
ps -ef | grep python

Command that can be used to check if Web App is up and running:
curl -X POST http://<public-ip-of-web-tier-instance>:5000/

Command that can be used to check if port is in use:
netstat -nlp | grep :<port>
