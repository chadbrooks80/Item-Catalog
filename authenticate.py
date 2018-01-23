from flask import session as login_session
from flask import flash, redirect, url_for

# this function is used to authenticate any
# users to ensure they are allowed access.
# ised as a decorator.


def login_required(myRoute):

    funcName = myRoute.__name__
    myRoute.__name__ = 'myRoute'

    def validate(**kargs):
        if not login_session.get('id'):
            flash("error: you must be logged in to perform this task")
            return redirect(url_for('login'))

        return myRoute(**kargs)

    # need to change __name__ for it to work as a decorator
    validate.__name__ = funcName
    return validate
