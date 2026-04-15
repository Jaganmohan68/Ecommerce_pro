import smtplib
from email.message import EmailMessage   #EmailMessage-classname(camel_case) 

def sendmail(to,subject,body):
    server=smtplib.SMTP_SSL("smtp.gmail.com",465)
    server.login("jaganmohanmatsa@gmail.com","ywbl hbnv zfce lxxw")
    msg=EmailMessage()
    msg["FROM"]="jaganmohanmatsa@gmail.com"
    msg["TO"]=to
    msg["SUBJECT"]=subject
    msg.set_content(body)
    server.send_message(msg)
    server.close()