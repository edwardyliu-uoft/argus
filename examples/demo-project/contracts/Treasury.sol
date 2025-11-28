// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./RewardToken.sol";

/**
 * @title Treasury
 * @dev Manages ETH deposits and withdrawals for the reward system
 * Allows users to deposit ETH and earn reward tokens based on their contributions
 */
contract Treasury {
    RewardToken public rewardToken;
    address public owner;

    mapping(address => uint256) public deposits;
    uint256 public totalDeposits;

    event Deposit(address indexed user, uint256 amount);
    event Withdrawal(address indexed user, uint256 amount);
    event RewardClaimed(address indexed user, uint256 rewardAmount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }

    constructor(address _rewardToken) {
        rewardToken = RewardToken(_rewardToken);
        owner = msg.sender;
    }

    /**
     * @dev Deposit ETH into the treasury
     * Users can deposit ETH to participate in the reward program
     */
    function deposit() external payable {
        require(msg.value > 0, "Must deposit non-zero amount");

        deposits[msg.sender] += msg.value;
        totalDeposits += msg.value;

        emit Deposit(msg.sender, msg.value);
    }

    /**
     * @dev Claim deposited funds from the treasury
     * @param amount Amount of ETH to withdraw
     *
     * Allows users to withdraw their deposited ETH
     */
    function claimFunds(uint256 amount) external {
        require(amount > 0, "Amount must be greater than 0");
        require(deposits[msg.sender] >= amount, "Insufficient deposits");

        // Send funds to user
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        // Update user's deposit balance
        deposits[msg.sender] -= amount;
        totalDeposits -= amount;

        emit Withdrawal(msg.sender, amount);
    }

    /**
     * @dev Distribute reward tokens based on user's deposit ratio
     * @param user Address to receive rewards
     *
     * Calculate and mint reward tokens proportional to user's contribution
     */
    function distributeRewards(address user) external onlyOwner {
        require(deposits[user] > 0, "User has no deposits");

        // Calculate reward: 10% of deposited amount (in wei units for simplicity)
        uint256 rewardAmount = (deposits[user] * 10) / 100;

        // Mint reward tokens to user
        rewardToken.mintReward(user, rewardAmount);

        emit RewardClaimed(user, rewardAmount);
    }

    /**
     * @dev Get the deposit balance for a user
     */
    function getDeposit(address user) external view returns (uint256) {
        return deposits[user];
    }

    /**
     * @dev Get total contract balance
     */
    function getTreasuryBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
