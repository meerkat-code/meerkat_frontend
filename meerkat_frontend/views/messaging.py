"""
messaging.py

A Flask Blueprint module for Meerkat messaging services.
"""
from flask import Blueprint, render_template, abort, redirect, flash, request, send_file, current_app, Response
import time, random
try:
    import simplejson as json
except ImportError:
    import json
import requests
from .. import common as c

messaging = Blueprint('messaging', __name__)

def check_auth(username, password):
    """This function is called to check if a username / password combination is valid.

       Args:
           username (str): The given username
           password (str): The given password

       Returns:
           bool: True if username/password combination is valid, false otherwise.
    """
    return username == current_app.config["USERNAME"] and password == current_app.config["PASSWORD"]

def authenticate():
    """Sends a 401 response that enables basic auth."""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

@messaging.before_request
def requires_auth():
    """Checks that the user has authenticated before returning any page from the technical site."""
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

# THE SUBSCRIBING PROCESS
#Stage1: Fill out a subscription form.
@messaging.route('/')
def subscribe():
    """Subscription Process Stage 1: Render the page with the subscription form"""
    return render_template('messaging/subscribe.html',
                           content=current_app.config['MESSAGING_CONFIG'],
                           week=c.api('/epi_week'))

# Stage 2: Confirm subscription request and inform user of verification process.
@messaging.route('/subscribe/subscribed', methods=['POST'])
def subscribed(): 
    """Subscription Process Stage 2: Confirms successful subscription request and informs the 
       user of the verification process. This method assembles the HTML form data into a strcture
       that Meerkat Hermes understands and then uses the MeerkatHermes "subscribe" resource to create 
       the subscriber. It further assembles the email and SMS verification messages and uses the 
       Meerkat Hermes to send it out. """

    #Convert form immutabledict to dict.
    data = {}
    for key in request.form.keys():
        key_list = request.form.getlist(key) 
        if( len(key_list) > 1 ): 
            data[key] = key_list
        else: 
            data[key] = key_list[0]

    #Call hermes subscribe method.
    subscribe_response = c.hermes('/subscribe', 'PUT', data)
    current_app.logger.warning('Response is: ' + str(subscribe_response))

    #Assemble and send verification email.
    url = request.url_root + "messaging/subscribe/verify/"+subscribe_response['subscriber_id'];

    message = ( "Dear " + data['first_name'] + " " + data['last_name']+",\n\n"
                "Thank you for subscribing to receive public health surveillance notifications from "
                + current_app.config['MESSAGING_CONFIG']['messages']['country'] + ".\n\nPlease verify your "
                "contact details by copying and pasting the following url into your address bar:\n" + url )

    html = ( "<p>Dear " + data['first_name'] + " " + data['last_name']+",</p>"
             "<p>Thank you for subscribing to receive public health surveillance notifications from "
             + current_app.config['MESSAGING_CONFIG']['messages']['country'] + ".</p><p>Please "
             "verify your contact details by <a href='" + url + "' target='_blank'>clicking here</a>." 
             "</p>" )

    email = {
        'email': data['email'],
        'subject': "Please verify your contact details",
        'message': message,
		'html':html,
        'from': current_app.config['MESSAGING_CONFIG']['messages']['from']
    }

    email_response = c.hermes('/email', 'PUT', email)
    current_app.logger.warning('Response is: ' + str(email_response))

    #Set and send sms verification code.
    if 'sms' in data:
       __set_code(subscribe_response['subscriber_id'], data['sms'])

    return render_template('messaging/subscribed.html',
                           content=current_app.config['MESSAGING_CONFIG'],
                           week=c.api('/epi_week'),
                           data=data)

# Stage 3: Verify contact details.
@messaging.route('/subscribe/verify/<string:subscriber_id>')
def verify(subscriber_id):

    """Subscription Process Stage 3: Verfies contact details for the subscriber ID specified in
       the URL. If no SMS number is provided, then just landing on this page is enough to verify
       the users email address (assuming the ID is not guessable). In this case we do a redirect to 
       Stage 4. If the user has already been verified, then we also redirect to stage four with a
       flash message to remind them that they have already verified. In all other cases we show
       the SMS verification form.

       Args:
           subscriber_id (str):  The UUID that is assigned to the subscriber upon creation by Meerkat Hermes. 
    """

    #Get the subscriber
    subscriber = c.hermes( '/subscribe/'+subscriber_id, 'GET' )

    if subscriber['Item']['verified'] == True:
        flash( 'You have already verified your account.')
        return redirect('/messaging/subscribe/verified/' + subscriber_id, code=302)
    elif 'sms' not in subscriber['Item']:
        current_app.logger.warning(str(subscriber['Item']))
        c.hermes('/verify/'+subscriber_id, 'GET')
        return redirect('messaging/subscribe/verified/' + subscriber_id)
    else:
        return render_template('messaging/verify.html',
                               content=current_app.config['MESSAGING_CONFIG'],
                               week=c.api('/epi_week'),
                               data=subscriber['Item'])

# Stage 4: Confirm details have been verified.
@messaging.route('/subscribe/verified/<string:subscriber_id>')
def verified(subscriber_id):

    """Subscription Process Stage 4: Confirms that the users details has been verified, and sends
       out a confirmation email as well. 

       Args:
           subscriber_id (str):  The UUID that is assigned to the subscriber upon creation by Meerkat Hermes.
    """

    #Get the subscriber
    subscriber = c.hermes( '/subscribe/'+subscriber_id, 'GET' )['Item']

    country = current_app.config['MESSAGING_CONFIG']['messages']['country']

    # Send a confirmation e-mail with the unsubscribe link.
    message = ( "Dear " + subscriber['first_name'] + " " + subscriber['last_name']+",\n\n"
                "Thank you for subscribing to receive public health surveillance notifications from "
                + country + ".  We can confirm that your contact details have been "
                "successfully verified.\n\nYou can unsubscribe at any time by clicking on the " 
                "relevant link in your e-mails.\n\n If you wish to "
                "unsubscribe now copy and paste the following url into your address bar:\n"
                + current_app.config['HERMES_ROOT'] + "/unsubscribe/" + subscriber_id  )

    html = ( "<p>Dear " + subscriber['first_name'] + " " + subscriber['last_name'] + ",</p>"
             "<p>Thank you for subscribing to receive public health surveillance notifications from "
             + country +  ".  We can confirm that your contact details have been successfully verified."
             "</p><p>You can unsubscribe at any time by clicking on the relevant link in your e-mails.</p><p> " 
             "If you wish to unsubscribe now <a href='" + current_app.config['HERMES_ROOT'] + "/unsubscribe/" 
             + subscriber_id + "'>click here.</a></p>" )

    email = {
        'email': subscriber['email'],
        'subject': "Your subscription has been successful",
        'message': message,
        'html': html,
        'from': current_app.config['MESSAGING_CONFIG']['messages']['from']
    }

    email_response = c.hermes('/email', 'PUT', email)
    current_app.logger.warning('Response is: ' + str(email_response))

    return render_template('messaging/verified.html',
                           content=current_app.config['MESSAGING_CONFIG'],
                           week=c.api('/epi_week'))

# Choose, set and check SMS verification codes. 
@messaging.route('/subscribe/sms_code/<string:subscriber_id>', methods=['get', 'post'])
def sms_code(subscriber_id):

    """Chooses, sets and checks SMS verification codes for the subscriber corresponding
       to the ID given in the URL. If a POST request is made to this URL it checks whether the
       code supplied in the POST request form data matches the code sent to the phone. If it does,
       it redirects to Stage 4, if it doesn't it redirects to stage 3 again with a flash
       informing the user they got the wrong code. If a GET request is made to this URL, the function
       selects a new code and sends the code out to the phone. It then redirects to Stage 3 with a
       flash message informing the user whether the new code has been succesffully sent.

       Args:
           subscriber_id (str):  The UUID that is assigned to the subscriber upon creation by Meerkat Hermes. """

    current_app.logger.warning("Method is: " + request.method )

    if request.method == 'POST':
        if __check_code( subscriber_id, request.form['code'] ):
            c.hermes('/verify/'+subscriber_id, 'GET')
            return redirect("/messaging/subscribe/verified/"+subscriber_id, code=302)
        else:
            flash('You submitted the wrong code.', 'error')
            return redirect("/messaging/subscribe/verify/"+subscriber_id, code=302) 
    else:
        subscriber = c.hermes( '/subscribe/'+subscriber_id, 'GET' )
        response = __set_code(subscriber_id, subscriber['Item']['sms'])

		#Check that the new code was succesfully sent.
        success = True
        for r in response['messages']:

            current_app.logger.warning( "Status: "+str(r['status'])+"\nStatement: " + str(not r['status'] == '0') )
            if not r['status'] == '0': 
                success = False
                current_app.logger.warning( "Success: " + str(success) )

        if success==True: 
            flash('A new code has been sent to your phone.')
            return redirect("/messaging/subscribe/verify/"+subscriber_id, code=302)
        else:
            flash('Error: Try again later, or contact administrator.', 'error')
            return redirect("/messaging/subscribe/verify/"+subscriber_id, code=302)

# Utility function to check a code
def __check_code(subscriber_id, code):
    """Checks if the given code for the given subscriber ID is the correct SMS verification code.

       Args:
           subscriber_id (str):  The UUID that is assigned to the subscriber upon creation by Meerkat Hermes.
           code (str): The code to be checked.

       Returns:
           bool: True if there is a match, False otherwise. 
           
    """
    response = c.hermes('/verify', 'POST', {'subscriber_id':subscriber_id, 'code': code} )
    current_app.logger.warning( str(response ) )
    return bool(response['matched'])

# Utility function to set a new sms code.
def __set_code(subscriber_id, sms):
    """Sets a new sms verification code for the given subscriber ID.

       Args:
           subscriber_id (str):  The UUID that is assigned to the subscriber upon creation by Meerkat Hermes.
           sms (int): The SMS number to which the new code should be sent.

       Returns:
           The Meerkat Hermes response object.
           
    """
    code = round(random.random()*9999)
    message = ( 'Your verification code for ' + current_app.config['MESSAGING_CONFIG']['messages']['country'] + 
        ' public health surveillance notifications is: ' + str(code) + '. Please follow instructions'
        ' in the email to verify your contact details.' )

    data = {
        'sms': sms,
        'message': message
    }
    response = c.hermes('/verify', 'PUT', { 'subscriber_id':subscriber_id, 'code': code } )
    response = c.hermes( '/sms', 'PUT', data )
    return response
    

