// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.4;

import "EIP712Base.sol";

// @notice This contract is a test helper to expose internal functions of EIP712Base
contract MockEIP712Base is EIP712Base {
    function initialize(string memory name, string memory version) public initializer {
        _initializeEIP712(name, version);
    }

    function setDomainSeparator(string memory name, string memory version) public {
        _setDomainSeperator(name, version);
    }

    function toTypedMessageHashPublic(bytes32 messageHash)
        public
        view
        returns (bytes32)
    {
        return toTypedMessageHash(messageHash);
    }
}
