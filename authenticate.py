from flask import session as login_session
from flask import flash, redirect, url_for


def login_required(myRoute):	
	
	funcName = myRoute.__name__
	myRoute.__name__ = 'myRoute'

	def validate(**kargs):
		print 'here are your args:'
		if not login_session.get('id'):
			flash("error: you must be logged in to perform this task")
			return redirect(url_for('login'))

		return myRoute(**kargs)

	
	validate.__name__ = funcName
	return validate