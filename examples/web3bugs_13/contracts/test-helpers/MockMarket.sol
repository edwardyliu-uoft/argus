// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.4;

import "../interfaces/IRCMarket.sol";

// This is a mock contract implementing the IRCMarket interface for testing purposes.
contract MockMarket is IRCMarket {
    States public currentState;

    constructor() {
        currentState = States.OPEN;
    }

    // Function required by the tests to control the market state
    function setState(States _newState) external {
        currentState = _newState;
    }

    // --- Implementation of IRCMarket interface ---

    function state() external view override returns (States) {
        return currentState;
    }

    function isMarket() external view override returns (bool) {
        return true;
    }

    function sponsor(address, uint256) external override {}

    function sponsor(uint256) external override {}

    function initialize(
        uint256,
        uint32[] calldata,
        uint256,
        uint256,
        address,
        address,
        address[] calldata,
        address,
        string calldata
    ) external override {}

    function tokenURI(uint256) external view override returns (string memory) {
        return "";
    }

    function ownerOf(uint256) external view override returns (address) {
        return address(0);
    }

    function collectRentAllCards() external override returns (bool) {
        return true;
    }

    function exitAll() external override {}

    function exit(uint256) external override {}

    function marketLockingTime() external override returns (uint32) {
        return 0;
    }

    function transferCard(
        address,
        address,
        uint256,
        uint256,
        uint256
    ) external override {}

    // --- Functions from other interfaces that RCMarket inherits ---
    // These were causing compilation errors in the previous attempt, so adding them here.
    // Based on the error messages, these seem to be required.

    function newRental(
        uint256,
        uint256,
        address
    ) external returns (bool) {
        return true;
    }

    function token() external view returns (address) {
        return address(0);
    }

    function treasury() external view returns (address) {
        return address(0);
    }

    function nftHub() external view returns (address) {
        return address(0);
    }

    function orderbook() external view returns (address) {
        return address(0);
    }

    function getCardPrices(uint256[] calldata)
        external
        view
        returns (uint256[] memory)
    {
        uint256[] memory prices = new uint256[](1);
        return prices;
    }

    function isForeclosed(address) external view returns (bool) {
        return false;
    }
}
