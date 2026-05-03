from sqlalchemy import Column, ForeignKey, String, Integer, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class Customer(Base):
    __tablename__ = "customers"
    id = Column(UUID, primary_key=True)
    name = Column(String)
    kyc_status = Column(String)
    accounts = relationship("Account", back_populates="customer")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(UUID, primary_key=True)
    customer_id = Column(UUID, ForeignKey("customers.id"))
    account_type = Column(String)
    balance = Column(Float)
    customer = relationship("Customer", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(UUID, primary_key=True)
    account_id = Column(UUID, ForeignKey("accounts.id"))
    amount = Column(Float)
    txn_type = Column(String)
    account = relationship("Account", back_populates="transactions")
