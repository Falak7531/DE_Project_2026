# Schema Design

This document describes the tables in the supplied CSV files and how
they relate to each other.

## Tables

  -----------------------------------------------------------------------
  Table                   Primary key             Main columns
  ----------------------- ----------------------- -----------------------
  `users`                 `user_id`               `full_name`, `phone`,
                                                  `email`, `city_id`,
                                                  `kyc_status`,
                                                  `is_blocked`,
                                                  `created_at`

  `cities`                `city_id`               `city_name`, `state`

  `bank_accounts`         `account_id`            `user_id`, `bank_name`,
                                                  `ifsc`,
                                                  `account_last4`,
                                                  `account_type`,
                                                  `is_primary`,
                                                  `linked_at`

  `vpas`                  `vpa`                   `user_id`,
                                                  `account_id`,
                                                  `is_active`,
                                                  `created_at`

  `merchants`             `merchant_id`           `merchant_name`, `mcc`,
                                                  `merchant_vpa`,
                                                  `city_id`,
                                                  `is_verified`,
                                                  `onboarded_on`

  `transactions`          `txn_id`                `upi_ref`, `txn_type`,
                                                  `payer_vpa`,
                                                  `payee_vpa`,
                                                  `merchant_id`,
                                                  `amount`, `note`,
                                                  `initiated_at`,
                                                  `completed_at`,
                                                  `status`,
                                                  `failure_code`

  `bill_payments`         `bill_id`               `user_id`,
                                                  `biller_category`,
                                                  `biller_name`,
                                                  `consumer_number`,
                                                  `amount`, `due_date`,
                                                  `status`, `paid_at`

  `rewards`               `reward_id`             `user_id`, `txn_id`,
                                                  `reward_type`,
                                                  `amount`, `status`,
                                                  `issued_at`,
                                                  `expires_at`,
                                                  `credited_at`

  `disputes`              `dispute_id`            `txn_id`, `raised_by`,
                                                  `reason`, `raised_at`,
                                                  `status`, `resolved_at`
  -----------------------------------------------------------------------

## Relationships

-   One city can have many users. `users.city_id` references
    `cities.city_id`.
-   One city can have many merchants. `merchants.city_id` references
    `cities.city_id`.
-   One user can have many bank accounts. `bank_accounts.user_id`
    references `users.user_id`.
-   One user can have many VPAs. `vpas.user_id` references
    `users.user_id`.
-   One bank account can be linked to many VPAs. `vpas.account_id`
    references `bank_accounts.account_id`.
-   Transactions use VPAs for the payer and payee.
    `transactions.payer_vpa` and `transactions.payee_vpa` reference
    `vpas.vpa`.
-   A transaction may be associated with a merchant.
    `transactions.merchant_id` references `merchants.merchant_id`.
-   One user can have many bill payments. `bill_payments.user_id`
    references `users.user_id`.
-   Rewards belong to a user and may be linked to a transaction.
    `rewards.user_id` references `users.user_id`; `rewards.txn_id`
    references `transactions.txn_id`.
-   A dispute is raised against a transaction by a user.
    `disputes.txn_id` references `transactions.txn_id`;
    `disputes.raised_by` references `users.user_id`.

## Optional fields

The CSV data contains blank values in some fields. These should be
allowed to be `NULL`:

-   `users.email`
-   `transactions.merchant_id`, `note`, `completed_at`, `failure_code`
-   `bill_payments.paid_at`
-   `rewards.credited_at`
-   `disputes.resolved_at`

## Notes

-   The primary and foreign keys above are inferred from the column
    names and the relationships in the supplied CSV files.
-   Keep IDs and references consistent when importing the CSV files.
-   Store dates and timestamps using date/time types, and store monetary
    values using a fixed-precision decimal type rather than floating
    point.
-   Treat status, type, and category columns as controlled values based
    on the values present in the data.
