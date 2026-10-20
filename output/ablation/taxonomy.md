# Taxonomy: Decentralized finance (DeFi)

Meta-characteristic: DeFi applications viewed as financial services delivered by smart contracts on public blockchains without intermediaries, examined through how they create value and business models (strategy), how they are operated and governed (organization), and how they are technically implemented (technology).

Status: completed. 

## strategy

| Dimension | Characteristics |
|---|---|
| Primary financial service | Lending and borrowing; Trading and exchange; Derivatives and synthetic assets; Stablecoin issuance; Insurance and risk coverage; Yield optimization; Payments, streaming and asset management; Prediction markets and gambling; Analytics, aggregation and wallet interfaces; No standalone financial service; no_information: service |
| Target user group | Institutional investors; no_information: user group |

## organization

| Dimension | Characteristics |
|---|---|
| Governance and operating model | Company-operated or centralized; Token-holder governance; Multi-party governance; Autonomous operation without stated governance; no_information: governance |
| Custody of user assets | Non-custodial; Custodial; no_information: custody |

## technology

| Dimension | Characteristics |
|---|---|
| Technical role | End-user financial application; Infrastructure component; Security and monitoring tool; no_information: technical role |
| Blockchain deployment | Ethereum; Binance Smart Chain; Other single public blockchain; Multiple blockchains; no_information: blockchain |
| Price formation mechanism | Automated market maker pools; Order book; External oracle price input; No price-setting mechanism; no_information: price mechanism |
| Asset custody of blockchain bridges | Centralized bridge (conceptual); Decentralized bridge (conceptual); No bridge: object is not a blockchain bridge (conceptual); no_information: bridge custody (conceptual) |

## Definitions

**Primary financial service** (strategy). The main financial service that the DeFi application offers to its users, as stated in its description. *Application rule:* Observe the financial service the application primarily offers. If several services are offered, the primary one decides. Use the no_information characteristic only when the sources state no service.

- *Lending and borrowing*: Users lend or borrow crypto assets, with collateral or via flash loans, without intermediaries.
- *Trading and exchange*: Users swap or trade crypto assets through the application.
- *Derivatives and synthetic assets*: Users trade options, futures or tokens that track other assets.
- *Stablecoin issuance*: The application issues a stablecoin backed by collateral or by an algorithm.
- *Insurance and risk coverage*: The application covers risks such as smart contract failures, wallet theft or collateral price changes.
- *Yield optimization*: The application aggregates or automates yield farming and vault strategies across other protocols.
- *Payments, streaming and asset management*: The application provides payment streams, tokenized baskets or asset management.
- *Prediction markets and gambling*: The application offers prediction markets or gambling on outcomes.
- *Analytics, aggregation and wallet interfaces*: The application analyses, aggregates or displays DeFi data and positions without executing financial transactions itself.
- *No standalone financial service*: The object does not on its own provide a financial service, for example a token or a script product.
- *no_information: service*: The sources do not state the financial service offered.

**Target user group** (strategy). The user group that the DeFi application addresses with its services. *Application rule:* Observe which user group the application explicitly addresses. Use no_information when the sources do not state it.

- *Institutional investors*: The application offers a service specifically for institutional investors.
- *no_information: user group*: The sources do not state the target user group.

**Governance and operating model** (organization). Who operates and steers the DeFi application. *Application rule:* Observe whether a company or centralized intermediary operates the application (this takes precedence), otherwise whether token holders govern it by vote, otherwise whether multiple named parties govern it, otherwise whether the application runs autonomously without stated governance. Use no_information when nothing is stated.

- *Company-operated or centralized*: The application is operated by a company or centralized intermediary rather than purely by smart contracts.
- *Token-holder governance*: The application is governed by holders of its governance token through voting.
- *Multi-party governance*: The application is governed by multiple parties without token-holder voting.
- *Autonomous operation without stated governance*: The application runs through smart contracts without a stated governing body.
- *no_information: governance*: The sources do not state how the application is operated or governed.

**Custody of user assets** (organization). Whether the application holds the assets of its users. *Application rule:* Observe whether a custodian holds user assets in accounts or whether users keep control of their own assets in their wallets or in smart contracts. Use no_information when the sources are silent.

- *Non-custodial*: Users keep control of their own assets and no intermediary holds them.
- *Custodial*: An intermediary company holds customer deposits and assets.
- *no_information: custody*: The sources do not state who holds the user assets.

**Technical role** (technology). The role that the object plays in the technical landscape of DeFi. *Application rule:* Observe whether the object is an end-user financial application, a supporting infrastructure component (oracle, bridge, sidechain, scaling, interoperability) or a security and monitoring tool. Use no_information when the sources do not state it.

- *End-user financial application*: The object is a financial application used directly by end users.
- *Infrastructure component*: The object supplies oracle data, bridging, sidechain, scaling or interoperability services to other applications.
- *Security and monitoring tool*: The object detects, prevents or repairs vulnerabilities or attacks in smart contracts.
- *no_information: technical role*: The sources do not state the technical role.

**Blockchain deployment** (technology). The public blockchain on which the DeFi application runs. *Application rule:* Observe the public blockchain named for the application. Use multiple blockchains when the application spans more than one chain. Use no_information when no blockchain is stated.

- *Ethereum*: The application runs on the Ethereum blockchain or its Layer 2 or sidechain as its main deployment.
- *Binance Smart Chain*: The application runs on the Binance Smart Chain (BNB Chain).
- *Other single public blockchain*: The application runs on one other public blockchain, such as EOS, Fantom, TRON, Cosmos-based Terra or Polygon.
- *Multiple blockchains*: The application connects or operates across several public blockchains.
- *no_information: blockchain*: The sources do not state the blockchain on which the application runs.

**Price formation mechanism** (technology). How the application sets or obtains the prices of the assets it handles. *Application rule:* For trading venues observe the price mechanism of the venue (automated market maker takes precedence over order book). For applications that use external price data, use the oracle characteristic. If the application uses no price mechanism, use the negation characteristic. Use no_information when the sources are silent.

- *Automated market maker pools*: Prices are set by liquidity pools using an automated market maker model.
- *Order book*: Trades are matched through an on-chain or off-chain order book.
- *External oracle price input*: Asset prices are taken from external oracle feeds for lending, collateral or settlement.
- *No price-setting mechanism*: The application neither sets prices by pools or order books nor takes external price feeds.
- *no_information: price mechanism*: The sources do not state how prices are formed.

**Asset custody of blockchain bridges** (technology). Whether a blockchain bridge has a centralized custodian that tracks transactions or stores assets through a smart contract without third parties. *Application rule:* Observe whether the object is a blockchain bridge. If it is, observe whether a centralized custodian (keeper) tracks the transactions, or whether assets are stored through a smart contract with no third party involved. If the object is not a blockchain bridge, use the negation characteristic. Use no_information when the sources are silent on the custody of a bridge.

- *Centralized bridge*: A bridge with a centralized custodian (keeper) that tracks transactions.
- *Decentralized bridge*: A bridge in which assets are stored on the basis of a smart contract and no third parties are involved.
- *No bridge: object is not a blockchain bridge*: The object is not a blockchain bridge, so bridge custody does not apply to it.
- *no_information: bridge custody*: The sources do not state how a blockchain bridge holds its assets.
