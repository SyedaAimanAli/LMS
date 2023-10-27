from flask import Flask, render_template, request, session, redirect, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import json
import mysql.connector
from mysql.connector import Error
from functools import wraps
from datetime import datetime

def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if 'user' in session:
            return route_function(*args, **kwargs)
        elif 'user' not in session:
            return redirect('/login')  
    return wrapper

with open('config.json', 'r') as c:
    parameters = json.load(c)["parameters"]
    
try:
    connection = mysql.connector.connect(
        host='localhost',
        database='lms',
        user='root',
        password=''
    )
except Error as e:
    print("Error connecting to MySQL database:", e)    


app = Flask(__name__)

local_server = False    
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.secret_key = 'code-is-life' 
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'lms'
local_server = True 
if(local_server):
    app.config['SQLALCHEMY_DATABASE_URI'] = parameters['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = parameters['prod_uri']
    
   

db = SQLAlchemy(app)

class Books(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), unique=False, nullable=False)
    writer = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(12),nullable=False)
    quantity = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
class Issued(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    book = db.Column(db.String(80), unique=False, nullable=False)
    date = db.Column(db.String(12),nullable=False)  

class Register(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=False, nullable=False)
    full_name = db.Column(db.String(80), unique=False, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
class Customer(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(20), nullable=False)
    

@app.route('/api/books_data')
def books_data():
    books = Books.query.all()
    category_counts = {}

    for book in books:
        category = book.category
        if category in category_counts:
            category_counts[category] += 1
        else:
            category_counts[category] = 1

    books_data = [{'category': category, 'count': count} for category, count in category_counts.items()]
    
    return jsonify(books_data)


@app.route("/")
@login_required
def index():
    total_entries = Books.query.count()
    total_entries_user = Customer.query.count()
    total_entries_issued = Issued.query.count()
    if 'user' in session:
        username = session['user']
    return render_template('index.html',username=username, total_entries=total_entries, total_entries_user=total_entries_user, total_entries_issued=total_entries_issued)

@app.route("/books")
@login_required
def books():
    books = Books.query.all()
    issued_books = set(issue.book for issue in Issued.query.all())
    for book in books:
        book.issued = book.title in issued_books
    if 'user' in session:
        username = session['user']
    return render_template('books.html', books=books, username=username)


@app.route("/issue_books", methods=['POST','GET'])
@login_required  
def issue_books():
    customers = Customer.query.all()
    books = Books.query.with_entities(Books.id, Books.title, Books.quantity).all() 
    if request.method == 'POST':
        name = request.form.get('name')
        book_title = request.form.get('book') 
        date = datetime.now()
        issue = Issued(name=name, book=book_title, date=date)
        book = Books.query.filter_by(title=book_title).first()
        if book and book.is_active == True and book.quantity > 0:
            issue = Issued(name=name, book=book_title, date=date)
            db.session.add(issue)
            db.session.commit()
            book.quantity -= 1
            db.session.commit()
        else:
            flash('book not available', 'error')
    if 'user' in session:
        username = session['user']
    return render_template('issue_books.html', books=books, customers=customers, username=username)

@app.route('/bookcustomer', methods = ['POST', 'GET'])
def bookcustomer():
    if request.method == 'POST':
        name = request.form.get('fullname')
        contact = request.form.get('contact')
        email = request.form.get('email')
        customer = Customer(name=name, contact=contact, email=email)
        db.session.add(customer)
        db.session.commit()
        return redirect('/issue_books')
        

@app.route("/users")
@login_required
def profile():
    users = Register.query.all()
    if 'user' in session:
        username = session['user']
    return render_template('users.html', users=users, username=username)


@app.route("/issued")
@login_required
def issued():
    books = Issued.query.all()
    if 'user' in session:
        username = session['user']
    return render_template('issued.html', books=books, username=username)

  
@app.route("/trash/<string:sno>" , methods=['GET', 'POST'])
def trash(sno):
        customerr = Customer.query.filter_by(sno=sno).first()
        if customerr:
            db.session.delete(customerr)
            db.session.commit()
        return redirect('/users')    
@app.route("/remove/<string:id>" , methods=['GET', 'POST'])
def remove(id):
        book = Books.query.filter_by(id=id).first()
        if book:
            db.session.delete(book)
            db.session.commit()
        return redirect('/books')
@app.route("/return/<string:id>" , methods=['GET', 'POST'])
def returnn(id):
    issued_book = Issued.query.get(id)
    if issued_book:
        book_title = issued_book.book
        db.session.delete(issued_book)
        db.session.commit()
        book = Books.query.filter_by(title=book_title).first()
        if book:
            book.quantity += 1
            db.session.commit()
        return redirect('/issued')


@app.route("/register", methods = ['POST', 'GET'])
@login_required
def register():
    if request.method == "POST":
        username = request.form.get('username')
        fullname = request.form.get('fullname')
        password = request.form.get('password')
        contact = request.form.get('contact')
        email = request.form.get('email')
        is_active = request.form.get('is_active') == '1'
        user = Register(username=username, password=password, full_name=fullname, contact=contact, email=email, is_active=is_active)
        db.session.add(user)
        db.session.commit()
    return redirect('/users')

@app.route("/customer", methods = ['POST', 'GET'])
def addcustomer():
    if request.method == "POST":
        fullname = request.form.get('fullname')
        contact = request.form.get('contact')
        email = request.form.get('email')
        customerr = Customer(name=fullname, contact=contact, email=email)
        db.session.add(customerr)
        db.session.commit()
    return redirect('/customers_list')


@app.route("/customers_list", methods = ['POST', 'GET'])
@login_required
def customer():
    customers = Customer.query.all()
    if 'user' in session:
        username = session['user']
    return render_template('customers.html', customers=customers, username=username)

@app.route("/rename/<string:sno>", methods = ['POST', 'GET'])
def remane(sno):
    if request.method == 'POST':
        fullname = request.form.get('name')
        contact = request.form.get('contact')
        email = request.form.get('email')
        user = Customer.query.filter_by(sno=sno).first()
        print(user)
        user.sno = sno
        user.name = fullname
        user.contact = contact
        user.email = email
        db.session.commit()
    user = Customer.query.filter_by(sno=sno).first()    
    return redirect('/customers_list')

@app.route("/add_book", methods = ['POST', 'GET'])
@login_required
def addbook():
    if request.method == "POST":
        title = request.form.get('title')
        author = request.form.get('author')
        category = request.form.get('category')
        quantity = request.form.get('quantity')
        is_active = request.form.get('is_active') == '1'
        books = Books(title=title, writer=author, category=category, quantity=quantity, is_active=is_active)
        db.session.add(books)
        db.session.commit()
    return redirect('/books')


@app.route("/addbook/<string:id>", methods = ['POST', 'GET'])
def add(id):
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        category = request.form.get('category')
        quantity = request.form.get('quantity')
        is_active = request.form.get('is_active') == '1'
        books = Books.query.filter_by(id=id).first()
        books.sno = id
        books.title = title
        books.writer = author
        books.category = category
        books.quantity = quantity
        books.is_active = is_active
        db.session.commit()
    return redirect('/books')


@app.route("/edit/<string:sno>", methods = ['POST', 'GET'])
def edit(sno):
    username = session['user']
    if username == session.get('user'):
        flash('You are not allowed to edit your own profile.', 'error')
    if request.method == 'POST':
        username = request.form.get('username')
        fullname = request.form.get('fullname')
        password = request.form.get('password')
        contact = request.form.get('contact')
        email = request.form.get('email')
        is_active = request.form.get('is_active') == '1'
        user = Register.query.filter_by(sno=sno).first()
        print(user)
        user.sno = sno
        user.username = username
        user.password = password
        user.full_name = fullname
        user.contact = contact
        user.email = email
        user.is_active = is_active
        db.session.commit()
    user = Register.query.filter_by(sno=sno).first()    
    return redirect('/users')


@app.route("/logout")
def logout():
    session.clear()
    return redirect('/login')


@app.after_request
def add_cache_control(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response  


@app.route("/login", methods=['POST', 'GET'])
def login():
    user_json = None  

    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('pass')

        user = Register.query.filter_by(username=username, password=password, is_active=True).first()

        if user:
            user_data = {
                'username': user.username,
                'user_id': user.sno,
                'password' : user.password
            }

            user_json = json.dumps(user_data)

            session['user'] = user.username
            session['pass'] = user.password
            session['user_id'] = user.sno
            return redirect('/')
    return render_template('login.html', user_json=user_json)
app.run(debug=True)