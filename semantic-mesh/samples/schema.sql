CREATE TABLE customers (
  id UUID PRIMARY KEY,
  name VARCHAR(255),
  kyc_status VARCHAR(50),
  risk_tier INTEGER,
  created_at TIMESTAMPTZ
);

CREATE TABLE accounts (
  id UUID PRIMARY KEY,
  customer_id UUID REFERENCES customers(id),
  account_type VARCHAR(50),
  balance DECIMAL(18,2),
  opened_at TIMESTAMPTZ
);

CREATE TABLE transactions (
  id UUID PRIMARY KEY,
  account_id UUID REFERENCES accounts(id),
  amount DECIMAL(18,2),
  txn_type VARCHAR(50),
  created_at TIMESTAMPTZ
);

CREATE TABLE products (
  id UUID PRIMARY KEY,
  name VARCHAR(255),
  category VARCHAR(100),
  price DECIMAL(10,2)
);

CREATE TABLE account_products (
  account_id UUID REFERENCES accounts(id),
  product_id UUID REFERENCES products(id),
  purchased_at TIMESTAMPTZ,
  PRIMARY KEY (account_id, product_id)
);
