"""
explore.py

A Flask Blueprint module for the explore data page.
"""
from flask import Blueprint, render_template, current_app, request, Response
import json
from .. import common as c
import authorise as auth

explore = Blueprint('explore', __name__, url_prefix="/<language>")

@explore.before_request
def requires_auth():
    """Checks that the user has authenticated before returning any page from this Blueprint."""
    auth.check_auth( ['registered'] )


@explore.route('/')
@explore.route('/loc_<int:locID>')
def index(locID=1):
    return render_template('explore/index.html', 
                           content=current_app.config['EXPLORE_CONFIG'],
                           loc=locID,
                           week=c.api('/epi_week'))
