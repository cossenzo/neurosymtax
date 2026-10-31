# Taxonomy: Decentralized finance (DeFi)

Meta-characteristic: DeFi applications viewed as financial services delivered through smart contracts on public blockchains without intermediaries, examined by how they create and capture value (strategy), how they are organized and governed (organization), and how they are technically implemented (technology).

Status: completed. 

## strategy

| Dimension | Characteristics |
|---|---|
| Primary financial service | Exchange and trading; Lending and borrowing; Stablecoin issuance; Insurance; Derivatives and synthetic assets; Asset management and funds; Prediction markets; Data and analytics; Infrastructure and access |
| Value capture mechanism | Fees on transactions; Native token value capture; No direct value capture |
| Collateralization | Overcollateralized (conceptual); Undercollateralized (conceptual); Zero collateral (conceptual); No loan (conceptual) |
| Rate variability over time | Dynamic rate (conceptual); Fixed rate (conceptual); No interest rate (conceptual) |

## organization

| Dimension | Characteristics |
|---|---|
| Governance model | Token-holder governance; Validator-run network; Company operation; Autonomous without central operator |
| Asset custody model | Self-custody by users; Assets held in smart contracts; Assets held by a company; No assets held |
| Collateral backing | Off-chain reserves (conceptual); On-chain crypto assets (conceptual); Commodity-based (conceptual); Not fully backed by collateral (conceptual); Not a stablecoin (conceptual) |

## technology

| Dimension | Characteristics |
|---|---|
| Underlying consensus | Proof-of-work; Proof-of-stake; Other consensus (aBFT or DAG); No own blockchain |
| Blockchain deployment layer | Ethereum mainnet; Layer-2 on Ethereum; Own layer-1 blockchain; Other existing public blockchain; No blockchain deployment |
| Trading mechanism | Automated market maker; On-chain order book; Off-chain matching with on-chain settlement; No trading mechanism |

## Definitions

**Primary financial service** (strategy). The main financial function that the DeFi application provides to its users. *Application rule:* Choose the service through which users mainly transact with the application, following this precedence when several services apply: stablecoin issuance and insurance first if the application's core user action is issuing a stablecoin or buying cover; then derivatives and synthetic assets; then prediction markets; then lending and borrowing; then exchange and trading; then asset management and funds; then data and analytics. Infrastructure and access applies to blockchains, wallets, bridges and development tools even when they host financial services; the other values apply to applications that offer the service itself.

- *Exchange and trading*: Users trade crypto-assets with each other or against liquidity pools.
- *Lending and borrowing*: Users supply assets for interest or borrow against collateral.
- *Stablecoin issuance*: The application issues or manages a stablecoin pegged to a currency.
- *Insurance*: The application provides cover or claims payouts against risks.
- *Derivatives and synthetic assets*: The application creates or trades derivatives or assets that track other assets.
- *Asset management and funds*: The application pools, tokenizes or manages investment funds or baskets of assets.
- *Prediction markets*: Users trade shares on the outcomes of events.
- *Data and analytics*: The application presents financial data about DeFi protocols.
- *Infrastructure and access*: Blockchains, wallets, bridges and development tools that enable DeFi without themselves providing a financial service.

**Value capture mechanism** (strategy). The main way in which the provider of the DeFi application captures value. *Application rule:* Choose the revenue or incentive mechanism that is central to the application. Native token value applies only when the native token is central to revenue or incentives.

- *Fees on transactions*: The provider or liquidity providers earn fees charged on transactions.
- *Native token value capture*: Value is captured through a native token used for governance, rewards, collateral or utility.
- *No direct value capture*: The object is an infrastructure or information service without its own revenue mechanism.

**Governance model** (organization). Who makes the operational and protocol decisions of the DeFi application. *Application rule:* Choose the body that decides protocol parameters or operations, following this precedence: token-holder governance first when governance token holders vote, even if no central operator exists; then company operation when a company or exchange operates the application or its blockchain; then validator-run network when network validators keep the network running and decide its operation; then autonomous without central operator when no central party runs the application and it operates through smart contracts.

- *Token-holder governance*: Holders of a governance or native token vote on protocol decisions.
- *Validator-run network*: Network validators keep the network running and decide its operation.
- *Company operation*: A company or exchange operates the application or its blockchain.
- *Autonomous without central operator*: No central party runs the application; it operates through smart contracts.

**Asset custody model** (organization). Where the assets of users are held while the DeFi application processes them. *Application rule:* Choose where user assets are held. Self-custody applies when users keep their private keys; assets held in smart contracts apply when deposits are locked in protocol contracts.

- *Self-custody by users*: Users keep their own private keys and control their assets.
- *Assets held in smart contracts*: Deposited assets are locked in and managed by smart contracts.
- *Assets held by a company*: A company or platform holds the assets of users.
- *No assets held*: The object is an information or infrastructure service that does not hold user assets.

**Underlying consensus** (technology). The consensus mechanism of the blockchain on which the application runs. *Application rule:* Choose the consensus of the blockchain that validates the transactions of the object. Use the negation value when the object has no own blockchain and runs on an existing public chain.

- *Proof-of-work*: Transactions are validated through proof-of-work consensus.
- *Proof-of-stake*: Transactions are validated through proof-of-stake consensus.
- *Other consensus (aBFT or DAG)*: Transactions are validated through a non-standard mechanism such as aBFT or a directed acyclic graph.
- *No own blockchain*: The application runs on an existing public blockchain and has no consensus of its own.

**Blockchain deployment layer** (technology). The layer of the blockchain architecture on which the application is deployed. *Application rule:* Choose the chain on which the core smart contracts of the object run. Ethereum mainnet is the Ethereum base layer; layer-2 applies to networks built on Ethereum; own layer-1 applies when the object is its own blockchain.

- *Ethereum mainnet*: The application runs on the Ethereum public blockchain.
- *Layer-2 on Ethereum*: The application runs on a scaling network built on Ethereum.
- *Own layer-1 blockchain*: The object is its own layer-1 blockchain.
- *Other existing public blockchain*: The application runs on a public blockchain other than Ethereum.
- *No blockchain deployment*: The service is run off-chain by a company.

**Trading mechanism** (technology). How the application matches trades between users. *Application rule:* Choose the mechanism used to price or match trades. Use the negation value when the application does not trade assets.

- *Automated market maker*: Trades are priced by liquidity pools rather than order books.
- *On-chain order book*: Orders are placed and matched through an order book on the blockchain.
- *Off-chain matching with on-chain settlement*: Orders are matched off-chain while trades are settled on-chain.
- *No trading mechanism*: The application does not trade assets between users.

**Collateral backing** (organization). How the reserves or assets that back a stablecoin are constituted. *Application rule:* For a stablecoin, choose the main type of asset that backs it. Choose 'Not fully backed by collateral' when its collateral is less than its value in circulation. Choose 'Not a stablecoin' for objects that do not issue a stablecoin.

- *Off-chain reserves*: The stablecoin is backed by reserves held outside the blockchain, such as fiat currency.
- *On-chain crypto assets*: The stablecoin is backed by crypto-assets locked on the blockchain.
- *Commodity-based*: The stablecoin is backed by commodities.
- *Not fully backed by collateral*: The stablecoin is not fully backed by collateral.
- *Not a stablecoin*: The object does not issue or manage a stablecoin, so no backing applies.

**Collateralization** (strategy). Whether a loan is secured by collateral relative to the loan value. *Application rule:* For a lending object, choose the collateral level of the loan offered as the main lending option. Choose 'No loan' for objects that do not grant loans.

- *Overcollateralized*: The collateral exceeds the loan value, so liquidation occurs if the collateral-to-loan ratio falls under the threshold.
- *Undercollateralized*: The collateral is less than the loan value.
- *Zero collateral*: The loan requires no collateral.
- *No loan*: The object does not grant loans, so no collateralization applies.

**Rate variability over time** (strategy). Whether the interest rate changes dynamically over time or is fixed when the loan is taken or the liquidity is provided. *Application rule:* For an object that charges or pays interest, choose whether the rate changes with the current utilization of the pool (dynamic) or is fixed at the time of the loan or deposit (fixed). Choose 'No interest rate' for objects that charge or pay no interest.

- *Dynamic rate*: The rate can change over time, for example based on the updated utilization.
- *Fixed rate*: The rate is fixed based on the rate at the time the loan was taken or the liquidity was provided.
- *No interest rate*: The object charges or pays no interest on loans or deposits.
