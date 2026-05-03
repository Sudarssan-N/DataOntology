package com.bank.model;

import javax.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Entity
@Table(name = "customers")
public class Customer {

    @Id
    private String id;

    @Column
    private String name;

    @Column(name = "kyc_status")
    private String kycStatus;

    @Column
    private Integer riskTier;

    @OneToMany(mappedBy = "customer")
    private List<Account> accounts;
}

@Entity
@Table(name = "accounts")
public class Account {

    @Id
    private String id;

    @ManyToOne
    @JoinColumn(name = "customer_id")
    private Customer customer;

    @Column(name = "account_type")
    private String accountType;

    @Column
    private BigDecimal balance;

    @OneToMany(mappedBy = "account")
    private List<Transaction> transactions;
}

@Entity
@Table(name = "transactions")
public class Transaction {

    @Id
    private String id;

    @ManyToOne
    @JoinColumn(name = "account_id")
    private Account account;

    @Column
    private BigDecimal amount;

    @Column(name = "txn_type")
    private String txnType;

    @Column
    private LocalDateTime createdAt;
}
