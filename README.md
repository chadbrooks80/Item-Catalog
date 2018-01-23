# Item Catalog Web App

The item catalog provides a list of items within a variety of categories that can also be created.  This app uses a registration and authentication system, allowing the user to either register within the app themselves, or using Google Oauth 2.0 authentication. 

## Files used within the the Item Catalog App

This App has three main python files, including: 
* views.py
this is the main file that is used for running the app with the rest of the python files being utlized as libraries. To run the Item Catalog App, you need to have Python 2 installed and run the following command from the terminal: 

`python views.py`

* models.py
This file is used to configure the the database using SqlAlchemy`. The Item Catalog App uses sqllite as its database and has three main tables:

    1. Users - holds the user information with hashed passwords for security
    2. Categories - holds the category information
    3. Items - holds the items created for each category

* authenticate.py
this file holds one main function imported into the views.py: `login_required`.  This file is used as a decorator to any specific routes within this application to ensure users are logged in to perform specific tasks, including adding, editing, and deleting any categories or items. 

In addition to the python files used the ``client_secrets.json`` file is used for authenticating to Google's oauth 2.0 server, and the ``itemCatalog.db`` file is the Sqllite database, which is automatically created by sqlAlchemy if it does not exist. 

There are a large number of html template files utilized within the templates folder, along with any other static files needed, which includes style.css and a couple of image files used. 

## JSON Endpoints

The Item Catalog app also includes a json endpoint that allows users to retreive all categories and items stored in JSON format.  Anyone accessing this file must be registered and logged in. to access this JSON endpoint, use the following path: 

`/catalog.json`

## Suported Python Versions

Log Analysis Application has been tested and working on Python versions 2.

## Licensing
`Log Analysis Application` is a public domain work, dedicated using [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). Feel free to do whatever you want with it.