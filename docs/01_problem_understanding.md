# Problem Understanding

## Business needs and stakeholders

  ---------------------------------------------------------------------------
  Problem           Business need (in Stakeholders affected Classification
                    plain words)                            
  ----------------- ----------------- --------------------- -----------------
  **P1 --           Users need to     Payer, payee,         Customer-facing /
  Transaction       view recent       customer support      real-time
  history and pay   payments, verify                        
  screen**          a UPI ID (VPA),                         
                    and see linked                          
                    bank accounts                           
                    quickly so they                         
                    can make and                            
                    track payments                          
                    without delay.                          

  **P2 -- Daily UPI Before processing Payer, payments core, Customer-facing /
  limit**           a payment, the    bank partner          real-time
                    system must                             
                    quickly calculate                       
                    the user's daily                        
                    payment total and                       
                    check it against                        
                    the applicable                          
                    limit.                                  

  **P3 -- Pending   Operations teams  Payer, payee, bank    Customer-facing /
  payments and      need to find      partner,              real-time
  callbacks**       stuck PENDING     reconciliation/ops    
                    transactions and                        
                    process bank                            
                    callbacks                               
                    promptly so                             
                    transaction                             
                    statuses stay up                        
                    to date.                                

  **P4 -- Merchant  Merchants need    Merchant, bank        Real-time for
  collections and   current           partner,              collections and
  settlement**      collection        reconciliation/ops    settlement;
                    information and                         reporting /
                    accurate daily                          analytics for
                    settlement. The                         merchants with no
                    business team                           payments
                    also needs to                           
                    identify                                
                    merchants who                           
                    have not received                       
                    any payments.                           

  **P5 -- Fraud and Risk teams need   Payer, payee, fraud & Customer-facing /
  risk checks**     to detect         risk, compliance      real-time
                    suspicious                              
                    mule-account                            
                    activity,                               
                    repeated                                
                    payments, and                           
                    unusually high                          
                    refund rates                            
                    quickly enough to                       
                    investigate or                          
                    prevent loss.                           

  **P6 -- Rewards   Automated jobs    Payer, rewards team,  Customer-facing /
  and bill          must issue        customer support      real-time for
  reminders**       scratch-card                            reward and bill
                    rewards, identify                       notifications;
                    rewards nearing                         reporting /
                    expiry, and find                        analytics for
                    overdue bills on                        operational lists
                    time.                                   

  **P7 -- KYC, UPI  Compliance needs  Payer, payee,         Reporting /
  reference and     reports to        compliance (RBI/KYC), analytics for
  disputes**        identify          customer support      KYC-risk reports;
                    KYC-related risk.                       customer-facing /
                    Support teams                           real-time for
                    need to find a                          transaction
                    transaction using                       lookups and
                    its UPI reference                       dispute queues
                    and quickly                             
                    access open                             
                    disputes.                               

  **P8 -- Bank      Bank partners and Bank partner,         Reporting /
  health and        analytics teams   reconciliation/ops,   analytics
  business          need reliable     business and          
  insights**        views of failure  analytics teams       
                    codes, payment                          
                    latency, success                        
                    rates, and                              
                    business trends.                        
                    The database must                       
                    also support                            
                    projected 20× UPI                       
                    volume growth.                          
  ---------------------------------------------------------------------------

## Assumptions

-   The supplied CSV exports are the available source for reconstructing
    the current database; undocumented rules are not assumed to exist
    unless supported by the data or assignment brief.
-   P2P payments may involve users of other UPI apps. The payer or payee
    may therefore not always be represented as a Google Pay user in the
    exports.
-   P2M payments are associated with merchants; not every transaction is
    necessarily a merchant payment.
-   Transaction states include success, failure, reversal, refund, and
    PENDING as described in the assignment. Exact status values and NPCI
    failure-code meanings should be confirmed from the data or provided
    reference material.
-   The 12-digit UPI reference is used for transaction identification.
    It should be treated as a reference number, not assumed to be the
    database primary key.
-   "Real-time" means the operation must be responsive during a user
    action or operational payment workflow. Reports and trend analysis
    can run as reporting workloads.
-   The 20× growth statement is a scalability requirement for the future
    workload; the actual large dataset and its size will be supplied
    later by faculty.
-   Performance targets and acceptable response times will be defined
    and measured in the later baseline and optimization phases.
