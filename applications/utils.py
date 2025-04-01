from __future__ import unicode_literals
from django.db.models import Q
# from ledger.payments.invoice import utils
# from ledger.payments.models import Invoice,OracleInterface,CashTransaction
# from ledger.payments.utils import oracle_parser_on_invoice,update_payments
# from ledger.checkout.utils import create_basket_session, create_checkout_session, place_order_submission, get_cookie_basket
from ledger_api_client.utils import create_basket_session, create_checkout_session
from ledger_api_client.ledger_models import EmailUserRO as EmailUser
# from oscar.apps.order.models import Order
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from applications.email import sendHtmlEmail, emailGroup, emailApplicationReferrals
from applications import models
from ledger_api_client.managed_models import SystemUser, SystemGroupPermission
import random
import re
import string


def random_dpaw_email():
    """Return a random email address ending in dpaw.wa.gov.au
    """
    s = ''.join(random.choice(string.ascii_letters) for i in range(20))
    return '{}@dpaw.wa.gov.au'.format(s)


def get_query(query_string, search_fields):
    """Function to return a Q object that can be used to filter a queryset.
    A search string and a list of model fields is passed in.

    Splits the query string into individual keywords, getting rid of extra
    spaces and grouping quoted words together as a phrase (use double quotes).
    """
    findterms = re.compile(r'"([^"]+)"|(\S+)').findall
    normspace = re.compile(r'\s{2,}').sub
    query = None  # Query to search for every search term
    terms = [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]
    for term in terms:
        or_query = None  # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    return query

def random_generator(size=12, chars=string.digits):
        return ''.join(random.choice(chars) for _ in range(size))


def set_session_booking(session, key, value):
    session[key] = value
    session.modified = True

def checkout(request, booking, lines, booking_reference, invoice_text=None, vouchers=[], internal=False):
    basket_params = {
        'products': lines,
        'vouchers': vouchers,
        'system': settings.PS_PAYMENT_SYSTEM_ID,
        'custom_basket': True,
        'tax_override': True, #TODO: check this not sure if needed
        'booking_reference': booking_reference,
        'booking_reference_link': booking_reference,
    }
    set_session_booking(request.session, 'test', 'JASON TEST')

    basket_hash = create_basket_session(request, booking['booking'].customer, basket_params)
    checkout_params = {
        'system': settings.PS_PAYMENT_SYSTEM_ID,
        'fallback_url': request.build_absolute_uri('/'),
        'return_url': request.build_absolute_uri(reverse('payment_success', kwargs={"booking_id": booking['booking'].id})), #request.build_absolute_uri(reverse('public_booking_success')),
        'return_preload_url': request.build_absolute_uri(reverse('payment_success_preload', kwargs={"booking_id": booking['booking'].id, "booking_hash": booking['booking'].booking_hash})), #request.build_absolute_uri(reverse('public_booking_success')),
        'force_redirect': True,
        'invoice_text': invoice_text,
        'basket_owner': booking['booking'].customer,
        'session_type': 'ledger_api',
    }
#    if not internal:
#        checkout_params['check_url'] = request.build_absolute_uri('/api/booking/{}/booking_checkout_status.json'.format(booking.id))
    if internal or request.user.is_anonymous:
        checkout_params['basket_owner'] = booking['booking'].customer
    create_checkout_session(request, checkout_params)
    response = HttpResponse(
        "<script> window.location='" + reverse('ledgergw-payment-details') + "';</script> <a href='" + reverse(
            'ledgergw-payment-details'
            ) + "'> Redirecting please wait: " + reverse('ledgergw-payment-details') + "</a>"
        )

    set_session_booking(request.session, 'application_id', booking['app'].id)
    set_session_booking(request.session, 'booking_id', booking['booking'].id)
    set_session_booking(request.session, 'routeid', booking['app'].routeid)


#    if internal:
#        response = place_order_submission(request)
#    else:
    # response = HttpResponseRedirect(reverse('checkout:index'))
    # inject the current basket into the redirect response cookies
    # or else, anonymous users will be directionless
    # response.set_cookie(
    #         settings.OSCAR_BASKET_COOKIE_OPEN, basket_hash,
    #         max_age=settings.OSCAR_BASKET_COOKIE_LIFETIME,
    #         secure=settings.OSCAR_BASKET_COOKIE_SECURE, httponly=True
    # )

    #if booking.cost_total < 0:
    #    response = HttpResponseRedirect('/refund-payment')
    #    response.set_cookie(
    #        settings.OSCAR_BASKET_COOKIE_OPEN, basket_hash,
    #        max_age=settings.OSCAR_BASKET_COOKIE_LIFETIME,
    #        secure=settings.OSCAR_BASKET_COOKIE_SECURE, httponly=True
    #    )

    ## Zero booking costs
    #if booking.cost_total < 1 and booking.cost_total > -1:
    #    response = HttpResponseRedirect('/no-payment')
    #    response.set_cookie(
    #        settings.OSCAR_BASKET_COOKIE_OPEN, basket_hash,
    #        max_age=settings.OSCAR_BASKET_COOKIE_LIFETIME,
    #        secure=settings.OSCAR_BASKET_COOKIE_SECURE, httponly=True
    #    )

    return response


def application_lodgment_info(request,app):

        # Success message.
        msg = """Your {0} application has been successfully submitted. The application
        number is: <strong>WO-{1}</strong>.<br>
        Please note that routine applications take approximately 4-6 weeks to process.<br>
        If any information is unclear or missing, Parks and Wildlife may return your
        application to you to amend or complete.<br>
        The assessment process includes a 21-day external referral period. During this time
        your application may be referred to external departments, local government
        agencies or other stakeholders. Following this period, an internal report will be
        produced by an officer for approval by the Manager, Rivers and Estuaries Division,
        to determine the outcome of your application.<br>
        You will be notified by email once your {0} application has been determined and/or
        further action is required.""".format(app.get_app_type_display(), app.pk)
        messages.success(request, msg)
        submitted_by = SystemUser.objects.get(ledger_id=app.submitted_by)
        emailcontext = {}
        emailcontext['app'] = app
        emailcontext['application_name'] = models.Application.APP_TYPE_CHOICES[app.app_type]
        emailcontext['person'] = submitted_by
        emailcontext['body'] = msg
        sendHtmlEmail([submitted_by.email], emailcontext['application_name'] + ' application submitted ', emailcontext, 'application-lodged.html', None, None, None)
