// SPDX-License-Identifier: MIT
pragma solidity 0.8.4;

contract MockRCTreasury {
    address public marketAddress;
    mapping(address => uint256) public deposits;
    mapping(address => uint256) public totalBids;
    mapping(address => bool) public foreclosed;

    function setMarket(address _market) external {
        marketAddress = _market;
    }

    function minRentalDayDivisor() external pure returns (uint256) {
        return 24; // 1 hour
    }

    function payout(address _recipient, uint256 _amount) external returns (bool) {
        return true;
    }

    function sponsor(address _sponsor, uint256 _amount) external returns (bool) {
        return true;
    }
    
    function checkSponsorship(address, uint256) external {}

    function collectRentUser(address, uint256) external returns (uint256) {
        return 0; // 0 means not foreclosed
    }

    function isForeclosed(address _user) external view returns (bool) {
        return foreclosed[_user];
    }

    function userDeposit(address _user) external view returns (uint256) {
        return deposits[_user];
    }

    function userTotalBids(address _user) external view returns (uint256) {
        return totalBids[_user];
    }

    function updateLastRentalTime(address) external returns (bool) {
        return true;
    }

    function marketPaused(address) external view returns (bool) {
        return false;
    }

    function globalPause() external view returns (bool) {
        return false;
    }

    function refundUser(address, uint256) external {}
    function payRent(uint256) external {}

    // Test helpers
    function setUserDeposit(address _user, uint256 _amount) external {
        deposits[_user] = _amount;
    }

    function setUserTotalBids(address _user, uint256 _amount) external {
        totalBids[_user] = _amount;
    }
}
