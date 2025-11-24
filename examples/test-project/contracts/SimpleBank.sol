// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title SimpleBank
 * @dev A simple bank contract for managing deposits and withdrawals
 */
contract SimpleBank {
    mapping(address => uint256) public balances;
    address public owner;

    event Deposit(address indexed user, uint256 amount);
    event Withdrawal(address indexed user, uint256 amount);

    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Deposit funds into the bank
     */
    function deposit() public payable {
        require(msg.value > 0, "Deposit amount must be greater than 0");
        balances[msg.sender] += msg.value;
        emit Deposit(msg.sender, msg.value);
    }

    /**
     * @dev Withdraw funds from the bank
     * @param amount The amount to withdraw
     */
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // Transfer funds to user
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        // Update balance
        balances[msg.sender] -= amount;
        emit Withdrawal(msg.sender, amount);
    }

    /**
     * @dev Get balance of an account
     */
    function getBalance(address account) public view returns (uint256) {
        return balances[account];
    }

    /**
     * @dev Emergency withdrawal function for contract maintenance
     */
    function emergencyWithdraw() public {
        uint256 balance = address(this).balance;
        (bool success, ) = msg.sender.call{value: balance}("");
        require(success, "Emergency withdrawal failed");
    }

    /**
     * @dev Get total contract balance
     */
    function getContractBalance() public view returns (uint256) {
        return address(this).balance;
    }
}
