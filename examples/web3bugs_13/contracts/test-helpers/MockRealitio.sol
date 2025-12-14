// SPDX-License-Identifier: MIT
pragma solidity 0.8.4;

contract MockRealitio {
    bytes32 public questionId;
    bool private finalized;
    bytes32 private outcome;

    function askQuestion(uint16, string calldata, address, uint32, uint32, uint8) external returns (bytes32) {
        questionId = keccak256(abi.encodePacked(block.timestamp));
        return questionId;
    }

    function isFinalized(bytes32) public view returns (bool) {
        return finalized;
    }

    function resultFor(bytes32) public view returns (bytes32) {
        return outcome;
    }

    function setFinalized(bool _finalized) external {
        finalized = _finalized;
    }

    function setOutcome(bytes32 _outcome) external {
        outcome = _outcome;
    }
}
