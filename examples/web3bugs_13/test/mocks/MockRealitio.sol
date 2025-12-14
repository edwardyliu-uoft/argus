// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.4;

import "../../contracts/interfaces/IRealitio.sol";

contract MockRealitio is IRealitio {
    function askQuestion(uint256, string memory, address, uint32, uint256) external override returns (bytes32) {
        return bytes32(0);
    }
    function askQuestionWithMinBond(uint256, string memory, address, uint32, uint256, uint256) external override returns (bytes32) {
        return bytes32(0);
    }
    function resultFor(bytes32) external view override returns (bytes32) {
        return bytes32(0);
    }
    function isFinalized(bytes32) external view override returns (bool) {
        return true;
    }
    function getContentHash(bytes32) external view override returns (bytes32) {
        return bytes32(0);
    }
}
