from flask import Flask,url_for,redirect,render_template,request,flash,session
from flask_session import Session
from otp import genotp
from cmail import sendmail
from stoken import endata, dndata
from flask_bcrypt import Bcrypt
from mysql.connector import (connection)
import os
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
    return render_template("index.html")

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

@app.route("/userlogin",methods=["GET","POST"])
def userlogin():
    if request.method=="POST":
        login_email=request.form["email"]
        login_password= request.form["password"]
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("select count(*) from userdata where user_email=%s",[login_email])
            email_count=cursor.fetchone() # (1,) (0,)
            cursor.close()
        except Exception as e:
            print(e)
            flash("Could not connect db")
            return redirect (url_for("userlogin"))
        else:
            if email_count:
                if email_count[0]==1:
                    try:
                        cursor=mydb.cursor(buffered=True)
                        cursor.execute("select password from userdata where user_email=%s",[login_email])
                        stored_password=cursor.fetchone() # ("sdfghjkjhgf")
                        if stored_password:
                            if bcrypt.check_password_hash(stored_password[0],login_password):
                                session["user"]=login_email
                                return redirect(url_for("index")) # need to write
                            else:
                                flash("Wrong Password")
                                return redirect(url_for("userlogin"))
                        else:
                            flash("could not verify password")
                            return redirect(url_for("userlogin"))
                    except Exception as e:
                        print(e)
                        flash("could not verify password")
                        return redirect(url_for("userlogin"))
                elif email_count[0]==0:
                    flash("Email not found")
                    return redirect(url_for("userlogin"))
            else:
                flash("Email Not Found")
                return redirect(url_for("userlogin"))
    return render_template("userlogin.html")

@app.route("/userdashboard")
def userdashboard():
    if session.get("user"):
        return "Login Dashboard"
    else:
        flash("Please Login to Access")
        return redirect(url_for("userlogin"))
 

app.run(debug=True,use_reloader=True)


