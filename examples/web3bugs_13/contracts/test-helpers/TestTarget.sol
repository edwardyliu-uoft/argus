// SPDX-License-Identifier: MIT
pragma solidity 0.8.4;

/**
 * @title TestTarget
 * @dev A simple helper contract for testing NativeMetaTransaction.
 * It has a function that can be called via a meta-transaction and emits
 * the data it receives, allowing tests to assert the outcome.
 */
contract TestTarget {
    event CallReceived(bytes data, uint256 value, address sender);

    /**
     * @dev A dummy function to be the target of a meta-transaction.
     * It is payable to test if msg.value is forwarded correctly.
     * It emits the raw msg.data, msg.value, and msg.sender it receives.
     */
    function doSomething() public payable {
        emit CallReceived(msg.data, msg.value, msg.sender);
    }

    /**
     * @dev A function to allow the owner to withdraw any ETH sent to this contract.
     * Not used in the current tests but is good practice for a contract that can receive ETH.
     */
    function withdraw(address payable to) public {
        to.transfer(address(this).balance);
    }
}
