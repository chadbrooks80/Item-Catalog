import time
from models import Base, Categories, Items, Users
from flask import Flask, jsonify, request, url_for, abort, g, render_template, redirect, flash
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from authenticate import login_required
from flask import session as login_session
import random, string 

from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

GOOGLE_CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

engine = create_engine('sqlite:///itemCatalog.db')

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)
app.secret_key = "make this a random 32 character string later"









def validateGoogle(code):

	#upgrade the authorization code for access token
	try:
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)

	except FlowExchangeError:
		response = make_response(json.dumps('Failed to upgrade the authorization code'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response



	
	#attempts to make request and determines if there was an error
	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
	h = httplib2.Http()
	result = json.loads(h.request(url, 'GET')[1])
	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')), 500)



	#verify that the access token is used for intended user: 
	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
		response = make_response(json.dumps("Token ID doesn't match given user Id"), 401)
		response.headers['Content-Type'] = 'application/json'
		return response


	# Verify that the access token is valid for this app.
	if result['issued_to'] != GOOGLE_CLIENT_ID:
		response = make_response(json.dumps("Token client's ID doesn't match app's"), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	#get the user info
	userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
	params = { 'access_token': credentials.access_token, 'alt': 'json' }
	answer = requests.get(userinfo_url, params=params)

	data = answer.json()

	return data















@app.route('/gconnect', methods=['POST'])
def gconnect():
	
	#checks to ensure that the state is valid so it comes from original source
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Error: invalid State'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	
	code = request.data


	#upgrade the authorization code for access token
	try:
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)

	except FlowExchangeError:
		response = make_response(json.dumps('Failed to upgrade the authorization code'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response



	
	#attempts to make request and determines if there was an error
	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
	h = httplib2.Http()
	result = json.loads(h.request(url, 'GET')[1])
	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')), 500)



	#verify that the access token is used for intended user: 
	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
		response = make_response(json.dumps("Token ID doesn't match given user Id"), 401)
		response.headers['Content-Type'] = 'application/json'
		return response


	# Verify that the access token is valid for this app.
	if result['issued_to'] != GOOGLE_CLIENT_ID:
		response = make_response(json.dumps("Token client's ID doesn't match app's"), 401)
		response.headers['Content-Type'] = 'application/json'
		return response


	#NOTE THIS IS NOT NEEDED SINCE THIS IS ALREADY CHECKED WHEN USER ATTEMPT TO GO TO /login
	# Check if User is already logged into the system
	# if login_session.get('credentials') is not None and gplus_id == login_session.get('gplus_id'):
	# 	response = make_response(json.dumps('User is already logged connected'), 200)
	# 	response.headers['Content-Type'] = 'application/json'
	# 	return response


	# assign to login session if user is not logged in already
	# login_session['credentials'] = credentials.access_token
	# login_session['gplus_id'] = gplus_id

	#get the user info
	userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
	params = { 'access_token': credentials.access_token, 'alt': 'json' }
	answer = requests.get(userinfo_url, params=params)

	data = answer.json()

	#checks if person logging in has an account, if they don't have one it will ask if they would like to create one
	user = session.query(Users).filter_by(email=data['email']).first()
	
	if not user:

		login_session['g-name'] = data['name']
		login_session['g-picture'] = data['picture']
		login_session['g-email'] = data['email']

		noUser = '''
			<h2>User with email %s does not exist</h2>
			<div>Would you like to register this account now?
			<button id="yes">Yes</button>
			<button>No</button>

			<script>
				$("#yes").click(function(){
					$.ajax({

						type: 'post',
						url: '/addGoogleAccount',
						processData: false,
						contentType: 'application/octet-stream; charset=utf-8',
						data: '%s',
						success: function(result) {
							if(result) {
								$("#result").html(result);
								setTimeout(function() {
									window.location.href = "%s"
								}, 4000);
							} else if(authResult['error']) {
								console.log('there was an error ' + authResult['error']);
							}
						}
					});
				})
			</script>

		''' % (data['email'], login_session['state'], url_for('showCatalogs'))

		login_result = {
			'registered': False,
			'html': noUser
		}
		
		return jsonify(login_result)

	login_session['name'] = user.name
	login_session['id'] = user.id


	output = ''
	output += '<h1>Welcome, '
	output += login_session['name']
	output += '!</h1>'
	output += '<img src="'
	output += user.picture
	output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
	flash("Welcome %s!" % login_session['name'])
	print "done!"
	
	login_result = {
		'registered': True,
		'html': output
	}

	return jsonify(login_result)


@app.route('/addGoogleAccount', methods=['POST'])
def addGoogleAccount():

	print "Start of addgoogleAccount function"


	#validate State
	if request.args.get('state') != login_session['state']:
		return 'Bad State'

	print "State Validated"


	#checks if already logged in, if so it will raise error
	if id in login_session:
		return "Error, already logged in"


	print "Confirmed user is not logged in"


	#if g-name is in login_session, then it comes from someone registering from the /login page
	if 'g-name' in login_session:
		user = Users(name=login_session['g-name'], email=login_session['g-email'], picture=login_session['g-picture'])
		session.add(user)
		session.commit()

		login_session['id'] = user.id
		login_session['name'] = login_session['g-name']
	
		del login_session['g-name']
		del login_session['g-email']
		del login_session['g-picture']

		return "You have been succesfully Registered! Redirecting..."

	

	#this code will run if someone is trying to register from /register
	data = validateGoogle(request.data)

	#checks if user exits
	user = session.query(Users).filter_by(email=data['email']).first()

	if user:
		return "error: user already exists, please <a href='%s'>Login Instead</a>" % url_for('login')

	#if user does not exists, creates registers user and logs them in
	user = Users(email=data['email'], name=data['name'], picture=data['picture'])
	session.add(user)
	session.commit()

	login_session['id'] = user.id
	login_session['name'] = user.name

	return "user succesfully registered! Redirecting..."


@app.route('/logout')
def logout():
	
	if 'id' not in login_session:
		flash('Error:  you are not logged in')
		return redirect(url_for('showCatalogs'))	

	del login_session['id']
	del login_session['name']
	flash("You have been succesfully logged out")
	return redirect(url_for('showCatalogs'))



@app.route('/register', methods=['GET', 'POST'])
def register():

	if request.method=='POST':
		
		#Name, Email, and Password should not be black
		if not request.form['email'] or not request.form['password'] or not request.form['name']:
			flash('email and password cannot be blank')
			return redirect('register')

		#check if someone with that email is already registered
		if session.query(Users).filter_by(email=request.form['email']).first() is not None: 
			flash('user with that email already exists!')
			return redirect('register')

		#if everything else is good, it will create an account and store the unique ID into the session. 
		user = Users(name=request.form['name'], email=request.form['email'])
		user.hash_password(request.form['password'])
		session.add(user)
		session.commit()
		login_session['id'] = user.id
		login_session['name'] = user.name
		flash('Registration was Succesful!')
		return redirect('/')

	#if Get request, will render the registration form.
	#check if they are already logged in
	if 'id' in login_session:
		flash('error: you are already logged in as %s' % login_session['name'])
		return redirect('/')
	return render_template('register.html')

	#creates a secured State (if one doesn't exist):
	if 'state' not in login_session:
		login_session['state'] = ''.join( random.choice(string.ascii_uppercase + string.digits) for x in range(32) )


#used for a user to login or register
@app.route('/login', methods=['GET', 'POST'])
def login():

	#determines if user already exists
	if 'id' in login_session:
		flash('Error: You are already logged in!')
		return redirect(url_for('showCatalogs'))


	#creates a secured State (if one doesn't exist):
	if 'state' not in login_session:
		login_session['state'] = ''.join( random.choice(string.ascii_uppercase + string.digits) for x in range(32) )

	if request.method == 'POST':
		
		
		user = session.query(Users).filter_by(email=request.form.get('email')).first()
		

		if not user:
			flash('Error: Email does not exist')
			return redirect(url_for('login'))

		
		if not user.verify_password(request.form.get('password')):
			flash('Invalid Password')
			return redirect(url_for('login'))			

		login_session['id'] = user.id
		login_session['name'] = user.name
		flash('Welcome %s!' % user.name)
		return redirect(url_for('showCatalogs'))

	return render_template('login.html')

# @app.route('/register', methods=['GET', 'POST'])
# def registerAccount():
# 	user = Users(email=request.form['email'])



@app.route('/')
def showCatalogs():
	categories = session.query(Categories)
	
	if 'id' not in login_session:
		return render_template('public_home.html', categories=categories)	

	return render_template('home.html', categories=categories)


#creates new Category
@app.route('/catalog/new', methods=['POST', 'GET'])
@login_required
def createCategory():
	if request.method =='POST':
		category = Categories(category=request.form['category'])
		session.add(category)
		session.commit()
		flash('succesfully added category %s' % request.form['category'])
		return redirect(url_for('showItems', category=request.form['category']))

	return render_template('newCategory.html')


@app.route('/catalog/<category>/delete', methods=['GET', 'POST'])
@login_required
def deleteCategory(category):
	del_category = session.query(Categories).filter_by(category=category).first()

	if request.method == 'GET':
		return render_template('deleteCategory.html', category=category)

	session.delete(del_category)
	session.commit()
	flash('%s has been succesfully deleted' % category)
	return redirect(url_for('showCatalogs'))

@app.route('/catalog/<category>/edit', methods=['GET', 'POST'])
@login_required
def updateCategory(category):
	edit_category = session.query(Categories).filter_by(category=category).first()

	if request.method=='GET':
		return render_template('updateCategory.html', category=category)

	edit_category.category = request.form['category']
	session.commit()
	flash('Category has been succesfully changed to %s' % request.form['category'])
	return redirect(url_for('showItems', category=request.form['category']))

#this will show all of the items available. 
@app.route('/catalog/<category>/items')
def showItems(category):
	category = session.query(Categories).filter_by(category=category).first()
	items = session.query(Items).filter_by(category_id=category.id)
	
	return render_template('items.html', category=category.category, items=items, login_id =login_session.get('id'))


@app.route('/catalog/<category>/items/new', methods=['POST', 'GET'])
@login_required
def createItem(category):
	
	if request.method=='POST':
		find_category = session.query(Categories).filter_by(category=category).first()
		item = Items(category_id=find_category.id, item=request.form['item'], description=request.form['description'], user_id=login_session['id'])
		session.add(item)
		session.commit()
		flash('%s has been succesfully added' % request.form['item'])
		return redirect(url_for('itemDetail', category=category, item=request.form['item']))

	#GET request
	return render_template('newItem.html', category=category)


@app.route('/catalog/<category>/<item>')
def itemDetail(category, item):
	
	find_category = session.query(Categories).filter_by(category=category).first()
	find_item = session.query(Items).filter_by(category_id=find_category.id, item=item).first()

	return render_template('itemDetail.html', category=find_category, item=find_item, login_id=login_session.get('id'))
	# return "Category: %s, Item: %s" % (find_category.category, find_item.item)
	


@app.route('/catalog/<category>/<item>/delete', methods=['GET', 'POST'])
# @login_required
def deleteItem(category, item):
	find_category = session.query(Categories).filter_by(category=category).first()
	find_item = session.query(Items).filter_by(category_id=find_category.id, item=item).first()

	if login_session.get('id') != find_item.user_id:
			flash("error: you do not have permission to Delete item!")
			return redirect(url_for('itemDetail', category=category, item=item))

	if request.method == 'POST':
		
		session.delete(find_item)
		session.commit()
		flash('%s has been deleted' % find_item.item)
		return redirect(url_for('showItems', category=category))

	return render_template('deleteItem.html', item=item.item, category=find_category.category)


@app.route('/catalog/<category>/<item>/edit', methods=['GET', 'POST'])
@login_required
def updateItem(category, item):

	find_category = session.query(Categories).filter_by(category=category).first()
	find_item = session.query(Items).filter_by(category_id = find_category.id, item=item).first()

	#ensures any post request changes are made by the right user
	if login_session.get('id') != find_item.user_id:
			flash("error: you do not have permission to Edit item!")
			return redirect(url_for('itemDetail', category=category, item=item))
	
	if request.method == 'POST':
		find_item.item = request.form['item']
		find_item.description = request.form['description']
		session.commit()
		flash('item has been updated to %s' % request.form['item'])
		return redirect(url_for( 'itemDetail', category=category, item=request.form['item']))
            

	return render_template('updateItem.html', category=category, item=find_item)

@app.route('/catalog.json')
@login_required
def getItemsJson():
	categories = session.query(Categories).all()
	
	categories_json = { 'Category': [] }
	
	for category in categories:
		
		#this provides the current index of categories_json since the index starts at zero
		category_index = len(categories_json['Category'])
		
		categories_json['Category'].append(category.serialize)

		items = session.query(Items).filter_by(category_id=category.id).all()
		categories_json['Category'][category_index]['Item'] = [item.serialize for item in items]

		
	
	return jsonify(categories_json)



if __name__ == '__main__':
	app.debug = True
	app.run(host='0.0.0.0', port=5000)
