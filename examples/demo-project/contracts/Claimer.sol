// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./Treasury.sol";

/**
 * @title Claimer
 * @dev Helper contract for batch claiming operations
 * Allows automated claiming of funds on behalf of users
 */
contract Claimer {
    Treasury public treasury;
    address public owner;

    event FundsClaimed(address indexed user, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }

    constructor(address _treasury) {
        treasury = Treasury(_treasury);
        owner = msg.sender;
    }

    /**
     * @dev Claim funds from treasury and forward to recipient
     * @param amount Amount to claim from treasury
     * @param recipient Address to receive the claimed funds
     *
     * Useful for automated fund management and distribution
     */
    function claimAndForward(uint256 amount, address payable recipient) external onlyOwner {
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Amount must be greater than 0");

        // Claim funds from treasury
        treasury.claimFunds(amount);

        // Forward to recipient
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "Transfer to recipient failed");

        emit FundsClaimed(recipient, amount);
    }

    /**
     * @dev Deposit ETH into the treasury on behalf of this contract
     */
    function depositToTreasury() external payable {
        require(msg.value > 0, "Must send ETH to deposit");

        // Forward deposit to treasury
        treasury.deposit{value: msg.value}();
    }

    /**
     * @dev Receive function to accept ETH
     */
    receive() external payable {}

    /**
     * @dev Fallback function
     */
    fallback() external payable {}

    /**
     * @dev Get contract balance
     */
    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
