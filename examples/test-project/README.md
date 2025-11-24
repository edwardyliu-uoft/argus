# SimpleBank

A decentralized banking application built on Ethereum that allows users to deposit and withdraw funds securely.

## Features

- **Deposit Funds**: Users can deposit ETH into their account
- **Withdraw Funds**: Users can withdraw their deposited ETH at any time
- **Balance Tracking**: Track individual user balances
- **Emergency Controls**: Owner can perform emergency withdrawals if needed

## Getting Started

Install dependencies:
```bash
npm install
```

Compile contracts:
```bash
npx hardhat compile
```

Run tests:
```bash
npx hardhat test
```

## Contract Architecture

The SimpleBank contract manages user deposits through a mapping of addresses to balances. All funds are held in the contract and can be withdrawn by users at any time.
