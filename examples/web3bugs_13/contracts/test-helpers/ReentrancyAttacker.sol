// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.4;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../interfaces/IRCTreasury.sol";
import "../interfaces/IRCOrderbook.sol";

contract ReentrancyAttacker is IRCTreasury {
    IRCOrderbook public orderbook;
    address public victim;
    uint256 public reentrancyCount = 0;
    bool public reenter = true;

    constructor(address _orderbook) {
        orderbook = IRCOrderbook(_orderbook);
    }

    function setVictim(address _victim) external {
        victim = _victim;
    }

    function setReenter(bool _reenter) external {
        reenter = _reenter;
    }

    // Malicious functions
    function decreaseBidRate(address _user, uint256) external override {
        if (reenter && msg.sender == address(orderbook) && _user == victim && reentrancyCount < 1) {
            reentrancyCount++;
            orderbook.removeUserFromOrderbook(victim);
        }
    }
    function isForeclosed(address _user) external view override returns (bool) {
        return _user == victim;
    }
    function resetUser(address) external override {}

    // Boilerplate IRCTreasury functions
    function setTokenAddress(address) external override {}
    function foreclosureTimeUser(address, uint256, uint256) external view override returns (uint256) { return type(uint256).max; }
    function refundUser(address, uint256) external override {}
    function bridgeAddress() external view override returns (address) { return address(0); }
    function factoryAddress() external view override returns (address) { return address(0); }
    function isMarket(address) external view override returns (bool) { return true; }
    function totalDeposits() external view override returns (uint256) { return 0; }
    function marketPot(address) external view override returns (uint256) { return 0; }
    function totalMarketPots() external view override returns (uint256) { return 0; }
    function minRentalDayDivisor() external view override returns (uint256) { return 1; }
    function maxContractBalance() external view override returns (uint256) { return 0; }
    function globalPause() external view override returns (bool) { return false; }
    function marketPaused(address) external view override returns (bool) { return false; }
    function uberOwner() external view override returns (address) { return address(0); }
    function addMarket(address) external override {}
    function setMinRental(uint256) external override {}
    function setMaxContractBalance(uint256) external override {}
    function setBridgeAddress(address) external override {}
    function changeGlobalPause() external override {}
    function changePauseMarket(address) external override {}
    function setFactoryAddress(address) external override {}
    function changeUberOwner(address) external override {}
    function erc20() external override returns (IERC20) { return IERC20(address(0)); }
    function deposit(uint256, address) external override returns (bool) { return true; }
    function withdrawDeposit(uint256, bool) external override {}
    function payRent(uint256) external override returns (bool) { return true; }
    function payout(address, uint256) external override returns (bool) { return true; }
    function sponsor(address, uint256) external override returns (bool) { return true; }
    function updateLastRentalTime(address) external override returns (bool) { return true; }
    function userTotalBids(address) external view override returns (uint256) { return 0; }
    function checkSponsorship(address, uint256) external view override {}
    function updateRentalRate(address, address, uint256, uint256, uint256) external override {}
    function increaseBidRate(address, uint256) external override {}
    function collectRentUser(address, uint256) external override returns (uint256) { return 0; }
    function userDeposit(address) external view override returns (uint256) { return 1 ether; }
    function topupMarketBalance(uint256) external override {}
    function toggleWhitelist() external override {}
    function addToWhitelist(address) external override {}
    function batchAddToWhitelist(address[] calldata) external override {}
}
