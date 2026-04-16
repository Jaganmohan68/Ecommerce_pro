from flask import Flask,url_for,redirect,render_template,request,flash
from otp import genotp
from cmail import sendmail
from stoken import endata, dndata
from flask_bcrypt import Bcrypt
from mysql.connector import (connection)
mydb=connection.MySQLConnection(user="root",host="localhost",password="Admin@68",db="ecomdb")

app=Flask(__name__) #class
bcrypt=Bcrypt(app)
app.secret_key="Code2345"
@app.route("/")
def home():
    return render_template("welcome.html")

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/admincreate",methods=["GET","POST"])
def admincreate():
    if request.method=="POST":
        admin_username=request.form['username']
        admin_useremail=request.form['email']
        admin_userpassword=request.form['password']
        admin_useraddress=request.form['address']
        admin_useragree=request.form['agree']
        admin_otp=genotp()

        admin_data={"admin_username":admin_username,"admin_useremail":admin_useremail,
                    "admin_userpassword":admin_userpassword,"admin_useraddress":admin_useraddress,
                    "admin_useragree":admin_useragree,"admin_otp":admin_otp}
        
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("select count(*) from admindata where admin_email=%s",[admin_useremail])
            email_count=cursor.fetchone()[0]
            cursor.close()
        except Exception as e:
            print(e)
            flash("something went wrong")
            return redirect(url_for('admincreate'))
        else:
            if email_count==0:
                
                subject="OTP For Ecomdb verification"
                body=f"User the given OTP for verification is {admin_otp}"
                sendmail(to=admin_useremail,subject=subject,body=body)
                flash("OTP has been sent to given email...")
                return redirect(url_for("adminotpverify",serverdata=endata(admin_data)))

            elif email_count==1:
                flash("email already existed")
                return redirect(url_for('admincreate'))
            else:
                flash("email not found")
                return redirect(url_for('admincreate'))
            
    return render_template("admincreate.html")

@app.route("/adminotpverify/<serverdata>",methods=["GET","POST"])
def adminotpverify(serverdata):
    if request.method=="POST":
        userotp=request.form["otp"]
        try:
            admin_data=dndata(serverdata)
        except Exception as e:
            print(e)
            flash("TimeOut error")
            return redirect(url_for('admincreate'))
        else:
            if admin_data["admin_otp"]==userotp:

                try:
                    hash_password=bcrypt.generate_password_hash(admin_data["admin_userpassword"])
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute=('insert into admindata(adminid,admin_username,admin_email,admin_address,admin_agree,admin_password) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s)',[admin_data["admin_username"],admin_data['admin_useremail'],admin_data['admin_useraddress'],admin_data["admin_useragree"],hash_password]) 
                    mydb.commit()
                    cursor.close()
                except Exception as e:
                    print(e)
                    flash("Could not store details...")
            else:
                flash("Wrong OTP")
                return redirect(url_for("adminotpverify",serverdata=serverdata))
    return render_template("adminotp.html")

app.run(debug=True,use_reloader=True)

