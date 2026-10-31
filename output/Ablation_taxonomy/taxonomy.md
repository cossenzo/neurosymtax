# Taxonomy: Decentralized finance (DeFi)

Meta-characteristic: DeFi applications viewed as financial services delivered by smart contracts on public blockchains without intermediaries, examined through the strategic, organizational, and technological means by which they create value and are structured.

Status: completed. objective and subjective conditions hold; no evaluation (R9 not applied)

## strategy

| Dimension | Characteristics |
|---|---|
| Primary financial service | Yield aggregation and optimization; Lending and borrowing; Trading and exchange; Stablecoin issuance; Staking and liquid staking; Insurance; Other financial service |
| Revenue model | Revenue shared with token stakers; Protocol fees retained by the application; No protocol fee charged; No revenue model described |

## organization

| Dimension | Characteristics |
|---|---|
| Governance model | Token-holder governance; Team-controlled governance; Governance not described |
| Platform scope | Standalone application; Product within a multi-product platform or ecosystem |

## technology

| Dimension | Characteristics |
|---|---|
| Blockchain deployment | Single public blockchain; Multiple public blockchains; Blockchain not specified |
| Core mechanism | Automated market maker; Order book or auction settlement; Interest-rate lending market; Vault-based strategy automation; Other mechanism |
| Role in the DeFi stack | Aggregator or optimizer; Primitive protocol |

## Definitions

**Primary financial service** (strategy). The financial service that forms the core value proposition of the DeFi application, delivered by smart contracts without intermediaries. *Application rule:* Observe the financial service the application mainly offers to users. If several services apply, choose the first matching characteristic in this order: yield aggregation and optimization, lending and borrowing, trading and exchange, stablecoin issuance, staking and liquid staking, insurance, other financial service.

- *Yield aggregation and optimization*: The primary service routes or compounds users' funds across yield opportunities to generate returns.
- *Lending and borrowing*: The primary service lets users lend assets for interest or borrow assets against collateral.
- *Trading and exchange*: The primary service enables swaps or derivative trading of crypto assets.
- *Stablecoin issuance*: The primary service issues a stablecoin or a certificate-of-deposit token.
- *Staking and liquid staking*: The primary service lets users stake assets, often receiving tokens that represent the staked position.
- *Insurance*: The primary service provides cover against losses such as smart contract risks.
- *Other financial service*: The primary service is none of the above, such as prize-linked savings or NFT farming.

**Revenue model** (strategy). How the DeFi application captures value from its activities for its owners or token holders. *Application rule:* Observe how the application generates and distributes revenue. If it shares revenue with token stakers, choose that characteristic. Otherwise, if it charges protocol fees, choose the fee characteristic. Otherwise, if it states that no protocol fee is charged, choose that characteristic. If no revenue information is given, choose the negation characteristic.

- *Revenue shared with token stakers*: Holders who stake the application's token receive part of the revenue collected by the application.
- *Protocol fees retained by the application*: The application charges performance, management, service or protocol fees that it keeps as revenue.
- *No protocol fee charged*: The application does not charge a protocol fee on its services by default.
- *No revenue model described*: The sources do not describe how the application generates or distributes revenue.

**Governance model** (organization). How decisions on the DeFi application and control over its smart contracts are made. *Application rule:* If decisions are made by holders of a governance token or the application is organized as a DAO, choose token-holder governance. If a project team or individuals control decisions or contract changes, choose team-controlled governance. If governance is not described, choose the negation characteristic.

- *Token-holder governance*: Decisions are made by holders of the application's governance token, for example through voting or as a DAO.
- *Team-controlled governance*: Decisions or contract changes rest with a project team or individuals rather than with token holders.
- *Governance not described*: The sources do not describe how decisions on the application are made.

**Platform scope** (organization). Whether the DeFi application is offered on its own or as one product within a larger platform or ecosystem. *Application rule:* If the application is described as a product, feature or component of a multi-product platform or ecosystem, choose that characteristic. Otherwise choose standalone application.

- *Standalone application*: The application is offered as a single application and is not described as part of a larger product platform or ecosystem.
- *Product within a multi-product platform or ecosystem*: The application is one of several products, features or components of a larger platform or DeFi ecosystem.

**Blockchain deployment** (technology). The number of public blockchains on which the DeFi application operates. *Application rule:* If the application is deployed on two or more public blockchains, choose multiple public blockchains. If it is deployed on exactly one public blockchain, choose single public blockchain. If the blockchain is not stated, choose the negation characteristic.

- *Single public blockchain*: The application operates on exactly one public blockchain.
- *Multiple public blockchains*: The application operates on two or more public blockchains.
- *Blockchain not specified*: The sources do not state on which public blockchain the application operates.

**Core mechanism** (technology). The technical mechanism through which the DeFi application executes its financial service in smart contracts. *Application rule:* Choose the first matching characteristic in this order: automated market maker, order book or auction settlement, interest-rate lending market, vault-based strategy automation, other mechanism.

- *Automated market maker*: Trades or liquidity are priced from liquidity pools by an automated market maker formula rather than an order book.
- *Order book or auction settlement*: Trades are settled through an order book, batch auction, Dutch auction or intent-based execution by solvers or fillers.
- *Interest-rate lending market*: Deposited assets are lent in markets whose interest rates are set by supply and demand or by a rate mechanism.
- *Vault-based strategy automation*: User deposits are placed in smart contract vaults that automatically run yield strategies.
- *Other mechanism*: The application uses a mechanism not covered above, such as collateralized stablecoin loans, prize lotteries, insurance pools, liquid staking tokens or rebasing tokens.

**Role in the DeFi stack** (technology). Whether the DeFi application primarily aggregates or optimizes access to other DeFi protocols or provides its own primitive service. *Application rule:* If the application routes trades, deposits or funds to other protocols, or aggregates supply or demand across them, choose aggregator or optimizer. Otherwise choose primitive protocol.

- *Aggregator or optimizer*: The application routes trades, deposits or funds to other DeFi protocols or aggregates their liquidity to offer users better rates or returns.
- *Primitive protocol*: The application provides its own financial service on its own contracts and liquidity rather than mainly routing to other protocols.
