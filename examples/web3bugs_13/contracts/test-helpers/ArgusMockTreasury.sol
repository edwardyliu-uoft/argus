// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.4;

import "../interfaces/IRCTreasury.sol";

// Mock for the IRCTreasury interface for testing purposes
contract ArgusMockTreasury is IRCTreasury {
    mapping(address => bool) public isForeclosedMapping;
    mapping(address => uint256) public bidRates;
    uint256 public minRentalDivisor = 1;

    function setForeclosed(address user, bool foreclosed) external {
        isForeclosedMapping[user] = foreclosed;
    }

    function isForeclosed(address user) external view override returns (bool) {
        return isForeclosedMapping[user];
    }

    function increaseBidRate(address user, uint256 amount) external override {
        bidRates[user] += amount;
    }

    function decreaseBidRate(address user, uint256 amount) external override {
        bidRates[user] -= amount;
    }

    function updateRentalRate(
        address,
        address,
        uint256,
        uint256,
        uint256
    ) external override {
        // No-op for testing
    }



    function resetUser(address user) external override {
        isForeclosedMapping[user] = false;
    }

    function foreclosureTimeUser(
        address,
        uint256,
        uint256
    ) external view override returns (uint256) {
        // Return a very large number to prevent foreclosure during findNewOwner tests
        return type(uint256).max;
    }

    function minRentalDayDivisor() external view override returns (uint256) {
        return minRentalDivisor;
    }
}
