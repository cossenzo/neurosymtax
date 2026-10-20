# Taxonomy: Decentralized finance (DeFi)

Meta-characteristic: DeFi applications viewed as financial services delivered through smart contracts on public blockchains without intermediaries, examined as strategic value-creation and business model choices, organizational arrangements, and technological design features.

Status: completed. 

## strategy

| Dimension | Characteristics |
|---|---|
| Primary financial service | Lending and borrowing; Stablecoin issuance; Trading and exchange; Derivatives and yield trading; Yield optimization and aggregation; Liquid staking; Cross-chain transfer; Oracle and data infrastructure; Insurance and risk coverage; Prediction markets; Real-world asset tokenization; Blockchain platform or network; Off-chain payment channels; Collective investment fund; Wallet and key management interface; Security and monitoring tooling; No smart-contract delivery without intermediaries |
| Fee model | Fee on interest or returns; No default protocol fee; One-off transaction or origination fee |

## organization

| Dimension | Characteristics |
|---|---|
| Parameter control | Token-holder votes; Executive votes of governance system; Curator-set allocation and risk; Council or consortium control |
| Asset custody arrangement | Non-custodial user control; Delegated vault management; Custody by decentralized node network |
| Operating status | Actively operating; Ceased operation |
| Investor access restriction | Restricted to accredited or institutional investors; Open to retail users |

## technology

| Dimension | Characteristics |
|---|---|
| Blockchain deployment | Multi-chain deployment; Layer 2 or application chain; Single layer 1 blockchain |
| Position representation | Tokenized receipt for deposits or stake; Position held in protocol contracts |
| Risk and liquidity isolation | Isolated risk per market or vault; Shared liquidity layer |
| Security incident history | Prior exploit or security incident; No recorded exploit or incident |
| Oracle usage | Oracle usage (conceptual); No oracle usage (conceptual) |
| Consensus mechanism | Proof-of-stake consensus; Proof-of-work consensus; Other consensus mechanism |
| Stablecoin peg mechanism | Fiat reserve backing; Overcollateralized collateral backing; Arbitrage-based algorithmic peg; Delta-neutral hedged backing; No stablecoin peg mechanism |

## Definitions

**Primary financial service** (strategy). The financial service that the DeFi application mainly delivers to its users. *Application rule:* Choose the service that generates most of the user interactions described in the passages; if several services apply, the primary one decides. Where characteristics overlap, apply this precedence: a blockchain platform or network is chosen only where the application is itself the chain on which others build; a wallet and key management interface is chosen only where no pooling, lending, trading, derivatives, yield, staking, transfer or insurance service is delivered; a security and monitoring tool, an oracle and data infrastructure, or an insurance and risk coverage service is chosen only where that tooling or cover is the main service rather than an incidental feature of a financial service; a yield optimization and aggregation service is chosen only where deposits are routed by vaults or optimizers into strategies rather than lent, borrowed or traded directly; a liquid staking service is chosen only where staked assets are represented by receipt tokens.

- *Lending and borrowing*: The application mainly provides lending, borrowing or savings-rate deposits backed by loans.
- *Stablecoin issuance*: The application mainly issues a stablecoin against collateral deposited by users.
- *Trading and exchange*: The application mainly exchanges tokens through liquidity pools, order books or aggregated routes.
- *Derivatives and yield trading*: The application mainly offers perpetual futures, fixed-rate trading or trading of yield tokens.
- *Yield optimization and aggregation*: Deposits are routed by vaults or optimizers into yield strategies.
- *Liquid staking*: Staked assets are represented by tradable or usable receipt tokens.
- *Cross-chain transfer*: The application mainly moves assets or messages between public blockchains.
- *Oracle and data infrastructure*: The application mainly supplies external data or tooling to smart contracts.
- *Insurance and risk coverage*: The application mainly sells or pools cover against losses or smart-contract risk.
- *Prediction markets*: The application mainly lets users trade on the outcomes of real-world events.
- *Real-world asset tokenization*: The application mainly represents off-chain real-world assets, such as treasury exposure or property, as tokens on a blockchain.
- *Blockchain platform or network*: The application is itself a blockchain or network infrastructure on which others build services, rather than a financial service built on one.
- *Off-chain payment channels*: The application mainly routes payments through off-chain payment channels that are settled on a blockchain.
- *Collective investment fund*: The application mainly pools participants' capital in a smart contract to invest it.
- *Wallet and key management interface*: The application mainly lets users hold, access or manage their own keys and assets, rather than providing a financial service that pools, lends or trades funds.
- *Security and monitoring tooling*: The application mainly provides security tools that monitor, patch or protect smart contracts against exploits.
- *No smart-contract delivery without intermediaries*: The service is operated by a centralized company or exchange acting as intermediary, so it is not delivered by smart contracts without intermediaries.

**Fee model** (strategy). Whether the application charges a protocol, performance or management fee by default. *Application rule:* If a share of interest or yield is taken as protocol, performance or management fee, choose fee on interest or returns; otherwise, if a one-off fee is charged per transaction or loan origination, choose one-off transaction or origination fee; otherwise choose no default protocol fee.

- *Fee on interest or returns*: The application takes a share of interest or yield as protocol, performance or management fee.
- *No default protocol fee*: The application charges no exchange or protocol fee by default.
- *One-off transaction or origination fee*: The application charges a one-time fee on transactions or on loan origination by default, and takes no share of interest or returns.

**Parameter control** (organization). Who sets the protocol parameters of the application. *Application rule:* Choose the actor that sets the protocol parameters as described in the passages; token-holder votes apply where governance tokens decide parameters.

- *Token-holder votes*: Protocol parameters are set by votes of holders of a native governance token.
- *Executive votes of governance system*: Parameters are set through executive votes of an associated governance system.
- *Curator-set allocation and risk*: Curators set the allocation of deposits and the risk parameters of vaults.
- *Council or consortium control*: Protocol parameters are set by a fixed council or consortium of members rather than by votes of token holders.

**Asset custody arrangement** (organization). Whether users keep direct control of their assets or delegate them to managed vaults. *Application rule:* If deposits are pooled into vaults or strategies that allocate funds on the user's behalf, choose delegated vault management; otherwise, if assets are held by a decentralized network of nodes, choose custody by decentralized node network; otherwise choose non-custodial user control.

- *Non-custodial user control*: Users keep control of their own assets or positions without a custodian.
- *Delegated vault management*: Deposits are pooled into vaults or strategies that allocate funds on behalf of users.
- *Custody by decentralized node network*: Assets are held on users' behalf by a decentralized network of nodes rather than by users directly or by managed vaults.

**Operating status** (organization). Whether the application is still operating. *Application rule:* Choose ceased operation only where the passages state that the application stopped operating.

- *Actively operating*: The application is in operation as described in the passages.
- *Ceased operation*: The application stopped operating.

**Blockchain deployment** (technology). The public blockchain arrangement on which the application runs. *Application rule:* If the application runs on several blockchains, choose multi-chain deployment; else if it runs on a layer 2 or its own application chain, choose that; otherwise choose a single layer 1 blockchain.

- *Multi-chain deployment*: The application runs across multiple public blockchains.
- *Layer 2 or application chain*: The application runs on a layer 2 scaling solution or its own application chain.
- *Single layer 1 blockchain*: The application runs on one public layer 1 blockchain such as Ethereum or Solana.

**Position representation** (technology). Whether user deposits or stakes are represented by a tokenized receipt. *Application rule:* Choose tokenized receipt where the passages state that a transferable token represents the deposit or stake; otherwise choose positions held in protocol contracts.

- *Tokenized receipt for deposits or stake*: A transferable receipt token represents supplied assets or staked assets.
- *Position held in protocol contracts*: Positions are recorded in the protocol's own contracts without a separate receipt token.

**Risk and liquidity isolation** (technology). Whether risk and liquidity are isolated per market or vault or shared across a common layer. *Application rule:* Choose isolated risk where each market or vault has its own risk boundary; choose shared liquidity where markets draw on a common liquidity layer.

- *Isolated risk per market or vault*: Each market, silo or vault has its own risk boundary so that failures do not spread.
- *Shared liquidity layer*: Lending and trading components draw on a common liquidity layer or shared vault architecture.

**Security incident history** (technology). Whether the application has suffered an exploit or security incident. *Application rule:* Choose prior exploit or security incident where the passages report one; choose the negation where none is stated.

- *Prior exploit or security incident*: The application suffered an exploit or security incident reported in the passages.
- *No recorded exploit or incident*: The passages record no exploit or security incident for the application.

**Oracle usage** (technology). Whether the application uses oracles to import data from outside the blockchain or to link blockchains. *Application rule:* Choose oracle usage where the passages state that the application imports external data into a blockchain or establishes interoperability between blockchains through oracles; choose no oracle usage where the passages state that the application does not use oracles; record no_information where the passages are silent.

- *Oracle usage*: DeFi services that use oracles to import external data into a blockchain network or to establish interoperability between blockchains.
- *No oracle usage*: DeFi services that do not use oracles, so data does not flow in from outside the blockchain ecosystem.

**Consensus mechanism** (technology). The consensus mechanism by which the underlying blockchain or network validates transactions. *Application rule:* Choose the consensus mechanism the passages state for the underlying blockchain or network; choose proof-of-stake for delegated proof-of-stake and validator-set variants; choose other consensus mechanism for any other stated mechanism; record no_information where the passages are silent.

- *Proof-of-stake consensus*: Transactions are validated through proof-of-stake, including delegated proof-of-stake and validator-set variants.
- *Proof-of-work consensus*: Transactions are validated through proof-of-work mining.
- *Other consensus mechanism*: Transactions are validated through a stated mechanism that is neither proof-of-stake nor proof-of-work, such as federated Byzantine agreement or gossip-based ledger timestamping.

**Stablecoin peg mechanism** (technology). The mechanism by which a stablecoin maintains its peg to a reference value. *Application rule:* Choose the mechanism the passages state for the stablecoin's peg: fiat reserve backing where fully backed by audited fiat reserves; overcollateralized collateral backing where collateral exceeds the issued amount; arbitrage-based algorithmic peg where a native token is burned and minted; delta-neutral hedged backing where collateral is hedged by short perpetual positions without overcollateralization; otherwise choose no stablecoin peg mechanism.

- *Fiat reserve backing*: The stablecoin is fully backed by fiat reserves that are audited.
- *Overcollateralized collateral backing*: The peg is secured by collateral deposited in excess of the issued amount, including centralized stablecoins accepted as collateral.
- *Arbitrage-based algorithmic peg*: The peg is maintained through arbitrage, with a native token burned and minted to keep the stablecoin at its reference value.
- *Delta-neutral hedged backing*: Collateral reserves are hedged by short perpetual-type positions without leverage, and the peg holds without overcollateralization.
- *No stablecoin peg mechanism*: The application does not issue a stablecoin or maintain a stablecoin peg.

**Investor access restriction** (organization). Whether access to the application is restricted to qualified investors or open to retail users. *Application rule:* Choose restricted to accredited or institutional investors where the passages state that access requires accredited or institutional status or KYC checks; otherwise choose open to retail users where the passages state retail targeting or open participation.

- *Restricted to accredited or institutional investors*: Access is limited to accredited, institutional or qualified investors who pass identity and capital checks.
- *Open to retail users*: The application is aimed at retail users or has no participation limits for users.
