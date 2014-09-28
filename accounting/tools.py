#!/user/bin/env python2.7

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy


"""
#######################################################
This is the base code for the intern project.

If you have any questions, please contact Amanda at:
    amanda@britecore.com
#######################################################
"""

class PolicyAccounting(object):
    """
     Each policy has its own instance of accounting.
    """
    def __init__(self, policy_id):
        self.policy = Policy.query.filter_by(id=policy_id).one()

        if not self.policy.invoices:
            self.make_invoices()

    """
     Sums the total amount due across all invoices for the policy up to and including
     the date indicated by date_cursor, then sums and subtracts the total payments
     made up to that same date from the total amount due and returns the result.
    """
    def return_account_balance(self, date_cursor=None):
        if not date_cursor:
            date_cursor = datetime.now().date()

        # invoices and payments from the same day as date_cursor should be included
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.bill_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()
        due_now = 0
        for invoice in invoices:
            due_now += invoice.amount_due

        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date <= date_cursor)\
                                .all()
        for payment in payments:
            due_now -= payment.amount_paid

        return due_now

    """
     Creates a payment for the policy represented by the object and adds it to the database.

     Note: it is possible for the contact_id to be added to the database as None if no
           contact_id is passed to the function and no named_insured is held in the policy
    """
    def make_payment(self, contact_id=None, date_cursor=None, amount=0):
        if not date_cursor:
            date_cursor = datetime.now().date()

        """
         Added for problem 7. If the policy is in cancellation_due_to_non_pay status
         and the contact_id does not match an agent in the database then the payment
         will not be processed.
        """        
        if( self.evaluate_cancellation_pending_due_to_non_pay( date_cursor=date_cursor )\
            and not Contact.query.filter_by(name=contact_id).filter_by(role='Agent').all() ):
                print "ONLY AGENTS MAY MAKE PAYMENTS ON CANCELLATION PENDING POLICIES"
                return False
        
            
        if not contact_id:
            try:
                contact_id = self.policy.named_insured
            except:
                pass

        payment = Payment(self.policy.id,
                          contact_id,
                          amount,
                          date_cursor)
        db.session.add(payment)
        db.session.commit()

        return payment


    def evaluate_cancellation_pending_due_to_non_pay(self, date_cursor=None):
        # problem 7
        """
         If this function returns true, an invoice
         on a policy has passed the due date without
         being paid in full. However, it has not necessarily
         made it to the cancel_date yet.
        """
        if not date_cursor:
            date_cursor = datetime.now().date()
            
        # not concerned with whether or not the cancel_date has passed
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(date_cursor >= Invoice.due_date )\
                                .order_by(Invoice.bill_date)\
                                .all()

        for invoice in invoices:
            if invoice.amount_due:
                return True
        else:
            return False

    """
     Evaluates whether a policy should be canceled by determining if there are any
     invoices with an outstanding balance past their cancel_date.
    """
    def evaluate_cancel(self, date_cursor=None):
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.cancel_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()

        for invoice in invoices:
            if not self.return_account_balance(invoice.cancel_date):
                continue
            else:
                print "THIS POLICY SHOULD HAVE CANCELED"
                break
        else:
            print "THIS POLICY SHOULD NOT CANCEL"


    """
     Deletes any invoices for the policy and re-creates them. Invoices are made based on the
     billing_schedule and the annual_premium of the policy. An Annual billing schedule will
     have a single invoice with the full annual_premium, a Quarterly will have 4 invoices and
     each will charge 1/4th the annual_premium, etc. Adds these invoices to the database.
    """
    def make_invoices(self):
        for invoice in self.policy.invoices:
            invoice.delete()

        '''
        The numbers being used for division and should be cast as floats
        to avoid accidental integer division truncating change from the amount due
        '''
        billing_schedules = {'Annual': None, 'Two-Pay': 2, 'Semi-Annual': 3,
                             'Quarterly': 4, 'Monthly': 12} #added Two-Pay

        invoices = []
        first_invoice = Invoice(self.policy.id,
                                self.policy.effective_date,  # bill_date
                                self.policy.effective_date + relativedelta(months=1),  # due
                                self.policy.effective_date + relativedelta(months=1, days=14),  # cancel
                                self.policy.annual_premium)  # defaults to assume an annual payment schedule
        invoices.append(first_invoice)  # Annual payment schedule is done

        # Use a switch-case instead for readability?
        if self.policy.billing_schedule == "Annual":
            pass
        elif self.policy.billing_schedule == "Two-Pay":
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                months_after_eff_date = i*6
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
        elif self.policy.billing_schedule == "Quarterly":
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                months_after_eff_date = i*3
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
        elif self.policy.billing_schedule == "Monthly":
            """
            Newly implemented
            """
            # corrects the amount due in the first invoice
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule )
            for i in range( 1, billing_schedules.get(self.policy.billing_schedule) ):
                months_after_eff_date = i
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),  # assuming a monthly bill has the same grace period as others
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule) )
                invoices.append(invoice)
        else:
            print "You have chosen a bad billing schedule."

        """
         If a bad billing_schedule is chosen then we will add a single invoice as if the policy
         had an Annual billing_schedule? This is probably not good.
        """
        for invoice in invoices:
            db.session.add(invoice)
        db.session.commit()

################################
# The functions below are for the db and 
# shouldn't need to be edited.
################################
def build_or_refresh_db():
    db.drop_all()
    db.create_all()
    insert_data()
    print "DB Ready!"

def insert_data():
    #Contacts
    contacts = []
    john_doe_agent = Contact('John Doe', 'Agent')
    contacts.append(john_doe_agent)
    john_doe_insured = Contact('John Doe', 'Named Insured')
    contacts.append(john_doe_insured)
    bob_smith = Contact('Bob Smith', 'Agent')
    contacts.append(bob_smith)
    anna_white = Contact('Anna White', 'Named Insured')
    contacts.append(anna_white)
    joe_lee = Contact('Joe Lee', 'Agent')
    contacts.append(joe_lee)
    ryan_bucket = Contact('Ryan Bucket', 'Named Insured')
    contacts.append(ryan_bucket)

    for contact in contacts:
        db.session.add(contact)
    db.session.commit()

    policies = []
    p1 = Policy('Policy One', date(2015, 1, 1), 365)
    p1.billing_schedule = 'Annual'
    p1.named_insured = john_doe_insured.id # newly added for problem 6
    p1.agent = bob_smith.id
    policies.append(p1)

    p2 = Policy('Policy Two', date(2015, 2, 1), 1600)
    p2.billing_schedule = 'Quarterly'
    p2.named_insured = anna_white.id
    p2.agent = joe_lee.id
    policies.append(p2)

    p3 = Policy('Policy Three', date(2015, 1, 1), 1200)
    p3.billing_schedule = 'Monthly'
    p3.named_insured = ryan_bucket.id
    p3.agent = john_doe_agent.id
    policies.append(p3)

    # newly added for problem 5
    p4 = Policy( 'Policy Four', date( 2015, 2, 1 ), 500 )
    p4.billing_schedule = 'Two-Pay'
    p4.named_insured = ryan_bucket.id
    p4.agent = john_doe_agent.id
    policies.append(p4)

    for policy in policies:
        db.session.add(policy)
    db.session.commit()

    for policy in policies:
        PolicyAccounting(policy.id)

    payment_for_p2 = Payment(p2.id, anna_white.id, 400, date(2015, 2, 1))
    db.session.add(payment_for_p2)
    db.session.commit()

