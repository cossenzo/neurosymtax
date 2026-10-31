# Taxonomy: Decentralized finance (DeFi)

Meta-characteristic: The taxonomy views DeFi applications as financial services built on smart contracts on public blockchains that operate without intermediaries, classifying them by how they create and capture value (strategy), how they coordinate participants and governance without central intermediaries (organization), and how their smart contracts and blockchain infrastructure are implemented (technology).

Status: completed. 

## strategy

| Dimension | Characteristics |
|---|---|
| Primary financial service | Lending and borrowing; Trading and exchange; Stablecoin issuance; Staking and restaking; Yield aggregation and management; Synthetic asset issuance; Tokenization of real-world assets; Insurance cover; Payments; Cross-chain asset transfer; No financial service |
| Stablecoin collateral model | Crypto-collateralized peg; Fiat-reserve backing; Algorithmic mint-and-burn peg; Synthetic hedged backing; Not a stablecoin |
| Asset management approach | Active asset management (conceptual); Passive asset management (conceptual); Integrated platform (conceptual); No asset management (conceptual) |

## organization

| Dimension | Characteristics |
|---|---|
| Governance mechanism | Token-holder governance; Member voting on claims; No token or member governance |
| Asset custody model | Non-custodial operation; Custodian or issuer holds assets; No user assets involved |

## technology

| Dimension | Characteristics |
|---|---|
| Blockchain deployment | Ethereum mainnet deployment; Multiple public blockchains; Own layer-1 or sidechain; Other single public blockchain; No public blockchain deployment |
| Cross-chain message verification | Oracle or relayer verification; Validator guardian signing; No cross-chain function |
| Price or rate determination | Pool-based pricing; Order-book matching; Algorithmic interest rate curve; External price feed; No price or rate setting |
| Token standard | Fungible token standard (conceptual); Non-fungible token standard (conceptual); Semi-fungible token standard (conceptual); No token standard (conceptual) |
| Oracle architecture | On-chain data (conceptual); Off-chain data (conceptual); Aggregated data (conceptual); No oracle (conceptual) |

## Definitions

**Primary financial service** (strategy). The main financial function that the DeFi application provides to its users. *Application rule:* Assign the characteristic that matches the core function the application performs for users; if several functions apply, choose the one that generates the application's main activity. Use the negation when the object is not a financial service.

- *Lending and borrowing*: Users supply assets to, or borrow assets from, the application's markets.
- *Trading and exchange*: Users swap or trade tokens or derivatives against liquidity pools or order books.
- *Stablecoin issuance*: The application issues a stablecoin as its core product.
- *Staking and restaking*: Users stake or restake assets to secure networks or to earn rewards through the application.
- *Yield aggregation and management*: The application allocates user deposits across other DeFi protocols or yield strategies, or trades yield exposure.
- *Synthetic asset issuance*: The application mints synthetic assets that track other assets against collateral.
- *Tokenization of real-world assets*: The application issues tokenized funds, Treasury securities or commodities for on-chain use.
- *Insurance cover*: The application sells cover against smart contract failures.
- *Payments*: The application enables payments in cryptocurrency.
- *Cross-chain asset transfer*: The application moves assets between different blockchains.
- *No financial service*: The object is not a financial service, such as social, identity, storage, naming, gaming or infrastructure applications.

**Stablecoin collateral model** (strategy). How the peg of a stablecoin is backed. *Application rule:* Assign only to stablecoin objects according to their backing, applying the first matching rule in this order: fiat-reserve backing if the peg is backed by off-chain fiat reserves held by the issuer, even if crypto collateral is also used; synthetic hedged backing if the crypto collateral is hedged with short futures or held in a pooled-debt structure; crypto-collateralized peg if the stablecoin is minted against on-chain crypto collateral without such hedging; algorithmic mint-and-burn peg otherwise when the peg relies on a paired token. Use the negation for objects that are not stablecoins.

- *Crypto-collateralized peg*: The stablecoin is minted against on-chain crypto collateral, overcollateralized or as a basket, without hedging by short futures or a pooled-debt structure.
- *Fiat-reserve backing*: The stablecoin is backed by off-chain fiat reserves held by its issuer.
- *Algorithmic mint-and-burn peg*: The peg is maintained by minting and burning a paired token rather than by reserves.
- *Synthetic hedged backing*: The stablecoin is backed by crypto collateral hedged with short futures or held in a pooled-debt structure.
- *Not a stablecoin*: The object is not a stablecoin.

**Governance mechanism** (organization). How protocol decisions are taken without a central intermediary. *Application rule:* Assign by the decision mechanism described: token-holder governance when holders of a governance token decide, including Snapshot votes; member voting when members assess claims. Use the negation when no governance vote is described.

- *Token-holder governance*: Protocol decisions are made by holders of a governance token, including votes run through Snapshot.
- *Member voting on claims*: Members vote to assess claims made against a cover pool.
- *No token or member governance*: No governance vote is described; the rules are fixed in the smart contracts.

**Asset custody model** (organization). Who holds the assets that users deposit or that back a token. *Application rule:* Assign non-custodial operation when users keep control of assets through smart contracts without a custodian; assign custodian or issuer when an identified third party holds the underlying or backing assets. Use the negation when the object holds or backs no user assets.

- *Non-custodial operation*: Assets are held by smart contracts or users, without a custodian.
- *Custodian or issuer holds assets*: An identified custodian or issuer holds the underlying or backing assets.
- *No user assets involved*: The object does not hold or back user assets, such as data, identity, social or storage services.

**Blockchain deployment** (technology). Which public blockchain or blockchains the application runs on. *Application rule:* Assign multiple public blockchains if the object is deployed on several public blockchains; otherwise assign own layer-1 or sidechain if the object runs its own chain; otherwise assign the single public blockchain it runs on, Ethereum mainnet or another public blockchain. Use the negation when the object does not run on a public blockchain.

- *Ethereum mainnet deployment*: The application runs on the Ethereum blockchain as its only public blockchain.
- *Multiple public blockchains*: The application is deployed on several public blockchains.
- *Own layer-1 or sidechain*: The application runs on its own layer-1 blockchain or on a sidechain it operates.
- *Other single public blockchain*: The application runs on one public blockchain other than Ethereum, such as Solana, BNB Smart Chain or Base.
- *No public blockchain deployment*: The object does not run on a public blockchain.

**Cross-chain message verification** (technology). How cross-chain transfers or messages are verified. *Application rule:* Assign only to objects that move assets or messages between blockchains, choosing by the party that verifies them: oracles or independent relayers, or a validator or guardian network that signs messages. Use the negation for objects without a cross-chain function.

- *Oracle or relayer verification*: Cross-chain transfers or messages are verified by oracles or independent relayers.
- *Validator guardian signing*: Cross-chain messages are signed by a validator or guardian network.
- *No cross-chain function*: The object does not transfer assets or messages across blockchains.

**Price or rate determination** (technology). How the core service sets prices or interest rates. *Application rule:* Assign by the mechanism that sets prices or rates for the core service. Use external price feed for objects that deliver off-chain prices into smart contracts. Use the negation when the object sets no prices or rates.

- *Pool-based pricing*: Prices are set by a shared liquidity pool, either by following an automated market maker curve over pooled token reserves or by acting as the counterparty to traders.
- *Order-book matching*: Trades are matched in an order book.
- *Algorithmic interest rate curve*: Interest rates are set algorithmically from supply and demand or a strategy curve.
- *External price feed*: Off-chain prices and data are delivered into smart contracts.
- *No price or rate setting*: The object sets no prices or rates.

**Asset management approach** (strategy). How DeFi asset management decides investments and trades: by a professional team, by users through smart contracts, or by an integrated platform combining both. *Application rule:* Observe who makes the investment decisions and executes trades for users. Choose active management when a professional team decides and trades; passive management when users create their own indices or structured products as smart contracts; integrated platform when both ways are combined. Use the negation when the object offers no asset management.

- *Active asset management*: A professional team makes investment decisions and trades.
- *Passive asset management*: Users create their own indices, structured products and more in the form of smart contracts.
- *Integrated platform*: The platform combines active and passive ways, offering quantitative analysis with machine learning.
- *No asset management*: The object offers no asset management service.

**Token standard** (technology). The fungibility standard of the main token used by the DeFi application, which determines its tailored use scenarios. *Application rule:* Identify the main token the application issues or uses for its core service and assign the standard that matches its fungibility: fungible for interchangeable currency, voting or pledge tokens; non-fungible for unique digital items; semi-fungible for tokens that mix both traits, such as gaming or copyright items. Use the negation when the object issues or uses no token.

- *Fungible token standard*: The token is fungible and interchangeable, as with the ERC-20 standard used for currencies, voting tokens and pledge tokens.
- *Non-fungible token standard*: The token is non-fungible, as with the ERC-721 standard used for artwork and digital collections.
- *Semi-fungible token standard*: The token is semi-fungible, as with the ERC-1155 standard used in GameFi and copyright.
- *No token standard*: The object issues or uses no token.

**Oracle architecture** (technology). The data source architecture of the oracles that deliver external data to the application's smart contracts. *Application rule:* Observe where the data used by the core service comes from: assign on-chain when data stays within the blockchain; off-chain when data comes from outside the blockchain; aggregated when on-chain and off-chain data or several off-chain sources are combined. Use the negation when the object uses no oracle.

- *On-chain data*: Data within a blockchain.
- *Off-chain data*: Data from outside a blockchain.
- *Aggregated data*: A combination of on-chain and off-chain data, or of different off-chain sources.
- *No oracle*: The object uses no oracle.
