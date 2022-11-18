from ftplib import FTP
import hashlib
import os
from dateutil import parser
from datetime import datetime
from mail import send_message
from mail import gmail_authenticate
from pathlib import Path
import json
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


#reding from config.json
f = open("config.json")
data = json.load(f)

#ftp client parameters
HOST = data["ftp"]["host"]
USER = data["ftp"]["user"]
PASSWORD = data["ftp"]["password"]
SERVER_WD_FOLDER  = data["ftp"]["server_wd_path"]
LOCAL_WD = data["ftp"]["local_wd"]
HOUR = data["ftp"]["hour"]
MINUTE = data["ftp"]["minute"]
MAIL_RECEIVER = data["api_mail"]["receiver_mail"]
REMOVE_BOOL = data["ftp"]["remove"]
DAYS = data["ftp"]["days_before"]
if(DAYS < 0 or DAYS > 28):
    raise Exception("day_before in config.json: wrong value. > 0 e < 28")

#smtp parameter
SMTP_MY_ADDRESS = data["smtp"]["my_address"]
SMTP_PASSWORD = data["smtp"]["password"]
SMTP_HOST = data["smtp"]["host"]
SMTP_PORT = data["smtp"]["port"]
SMTP_RECEIVER_MAIL = data["smtp"]["receiver_mail"]
SMTP_SUBJECT = data["smtp"]["subject"]
SMTP_TEXT = data["smtp"]["text"]

WHICH_MAIL = data["which_mail"]

f.close()


#ftp connection parameter
ftp = FTP(HOST)
ftp.login(USER,PASSWORD)
ftp.cwd(SERVER_WD_FOLDER)
print("FTP connection right!")

#email parameter
service = gmail_authenticate()

# set up the SMTP server
s = smtplib.SMTP_SSL(SMTP_HOST,SMTP_PORT)
s.login(SMTP_MY_ADDRESS, SMTP_PASSWORD)
print("smtp login coorect!")

def switch(m):
    if(m == 1 ):
        return 31
    if(m == 2 ):
        return 28
    if(m == 3 ):
        return 31
    if(m == 4 ):
        return 30
    if(m == 5 ):
        return 31
    if(m == 6 ):
        return 30
    if(m == 7 ):
        return 31
    if(m == 8 ):
        return 31
    if(m == 9 ):
        return 30
    if(m == 10 ):
        return 31
    if(m == 11 ):
        return 30
    if(m == 12 ):
        return 31

def getdate():
    today = datetime.now().day - DAYS

    month = 0
    if(today<1):
        days_to_sub = DAYS - datetime.now().day 
        
        if(datetime.now().month == 1):
            month = 12
            year = datetime.now().year -1
            day_in_a_month = switch(month)
            day = day_in_a_month - days_to_sub
            dat = datetime.now()
            dat = dat.replace(day = day, month=month, year=year, minute = 55 , hour = 23 , second=0)
            return dat
        else:
            month = datetime.now().month -1

        day_in_a_month = switch(month)
        day = day_in_a_month - days_to_sub
        dat = datetime.now()
        dat = dat.replace(day = day,month=month, minute = 55 , hour = 23 , second=0)
        return dat

    else:
        dat = datetime.now()
        dat = dat.replace(day = today,minute = 55 , hour = 23 , second=0)
        return dat

def check_ftp_date():
     files = ftp.mlsd("/upload")

     for file in files:
          name = file[0]
          if(not(name == "." or name == "..")):
               timestamp = file[1]['modify']
               time = parser.parse(timestamp)
               print(name + ' - ' + str(time))
          else:
               break

     timestamp = ftp.voidcmd("MDTM /upload/myupload.txt")[4:].strip()
     time = parser.parse(timestamp)
     print(time)
  
def check_date(file):
     timestamp = os.path.getctime(file)
     time = datetime.fromtimestamp(timestamp)

     dat = getdate()
     print(dat)
     if(time < dat):
          if(REMOVE_BOOL):
               os.remove(file)
          print(str(file) + " removed.")
     else:
          return

def get_ftp_md5(ftp, remote_path):
    m = hashlib.md5()
    ftp.retrbinary(f'RETR {remote_path}', m.update)
    return m.hexdigest()

def upload_checksum(f):
     count = 0 #count to check consecutive right checksum of our file
     file = f
     file_to_upload = open(file,'rb')
     filename = os.path.basename(file)
     #print("filename= " + filename + "\n")
     #print("file = " + file)
     ftp.storbinary('STOR ' + filename, file_to_upload)

     file_to_upload.close()

     local_file_hash = hashlib.md5(open(file, 'rb').read()).hexdigest()
     server_file_hash = get_ftp_md5(ftp,filename) 


     if local_file_hash == server_file_hash:
          count = count + 1
          print("Successful transfer")
          if(count%50 == 0):
               count_str = str(count)
               send_message(service, MAIL_RECEIVER, "Ftp upload", 
               "We have reched" + count_str + "files upload correctly!")
     else:
          count = 0
          print("Failure transfer")

          if(WHICH_MAIL == "api"):
               #send mail on api gmail 
               sub_gmail = SMTP_SUBJECT + "from gmail"
               send_message(service, MAIL_RECEIVER, sub_gmail, 
               SMTP_TEXT + str(file))

          if(WHICH_MAIL == "smtp"):
               #send smtp mail
               msg = MIMEMultipart()
               msg['Subject'] = SMTP_SUBJECT + "from smtp"
               msg['From'] = SMTP_MY_ADDRESS
               msg['To'] = SMTP_RECEIVER_MAIL
               msg.preamble = SMTP_SUBJECT
               text = SMTP_TEXT + str(file)
               msg.attach(MIMEText(text,'plain'))

               s.sendmail(SMTP_MY_ADDRESS, SMTP_RECEIVER_MAIL, msg.as_string())
               s.quit()
          else:
               pass
          

data_folder = Path(LOCAL_WD)
for filename in os.listdir(LOCAL_WD):
     f = data_folder / filename
     if os.path.isfile(f):
          upload_checksum(f)
          check_date(f)
          print(f)



     



