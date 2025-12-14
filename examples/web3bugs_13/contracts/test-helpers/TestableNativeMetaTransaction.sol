// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.4;

import "../NativeMetaTransaction.sol";

// This helper contract inherits from NativeMetaTransaction to expose internal state/functions for testing.
contract TestableNativeMetaTransaction is NativeMetaTransaction {

    // Call the EIP712Base constructor to set up the domain separator, which is missing in the base contract
    constructor() EIP712Base("TestableNativeMetaTransaction", "1") {}

    address public lastSender;
    uint256 public lastValue;

    /**
     * @dev A target function to be called via a meta-transaction.
     * It calls the internal `msgSender()` function and stores the result
     * in a public state variable `lastSender` so it can be asserted in a test.
     */
    function recordSender() public {
        lastSender = msgSender();
    }

    /**
     * @dev A payable function to test value transfers.
     * It's not strictly necessary for the vulnerability but can be a target
     * for a meta-transaction call.
     */
    function somePayableFunction() public payable {
        lastValue = msg.value;
        lastSender = msgSender();
    }
}
