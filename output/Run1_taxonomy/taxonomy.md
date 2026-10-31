# Taxonomy: Decentralized finance (DeFi)

Meta-characteristic: The taxonomy views DeFi applications as financial services built on smart contracts on public blockchains without intermediaries, examined through how they create and deliver value to users (strategy), how they are operated and governed without central intermediaries (organization), and how their underlying blockchain and smart contract technology enables these services (technology).

Status: completed. 

## strategy

| Dimension | Characteristics |
|---|---|
| Primary financial service | Trading and derivatives; Lending and borrowing; Stablecoin issuance; Yield aggregation; Decentralized data storage; Play-to-earn gaming; Prediction and event-outcome markets; Real-world asset tokenization; Insurance and risk coverage; Payments and transfers; Rewards for user activity; Collective funding and investment |
| Token-holder value capture | Fee or revenue distribution to token holders; Token-based trading fee discounts; No holder fee redistribution |
| Target customer segment | Exclusive B2B-focused (conceptual); B2B and B2C (conceptual); B2B, B2C and C2C (conceptual) |

## organization

| Dimension | Characteristics |
|---|---|
| Governance model | Decentralized autonomous organization; Governance-token holder voting; Centralized operator governance (conceptual) |
| Central component for requests and incentives | Central component authorizes requests and incentives; No central component |

## technology

| Dimension | Characteristics |
|---|---|
| Underlying blockchain deployment | Own layer 1 or application chain; Ethereum mainnet; Ethereum layer 2 network; BNB Smart Chain; Other public blockchain |
| Trade matching mechanism | Automated market maker; Order book matching; Aggregated trade routing |
| Stack layer | Protocol layer (conceptual); Application layer (conceptual); Aggregation layer (conceptual); Storage infrastructure layer |
| Oracle data import | Oracle usage (conceptual); No oracle usage (conceptual) |

## Definitions

**Primary financial service** (strategy). The core service that a DeFi application delivers to its users, as stated in the sources. *Application rule:* Observe the main service the application offers. Choose the characteristic that matches that primary service. When several characteristics could apply, prefer prediction and event-outcome markets, then real-world asset tokenization, then insurance and risk coverage, over trading and derivatives.

- *Trading and derivatives*: Exchange of assets or derivative positions, including perpetual futures and synthetic assets.
- *Lending and borrowing*: Supplying assets for interest and borrowing against collateral.
- *Stablecoin issuance*: Issuing a stablecoin against overcollateralized deposits.
- *Yield aggregation*: Providing yield by aggregating returns across automated strategies in vaults.
- *Decentralized data storage*: Providing decentralized storage or retrieval of data, paid with tokens.
- *Play-to-earn gaming*: Earning users value through a blockchain game.
- *Prediction and event-outcome markets*: Users bet on or trade positions on outcomes of real-world events, such as elections or market events, with outcomes resolved through a decentralized process.
- *Real-world asset tokenization*: Real-world or financial assets are represented as blockchain tokens that investors hold or trade, including fractional ownership.
- *Insurance and risk coverage*: Users are covered against risk through pooled endorsements or smart-contract agreements that offer a financial guarantee.
- *Payments and transfers*: The service enables users to send and receive value, such as micropayments, over the network.
- *Rewards for user activity*: Tokens reward users for attention or activity on the platform and compensate publishers.
- *Collective funding and investment*: A community funds projects, public goods or early-stage ventures through collective governance.

**Token-holder value capture** (strategy). How the application passes its fee revenue to holders of its native token. *Application rule:* Observe whether trading fees or revenue are distributed to token holders or whether holders receive fee discounts. Choose the characteristic that matches. Choose the negation characteristic only when the source states that no fees are redistributed.

- *Fee or revenue distribution to token holders*: Trading fees or protocol revenue are distributed to holders of the native or governance token.
- *Token-based trading fee discounts*: Holders of the native token receive trading fee discounts rather than fee distributions.
- *No holder fee redistribution*: Trading fees are never redistributed to token holders.

**Governance model** (organization). How decisions about the application's protocol are made and by whom. *Application rule:* If the entity is organized as a decentralized autonomous organization, choose that characteristic, which takes precedence. Otherwise, if governance token holders vote on the protocol, choose the token-holder voting characteristic.

- *Decentralized autonomous organization*: The entity is organized as a decentralized autonomous organization. This takes precedence over token-holder voting.
- *Governance-token holder voting*: The protocol is governed by holders of its governance token, who vote on proposals.
- *Centralized operator governance*: Operators alone have the right to make changes to the service, and users have no say.

**Central component for requests and incentives** (organization). Whether a central component authorizes requests and handles incentives in the application. *Application rule:* Observe whether a central component, such as satellite nodes, authorizes requests and handles incentivization. Choose the negation characteristic when the source states that authentication or operation relies on no centralized component.

- *Central component authorizes requests and incentives*: A central component, such as satellite nodes, authorizes requests and handles incentivization.
- *No central component*: Authentication or operation follows a mechanism that relies on no centralized component.

**Underlying blockchain deployment** (technology). The blockchain on which the application runs. *Application rule:* Observe the blockchain on which the application operates. If it runs on its own Layer 1 or application chain, choose that characteristic, which takes precedence. Otherwise choose the Ethereum mainnet, Ethereum layer 2 or BNB Smart Chain characteristic that matches.

- *Own layer 1 or application chain*: The application runs on its own layer 1 blockchain or application chain. This takes precedence over the other deployments.
- *Ethereum mainnet*: The application operates on the Ethereum blockchain.
- *Ethereum layer 2 network*: The application runs on a layer 2 network built on Ethereum, such as Arbitrum, Optimism, Base or StarkEx.
- *BNB Smart Chain*: The application operates on the BNB Smart Chain public blockchain.
- *Other public blockchain*: The application runs on a public blockchain that is neither its own layer 1 or application chain, Ethereum, an Ethereum layer 2 network nor BNB Smart Chain.

**Trade matching mechanism** (technology). How trades are priced and matched in the application. *Application rule:* If prices come from an automated market maker, a virtual AMM or a shared liquidity pool acting as counterparty, choose the automated market maker characteristic, which takes precedence. Otherwise, if trades are matched in an order book, choose the order book characteristic. Otherwise, if trades are routed across several external exchanges, choose aggregated trade routing.

- *Automated market maker*: Trades are priced and executed by an automated market maker or liquidity pool. This takes precedence over order matching.
- *Order book matching*: Trades are matched through an order book, on-chain or off-chain, without an automated market maker as the pricing mechanism.
- *Aggregated trade routing*: Trades are routed across several external decentralized exchanges to find favorable prices.

**Target customer segment** (strategy). The customer groups a DeFi service serves, from exclusive B2B focus to business and consumer segments, including peer-to-peer trading between users. *Application rule:* Observe which customer groups the service serves. Choose 'Exclusive B2B-focused' if it serves only other DeFi service providers and companies. Choose 'B2B and B2C' if it also serves private consumers. Choose 'B2B, B2C and C2C' if users also trade with each other.

- *Exclusive B2B-focused*: The service is offered to other DeFi service providers and companies.
- *B2B and B2C*: The service is offered to private consumers, businesses and other DeFi providers.
- *B2B, B2C and C2C*: The service is offered to businesses and consumers, and enables trading of tokens between consumers.

**Stack layer** (technology). The layer of the hierarchical, multi-layer DeFi architecture on which a service is positioned. *Application rule:* Observe where the service sits in the architecture. Choose 'Protocol layer' if it defines standards for applications. Choose 'Application layer' if it is built on top of individual protocols to simplify user access. Choose 'Aggregation layer' if it bundles several applications and protocols into one access point.

- *Protocol layer*: DeFi protocols that define standards for applications such as decentralized exchanges or lending and borrowing services.
- *Application layer*: DeFi services built on top of individual protocols of the protocol layer, simplifying user access to DeFi services.
- *Aggregation layer*: DeFi services that bundle several applications and protocols to give users easy access to multiple DeFi services.
- *Storage infrastructure layer*: Decentralized storage or retrieval infrastructure that other services use, paid with tokens.

**Oracle data import** (technology). Whether external data can flow into the blockchain ecosystem through oracles. *Application rule:* Observe whether the service uses oracles to import external data into the blockchain network. Choose 'Oracle usage' if it does. Choose 'No oracle usage' if the source states that it uses no oracles.

- *Oracle usage*: The service uses oracles to import external data into the blockchain network.
- *No oracle usage*: The service uses no oracles, so data cannot flow from the outside world into the blockchain ecosystem.
