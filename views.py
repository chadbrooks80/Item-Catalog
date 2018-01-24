import time
from models import Base, Categories, Items, Users
from flask import Flask, jsonify, request, url_for, abort, g
from flask import render_template, redirect, flash
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from authenticate import login_required
from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

# get Google Client_id from client_secrets.json file
GOOGLE_CLIENT_ID = json.loads(open(
    'client_secrets.json', 'r').read())['web']['client_id']

# connect to sql database and initiate flask
engine = create_engine('sqlite:///itemCatalog.db')

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)
app.secret_key = "make this a random 32 character string later"


# used to validate the Google code from teh client_secrets file
def validateGoogle(code):
    # upgrade the authorization code for access token
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)

    except FlowExchangeError:
        response = make_response(json.dumps(
            'Failed to upgrade the authorization code'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # attempts to make request and determines if there was an error
    access_token = credentials.access_token
    url = (
        'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' %
        access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)

    # verify that the access token is used for intended user:
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token ID doesn't match given user Id"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != GOOGLE_CLIENT_ID:
        response = make_response(
            json.dumps("Token client's ID doesn't match app's"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # get the user info
    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    return data


# used for oauth connection to google
@app.route('/gconnect', methods=['POST'])
def gconnect():

    # checks to ensure that the state is valid so it comes from original source
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Error: invalid State'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    code = request.data

    # upgrade the authorization code for access token
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)

    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # attempts to make request and determines if there was an error
    access_token = credentials.access_token
    url = (
        'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' %
        access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)

    # verify that the access token is used for intended user:
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token ID doesn't match given user Id"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != GOOGLE_CLIENT_ID:
        response = make_response(
            json.dumps("Token client's ID doesn't match app's"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # get the user info
    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    # checks if person logging in has an account, if they don't have one it
    # will ask if they would like to create one
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
                                console.log(
                                    'there was an error '
                                        + authResult['error']);
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

    # initiates welcome screen
    output = ''
    output += '<h1>Welcome, '
    output += login_session['name']
    output += '!</h1>'
    output += '<img src="'
    output += user.picture
    output += ' " style = "width: 300px; height: 300px;border-radius: '
    output += '150px;-webkit-border-radius: '
    output += '150px;-moz-border-radius: 150px;"> '
    flash("Welcome %s!" % login_session['name'])
    print "done!"

    login_result = {
        'registered': True,
        'html': output
    }

    return jsonify(login_result)

# used to add the Google Account


@app.route('/addGoogleAccount', methods=['POST'])
def addGoogleAccount():

    # validate State
    if request.args.get('state') != login_session['state']:
        return 'Bad State'

    print "State Validated"

    # checks if already logged in, if so it will raise error
    if id in login_session:
        return "Error, already logged in"

    print "Confirmed user is not logged in"

    # if g-name is in login_session, then it comes from someone registering
    # from the /login page
    if 'g-name' in login_session:
        user = Users(
            name=login_session['g-name'],
            email=login_session['g-email'],
            picture=login_session['g-picture'])
        session.add(user)
        session.commit()

        login_session['id'] = user.id
        login_session['name'] = login_session['g-name']

        del login_session['g-name']
        del login_session['g-email']
        del login_session['g-picture']

        return "You have been succesfully Registered! Redirecting..."

    # this code will run if someone is trying to register from /register
    data = validateGoogle(request.data)

    # checks if user exits
    user = session.query(Users).filter_by(email=data['email']).first()

    if user:
        return "error: user already exists, <a href='%s'>Login Instead</a>" % url_for(
            'login')

    # if user does not exists, creates registers user and logs them in
    user = Users(
        email=data['email'],
        name=data['name'],
        picture=data['picture'])
    session.add(user)
    session.commit()

    login_session['id'] = user.id
    login_session['name'] = user.name

    return "user succesfully registered! Redirecting..."


# this returns a json file, which is used in the side-bar of the website
# (<aside> tag)
@app.route('/top-ten', methods=['GET', 'POST'])
def top_ten():

    # first get the latest ten created items
    ten_items = session.query(Items).order_by(
        Items.created.desc()).limit(10).all()

    # creates an array with each of the top ten items as objects
    items_json = [item.serialize for item in ten_items]

    # this grabs the category name for the top 10 items (since it only has the
    # category ID and not name)
    for i, item in enumerate(items_json):
        category = session.query(Categories).filter_by(
            id=item['cat_id']).first().category
        items_json[i]['url'] = url_for(
            'itemDetail', category=category, item=item['title'])
        print(item['title'])

    return jsonify(items_json)


# if someone routes to this url, it will log them out and will give error
# if they are not logged in (by checking the state)
@app.route('/logout')
def logout():

    if 'id' not in login_session:
        flash('Error:  you are not logged in')
        return redirect(url_for('showCatalogs'))

    del login_session['id']
    del login_session['name']
    flash("You have been succesfully logged out")
    return redirect(url_for('showCatalogs'))


# used to register a new user account (post to send the information)
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        # Name, Email, and Password should not be blank
        if not request.form['email'] or not request.form['password'] or not request.form['name']:
            flash('email and password cannot be blank')
            return redirect('register')

        # check if someone with that email is already registered
        if session.query(Users).filter_by(
                email=request.form['email']).first() is not None:
            flash('user with that email already exists!')
            return redirect('register')

        # if everything else is good, it will create an account and store the
        # unique ID into the session.
        user = Users(name=request.form['name'], email=request.form['email'])
        user.hash_password(request.form['password'])
        session.add(user)
        session.commit()
        login_session['id'] = user.id
        login_session['name'] = user.name
        flash('Registration was Succesful!')
        # redirects to the home page
        return redirect(url_for('showCatalogs'))

    # if Get request, will render the registration form.

    # check if they are already logged in
    if 'id' in login_session:
        flash('error: you are already logged in as %s' % login_session['name'])
        return redirect(url_for('showCatalogs'))
    return render_template('register.html')

    # creates a secured State (if one doesn't exist):
    if 'state' not in login_session:
        login_session['state'] = ''.join(
            random.choice(
                string.ascii_uppercase +
                string.digits) for x in range(32))


# used for a user to login
@app.route('/login', methods=['GET', 'POST'])
def login():

    # determines if user already exists
    if 'id' in login_session:
        flash('Error: You are already logged in!')
        return redirect(url_for('showCatalogs'))

    # creates a secured State (if one doesn't exist):
    if 'state' not in login_session:
        login_session['state'] = ''.join(
            random.choice(
                string.ascii_uppercase +
                string.digits) for x in range(32))

    # post request used for logging them in
    if request.method == 'POST':

        # first looks for user email to see if exists
        user = session.query(Users).filter_by(
            email=request.form.get('email')).first()
        if not user:
            flash('Error: Email does not exist')
            return redirect(url_for('login'))

        # verifies password
        if not user.verify_password(request.form.get('password')):
            flash('Invalid Password')
            return redirect(url_for('login'))

        login_session['id'] = user.id
        login_session['name'] = user.name
        flash('Welcome %s!' % user.name)
        return redirect(url_for('showCatalogs'))

    return render_template('login.html')

# for the homepage


@app.route('/')
def showCatalogs():
    categories = session.query(Categories)

    # renders the public_homepage if they are not logged in (indicating that
    # they can't create categories)
    if 'id' not in login_session:
        return render_template('public_home.html', categories=categories)

    # if they are logged in, allows them to use home page (allowing them to
    # create categories)
    return render_template('home.html', categories=categories)


# creates new Category (@login_requires means they must be logged in to do
# this)
@app.route('/catalog/new', methods=['POST', 'GET'])
@login_required
def createCategory():
    if request.method == 'POST':
        category = Categories(
            category=request.form['category'],
            user_id=login_session['id'])
        session.add(category)
        session.commit()
        flash('succesfully added category %s' % request.form['category'])
        return redirect(
            url_for(
                'showItems',
                category=request.form['category']))

    # if get request
    return render_template('newCategory.html')


# allows to delete a category (with confirmation)
@app.route('/catalog/<path:category>/delete', methods=['GET', 'POST'])
@login_required
def deleteCategory(category):
    # finds category from url
    del_category = session.query(Categories).filter_by(
        category=category).first()

    # finds out if user is able to delete and if not redirects to the category
    # page
    if login_session.get('id') != del_category.user_id:
        flash("error, You are not allowed to Delete this Category!")
        return redirect(url_for('showItems', category=category))

    if request.method == 'GET':
        return render_template('deleteCategory.html', category=category)

    session.delete(del_category)
    session.commit()
    flash('%s has been succesfully deleted' % category)
    return redirect(url_for('showCatalogs'))

# allows to edit category


@app.route('/catalog/<path:category>/edit', methods=['GET', 'POST'])
@login_required
def updateCategory(category):
    edit_category = session.query(
        Categories).filter_by(category=category).first()

    # finds out if user is able to delete and if not redirects to the category
    # page
    if login_session.get('id') != edit_category.user_id:
        flash("error, You are not allowed to Edit this Category!")
        return redirect(url_for('showItems', category=category))

    if request.method == 'GET':
        return render_template('updateCategory.html', category=category)

    edit_category.category = request.form['category']
    session.commit()
    flash(
        'Category has been succesfully changed to %s' %
        request.form['category'])
    return redirect(url_for('showItems', category=request.form['category']))

# this will show all of the items available in category.


@app.route('/catalog/<path:category>/items')
def showItems(category):
    category = session.query(Categories).filter_by(category=category).first()
    items = session.query(Items).filter_by(category_id=category.id)

    return render_template(
        'items.html',
        category=category.category,
        items=items,
        login_id=login_session.get('id'))

# allows to create new item if logged in


@app.route('/catalog/<path:category>/items/new', methods=['POST', 'GET'])
@login_required
def createItem(category):

    if request.method == 'POST':
        find_category = session.query(
            Categories).filter_by(category=category).first()
        item = Items(
            category_id=find_category.id,
            item=request.form['item'],
            description=request.form['description'],
            user_id=login_session['id'])
        session.add(item)
        session.commit()
        flash('%s has been succesfully added' % request.form['item'])
        return redirect(
            url_for(
                'itemDetail',
                category=category,
                item=request.form['item']))

    # GET request
    return render_template('newItem.html', category=category)

# shows details of the item and description


@app.route('/catalog/<path:category>/<path:item>')
def itemDetail(category, item):

    find_category = session.query(
        Categories).filter_by(category=category).first()
    find_item = session.query(Items).filter_by(
        category_id=find_category.id, item=item).first()

    return render_template(
        'itemDetail.html',
        category=find_category,
        item=find_item,
        login_id=login_session.get('id'))


# allows to delete item with login required authentication
@app.route(
    '/catalog/<path:category>/<path:item>/delete',
    methods=[
        'GET',
        'POST'])
@login_required
def deleteItem(category, item):

    # finds the item and details of the category
    find_category = session.query(
        Categories).filter_by(category=category).first()
    find_item = session.query(Items).filter_by(
        category_id=find_category.id, item=item).first()

    # determines if someone is allowed to delete (works for both get and post
    # since it does this first)
    if login_session.get('id') != find_item.user_id:
        flash("error: you do not have permission to Delete item!")
        return redirect(url_for('itemDetail', category=category, item=item))

    if request.method == 'POST':

        session.delete(find_item)
        session.commit()
        flash('%s has been deleted' % find_item.item)
        return redirect(url_for('showItems', category=category))

    # get request
    return render_template(
        'deleteItem.html',
        item=find_item.item,
        category=find_category.category)

# for editing a item


@app.route(
    '/catalog/<path:category>/<path:item>/edit',
    methods=[
        'GET',
        'POST'])
@login_required
def updateItem(category, item):

    find_category = session.query(
        Categories).filter_by(category=category).first()
    find_item = session.query(Items).filter_by(
        category_id=find_category.id, item=item).first()

    # ensures any request changes are made by the right user for both get and
    # post requests
    if login_session.get('id') != find_item.user_id:
        flash("error: you do not have permission to Edit item!")
        return redirect(url_for('itemDetail', category=category, item=item))

    if request.method == 'POST':
        find_item.item = request.form['item']
        find_item.description = request.form['description']
        session.commit()
        flash('item has been updated to %s' % request.form['item'])
        return redirect(
            url_for(
                'itemDetail',
                category=category,
                item=request.form['item']))

    # get request
    return render_template(
        'updateItem.html',
        category=category,
        item=find_item)

# this allows anyone that has an account to receive a full json file of
# the entire categories and items listed in the database


@app.route('/catalog.json')
@login_required
def getItemsJson():
    categories = session.query(Categories).all()

    # sets up the template to place categories into an arrary
    categories_json = {'Category': []}

    # goes through each category and grabs all the items
    for category in categories:

        # this provides the current index of categories_json since the index
        # starts at zero
        category_index = len(categories_json['Category'])

        # serializes each category
        categories_json['Category'].append(category.serialize)

        # searches for all items in categories and serizes them within the
        # category
        items = session.query(Items).filter_by(category_id=category.id).all()
        categories_json['Category'][category_index]['Item'] = [
            item.serialize for item in items]

    # returns json file to requester
    return jsonify(categories_json)


# Used to start the app.
if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
