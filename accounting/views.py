from flask import render_template, request, redirect, flash
from datetime import date, datetime
from accounting import app, db

# Import our models
from models import Contact, Invoice, Policy, Payment
from tools import PolicyAccounting

# Routing for the server.
@app.route("/", methods=['POST','GET'])
def index():
    return render_template('index.html')

'''
 Displays the page displaying information about the policy and
 the invoices associated with it.
'''
@app.route("/policyInfo", methods=['POST'])
def gather_policy_info():
    policy_number = request.form['policy_number']
    invoice_date = request.form['invoice_date']

    try:
        invoice_date = datetime.strptime( invoice_date, '%Y-%m-%d' ).date()
        policy_number = int(policy_number)
    except ValueError:
        flash('There was a problem processing the input')
        return render_template('index.html')

    try:
        # Invoices will be created when PolicyAccounting object is instantiated
        pa = PolicyAccounting(policy_number)
    except:
        flash('No policy matching that number found.')
        return render_template('index.html')

    # filters out all invoices with bill_dates past the entered date
    invoices_to_invoice_date = filter(lambda x: x.bill_date <= invoice_date,
                       pa.policy.invoices)

    if len(invoices_to_invoice_date) == 0:
            flash('No invoices found!')
            return render_template('index.html')

    payments = pa.policy.payments  # db.relation

    payments_contacts_dict = None  # pass None unless we have payments to match

    if len(payments) != 0:
        payments_contacts_dict = {}
        for payment in payments:
            print "payment"
            payments_contacts_dict[payment] = Contact.query.filter_by(id=payment.contact_id).first()

    return render_template('/invoices.html',
                           policy_number=policy_number,
                           invoice_date=invoice_date,
                           invoices=invoices_to_invoice_date,
                           policy_account=pa,
                           payments_contacts_dict=payments_contacts_dict)
