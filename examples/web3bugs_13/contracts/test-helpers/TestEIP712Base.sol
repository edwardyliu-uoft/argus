// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.4;

import "@openzeppelin/contracts/proxy/utils/Initializable.sol";

// NOTE: This is a combined file to bypass a persistent import issue.
// Original contract: EIP712Base.sol

contract EIP712Base is Initializable {
    struct EIP712Domain {
        string name;
        string version;
        address verifyingContract;
        bytes32 salt;
    }

    bytes32 internal constant EIP712_DOMAIN_TYPEHASH =
        keccak256(
            bytes(
                "EIP712Domain(string name,string version,address verifyingContract,bytes32 salt)"
            )
        );
    bytes32 internal domainSeperator;

    function _initializeEIP712(string memory name, string memory version)
        internal
        initializer
    {
        _setDomainSeperator(name, version);
    }

    function _setDomainSeperator(string memory name, string memory version)
        internal
    {
        domainSeperator = keccak256(
            abi.encode(
                EIP712_DOMAIN_TYPEHASH,
                keccak256(bytes(name)),
                keccak256(bytes(version)),
                address(this),
                bytes32(getChainId())
            )
        );
    }

    function getDomainSeperator() public view returns (bytes32) {
        return domainSeperator;
    }

    function getChainId() public view returns (uint256) {
        return block.chainid;
    }

    function toTypedMessageHash(bytes32 messageHash)
        internal
        view
        returns (bytes32)
    {
        return
            keccak256(
                abi.encodePacked("\x19\x01", getDomainSeperator(), messageHash)
            );
    }
}


// @notice Test helper contract to expose internal functions of EIP712Base
contract TestEIP712Base is EIP712Base {
    // This function is intentionally left without the `initializer` modifier
    // so it can be called easily from the test setup.
    // The underlying _initializeEIP712 function still respects the modifier.
    function initialize(string memory name, string memory version) public {
        _initializeEIP712(name, version);
    }
}
