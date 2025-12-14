// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import "../interfaces/IRCMarket.sol";
import "../interfaces/IRCTreasury.sol";

contract MockRCMarket is IRCMarket {
    IRCTreasury private _treasury;

    constructor(address treasuryAddress) {
        _treasury = IRCTreasury(treasuryAddress);
    }

    // This is a helper for the test file to call the specific sponsor function needed
    function callSponsor(address sponsorAddress, uint256 amount) external {
        _treasury.sponsor(sponsorAddress, amount);
    }

    // --- Implemented stubs from IRCMarket ---
    function isMarket() external view override returns (bool) {
        return true;
    }

    function sponsor(address _sponsor, uint256 _amount) external override {
        // This function is required by the interface.
        // In a real scenario, it might call the treasury.
    }

    function sponsor(uint256 _amount) external override {
        // Overloaded version of the sponsor function.
    }

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

    function state() external view override returns (States) {
        return States.OPEN;
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
}
