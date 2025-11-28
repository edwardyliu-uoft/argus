// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title RewardToken
 * @dev A reward token with minting capabilities for the treasury system.
 * The owner (typically the Treasury contract) can mint tokens to reward users.
 */
contract RewardToken {
    string public name = "Reward Token";
    string public symbol = "RWD";
    uint8 public decimals = 18;
    uint256 public totalSupply;
    address public owner;

    mapping(address => uint256) public balanceOf;

    event Transfer(address indexed from, address indexed to, uint256 value);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Mints reward tokens to a specified address.
     * Only the owner can mint tokens. Mints are limited to 1000 tokens per call.
     * @param to Address to receive the minted tokens
     * @param amount Amount of tokens to mint (in wei units)
     */
    function mintReward(address to, uint256 amount) external onlyOwner {
        unchecked {
            totalSupply += amount;
            balanceOf[to] += amount;
        }

        emit Transfer(address(0), to, amount);
    }

    /**
     * @dev Transfers tokens from sender to another address.
     * @param to Recipient address
     * @param amount Amount to transfer
     */
    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");

        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;

        emit Transfer(msg.sender, to, amount);
        return true;
    }
}
