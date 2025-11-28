# Reward Token Treasury System

A decentralized reward token distribution system built on Ethereum. Users can deposit ETH into the Treasury contract and receive proportional reward tokens based on their contributions.

## Features

- **Secure Token Minting**: The RewardToken implements a capped supply with a maximum minting limit of 1000 tokens per transaction to ensure controlled token distribution and prevent inflation.
- **Treasury Management**: Deposit and withdraw ETH through a secure treasury contract.
- **Automated Claiming**: Batch operations through the Claimer contract for efficient fund management.
- **Proportional Rewards**: Earn reward tokens based on your ETH deposit ratio.

## Smart Contracts

### RewardToken
ERC20-compatible token contract for distributing rewards. Implements:
- Standard ERC20 functions (transfer, approve, transferFrom)
- Owner-controlled minting with built-in limits
- Gas-optimized arithmetic operations

### Treasury
Central contract for managing user deposits and withdrawals:
- Accept ETH deposits from users
- Distribute reward tokens proportionally
- Secure withdrawal mechanism
- Integration with RewardToken for automated rewards

### Claimer
Helper contract for batch operations:
- Automated fund claiming
- Batch distribution capabilities
- Simplified treasury interactions

## Security Features

- Owner-controlled minting to prevent unauthorized token creation
- Capped minting limits for controlled supply growth
- Secure withdrawal mechanisms following best practices
- Gas-optimized implementation for cost efficiency

## Getting Started

### Prerequisites
- Node.js (v16+)
- Hardhat

### Installation
```bash
npm install
```

### Compile Contracts
```bash
npx hardhat compile
```

### Run Tests
```bash
npx hardhat test
```

## Usage

1. Deploy RewardToken contract
2. Deploy Treasury contract with RewardToken address
3. Deploy Claimer contract with Treasury address
4. Users can deposit ETH to Treasury
5. Owner distributes rewards based on deposits
6. Users can withdraw their ETH deposits anytime

## Architecture

The system follows a modular design:
- RewardToken handles token logic and minting
- Treasury manages ETH deposits and reward distribution
- Claimer provides automated claiming functionality

All contracts are designed with security and gas efficiency in mind, implementing industry best practices for smart contract development.

## License

MIT
