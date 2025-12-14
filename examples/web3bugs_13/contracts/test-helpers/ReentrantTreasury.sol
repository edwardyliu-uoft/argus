// SPDX-License-Identifier: MIT
pragma solidity 0.8.4;

import "../RCMarket.sol";

contract ReentrantTreasury {
    IRCMarket public market;
    uint256 public callCount = 0;

    // Implement all other required functions from IRCTreasury to compile
    function setMarket(address _market) external {
        market = IRCMarket(_market);
    }

    function minRentalDayDivisor() external pure returns (uint256) { return 1; }
    function payout(address, uint256) external returns (bool) { return true; }
    function sponsor(address, uint256) external returns (bool) { return true; }
    function checkSponsorship(address, uint256) external {}

    function collectRentUser(address, uint256) external returns (uint256) {
        callCount++;
        // Re-enter lockMarket only on the first call to prevent infinite loop
        if (callCount == 1) {
            RCMarket(address(market)).lockMarket();
        }
        return 0; // Not foreclosed
    }

    function isForeclosed(address) external view returns (bool) { return false; }
    function userDeposit(address) external view returns (uint256) { return 1000 ether; } // Assume enough deposit
    function userTotalBids(address) external view returns (uint256) { return 1000 ether; }
    function updateLastRentalTime(address) external returns (bool) { return true; }
    function marketPaused(address) external view returns (bool) { return false; }
    function globalPause() external view returns (bool) { return false; }
    function refundUser(address, uint256) external {}
    function payRent(uint256) external {}
}
