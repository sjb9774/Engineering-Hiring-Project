#!/user/bin/env python2.7

import unittest
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy
from tools import PolicyAccounting

"""
#######################################################
Test Suite for PolicyAccounting
#######################################################
"""
class TestBillingSchedules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1300)
        db.session.add(cls.policy)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        pass

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        db.session.commit()

    def test_annual_billing_schedule(self):
        self.policy.billing_schedule = "Annual"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Invoices should be made when the class is initiated
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 1)
        self.assertEquals(self.policy.invoices[0].amount_due, self.policy.annual_premium)

    def test_monthly_billing_schedule(self):
        self.policy.billing_schedule = "Monthly"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Invoices should be made when the class is initiated
        pa = PolicyAccounting(self.policy.id)
        #Monthly billing should have 12 invoices created
        self.assertEquals(len(self.policy.invoices),12)
        #Each invoice.amount_due should be equal to a twelfth of the annual_premium
        self.assertItemsEqual( [ inv.amount_due for inv in self.policy.invoices ],
                               [ self.policy.annual_premium/12 ] * 12  )


class TestReturnAccountBalance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_annual_on_eff_date(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 1200)

    def test_quarterly_on_eff_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 300)

    def test_quarterly_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[3].bill_date), 1200)
        
    """
     Will fail as given due to the payment being made on the bill date of the second invoice,
     which is past the cancellation pending date of the first invoice, therefore the payment would
     have to be made by an Agent or on a later date to pass the test.
    """
    def test_quarterly_on_second_installment_bill_date_with_full_payment(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()

        payment = pa.make_payment(contact_id=self.policy.named_insured,
                                  date_cursor=invoices[1].bill_date, amount=600)
        if payment:
            self.payments.append(payment)  # should be None, but keep track of it just in case

        # self.assertEquals(pa.return_account_balance(date_cursor=invoices[1].bill_date), 0) --original test, fails

        # new test, a better test that ensures the payment didn't go through
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[1].bill_date), pa.policy.annual_premium/2)

    """
     Added to test problem 7 restriction of Agent-only payments past the cancellation-pending date.
    """
    def test_non_agent_payment_on_annual_with_cancellation_pending(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy.id)
        invoice = pa.policy.invoices[0]
        p = pa.make_payment(contact_id=self.policy.named_insured,
                            date_cursor=invoice.due_date+relativedelta(days=21), amount=100)
        
        self.assertFalse(p)
