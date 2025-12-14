// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MockTreasury
 * @dev A mock Treasury contract for testing the Claimer contract in isolation.
 * This allows for precise control over the Treasury's behavior during tests.
 */
contract MockTreasury {
    mapping(address => uint256) public deposits;

    /**
     * @dev This function is intentionally left empty to simulate a scenario
     * where it only performs an accounting update and does not transfer ETH.
     * This is crucial for testing the fund drain vulnerability in Claimer, where
     * Claimer.claimAndForward sends its own balance regardless of what this function does.
     */
    function claimFunds(uint256 amount) external {
        // In a real scenario, this might check a balance and decrement it.
        // For the test, we only need it to exist and not revert.
        // It does NOT send ETH back to the caller (msg.sender).
    }

    /**
     * @dev Accept deposits to mimic the real Treasury's behavior and track them.
     */
    function deposit() external payable {
        deposits[msg.sender] += msg.value;
    }
}
