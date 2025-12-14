// SPDX-License-Identifier: MIT
pragma solidity 0.8.4;

import "../RCMarket.sol";

contract MockRCOrderbook {
    address public marketAddress;
    mapping(address => mapping(uint256 => uint256)) public bids; // user => card => price

    function setMarket(address _market) external {
        marketAddress = _market;
    }

    function removeUserFromOrderbook(address) external returns (bool) {
        return false;
    }

    function removeOldBids(address) external {}

    function getBidValue(address _user, uint256 _card) external view returns (uint256) {
        return bids[_user][_card];
    }

    function addBidToOrderbook(address _user, uint256 _card, uint256 _price, uint256 _timeLimit, address) external {
        RCMarket market = RCMarket(marketAddress);
        address currentOwner = market.ownerOf(_card);
        
        // Simplified logic: if new price is highest, become owner
        if (_price > market.cardPrice(_card)) {
            market.transferCard(currentOwner, _user, _card, _price, _timeLimit);
        }
        bids[_user][_card] = _price;
    }

    function setTimeHeldlimit(address, uint256, uint256) external {}
    function findNewOwner(uint256, uint256) external {}
    function bidExists(address, address, uint256) external view returns (bool) { return false; }
    function removeBidFromOrderbook(address, uint256) external {}
    function closeMarket() external {}
}
