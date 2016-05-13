"""
common.py

Shared functions for meerkat_frontend.
"""
from datetime import datetime, timedelta
from dateutil.parser import parse
from functools import wraps
from flask import current_app, abort, send_file, Response, request
import requests
import json, os
from requests.auth import HTTPBasicAuth

def check_auth(username, password):
    """This function is called to check if a username / password combination is valid.

       Args:
           username (str): The given username
           password (str): The given password

       Returns:
           bool: True if username/password combination is valid, false otherwise."""

    if not current_app.config["USE_BASIC_AUTH"]:
        return True
    if "~" in request.path:
        request_path = request.path.split("~")[0]
    else:
        request_path = request.path
    requested_object = request_path.strip("/").split("/")
    if len(requested_object) > 1 and "/".join(requested_object[:2]) in current_app.config["AUTH"]:
        current_app.logger.info("Found AUTH for level 2")
        auth_object = current_app.config["AUTH"]["/".join(requested_object[:2])]
        return username == auth_object["USERNAME"] and password == auth_object["PASSWORD"]
    elif requested_object[0] in current_app.config["AUTH"]:
        current_app.logger.info("Found AUTH for level 1")        
        auth_object = current_app.config["AUTH"][requested_object[0]]
        return username == auth_object["USERNAME"] and password == auth_object["PASSWORD"]
    else:
        return username == current_app.config["USERNAME"] and password == current_app.config["PASSWORD"]

def authenticate():
    """Sends a 401 response that enables basic auth."""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_api_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        non_proteced = ["key_indicators", "tot_map", "consultation_map", "num_alerts"]
        if "path" in kwargs and kwargs["path"] in non_proteced:
            return f(*args, **kwargs)
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def api(url, params=dict()):
    """Returns JSON data from API request.

    If we are in the testing envrionment we return json from files in apiData.

       Args:
           url (str): The Meerkat API url from which data is requested
           params (dict): Dictionary with url parameters
       Returns:
           dict: A python dictionary formed from the API reponse json string.
    """
    if( current_app.config['TESTING'] ):
        if url[0] == "/":
            url = url[1:]
        path = os.path.dirname(os.path.realpath(__file__))+"/apiData/"+url.replace("/", "_")
        with open(path+'.json') as data_file:    
            return json.load(data_file)
    else:
        api_request = '/'.join([current_app.config['INTERNAL_API_ROOT'], url])
        params["api_key"] = current_app.config["TECHNICAL_CONFIG"]["api_key"]
        try:
            r = requests.get(
                api_request,
                params=params)
        except requests.exceptions.RequestException as e:
            abort(500, e)
        try:
            output = r.json()
        except Exception as e:
            abort(500, e)
        return output

def hermes(url, method, data={}):
    """Makes a Hermes API request.
       
       Args:
           url (str): The Meerkat Hermes url for the desired function.
           method (str):  The desired HTML function: GET, POST or PUT.
           data (optional dict): The data to be sent to the url. Defaults to ```{}```.

       Returns:
           dict: a dictionary formed from the json data in the response.
    """

    #Add the API key and turn into JSON.
    data["api_key"] = current_app.config['HERMES_API_KEY']

    #Assemble the other request params.
    url = current_app.config['HERMES_ROOT']+url #+"?api_key="+current_app.config['HERMES_API_KEY']
    headers = {'content-type' : 'application/json'}

    current_app.logger.warning( "Sending json data:" + json.dumps(data) +"\nTo url: " + url )
    
    #Make the request and handle the response.
    try:
        r = requests.request( method, url, json=data, headers=headers)
    except requests.exceptions.RequestException as e:
        abort(500, "request")
    return r.json()

def epi_week_to_date(epi_week, year=datetime.today().year):
    """Converts an epi_week to a datetime object.
    
       Args:
           epi_week (int): The epi week to convert.
           year (optional int): The year of the epi-week to convert. Defaults to current year.

       Returns:
           datetime: a datetime object for the end of the given epiweek."""
    api_request = "/epi_week_start/{}/{}".format(year, epi_week)
    data = api(api_request)
    return parse(data["start_date"]) + timedelta(days=7)


def date_to_epi_week(day=datetime.today()):
    """Converts a datetime object to an epi_week.
 
       Args:
           day (optional datetime): The date for which to find the corressponding epi week. 
               Defaults to today.
        
       Returns:
           int: the epi week number for the week that contains the given date.
    """
    api_request = "/epi_week/{}".format(day.isoformat())
    data = api(api_request)
    return data["epi_week"]
