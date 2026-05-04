from flask import Flask,url_for,redirect,render_template,request,flash,session
from flask_session import Session
from otp import genotp
from cmail import sendmail
from stoken import endata, dndata
from flask_bcrypt import Bcrypt
from mysql.connector import (connection)
import os
import razorpay
client=razorpay.Client(auth=("rzp_test_Sjy5hYBNuv6idu","IHR2o3q89UEP4oZRQnzvxAtW"))
from werkzeug.utils import secure_filename # it checks weather file name consists of extra "/ or ,
mydb=connection.MySQLConnection(user="root",host="localhost",password="Admin@68",db="ecomdb")

# to save the files in a uploads folder

BASE_DIR=os.path.abspath(os.path.dirname(__file__)) # finds the exact path directory
UPLOAD_FOLDER=os.path.join(BASE_DIR,"static","uploads")
os.makedirs(UPLOAD_FOLDER,exist_ok=True)
ALLOWED_EXTENSIONS={"png","jpg","jpeg","gif","webp"}
MAX_CONTENT_LENGTH=6*1024*1024 # 6MB


app=Flask(__name__) #class
bcrypt=Bcrypt(app)
app.secret_key="Code2345"
app.config["SESSION_TYPE"]="filesystem" # redies
app.config["UPLOAD_FOLDER"]=UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"]=MAX_CONTENT_LENGTH
Session(app)

@app.route("/")
def home(): 
    return render_template("welcome.html")

@app.route("/index")
def index():
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute("select bin_to_uuid(itemid), itemname, item_description, item_about, item_price, item_quantity, item_category, filename from items ")
        allitems_data=cursor.fetchall()
        print(allitems_data)
        cursor.close()
    except Exception as e:
        print(e)
        flash("could not get all item data...")
        return redirect(url_for("index"))
    else:
        return render_template("index.html",allitems_data=allitems_data)


#----- Defining Admin routes.......

@app.route("/admincreate",methods=["GET","POST"])
def admincreate():
    if request.method=="POST":
        admin_username=request.form['username']
        admin_useremail=request.form['email']
        admin_userpassword=request.form['password']
        admin_useraddress=request.form['address']
        admin_useragree=request.form.get('agree', 'off')
        admin_otp=genotp()

        admin_data={"admin_username":admin_username,"admin_useremail":admin_useremail,
                    "admin_userpassword":admin_userpassword,"admin_useraddress":admin_useraddress,
                    "admin_useragree":admin_useragree,"admin_otp":admin_otp}
        
        try:
            cursor=mydb.cursor(buffered=True)
            print("admincreate")
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

@app.route('/adminotpverify/<serverdata>',methods=['GET','POST'])
def adminotpverify(serverdata):
    if request.method=='POST':
        userotp=request.form['otp']
        try:
            admin_data=dndata(serverdata)#{'admin_username':admin_username,'admin_useremail':admin_useremail,'admin_password':admin_password,'admin_address':admin_address,'adminagree':admin_agree,'admin_otp':admin_otp}
        except Exception as e:
            print(e)
            flash('Time out error')
            return redirect(url_for('admincreate'))
        else:
            if str(admin_data['admin_otp'])==str(userotp):
                print("anything")
                try:
                    hash_password=bcrypt.generate_password_hash(admin_data['admin_userpassword'])
                    print(hash_password)
                    cursor=mydb.cursor(buffered=True)
                    print("Nothing")
                    cursor.execute('insert into admindata(adminid,admin_username,admin_email,admin_address,admin_agree,admin_password) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s)',[admin_data['admin_username'],admin_data['admin_useremail'],admin_data['admin_useraddress'],admin_data['admin_useragree'],hash_password])
                    mydb.commit()
                    cursor.close()   
                except Exception as e:
                    print(e)
                    flash('Could not store details')
                    return redirect(url_for('admincreate'))
                else:
                    flash('User registered successfully')
                    return redirect(url_for('adminlogin'))
            else:
                flash('Wrong otp')
                return redirect(url_for('adminotpverify',serverdata=serverdata))

    return render_template('adminotp.html', serverdata=serverdata)

@app.route('/resendotp/<serverdata>')
def adminotpresent(serverdata):
    try:
        admin_data=dndata(serverdata)#{'admin_username':admin_username,'admin_useremail':admin_useremail,'admin_password':admin_password,'admin_address':admin_address,'adminagree':admin_agree,'admin_otp':admin_otp}
    except Exception as e:
        print(e)
        flash('Time out error')
        return redirect(url_for('admincreate'))
    else:
        admin_otp=genotp()
        admin_data['admin_otp']=admin_otp
        subject='OTP For Ecom23 verification'
        body=f"use the given otp for verification {admin_otp}"
        sendmail(to=admin_data['admin_useremail'],subject=subject,body=body)
        flash('OTP has been sent given mail')
        return redirect(url_for('adminotpverify',serverdata=endata(admin_data)))

@app.route("/adminlogin",methods=["GET","POST"])
def adminlogin():
    if request.method=="POST":
        login_email=request.form["email"]
        login_password= request.form["password"]
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("select count(*) from admindata where admin_email=%s",[login_email])
            email_count=cursor.fetchone() # (1,) (0,)
            cursor.close()
        except Exception as e:
            print(e)
            flash("Could not connect db")
            return redirect (url_for("adminlogin"))
        else:
            if email_count:
                if email_count[0]==1: 
                    try:
                        cursor=mydb.cursor(buffered=True)
                        cursor.execute("select admin_password from admindata where admin_email=%s",[login_email])
                        stored_password=cursor.fetchone() # ("sdfghjkjhgf")
                        if stored_password:
                            if bcrypt.check_password_hash(stored_password[0],login_password):
                                session["admin"]=login_email
                                return redirect(url_for("admindashboard"))
                            else:
                                flash("Wrong Password")
                                return redirect(url_for("adminlogin"))
                        else:
                            flash("could not verify password")
                            return redirect(url_for("adminlogin"))
                    except Exception as e:
                        print(e)
                        flash("could not verify password")
                        return redirect(url_for("adminlogin"))
                elif email_count[0]==0:
                    flash("Email not found")
                    return redirect(url_for("adminlogin"))
            else:
                flash("Email Not Found")
                return redirect(url_for("adminlogin"))
    return render_template("adminlogin.html")

@app.route("/admindashboard")
def admindashboard():
    if session.get("admin"):
        return render_template("adminpanel.html")
    else:
        flash("Please Login to Access")
        return redirect(url_for("adminlogin"))

def allowed_file(filename:str)->bool:
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/additem",methods=["GET","POST"])
def additem():
    if session.get("admin"):
        if request.method=="POST":
            item_name=request.form["title"]
            item_description=request.form["Description"]
            item_about=request.form["About_item"]
            item_price=request.form["price"]
            item_quantity=request.form["quantity"]
            item_category=request.form["category"]
            item_filedata=request.files["file"]
            item_filename=item_filedata.filename
            print(item_filename)

            if item_filedata and item_filename:
                if not allowed_file(item_filename):
                    flash("file type not allowed: png, jpeg,jpg,webp,gif")
                    return redirect(url_for("additem"))
                orig_secure=secure_filename(item_filename)
                print(orig_secure)
                ext=os.path.splitext(orig_secure)[1]
                print(ext)
                filename=genotp()+ext 
                save_path=os.path.join(app.config["UPLOAD_FOLDER"], filename)
                try:
                    item_filedata.save(save_path)
                except Exception as e:
                    print(e)
                    flash("could not save file")
                    return redirect(url_for("additem"))
            
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute("select adminid from admindata where admin_email=%s",[session.get("admin")])
                admin_id=cursor.fetchone()[0]
                cursor.execute("insert into items(itemid,itemname,item_description,item_about,item_price,item_quantity,item_category,filename,added_by) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s,%s,%s)",[item_name,item_description,item_about,item_price,item_quantity,item_category,filename,admin_id])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                if filename:   
                    try:
                        os.remove(save_path)
                    except Exception as e:
                        print(e)
                        return redirect(url_for('additem'))
                flash("could not store items in db")
                return redirect(url_for('additem'))
            else:
                flash("item stored successfully")
                return redirect(url_for('additem'))
          
        return render_template('additem.html')
    else:
        flash('please login to add item')
        return redirect(url_for('adminlogin'))
    
@app.route("/viewall_items")
def viewall_items():
    if session.get("admin"):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("select adminid from admindata where admin_email=%s",[session.get("admin")])
            admin_id=cursor.fetchone()[0]
            if admin_id:
                cursor.execute("select bin_to_uuid(itemid), itemname, item_description, item_about, item_price, item_quantity, item_category, filename from items where added_by=%s", [admin_id])
                allitems_data=cursor.fetchall()
                print(allitems_data)
                cursor.close()
            else:
                flash("Could not verify admin")
                return redirect(url_for("admindashboard"))
        except Exception as e:
            print(e)
            flash("could not get all item data...")
            return redirect(url_for("admindashboard"))
        else:
            return render_template("viewall_items.html",allitems_data=allitems_data)
    else:
        flash("please login to view items") 
        return redirect(url_for("adminlogin"))
        
@app.route("/view_item/<itemid>")
def view_item(itemid):
    if session.get("admin"):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("select adminid from admindata where admin_email=%s",[session.get("admin")])
            admin_id=cursor.fetchone()[0]
            if admin_id:
                cursor.execute("select bin_to_uuid(itemid), itemname, item_description, item_about, item_price, item_quantity, item_category, filename from items where uuid_to_bin(%s)=itemid and added_by=%s", [itemid, admin_id])
                item_data=cursor.fetchone()
                cursor.close()
            else:
                flash("could not verify admin")
                return redirect(url_for("viewall_items"))
        except Exception as e:
            print(e)
            flash("Could not get Item details") 
            return redirect(url_for("viewall_items"))
        else:
            return render_template("view_item.html",item_data=item_data)
    else:
        flash("Please login to view all items")
        return redirect(url_for("adminlogin"))
            
@app.route("/deleteitem/<itemid>")
def deleteitem(itemid):  
    if session.get("admin"):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("select adminid from admindata where admin_email=%s",[session.get("admin")])
            admin_id=cursor.fetchone()[0]
            if admin_id:
              
                cursor.execute("select filename from items where added_by=%s and uuid_to_bin(%s)=itemid", [admin_id, itemid])
                result=cursor.fetchone()
                
                if result:
                    filename=result[0]
                    cursor.execute("delete from items where added_by=%s and uuid_to_bin(%s)=itemid", [admin_id, itemid])
                    mydb.commit()
                    
                 
                    if filename:
                        file_path=os.path.join(app.config["UPLOAD_FOLDER"], filename)
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        except Exception as e:
                            print(f"Error deleting file: {e}")
                    
                    cursor.close()
                    flash("Item Deleted Successfully")
                    return redirect(url_for("viewall_items"))
                else:
                    cursor.close()
                    flash("Item not found")
                    return redirect(url_for("viewall_items"))
            else:
                flash("could not verify admin")
                return redirect(url_for("viewall_items"))
        except Exception as e:
            print(e)
            flash("could not delete item")
            return redirect(url_for("viewall_items"))
    else:
        flash("Please login to view all items")
        return redirect(url_for("adminlogin"))

@app.route('/updateitem/<itemid>',methods=['GET','POST'])
def updateitem(itemid):
    if not session.get('admin'):
        flash('PLs login to updateitem')
        return redirect(url_for('adminlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select adminid from admindata where admin_email=%s',[session.get('admin')])
        admin_id=cursor.fetchone()
        # print("hey")
        if not admin_id:
            flash('Admin not verified')
            return redirect(url_for('viewall_items'))
        admin_data=admin_id[0]
        cursor.execute('select bin_to_uuid(itemid),itemname,item_description,item_about,item_price,item_quantity,item_category,filename from items where added_by=%s and itemid=uuid_to_bin(%s)',[admin_data,itemid])
        storeditem_data=cursor.fetchone()
    
        if not storeditem_data:
            flash('Item details not found')
            return redirect(url_for('viewall_items'))
        filename=storeditem_data[7]
        old_filename=storeditem_data[7]
        cursor.close()
        
    except Exception as e:
        app.logger.exception(f'Could not fetch item data : {e}')
        flash('Could not find item')
        return redirect(url_for('viewall_items'))
    else:
        if request.method=='POST':
            print(request.form)
            updateditem_name=request.form['title']
            updateditem_description=request.form['Description']
            updateditem_about=request.form['About_item']
            updateditem_cost=request.form['price']
            updateditem_quantity=request.form['quantity']
            updateditem_category=request.form['category']
            updateditem_filedata=request.files['file']
            print(updateditem_filedata)
            updateditem_filename=updateditem_filedata.filename
            new_file_path=None
            if updateditem_filedata and updateditem_filename:
                if not allowed_file(updateditem_filename):
                    flash('File type not allowed: png,jpg,jpeg,webp,gif')
                    return redirect(url_for('updateitem',itemid=itemid))
                orig_secure=secure_filename(updateditem_filename)
                ext=os.path.splitext(orig_secure)[1]
                filename=genotp()+ext
                new_file_path=os.path.join(app.config["UPLOAD_FOLDER"],filename)
                try:
                    updateditem_filedata.save(new_file_path)
                except Exception as e:
                    app.logger.exception(f'File save failed:{e}')
                    flash('could not save file')
                    return redirect(url_for('updateitem',itemid=itemid))
            #DB update
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update items set itemname=%s,item_description=%s,item_about=%s,item_price=%s,item_quantity=%s,item_category=%s,filename=%s where added_by=%s and itemid=uuid_to_bin(%s)',[updateditem_name,updateditem_description,updateditem_about,updateditem_cost,updateditem_quantity,updateditem_category,filename,admin_data,itemid])
                mydb.commit()
                cursor.close()
            except Exception as e:
                mydb.rollback()
                app.logger.exception(f'DB update failed:{e}')
                # remove newly uploaded file if db fails
                if new_file_path and os.path.exists(new_file_path):
                    os.remove(new_file_path)
                flash('Could not update item details')
                return redirect(url_for('updateitem',itemid=itemid))
            #After Db success --> delete old img
            else:
                if new_file_path and old_filename:
                    try:
                        old_path=os.path.join(app.config["UPLOAD_FOLDER"],old_filename)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    except Exception as e:
                        app.logger.warning(f'Old file delete failed :{e}')
                flash('Item Updated successfully')
                return redirect(url_for('updateitem',itemid=itemid))
        return render_template('updateitem.html',item_data=storeditem_data)
    
@app.route('/adminprofileupdate',methods=['GET','POST'])
def adminprofileupdate():
    if not session.get('admin'):
        flash("pls login to view dashboard")
        return redirect(url_for('adminlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select adminid,admin_username,admin_phone,admin_address,admin_profileimg from admindata where admin_email=%s',[session.get('admin')])
        admin_data=cursor.fetchone()
        if not admin_data:
            flash('Admin not verified')
            return redirect(url_for('admindashboard'))
        cursor.close()
    except Exception as e:
        app.logger.exception(f'Could not fetch admin data : {e}')
        flash('Could not find admin details')
        return redirect(url_for('admindashboard'))
    else:
        if request.method=='POST':
            updatedadmin_username=request.form['adminname']
            updatedadmin_address=request.form['address']
            updatedadmin_phone=request.form['ph_no'] #"None"
            updatedadmin_profileimg=request.files['file']
            updatedadmin_filename=updatedadmin_profileimg.filename
            new_file_path=None
            filename=admin_data[4]
            old_filename=admin_data[4]
            if eval(updatedadmin_phone)==None: #  updatedadmin_phone=="None"
                updated_phone="0000000000"
            else:
                updated_phone=updatedadmin_phone
            
                
            if updatedadmin_filename:
                if not allowed_file(updatedadmin_filename):
                    flash('File type not allowed: png,jpg,jpeg,webp,gif')
                    return redirect(url_for('adminprofileupdate'))
                orig_secure=secure_filename(updatedadmin_filename) # it removes unwanted data
                ext=os.path.splitext(orig_secure)[1] # .jpg
                filename=genotp()+ext
                new_file_path=os.path.join(app.config["UPLOAD_FOLDER"],filename)
                try:
                    updatedadmin_profileimg.save(new_file_path)
                except Exception as e:
                    app.logger.exception(f'File save failed:{e}')
                    flash('could not save file')
                    return redirect(url_for('adminprofileupdate'))

            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update admindata set admin_username=%s,admin_address=%s,admin_profileimg=%s,admin_phone=%s where admin_email=%s',[updatedadmin_username,updatedadmin_address,filename,updated_phone,session.get('admin')])
                mydb.commit()
                cursor.close()
            except Exception as e:
                mydb.rollback()
                app.logger.exception(f'DB update failed:{e}')
                # remove newly uploaded file if db fails
                if new_file_path and os.path.exists(new_file_path):
                    os.remove(new_file_path)
                flash('Could not update admin details')
                return redirect(url_for('adminprofileupdate'))
            #After Db success --> delete old img
            else:
                if new_file_path and old_filename:
                    try:
                        old_path=os.path.join(app.config["UPLOAD_FOLDER"],old_filename)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    except Exception as e:
                        app.logger.warning(f'Old file delete failed :{e}')
                flash('admin Updated successfully')
                return redirect(url_for('adminprofileupdate'))
    return render_template('adminupdate.html',admin_data=admin_data)

@app.route("/adminlogout")
def adminlogout():
    if not session.get("admin"):
        flash("Please login to view dashboard")
        return redirect(url_for("adminlogin"))
    else:
        session.pop("admin")
        return redirect(url_for("adminlogin")) 








#-------------- defining user routes.......

@app.route("/usersignup",methods=["GET","POST"])
def usersignup():
    if request.method=="POST":
        user_username=request.form["name"]
        user_useremail=request.form['email']
        user_useraddress=request.form['address']
        user_userphone=request.form["phone_no"]
        user_password=request.form["password"]
        user_gender=request.form.get('usergender')  # Correctly extract gender from form
        user_otp=genotp()

        user_data={"user_username":user_username,"user_useremail":user_useremail,
                    "user_password":user_password,"user_useraddress":user_useraddress,
                    "user_userphone":user_userphone,"user_gender":user_gender,"user_otp":user_otp}
        
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("select count(*) from userdata where user_email=%s",[user_useremail])
            email_count=cursor.fetchone()[0]
            cursor.close()
        except Exception as e:
            print(e)
            flash("something went wrong")
            return redirect(url_for('usercreate'))
        else:
            if email_count==0:
                subject="OTP For Ecomdb verification"
                body=f"Use the given OTP for verification: {user_otp}"
                sendmail(to=user_useremail,subject=subject,body=body)
                flash("OTP has been sent to your email...")
                return redirect(url_for("userotpverify",serverdata=endata(user_data)))
            elif email_count==1:
                flash("Email already exists")
                return redirect(url_for('usersignup'))
            else:
                flash("Email verification failed")
                return redirect(url_for('usersignup'))
    
    return render_template("usersignup.html")

@app.route('/userotpverify/<serverdata>',methods=['GET','POST'])
def userotpverify(serverdata):
    if request.method=='POST':
        userotp=request.form['otp']
        try:
            user_data=dndata(serverdata)
        except Exception as e:
            print(e)
            flash('Time out error')
            return redirect(url_for('usercreate'))
        else:
            if str(user_data['user_otp'])==str(userotp):
                print("hey jagan")
                try:
                    hash_password=bcrypt.generate_password_hash(user_data['user_password'])
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute('insert into userdata(userid,username,user_email,address,user_phone,gender,password) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s)',[user_data['user_username'],user_data['user_useremail'],user_data['user_useraddress'],user_data['user_userphone'],user_data['user_gender'],hash_password])
                    mydb.commit()
                    cursor.close()   
                except Exception as e:
                    print(e)
                    flash('Could not store details')
                    return redirect(url_for('usercreat'))
                else:
                    flash('User registered successfully')
                    return redirect(url_for('userlogin'))
            else:
                flash('Wrong OTP')
                return redirect(url_for('userotpverify',serverdata=serverdata))
    return render_template('userotp.html', serverdata=serverdata)

@app.route('/resenduserotp/<serverdata>')
def userotpresent(serverdata): 
    try:
        user_data=dndata(serverdata)
    except Exception as e:
        print(e)
        flash('Time out error')
        return redirect(url_for('usersignup'))
    else:
        user_otp=genotp()
        user_data['user_otp']=user_otp
        subject='OTP For Ecom23 verification'
        body=f"use the given otp for verification {user_otp}"
        sendmail(to=user_data['user_useremail'],subject=subject,body=body)
        flash('OTP has been sent given mail')
        return redirect(url_for('userotpverify',serverdata=endata(user_data)))

@app.route('/userlogin',methods=['GET','POST'])
def userlogin():
    if request.method=='POST':
        login_email=request.form["email"]
        login_password=request.form['password']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from userdata where user_email=%s',[login_email])
            email_count=cursor.fetchone() #(1,) or (0,) none
            cursor.close()
        except Exception as e:
            print(e)
            flash('Could not connect db')
            return redirect(url_for('userlogin'))
        else:
            if email_count:
                if email_count[0]==1:
                    try:
                        cursor=mydb.cursor(buffered=True)
                        cursor.execute('select password from userdata where user_email=%s',[login_email])
                        stored_password=cursor.fetchone() #('fgjvjfj',)
                        if stored_password:
                            if bcrypt.check_password_hash(stored_password[0],login_password):
                                print(session)
                                session['user']=login_email
                                print(session,'user')
                                if not session.get(login_email):
                                    session[login_email]={}
                                print(session,'user cart session')
                                return redirect(url_for('index'))
                            else:
                                flash('Wrong password')
                                return redirect(url_for('userlogin'))
                        else:
                            flash(' password not found')
                            return redirect(url_for('userlogin'))
                    except Exception as e:
                        print(e)
                        flash('Could Verify password')
                        return redirect(url_for('userlogin'))        
                elif email_count[0]==0:
                    flash('Email not found')
                    return redirect(url_for('userlogin'))
            else:
                flash('Email Not registered')
                return redirect(url_for('userlogin'))
    return render_template('userlogin.html')

# @app.route("/userdashboard")
# def userdashboard():
#     if session.get("user"):
#         return "Login Dashboard"
#     else:
#         flash("Please Login to Access")
#         return redirect(url_for("userlogin"))
 
@app.route('/addcart/<itemid>',methods=['GET'])
def addcart(itemid):
    if not session.get('user'):
        flash('pls login to addcart')
        return redirect(url_for('userlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(itemid),itemname,item_description,item_about,item_price,item_quantity,item_category,filename from items where itemid=uuid_to_bin(%s)',[itemid])
        item_data=cursor.fetchone()
        cursor.close()
    except Exception as e:
        print(e)
        flash('Could not get item data')
        return redirect(url_for('index'))
    else:
        print(session)
        if itemid not in session[session.get('user')]:
            session[session.get('user')][itemid]=[item_data[1],1,item_data[4],item_data[5],item_data[6],item_data[7]]
            session.modified=True
            print(session)
            flash('item added to cart')
            return redirect(url_for('index'))
        else:
            session[session.get('user')][itemid][1] +=1
            session.modified=True
            print(session,'already')
            flash('item already in  cart')
            return redirect(url_for('index'))
@app.route('/viewcart')
def viewcart():
    if not session.get('user'):
        flash('pls login to view cart')
        return redirect(url_for('userlogin'))
    try:
        user=session.get('user')
        items=session.get(user,{})
        print(items)
        items_total=0
        items_for_display=[]
        for itemid,data in items.items():
            name=data[0]
            price=float(data[2])
            quantity=int(data[1])
            category=data[4] if len(data)>3 else None
            img=data[5] if len(data)>4 else None
            subtotal=price * quantity
            items_total +=subtotal
            items_for_display.append({
                'id':itemid,
                'name':name,
                'price':price,
                'quantity':quantity,
                'category':category,
                'imgname':img
            })
        delivery=40
        tax=round(items_total *0.05,2)
        grand_total=items_total+delivery+tax
        return render_template('cart.html',items_for_display=items_for_display,delivery=delivery,tax=tax,grand_total=grand_total,items_total=items_total)
    except Exception as e:
        print(e)
        flash('Could not get items details')
        return redirect(url_for('index'))
@app.route('/updatecart/<itemid>',methods=['POST'])
def updatecart(itemid):
    if not session.get('user'):
        flash('pls login to update cart')
        return redirect(url_for('userlogin'))
    try:
        updated_quantity=int(request.form['quantity'])
        if itemid in session[session.get('user')]:
            session[session.get('user')][itemid][1]=updated_quantity
            session.modified=True
            print(session)
            flash('item updated to cart')
            return redirect(url_for('viewcart'))
        else:
            flash('item not in  cart')
            return redirect(url_for('index'))
    except Exception as e:
        print(e)
        flash('Could not update cart item')
        return redirect(url_for('viewcart'))
@app.route('/removecart/<itemid>')
def removecart(itemid):
    if not session.get('user'):
        flash('pls login to update cart')
        return redirect(url_for('userlogin'))
    try:
        if itemid in session[session.get('user')]:
            session[session.get('user')].pop(itemid)
            session.modified=True
            print(session)
            flash('item removed from cart')
            return redirect(url_for('viewcart'))
        else:
            flash('item found in   cart')
            return redirect(url_for('index'))
    except Exception as e:
        print(e)
        flash('Could not remove cart item')
        return redirect(url_for('viewcart'))

@app.route("/category/<ctype>")
def category(ctype):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute("select bin_to_uuid(itemid), itemname, item_description, item_about, item_price, item_quantity, item_category, filename from items where item_category=%s",[ctype])
        items_data=cursor.fetchall()
        print(items_data)
        if not items_data:
            flash("there is no item available in this category")
            return redirect(url_for("index"))
    except Exception as e:
        app.logger.exception(f"Error fetching item {e}")
        flash("Could not fetch item") 
        return redirect(url_for("index"))
    else:
        return render_template("dashboard.html",items_data=items_data)

# pay route---
@app.route("/pay_cart",methods=["GET","POST"])
def pay_cart():
    if not session.get("user"):
        flash("Please Logion to Pay cart")
        return redirect(url_for("index"))
    try:
        # fetching all the cart items
        cart=session.get(session.get("user"),{})
        if not cart:
            flash("Your cart is empty")
            return redirect(url_for("index"))
        items_total=0
        items_data=[]
        for itemid,data in cart.items():
            name=data[0]
            price=float(data[2])
            quantity=int(data[1])
            category=data[4] if len(data)>3 else None
            img=data[5] if len(data)>4 else None
            subtotal=price * quantity
            items_total +=subtotal
            items_data.append({
                'id':itemid,
                'name':name,
                'price':price,
                'quantity':quantity,
                'category':category,
                'imgname':img,
                "subtotal":subtotal
            })
            delivery=40
            tax=round(items_total*0.05,2)
            grand_total=int(items_total+delivery+tax)
            razorpay_amount=grand_total*100 # coverting to paise

            # creating razorpay order
            order=client.order.create({
                "amount":razorpay_amount,
                "currency":"INR",
                "receipt": f"{session.get('user')}",
                "payment_capture":"1"

            })
            print("created an order: ",order)
            return render_template("pay.html",order=order,cart_items=items_data,items_total=items_total,delivery=delivery,tax=tax,grand_total=grand_total)
    except Exception as e:
        print('could not process payment: ',e)
        flash("payment failed")
        return redirect(url_for("viewcart"))

@app.route('/success_cart',methods=['POST'])
def success_cart():
    if not session.get('user'):
        flash('pls login')
        return redirect(url_for('userlogin'))
    try:
        payment_id=request.form['razorpay_payment_id']
        order_id=request.form['razorpay_order_id']
        signature=request.form['razorpay_signature']
        amount=float(request.form['grand_total'])
        #verify payment signature details
        param_dict={
            'razorpay_payment_id':payment_id,
            'razorpay_order_id':order_id,
            'razorpay_signature':signature
        }
        try:
            client.utility.verify_payment_signature(param_dict)
        except Exception as e:
            print(e)
            flash('Payment verification failed')
            return redirect(url_for('pay_cart'))
        cart=session.get(session.get('user'),{})
        if not cart:
            flash('Your cart is empty')
            return redirect(url_for('pay_cart'))
        items_total=sum(float(v[2]) * int(v[1]) for v in cart.values())
        delivery=40
        tax=round(items_total *0.05,2)
        grand_total=items_total+delivery+tax
        # print(grand_total,amount,111)
        if int(amount)==int(grand_total):
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select userid from userdata where user_email=%s',[session.get('user')])
                user=cursor.fetchone()[0]
                print(user,'user')
                cursor.execute('insert into orders(razorpay_orderid,razorpay_payment,userid,total_amount,delivery,tax,grand_total) values(%s,%s,%s,%s,%s,%s,%s)',[order_id,payment_id,user,items_total,delivery,tax,grand_total])
                order_table_id=cursor.lastrowid
                # print(order_table_id,'rowid')
                insert_item='''insert into order_items(order_items_id,order_id,itemid,item_name, item_price,item_quantity,subtotal,item_category,item_filename) values(uuid_to_bin(uuid()),%s,uuid_to_bin(%s),%s,%s,%s,%s,%s,%s)'''
                for i,j in cart.items():
                    itemid=i
                    item_name=j[0]
                    item_quantity=int(j[1])
                    item_price=float(j[2])
                    category=j[4] if len(i)>3 else None
                    print(category,'hi')
                    img=j[5] if len(i)>4 else None
                    sub_total=item_price*item_quantity
                    cursor.execute(insert_item,[order_table_id,itemid,item_name,item_price,item_quantity,sub_total,category,img])
                mydb.commit()
                cursor.close()
            except Exception as e:
                app.logger.exception(f'Error order storage:{e}')
                flash('Could not store order details')
                return redirect(url_for('pay_cart'))
            #------- remove temp cart items
            session[session.get('user')]={}
            flash('Payment successfull')
            return redirect(url_for('pay_cart'))
        else:
            # print('Amount Failed')
            flash('Amount Invalid')
            return redirect(url_for('pay_cart'))
    except Exception as e:
        app.logger.exception(f'Error  verification failed:{e}')
        flash('Could not order.payment verification failed')
        return redirect(url_for('pay_cart'))



app.run(debug=True,use_reloader=True)


