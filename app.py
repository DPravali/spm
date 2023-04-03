from flask import Flask,request,render_template,redirect,url_for,flash,session,send_file
from flask_mysqldb import MySQL
from flask_session import Session
from otp import genotp
from cemail import sendmail
import random
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from tokenreset import token
from io import BytesIO

app=Flask (__name__)
app.secret_key ='345678xfgh'

app.config['SESSION_TYPE']='filesystem'
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']='admin'
app.config['MYSQL_DB']='spm'

Session(app)
mysql=MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registration',methods=['GET','POST'])
def register():
    if request.method == 'POST':
        rollno = request.form['rollno']
        name = request.form['name']
        group = request.form['group']
        password = request.form['password']
        code = request.form['code']
        email= request.form['email']
        #define college code
        ccode='pbc#123'
        if ccode == code:
            cursor = mysql.connection.cursor()
            
            cursor.execute('select rollno from students')
            data = cursor.fetchall()
            
            cursor.execute('select email from students')
            edata = cursor.fetchall()
            #print(data)
            
            if (rollno,) in data:
                flash ('User already registered with this rollno')
                return render_template('register.html')
            
            if (email,) in edata:
                flash ('User already registered with this email')
                return render_template('register.html')
            
            print(data)
            cursor.close()
            otp = genotp()
            subject = 'Thanks for registering to the application'
            body= f'use this otp to register {otp}'
            sendmail(email,subject,body)
            return render_template('otp.html',otp=otp,rollno=rollno,name=name,group=group,password=password,email=email)
        else:
            flash('check your code that you entered')
            return render_template('register.html')
    return render_template('register.html')

@app.route('/login', methods = ['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        rollno = request.form['id']
        password = request.form['password']
        #connecting to sql
        cursor = mysql.connection.cursor()
        cursor.execute('select count(*) from students where rollno = %s and password = %s', [rollno, password])
        count = cursor.fetchone() [0]
        if count == 0:
            flash('invalid credentials')
            return render_template('login.html')
        else:
            session['user'] = rollno
            return redirect(url_for("home"))
    return render_template('login.html')
    
@app.route('/Studentshome')
def home():
    if session.get('user'):
        return render_template('home.html')
    else:
        flash('Log in to access notes')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('index'))
    else:
        flash('Logged out ')
        return redirect(url_for('login'))

@app.route('/otp/<otp>/<rollno>/<name>/<group>/<password>/<email>',methods=['GET','POST'])
def otp(otp,rollno,name ,group,password,email):
    if request.method == 'POST':
        uotp = request.form['otp']
        if otp == uotp:
            cursor = mysql.connection.cursor()
            lst=[rollno, name, group, password, email]
            query='insert into students values (%s,%s,%s,%s,%s)'
            cursor.execute(query,lst)
            cursor.connection.commit()
            cursor.close()
            flash('Details registered!')
            return redirect(url_for('login'))
        else:
            flash('Wrong OTP')
            return render_template('otp.html',otp=otp,rollno=rollno,name=name,group=group,password=password,email=email)

@app.route('/noteshome')
def noteshome():
    if session.get('user'):
        rollno = session.get('user')
        cursor = mysql.connection.cursor()
        cursor.execute('select *from notes where rollno = %s', [rollno])
        notes_data = cursor.fetchall()
        print(notes_data)
        cursor.close()
        return render_template('addnotetable.html', data = notes_data)
    else:
        return redirect( url_for('login'))

@app.route('/addnotes',methods =['GET','POST'])
def addnote():
    if session.get('user'):
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            cursor = mysql.connection.cursor()
            rollno = session.get('user')
            cursor.execute('insert into notes(rollno,title,content) values(%s,%s,%s)',[rollno,title,content])
            mysql.connection.commit()
            flash(f'{title} added successfully ')
            return redirect(url_for('noteshome'))
        return render_template('notes.html')
    else:
        return redirect(url_for('login'))

@app.route('/viewbotes/<nide>')
def viewnotes(nide):
    cursor = mysql.connection.cursor()
    cursor.execute('select title,content from notes where nide = %s ',[nide])
    data = cursor.fetchone()
    return render_template('notesview.html',data = data)

@app.route('/updatenotes/<nide>', methods=['GET','POST'])
def updatenotes(nide):
    if session.get('user'):
        cursor = mysql.connection.cursor()
        cursor.execute('select  title,content from notes where nide = %s',[nide])
        data = cursor.fetchone()
        cursor.close()

        
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            cursor = mysql.connection.cursor()
            cursor.execute('update notes set title = %s, content = %s where nide = %s',[title,content,nide])
            mysql.connection.commit()
            cursor.close()
            flash('Notes updates successfully')
            return redirect(url_for('noteshome'))
        
        return render_template('updatenotes.html',data = data)
    else:
        return redirect (url_for('login'))

@app.route('/deletenotes/<nide>')
def deletenotes(nide):
    cursor = mysql.connection.cursor()
    #cursor.execute('select  title from notes',[title])
    cursor.execute('delete from notes where nide = %s',[nide])
    mysql.connection.commit()
    cursor.close()
    flash('Notes is deleted')
    return redirect(url_for('noteshome'))

@app.route('/filehome')
def fileshome():
    if session.get('user'):
        rollno = session.get('user')
        cursor = mysql.connection.cursor()
        cursor.execute('select fid, filename, date from files where rollno  = %s',[rollno])
        data = cursor. fetchall()
        cursor.close()
        return render_template('fileuploadtable.html', data = data)
    else:
        return redirect(url_for('login'))

@app.route('/filehandling',methods=['POST'])
def filehandling():
    file = request.files['file']
    filename = file.filename
    bin_file = file.read()
    rollno = session.get('user')
    cursor = mysql.connection.cursor()
    cursor.execute('insert into files(rollno, filename, filedata) values(%s,%s,%s)',[rollno, filename, bin_file])
    mysql.connection.commit()
    cursor.close()
    flash(f'{filename} uploaded successfully')
    return redirect (url_for('fileshome'))

@app.route('/filedelete/<fid>')
def filedelete(fid):
    cursor=mysql.connection.cursor()
    cursor.execute('delete from files where fid=%s',[fid])
    mysql.connection.commit()
    cursor.close()
    flash('File deleted successfully')
    return redirect(url_for('fileshome'))


    
@app.route('/viewfile/<fid>')
def viewfile(fid):
    if session.get('user'):
        cursor = mysql.connection.cursor()
        cursor.execute('select filename, filedata from files where fid= %s', [fid])
        data =  cursor.fetchone()
        cursor.close()
        filename = data[0]
        bin_file = data[1]
        byte_data = BytesIO(bin_file)
        return send_file(byte_data,download_name = filename)
    else:
        return redirect(url_for('login'))

'''

@app.route('/downloadfile/<fid>')
def downloadfile(fid):
    if session.get('user'):
        cursor = mysql.connection.cursor()
        cursor.execute('select filename, filedata from files where fid= %s', [fid])
        data =  cursor.fetchone()
        cursor.close()
        filename = data[0]
        bin_file = data[1]
        byte_data = BytesIO(bin_file)
        return send_file(byte_data,download_name = filename,as_atachement = True)
    else:
        return redirect(url_for('login'))
'''

@app.route('/forgetpassword',methods=['GET','POST'])
def forget():
    if request.method=='POST':
        rollno=request.form['id']
        cursor=mysql.connection.cursor()
        cursor.execute('select rollno from students')
        data=cursor.fetchall()
        if (rollno,) in data:
            cursor.execute('select email from students where rollno=%s',[rollno])
            data=cursor.fetchone()[0]
            cursor.close()
            subject = f'Reset Password for {data}'
            body = f'Reset the password using-{ request.host+url_for("createpassword", token = token(rollno,120))}'
            sendmail(data,subject,body)
            flash('Reser link sent to your mail')
            return redirect ( url_for('login'))
        else:
            return 'Invalid user id'
    return render_template('forgot.html')


@app.route('/createpassword/<token>',methods=['GET','POST'])
def createpassword(token):
    try:
        s=Serializer(app.config['SECRET_KEY'])
        rollno=s.loads(token)['user']
        if request.method=='POST':
            npass=request.form['npassword']
            cpass=request.form['cpassword']
            if npass==cpass:
                cursor=mysql.connection.cursor()
                cursor.execute('update students set password=%s where rollno=%s',[npass,rollno])
                mysql.connection.commit()
                return 'Password reset Successfull'
            else:
                return 'Password mismatch'
        return render_template('newpassword.html')
    except Exception as e:
        
        return 'Link expired try again'





app.run(use_reloader =True,debug=True)



