// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.4;

import "../../contracts/interfaces/IRCOrderbook.sol";

contract MockRCOrderbook is IRCOrderbook {
    function addMarket(address, uint256, uint256) external override {}
    function newRental(uint256, uint256, address, address) external override {}
    function removeUserFromOrderbook(address) external override {}
    function setPrice(address, uint256, uint256) external override {}
    function rentalPrice(address, uint256) external view override returns (uint256) { return 0; }
    function changeUberOwner(address) external override {}
    function setFactoryAddress(address) external override {}
    function setLimits(uint256, uint256) external override {}
    function addBidToOrderbook(address, uint256, uint256) external override {}
    function removeBidFromOrderbook(address, uint256) external override {}
    function closeMarket() external override {}
    function findNewOwner(uint256, uint256) external override {}
    function getBidValue(address, uint256) external view override returns (uint256) { return 0; }
    function getTimeHeldlimit(address, uint256) external view override returns (uint256) { return 0; }
    function bidExists(address, uint256) external view override returns (bool) { return false; }
    function setTimeHeldlimit(address, uint256, uint256) external override {}
    function removeOldBids(address) external override {}
    function reduceTimeHeldLimit(address, uint256, uint256) external override {}
}
