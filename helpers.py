import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def percent(value):
    """Format value as percentage."""
    return f"{value:,.2%}"


## Thank you to https://stackoverflow.com/questions/783897/truncating-floats-in-python
def truncate(f, n):
    '''Truncates/pads a float f to n decimal places without rounding'''
    s = '{}'.format(f)
    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(f, n)
    i, p, d = s.partition('.')
    return '.'.join([i, (d+'0'*n)[:n]])


def prep(n):

    for x in n:
        x['ab'] = int(x['ab'])
        x['h'] = int(x['h'])
        x['twob'] = int(x['twob'])
        x['threeb'] = int(x['threeb'])
        x['hr'] = int(x['hr'])
        x['hbp'] = int(x['hbp'])
        x['bb'] = int(x['bb'])
        oneb = x['h'] - (x['twob'] + x['threeb'] + x['hr'])
        x['oneb'] = oneb
        x['tb'] = int(x['oneb'] + (x['twob'] * 2) + (x['threeb'] * 3) + (x['hr'] * 4))
        x['er'] = int(x['er'])
        if x['ab'] > 0:
            avg = "{:.3f}".format(x['h']/x['ab'])
            x['avg'] = avg
            slg = "{:.3f}".format(x['tb']/x['ab'])
            x['slg'] = slg
        else:
            x['avg'] = 'N/A'
            x['slg'] = 'N/A'
        if x['ab'] + x['hbp'] + x['bb'] > 0:
            obp = (x['h'] + x['hbp'] + x['bb']) / (x['ab'] + x['hbp'] + x['bb'])
            x['obp'] = "{:.3f}".format(obp)
        else:
            x['obp'] = 'N/A'
        if x['ip'] != 'N/A':
            x['ip'] = round(float(x['ip']), 2)
        if x['ip'] != 'N/A' and x['ip'] > 0:
            x['era'] = ((9*x['er'])/(x['ip']))
        else:
            x['era'] = 100000000
        x['ip'] = "{:.2f}".format(float(x['ip']))

    return n
